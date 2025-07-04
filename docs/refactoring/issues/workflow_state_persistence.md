# 13. Workflow State Persistence for LangGraph

## Priority: Critical

**Estimated Effort**: 3 days
**Python Version**: 3.10+
**Dependencies**: LangGraph, SQLModel, Redis (optional)

## Problem Statement

### Current Situation

LangGraph workflows for MCQ generation run entirely in memory without state persistence. If a workflow fails, crashes, or the system restarts, all progress is lost and the entire generation process must start from scratch.

### Why It's a Problem

- **No Recovery**: System crashes lose all workflow progress
- **Wasted Resources**: Completed work is discarded on failures
- **Poor User Experience**: Users must restart long-running tasks
- **No Debugging**: Cannot inspect failed workflow states
- **Limited Monitoring**: No visibility into workflow progress
- **Resource Inefficiency**: Cannot pause/resume expensive operations

### Affected Modules

- `app/services/mcq_generation.py` - LangGraph workflow implementation
- `app/api/routes/quiz.py` - Background task management
- All long-running workflow operations

### Technical Debt Assessment

- **Risk Level**: Critical - Data loss and poor reliability
- **Impact**: All AI-powered generation features
- **Cost of Delay**: Increases with workflow complexity

## Current Implementation Analysis

```python
# File: app/services/mcq_generation.py (current stateless implementation)
class MCQGenerationService:
    def __init__(self):
        self.workflow = self._build_workflow()

    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        """PROBLEM: Entire state exists only in memory."""

        initial_state: MCQGenerationState = {
            "quiz_id": str(quiz_id),
            "target_question_count": target_count,
            "model": model,
            "temperature": temperature,
            "content_chunks": [],
            "current_chunk_index": 0,
            "generated_questions": [],
            "questions_generated": 0,
            "error_message": None,
        }

        # PROBLEM: No persistence - crash loses everything
        result = await self.workflow.ainvoke(initial_state)

        # PROBLEM: No way to resume if this fails
        if result["error_message"]:
            logger.error("generation_failed", error=result["error_message"])
            return {"success": False, "error": result["error_message"]}

        return {"success": True, "questions": result["generated_questions"]}

    def should_continue_generation(self, state: MCQGenerationState) -> str:
        """PROBLEM: No checkpoint/recovery logic."""
        if state["error_message"] is not None:
            return "save_questions"  # Just stops, no recovery

        if state["questions_generated"] >= state["target_question_count"]:
            return "save_questions"

        return "generate_question"
```

### Current Failure Scenarios

```python
# Scenario 1: System crash during generation
# - Generated 45 out of 50 questions
# - System crashes or gets OOM killed
# - All 45 questions lost, must restart

# Scenario 2: Temporary API failure
# - OpenAI API has temporary outage
# - Workflow fails and exits
# - Cannot resume when API recovers

# Scenario 3: Long-running task timeout
# - Generation takes >10 minutes
# - Background task times out
# - No way to continue from last checkpoint
```

### Python Anti-patterns Identified

- **No State Persistence**: Everything in volatile memory
- **No Checkpointing**: Cannot save intermediate progress
- **No Recovery Mechanism**: Failures are terminal
- **Missing State History**: Cannot debug workflow issues
- **No Pause/Resume**: Cannot handle planned maintenance

## Proposed Solution

### Pythonic Approach

Implement workflow state persistence using a combination of database storage for checkpoints and optional Redis for real-time state updates, with automatic recovery capabilities.

### Design Patterns

- **Checkpoint Pattern**: Save state at key workflow nodes
- **Event Sourcing**: Track state transitions for debugging
- **Saga Pattern**: Compensating actions for failures
- **State Machine**: Explicit state management

### Code Examples

```python
# File: app/models.py (ADD new model)
from sqlalchemy import JSON
from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class WorkflowState(SQLModel, table=True):
    """Persistent workflow state storage."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workflow_id: str = Field(index=True)  # Unique workflow instance
    workflow_type: str = Field(index=True)  # e.g., "mcq_generation"
    quiz_id: uuid.UUID = Field(foreign_key="quiz.id", index=True)

    # State data
    current_node: str = Field(nullable=False)
    state_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    completed_at: datetime | None = Field(default=None)

    # Status tracking
    status: str = Field(index=True)  # running, paused, completed, failed
    error_message: str | None = Field(default=None)
    retry_count: int = Field(default=0)

    # Progress tracking
    total_steps: int | None = Field(default=None)
    completed_steps: int = Field(default=0)

    # Checkpointing
    last_checkpoint: datetime | None = Field(default=None)
    checkpoint_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

class WorkflowEvent(SQLModel, table=True):
    """Event log for workflow state transitions."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workflow_state_id: uuid.UUID = Field(foreign_key="workflowstate.id", index=True)
    event_type: str  # state_change, checkpoint, error, recovery
    event_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# File: app/services/workflow_persistence.py (NEW)
from typing import Optional, Dict, Any, Type, TypeVar
from sqlmodel import Session, select
from datetime import datetime, timedelta
import pickle
import json
from abc import ABC, abstractmethod

from app.core.db import engine
from app.models import WorkflowState, WorkflowEvent
from app.core.logging_config import get_logger

logger = get_logger("workflow_persistence")

T = TypeVar('T', bound=dict)

class WorkflowPersistenceManager(ABC):
    """Abstract base for workflow persistence strategies."""

    @abstractmethod
    async def save_state(
        self,
        workflow_id: str,
        state: Dict[str, Any],
        node: str
    ) -> None:
        """Save workflow state."""
        pass

    @abstractmethod
    async def load_state(
        self,
        workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load workflow state."""
        pass

    @abstractmethod
    async def delete_state(self, workflow_id: str) -> None:
        """Delete workflow state."""
        pass

class DatabasePersistenceManager(WorkflowPersistenceManager):
    """Database-based workflow persistence."""

    def __init__(self, session: Session):
        self.session = session

    async def save_state(
        self,
        workflow_id: str,
        state: Dict[str, Any],
        node: str,
        workflow_type: str = "mcq_generation"
    ) -> None:
        """Save workflow state to database."""

        # Find or create workflow state
        stmt = select(WorkflowState).where(
            WorkflowState.workflow_id == workflow_id
        )
        workflow_state = self.session.exec(stmt).first()

        if not workflow_state:
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                quiz_id=state.get("quiz_id"),
                current_node=node,
                state_data=state,
                status="running",
                total_steps=state.get("target_question_count", 0),
                completed_steps=state.get("questions_generated", 0)
            )
            self.session.add(workflow_state)
        else:
            workflow_state.current_node = node
            workflow_state.state_data = state
            workflow_state.updated_at = datetime.utcnow()
            workflow_state.completed_steps = state.get("questions_generated", 0)

        # Create checkpoint if significant progress
        if self._should_checkpoint(workflow_state):
            workflow_state.last_checkpoint = datetime.utcnow()
            workflow_state.checkpoint_data = state.copy()

            # Log checkpoint event
            event = WorkflowEvent(
                workflow_state_id=workflow_state.id,
                event_type="checkpoint",
                event_data={
                    "node": node,
                    "progress": workflow_state.completed_steps,
                    "total": workflow_state.total_steps
                }
            )
            self.session.add(event)

        self.session.commit()

        logger.info(
            "workflow_state_saved",
            workflow_id=workflow_id,
            node=node,
            progress=f"{workflow_state.completed_steps}/{workflow_state.total_steps}"
        )

    async def load_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow state from database."""

        stmt = select(WorkflowState).where(
            WorkflowState.workflow_id == workflow_id,
            WorkflowState.status.in_(["running", "paused"])
        )
        workflow_state = self.session.exec(stmt).first()

        if not workflow_state:
            return None

        logger.info(
            "workflow_state_loaded",
            workflow_id=workflow_id,
            node=workflow_state.current_node,
            status=workflow_state.status
        )

        return workflow_state.state_data

    async def mark_completed(
        self,
        workflow_id: str,
        final_state: Dict[str, Any]
    ) -> None:
        """Mark workflow as completed."""

        stmt = select(WorkflowState).where(
            WorkflowState.workflow_id == workflow_id
        )
        workflow_state = self.session.exec(stmt).first()

        if workflow_state:
            workflow_state.status = "completed"
            workflow_state.completed_at = datetime.utcnow()
            workflow_state.state_data = final_state

            event = WorkflowEvent(
                workflow_state_id=workflow_state.id,
                event_type="completed",
                event_data={"final_questions": len(final_state.get("generated_questions", []))}
            )
            self.session.add(event)
            self.session.commit()

    async def mark_failed(
        self,
        workflow_id: str,
        error: str,
        state: Dict[str, Any]
    ) -> None:
        """Mark workflow as failed."""

        stmt = select(WorkflowState).where(
            WorkflowState.workflow_id == workflow_id
        )
        workflow_state = self.session.exec(stmt).first()

        if workflow_state:
            workflow_state.status = "failed"
            workflow_state.error_message = error
            workflow_state.state_data = state

            event = WorkflowEvent(
                workflow_state_id=workflow_state.id,
                event_type="error",
                event_data={"error": error, "node": state.get("current_node")}
            )
            self.session.add(event)
            self.session.commit()

    def _should_checkpoint(self, workflow_state: WorkflowState) -> bool:
        """Determine if checkpoint should be created."""

        # Checkpoint every 5 questions or 5 minutes
        if not workflow_state.last_checkpoint:
            return True

        time_since_checkpoint = datetime.utcnow() - workflow_state.last_checkpoint
        steps_since_checkpoint = (
            workflow_state.completed_steps -
            len(workflow_state.checkpoint_data.get("generated_questions", []))
        )

        return (
            time_since_checkpoint > timedelta(minutes=5) or
            steps_since_checkpoint >= 5
        )

    async def list_resumable_workflows(
        self,
        quiz_id: Optional[uuid.UUID] = None
    ) -> list[WorkflowState]:
        """List workflows that can be resumed."""

        stmt = select(WorkflowState).where(
            WorkflowState.status.in_(["running", "paused", "failed"])
        )

        if quiz_id:
            stmt = stmt.where(WorkflowState.quiz_id == quiz_id)

        return list(self.session.exec(stmt).all())

# File: app/services/mcq_generation.py (UPDATED with persistence)
from app.services.workflow_persistence import DatabasePersistenceManager
from langgraph.checkpoint import Checkpoint

class PersistentMCQGenerationService(MCQGenerationService):
    """MCQ generation with state persistence."""

    def __init__(self):
        super().__init__()
        self.checkpointer = self._create_checkpointer()

    def _create_checkpointer(self) -> Checkpoint:
        """Create LangGraph checkpointer with custom persistence."""

        class DBCheckpointer(Checkpoint):
            """Custom checkpointer using our persistence layer."""

            async def save(self, config: dict, state: dict) -> None:
                """Save checkpoint."""
                workflow_id = config.get("configurable", {}).get("thread_id")
                if workflow_id:
                    with Session(engine) as session:
                        manager = DatabasePersistenceManager(session)
                        await manager.save_state(
                            workflow_id,
                            state,
                            state.get("current_node", "unknown")
                        )

            async def load(self, config: dict) -> Optional[dict]:
                """Load checkpoint."""
                workflow_id = config.get("configurable", {}).get("thread_id")
                if workflow_id:
                    with Session(engine) as session:
                        manager = DatabasePersistenceManager(session)
                        return await manager.load_state(workflow_id)
                return None

        return DBCheckpointer()

    def _build_workflow(self):
        """Build workflow with persistence hooks."""
        workflow = super()._build_workflow()

        # Add checkpointer to workflow
        workflow = workflow.with_config(
            checkpointer=self.checkpointer
        )

        # Wrap nodes with persistence
        original_nodes = workflow.nodes.copy()

        for node_name, node_func in original_nodes.items():
            workflow.nodes[node_name] = self._wrap_node_with_persistence(
                node_name, node_func
            )

        return workflow

    def _wrap_node_with_persistence(self, node_name: str, node_func):
        """Wrap node function with persistence logic."""

        async def wrapped_node(state: MCQGenerationState) -> MCQGenerationState:
            # Save state before node execution
            workflow_id = state.get("workflow_id", str(state["quiz_id"]))

            with Session(engine) as session:
                manager = DatabasePersistenceManager(session)
                await manager.save_state(
                    workflow_id,
                    state,
                    node_name
                )

            try:
                # Execute original node
                result = await node_func(state)

                # Save state after successful execution
                with Session(engine) as session:
                    manager = DatabasePersistenceManager(session)
                    await manager.save_state(
                        workflow_id,
                        result,
                        f"{node_name}_completed"
                    )

                return result

            except Exception as e:
                # Save error state
                with Session(engine) as session:
                    manager = DatabasePersistenceManager(session)
                    await manager.mark_failed(
                        workflow_id,
                        str(e),
                        state
                    )
                raise

        return wrapped_node

    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float,
        resume_workflow_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Generate MCQs with persistence and recovery."""

        workflow_id = resume_workflow_id or f"mcq_{quiz_id}_{datetime.utcnow().timestamp()}"

        # Check for resumable state
        initial_state = None
        if resume_workflow_id:
            with Session(engine) as session:
                manager = DatabasePersistenceManager(session)
                initial_state = await manager.load_state(resume_workflow_id)

                if initial_state:
                    logger.info(
                        "resuming_workflow",
                        workflow_id=resume_workflow_id,
                        progress=f"{initial_state.get('questions_generated', 0)}/{target_count}"
                    )

        if not initial_state:
            # Create new initial state
            initial_state = {
                "workflow_id": workflow_id,
                "quiz_id": str(quiz_id),
                "target_question_count": target_count,
                "model": model,
                "temperature": temperature,
                "content_chunks": [],
                "current_chunk_index": 0,
                "generated_questions": [],
                "questions_generated": 0,
                "error_message": None,
            }

        # Configure workflow with thread ID for checkpointing
        config = {"configurable": {"thread_id": workflow_id}}

        try:
            # Run workflow with checkpointing
            result = await self.workflow.ainvoke(initial_state, config)

            # Mark as completed
            with Session(engine) as session:
                manager = DatabasePersistenceManager(session)
                await manager.mark_completed(workflow_id, result)

            return {
                "success": True,
                "workflow_id": workflow_id,
                "questions": result["generated_questions"],
                "total_generated": result["questions_generated"]
            }

        except Exception as e:
            logger.error(
                "workflow_failed",
                workflow_id=workflow_id,
                error=str(e),
                exc_info=True
            )

            return {
                "success": False,
                "workflow_id": workflow_id,
                "error": str(e),
                "resumable": True
            }

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """Get current workflow status."""

        with Session(engine) as session:
            stmt = select(WorkflowState).where(
                WorkflowState.workflow_id == workflow_id
            )
            workflow_state = session.exec(stmt).first()

            if not workflow_state:
                return {"status": "not_found"}

            return {
                "status": workflow_state.status,
                "progress": {
                    "completed": workflow_state.completed_steps,
                    "total": workflow_state.total_steps,
                    "percentage": (
                        workflow_state.completed_steps / workflow_state.total_steps * 100
                        if workflow_state.total_steps > 0 else 0
                    )
                },
                "current_node": workflow_state.current_node,
                "error": workflow_state.error_message,
                "created_at": workflow_state.created_at,
                "updated_at": workflow_state.updated_at,
                "can_resume": workflow_state.status in ["running", "paused", "failed"]
            }

# File: app/api/routes/quiz.py (UPDATED endpoints)
from app.services.mcq_generation import PersistentMCQGenerationService

# Use persistent service
mcq_service = PersistentMCQGenerationService()

@router.post("/{quiz_id}/generate-questions")
async def generate_questions_endpoint(
    quiz_id: UUID,
    generation_request: MCQGenerationRequest,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Generate questions with workflow persistence."""

    # Check for existing workflows
    workflow_states = await list_resumable_workflows(session, quiz_id)

    if workflow_states and generation_request.resume_existing:
        # Resume most recent workflow
        workflow_id = workflow_states[0].workflow_id

        background_tasks.add_task(
            generate_questions_for_quiz_with_resume,
            quiz_id,
            generation_request.target_question_count,
            generation_request.model,
            generation_request.temperature,
            workflow_id
        )

        return {
            "message": "Resuming question generation",
            "workflow_id": workflow_id
        }
    else:
        # Start new workflow
        workflow_id = f"mcq_{quiz_id}_{datetime.utcnow().timestamp()}"

        background_tasks.add_task(
            generate_questions_for_quiz_persistent,
            quiz_id,
            generation_request.target_question_count,
            generation_request.model,
            generation_request.temperature,
            workflow_id
        )

        return {
            "message": "Question generation started",
            "workflow_id": workflow_id
        }

@router.get("/{quiz_id}/generation-status")
async def get_generation_status(
    quiz_id: UUID,
    workflow_id: Optional[str] = Query(None),
    current_user: CurrentUser,
    session: SessionDep,
) -> dict[str, Any]:
    """Get status of question generation workflow."""

    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if workflow_id:
        # Get specific workflow status
        status = await mcq_service.get_workflow_status(workflow_id)
    else:
        # Get all workflows for quiz
        workflows = await list_resumable_workflows(session, quiz_id)
        status = {
            "workflows": [
                {
                    "workflow_id": w.workflow_id,
                    "status": w.status,
                    "progress": f"{w.completed_steps}/{w.total_steps}",
                    "created_at": w.created_at,
                    "can_resume": w.status in ["running", "paused", "failed"]
                }
                for w in workflows
            ]
        }

    return status

@router.post("/{quiz_id}/resume-generation")
async def resume_generation(
    quiz_id: UUID,
    workflow_id: str,
    current_user: CurrentUser,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Resume a failed or paused workflow."""

    # Verify ownership and workflow exists
    workflow_state = session.exec(
        select(WorkflowState).where(
            WorkflowState.workflow_id == workflow_id,
            WorkflowState.quiz_id == quiz_id
        )
    ).first()

    if not workflow_state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow_state.status not in ["running", "paused", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume workflow in {workflow_state.status} state"
        )

    # Resume workflow
    background_tasks.add_task(
        resume_workflow_task,
        workflow_id,
        workflow_state.state_data
    )

    return {
        "message": "Workflow resumed",
        "workflow_id": workflow_id
    }
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── models.py                    # ADD: WorkflowState, WorkflowEvent
│   ├── services/
│   │   ├── workflow_persistence.py  # NEW: Persistence managers
│   │   └── mcq_generation.py        # UPDATE: Add persistence
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: New endpoints
│   ├── alembic/
│   │   └── versions/
│   │       └── xxx_workflow_state.py # NEW: Migration
│   └── tests/
│       └── services/
│           └── test_workflow_persistence.py # NEW: Tests
```

### Database Migration

```python
# File: alembic/versions/xxx_add_workflow_state.py
"""Add workflow state tables

Revision ID: xxx
Revises: yyy
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

def upgrade():
    # WorkflowState table
    op.create_table(
        'workflowstate',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('workflow_type', sa.String(), nullable=False),
        sa.Column('quiz_id', sa.UUID(), nullable=False),
        sa.Column('current_node', sa.String(), nullable=False),
        sa.Column('state_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('completed_steps', sa.Integer(), nullable=False),
        sa.Column('last_checkpoint', sa.DateTime(), nullable=True),
        sa.Column('checkpoint_data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quiz.id'], ),
    )
    op.create_index('ix_workflowstate_workflow_id', 'workflowstate', ['workflow_id'])
    op.create_index('ix_workflowstate_workflow_type', 'workflowstate', ['workflow_type'])
    op.create_index('ix_workflowstate_quiz_id', 'workflowstate', ['quiz_id'])
    op.create_index('ix_workflowstate_status', 'workflowstate', ['status'])

    # WorkflowEvent table
    op.create_table(
        'workflowevent',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_state_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_state_id'], ['workflowstate.id'], ),
    )
    op.create_index('ix_workflowevent_workflow_state_id', 'workflowevent', ['workflow_state_id'])

def downgrade():
    op.drop_index('ix_workflowevent_workflow_state_id')
    op.drop_table('workflowevent')
    op.drop_index('ix_workflowstate_status')
    op.drop_index('ix_workflowstate_quiz_id')
    op.drop_index('ix_workflowstate_workflow_type')
    op.drop_index('ix_workflowstate_workflow_id')
    op.drop_table('workflowstate')
```

### Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Workflow persistence settings
    WORKFLOW_CHECKPOINT_INTERVAL: int = 5  # Questions between checkpoints
    WORKFLOW_CHECKPOINT_TIMEOUT: int = 300  # Seconds between checkpoints
    WORKFLOW_MAX_RETRIES: int = 3
    ENABLE_WORKFLOW_PERSISTENCE: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/services/test_workflow_persistence.py
import pytest
from app.services.workflow_persistence import DatabasePersistenceManager
from app.models import WorkflowState, WorkflowEvent

@pytest.mark.asyncio
async def test_save_and_load_workflow_state(session):
    """Test basic save and load operations."""

    manager = DatabasePersistenceManager(session)

    # Save state
    state = {
        "quiz_id": "test-quiz-123",
        "questions_generated": 5,
        "target_question_count": 10,
        "generated_questions": ["q1", "q2", "q3", "q4", "q5"]
    }

    await manager.save_state("workflow-123", state, "generate_question")

    # Load state
    loaded_state = await manager.load_state("workflow-123")

    assert loaded_state is not None
    assert loaded_state["questions_generated"] == 5
    assert len(loaded_state["generated_questions"]) == 5

@pytest.mark.asyncio
async def test_checkpoint_creation(session):
    """Test checkpoint creation logic."""

    manager = DatabasePersistenceManager(session)

    # Create initial state
    initial_state = {
        "quiz_id": "test-quiz-123",
        "questions_generated": 0,
        "target_question_count": 20,
        "generated_questions": []
    }

    await manager.save_state("workflow-456", initial_state, "start")

    # Add questions incrementally
    for i in range(1, 11):
        state = initial_state.copy()
        state["questions_generated"] = i
        state["generated_questions"] = [f"q{j}" for j in range(1, i+1)]

        await manager.save_state("workflow-456", state, "generate_question")

    # Check checkpoints were created
    workflow_state = session.exec(
        select(WorkflowState).where(WorkflowState.workflow_id == "workflow-456")
    ).first()

    assert workflow_state.last_checkpoint is not None
    assert len(workflow_state.checkpoint_data["generated_questions"]) >= 5

@pytest.mark.asyncio
async def test_workflow_recovery(session, test_quiz):
    """Test workflow recovery after failure."""

    service = PersistentMCQGenerationService()

    # Start generation
    result = await service.generate_mcqs_for_quiz(
        test_quiz.id,
        target_count=10,
        model="gpt-4",
        temperature=0.7
    )

    workflow_id = result["workflow_id"]

    # Simulate failure by marking as failed
    manager = DatabasePersistenceManager(session)
    await manager.mark_failed(
        workflow_id,
        "Simulated failure",
        {"questions_generated": 5}
    )

    # Resume workflow
    resume_result = await service.generate_mcqs_for_quiz(
        test_quiz.id,
        target_count=10,
        model="gpt-4",
        temperature=0.7,
        resume_workflow_id=workflow_id
    )

    assert resume_result["success"] is True
    assert resume_result["workflow_id"] == workflow_id

@pytest.mark.asyncio
async def test_concurrent_workflow_isolation(session, test_quiz):
    """Test that concurrent workflows don't interfere."""

    manager = DatabasePersistenceManager(session)

    # Create two workflows for same quiz
    state1 = {"quiz_id": str(test_quiz.id), "questions_generated": 5}
    state2 = {"quiz_id": str(test_quiz.id), "questions_generated": 10}

    await manager.save_state("workflow-A", state1, "node1")
    await manager.save_state("workflow-B", state2, "node2")

    # Load states
    loaded1 = await manager.load_state("workflow-A")
    loaded2 = await manager.load_state("workflow-B")

    assert loaded1["questions_generated"] == 5
    assert loaded2["questions_generated"] == 10
```

### Integration Tests

```python
# File: app/tests/integration/test_workflow_persistence_integration.py
@pytest.mark.asyncio
async def test_full_workflow_with_persistence(client, test_user, test_quiz):
    """Test complete workflow with persistence."""

    # Start generation
    response = client.post(
        f"/api/quiz/{test_quiz.id}/generate-questions",
        json={
            "target_question_count": 20,
            "model": "gpt-4",
            "temperature": 0.7
        },
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    assert response.status_code == 200
    workflow_id = response.json()["workflow_id"]

    # Check status
    status_response = client.get(
        f"/api/quiz/{test_quiz.id}/generation-status?workflow_id={workflow_id}",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    status = status_response.json()
    assert status["status"] in ["running", "completed"]
    assert "progress" in status
```

## Code Quality Improvements

### Monitoring and Observability

```python
# Add workflow metrics
from prometheus_client import Counter, Histogram, Gauge

workflow_started = Counter(
    'workflow_started_total',
    'Total workflows started',
    ['workflow_type']
)

workflow_completed = Counter(
    'workflow_completed_total',
    'Total workflows completed',
    ['workflow_type']
)

workflow_failed = Counter(
    'workflow_failed_total',
    'Total workflows failed',
    ['workflow_type']
)

workflow_resumed = Counter(
    'workflow_resumed_total',
    'Total workflows resumed',
    ['workflow_type']
)

workflow_duration = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration',
    ['workflow_type']
)

active_workflows = Gauge(
    'active_workflows',
    'Currently active workflows',
    ['workflow_type']
)
```

## Migration Strategy

### Phase 1: Add Infrastructure
1. Create database tables
2. Implement persistence managers
3. Add monitoring

### Phase 2: Update Service
1. Wrap existing workflow with persistence
2. Add recovery logic
3. Test with feature flag

### Phase 3: Update API
1. Add new endpoints
2. Update UI to show progress
3. Enable resume functionality

### Rollback Plan

```python
# Feature flag for persistence
if settings.ENABLE_WORKFLOW_PERSISTENCE:
    service = PersistentMCQGenerationService()
else:
    service = MCQGenerationService()  # Original stateless
```

## Success Criteria

### Reliability Metrics

- **Recovery Rate**: 95%+ of failed workflows resumable
- **Data Loss**: 0% question loss on system failures
- **Checkpoint Overhead**: <5% performance impact
- **Resume Success**: 90%+ successful resumptions

### Performance Metrics

- **Checkpoint Time**: <100ms per checkpoint
- **State Load Time**: <200ms to resume workflow
- **Storage Growth**: <1MB per workflow average

### Monitoring Queries

```sql
-- Active workflows
SELECT
    workflow_type,
    status,
    COUNT(*) as count,
    AVG(completed_steps::float / NULLIF(total_steps, 0)) as avg_progress
FROM workflowstate
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY workflow_type, status;

-- Recovery effectiveness
SELECT
    COUNT(*) FILTER (WHERE retry_count > 0) as recovered_workflows,
    COUNT(*) as total_workflows,
    COUNT(*) FILTER (WHERE retry_count > 0)::float / COUNT(*) as recovery_rate
FROM workflowstate
WHERE status = 'completed';
```

---
