# Business Metrics Implementation Guide

This guide provides examples and patterns for implementing business-specific metrics and logging for the Rag@UiT application. These metrics will help track user behavior, application performance, and business KPIs.

## Overview

Business metrics go beyond technical application metrics to track:
- User engagement and behavior
- Feature usage and effectiveness
- Business process success rates
- Canvas integration health
- Quiz generation performance

## Implementation Patterns

### 1. User Activity Metrics

Track user interactions and engagement patterns to understand how users utilize the application.

#### Example Implementation

```python
# backend/app/core/metrics/user_metrics.py
from app.core.logging_config import get_logger
from datetime import datetime, timezone
from typing import Optional

logger = get_logger("metrics.user")

class UserMetrics:
    """Track user activity and engagement metrics"""

    @staticmethod
    def log_user_login(user_id: str, canvas_id: int, login_method: str = "canvas_oauth"):
        """Log user login events"""
        logger.info(
            "user_login",
            user_id=user_id,
            canvas_id=canvas_id,
            login_method=login_method,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_user_session_duration(user_id: str, session_start: datetime, session_end: datetime):
        """Log user session duration"""
        duration_minutes = (session_end - session_start).total_seconds() / 60
        logger.info(
            "user_session_completed",
            user_id=user_id,
            session_duration_minutes=round(duration_minutes, 2),
            session_start=session_start.isoformat(),
            session_end=session_end.isoformat()
        )

    @staticmethod
    def log_feature_usage(user_id: str, feature_name: str, action: str, metadata: dict = None):
        """Log when users interact with specific features"""
        logger.info(
            "feature_usage",
            user_id=user_id,
            feature=feature_name,
            action=action,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# Usage in route handlers:
from app.core.metrics.user_metrics import UserMetrics

@router.get("/dashboard")
async def get_dashboard(current_user: CurrentUser):
    UserMetrics.log_feature_usage(
        user_id=str(current_user.id),
        feature="dashboard",
        action="view"
    )
    # ... rest of handler
```

### 2. Canvas Integration Metrics

Track the health and performance of Canvas API integrations.

#### Example Implementation

```python
# backend/app/core/metrics/canvas_metrics.py
from app.core.logging_config import get_logger
import time
from typing import Optional

logger = get_logger("metrics.canvas")

class CanvasMetrics:
    """Track Canvas API integration metrics"""

    @staticmethod
    def log_api_call(
        user_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Log Canvas API call metrics"""
        logger.info(
            "canvas_api_call",
            user_id=user_id,
            canvas_endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            success=success,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_token_refresh(user_id: str, canvas_id: int, success: bool, error: Optional[str] = None):
        """Log Canvas token refresh events"""
        logger.info(
            "canvas_token_refresh",
            user_id=user_id,
            canvas_id=canvas_id,
            success=success,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_course_sync(user_id: str, canvas_id: int, courses_count: int, sync_duration_ms: float):
        """Log Canvas course synchronization"""
        logger.info(
            "canvas_course_sync",
            user_id=user_id,
            canvas_id=canvas_id,
            courses_synced=courses_count,
            sync_duration_ms=round(sync_duration_ms, 2),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# Context manager for API call tracking
class CanvasAPICallTracker:
    def __init__(self, user_id: str, endpoint: str, method: str):
        self.user_id = user_id
        self.endpoint = endpoint
        self.method = method
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        status_code = getattr(exc_val, 'status_code', 200) if exc_val else 200

        CanvasMetrics.log_api_call(
            user_id=self.user_id,
            endpoint=self.endpoint,
            method=self.method,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error=error
        )

# Usage example:
async def fetch_canvas_courses(user_id: str, access_token: str):
    with CanvasAPICallTracker(user_id, "/api/v1/courses", "GET"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.CANVAS_BASE_URL}/api/v1/courses",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
```

### 3. Quiz Generation Metrics

Track the performance and success rates of AI-powered quiz generation.

#### Example Implementation

```python
# backend/app/core/metrics/quiz_metrics.py
from app.core.logging_config import get_logger
from enum import Enum
from typing import List, Optional

logger = get_logger("metrics.quiz")

class QuestionDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class QuizMetrics:
    """Track quiz and question generation metrics"""

    @staticmethod
    def log_quiz_generation_started(
        user_id: str,
        canvas_course_id: int,
        content_type: str,  # "module", "page", "assignment", etc.
        content_id: str,
        requested_questions: int
    ):
        """Log when quiz generation begins"""
        logger.info(
            "quiz_generation_started",
            user_id=user_id,
            canvas_course_id=canvas_course_id,
            content_type=content_type,
            content_id=content_id,
            requested_questions=requested_questions,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_quiz_generation_completed(
        user_id: str,
        canvas_course_id: int,
        content_id: str,
        questions_generated: int,
        generation_duration_seconds: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Log quiz generation completion"""
        logger.info(
            "quiz_generation_completed",
            user_id=user_id,
            canvas_course_id=canvas_course_id,
            content_id=content_id,
            questions_generated=questions_generated,
            generation_duration_seconds=round(generation_duration_seconds, 2),
            success=success,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_question_quality_feedback(
        user_id: str,
        question_id: str,
        rating: int,  # 1-5 scale
        feedback_text: Optional[str] = None
    ):
        """Log user feedback on question quality"""
        logger.info(
            "question_quality_feedback",
            user_id=user_id,
            question_id=question_id,
            rating=rating,
            feedback_text=feedback_text,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_quiz_export_to_canvas(
        user_id: str,
        canvas_course_id: int,
        quiz_id: str,
        questions_count: int,
        export_success: bool,
        canvas_quiz_id: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Log quiz export to Canvas"""
        logger.info(
            "quiz_exported_to_canvas",
            user_id=user_id,
            canvas_course_id=canvas_course_id,
            quiz_id=quiz_id,
            questions_count=questions_count,
            export_success=export_success,
            canvas_quiz_id=canvas_quiz_id,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# Context manager for quiz generation tracking
class QuizGenerationTracker:
    def __init__(self, user_id: str, canvas_course_id: int, content_id: str, requested_questions: int):
        self.user_id = user_id
        self.canvas_course_id = canvas_course_id
        self.content_id = content_id
        self.requested_questions = requested_questions
        self.start_time = None
        self.questions_generated = 0

    def __enter__(self):
        self.start_time = time.time()
        QuizMetrics.log_quiz_generation_started(
            self.user_id,
            self.canvas_course_id,
            "module",  # or determine dynamically
            self.content_id,
            self.requested_questions
        )
        return self

    def set_questions_generated(self, count: int):
        self.questions_generated = count

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        error = str(exc_val) if exc_val else None

        QuizMetrics.log_quiz_generation_completed(
            self.user_id,
            self.canvas_course_id,
            self.content_id,
            self.questions_generated,
            duration,
            success,
            error
        )

# Usage example:
async def generate_quiz_from_content(user_id: str, canvas_course_id: int, content_id: str):
    with QuizGenerationTracker(user_id, canvas_course_id, content_id, 10) as tracker:
        # AI generation logic here
        questions = await ai_service.generate_questions(content)
        tracker.set_questions_generated(len(questions))
        return questions
```

### 4. Performance Metrics

Track application performance from a business perspective.

#### Example Implementation

```python
# backend/app/core/metrics/performance_metrics.py
from app.core.logging_config import get_logger
import psutil
import time

logger = get_logger("metrics.performance")

class PerformanceMetrics:
    """Track application performance metrics"""

    @staticmethod
    def log_database_query_performance(
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: int = 0,
        user_id: Optional[str] = None
    ):
        """Log database query performance"""
        logger.info(
            "database_query_performance",
            operation=operation,
            table=table,
            duration_ms=round(duration_ms, 2),
            rows_affected=rows_affected,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_memory_usage():
        """Log current memory usage"""
        memory = psutil.virtual_memory()
        logger.info(
            "memory_usage",
            total_gb=round(memory.total / (1024**3), 2),
            available_gb=round(memory.available / (1024**3), 2),
            percent_used=memory.percent,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_ai_model_performance(
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        processing_time_seconds: float,
        user_id: Optional[str] = None
    ):
        """Log AI model performance metrics"""
        logger.info(
            "ai_model_performance",
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            processing_time_seconds=round(processing_time_seconds, 2),
            tokens_per_second=round((input_tokens + output_tokens) / processing_time_seconds, 2),
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# Database query tracker decorator
def track_db_query(operation: str, table: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                rows_affected = getattr(result, 'rowcount', 0) if hasattr(result, 'rowcount') else 1

                PerformanceMetrics.log_database_query_performance(
                    operation=operation,
                    table=table,
                    duration_ms=duration_ms,
                    rows_affected=rows_affected
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                PerformanceMetrics.log_database_query_performance(
                    operation=operation,
                    table=table,
                    duration_ms=duration_ms,
                    rows_affected=0
                )
                raise
        return wrapper
    return decorator

# Usage example:
@track_db_query("SELECT", "users")
async def get_user_by_canvas_id(session: Session, canvas_id: int):
    return session.exec(select(User).where(User.canvas_id == canvas_id)).first()
```

### 5. Business KPI Metrics

Track key business indicators and goals.

#### Example Implementation

```python
# backend/app/core/metrics/business_metrics.py
from app.core.logging_config import get_logger

logger = get_logger("metrics.business")

class BusinessMetrics:
    """Track business KPIs and goals"""

    @staticmethod
    def log_user_onboarding_step(
        user_id: str,
        step: str,
        completed: bool,
        time_to_complete_seconds: Optional[float] = None
    ):
        """Track user onboarding progress"""
        logger.info(
            "user_onboarding_step",
            user_id=user_id,
            step=step,
            completed=completed,
            time_to_complete_seconds=time_to_complete_seconds,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_feature_adoption(
        feature_name: str,
        user_id: str,
        is_first_use: bool,
        success: bool
    ):
        """Track feature adoption rates"""
        logger.info(
            "feature_adoption",
            feature=feature_name,
            user_id=user_id,
            first_use=is_first_use,
            success=success,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_user_retention(
        user_id: str,
        days_since_registration: int,
        total_sessions: int,
        last_active_date: datetime
    ):
        """Track user retention metrics"""
        logger.info(
            "user_retention",
            user_id=user_id,
            days_since_registration=days_since_registration,
            total_sessions=total_sessions,
            last_active=last_active_date.isoformat(),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @staticmethod
    def log_error_impact(
        error_type: str,
        affected_users: int,
        affected_features: List[str],
        resolution_time_minutes: Optional[float] = None
    ):
        """Track business impact of errors"""
        logger.info(
            "error_business_impact",
            error_type=error_type,
            affected_users=affected_users,
            affected_features=affected_features,
            resolution_time_minutes=resolution_time_minutes,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

## Integration with Grafana Dashboards

### Business Metrics Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Rag@UiT Business Metrics",
    "panels": [
      {
        "title": "Daily Active Users",
        "targets": [
          {
            "expr": "count by (user_id) (count_over_time({container_name=~\".*backend.*\"} | json | event=\"user_login\" [1d]))"
          }
        ]
      },
      {
        "title": "Quiz Generation Success Rate",
        "targets": [
          {
            "expr": "sum(rate({container_name=~\".*backend.*\"} | json | event=\"quiz_generation_completed\" | success=\"true\" [1h])) / sum(rate({container_name=~\".*backend.*\"} | json | event=\"quiz_generation_completed\" [1h])) * 100"
          }
        ]
      },
      {
        "title": "Average Quiz Generation Time",
        "targets": [
          {
            "expr": "avg_over_time({container_name=~\".*backend.*\"} | json | event=\"quiz_generation_completed\" | unwrap generation_duration_seconds [1h])"
          }
        ]
      },
      {
        "title": "Canvas API Error Rate",
        "targets": [
          {
            "expr": "sum(rate({container_name=~\".*backend.*\"} | json | event=\"canvas_api_call\" | success=\"false\" [5m])) / sum(rate({container_name=~\".*backend.*\"} | json | event=\"canvas_api_call\" [5m])) * 100"
          }
        ]
      }
    ]
  }
}
```

## Implementation Checklist

When implementing business metrics:

### 1. Planning Phase
- [ ] Identify key business processes to track
- [ ] Define success criteria for each process
- [ ] Plan metric collection points in user journeys
- [ ] Design dashboard layouts for stakeholders

### 2. Implementation Phase
- [ ] Create metric classes for each business domain
- [ ] Add metric collection to relevant route handlers
- [ ] Implement context managers for complex processes
- [ ] Add database query performance tracking

### 3. Monitoring Phase
- [ ] Create Grafana dashboards for business metrics
- [ ] Set up alerts for critical business events
- [ ] Configure metric retention policies
- [ ] Train team on reading business metrics

### 4. Analysis Phase
- [ ] Regular review of business metric trends
- [ ] Correlation analysis between technical and business metrics
- [ ] User behavior analysis from metrics
- [ ] Performance optimization based on metrics

## Best Practices

1. **Consistent Event Naming**: Use a clear naming convention like `domain_action_status`
2. **Structured Data**: Always use structured logging with consistent field names
3. **Privacy Compliance**: Ensure no PII is logged in metrics
4. **Performance Impact**: Minimize performance impact of metric collection
5. **Retention Policies**: Set appropriate retention for different metric types
6. **Documentation**: Document all business events and their meanings

## Example Grafana Queries

### Business Health Queries

```logql
# User registration rate (daily)
sum by (day) (
  count_over_time(
    {container_name=~".*backend.*"}
    | json
    | event="new_user_created"
    [1d]
  )
)

# Quiz generation success rate
(
  sum(rate({container_name=~".*backend.*"} | json | event="quiz_generation_completed" | success="true" [1h]))
  /
  sum(rate({container_name=~".*backend.*"} | json | event="quiz_generation_completed" [1h]))
) * 100

# Average session duration
avg_over_time(
  {container_name=~".*backend.*"}
  | json
  | event="user_session_completed"
  | unwrap session_duration_minutes
  [1h]
)

# Feature usage distribution
sum by (feature) (
  count_over_time(
    {container_name=~".*backend.*"}
    | json
    | event="feature_usage"
    [1h]
  )
)
```

This implementation guide provides a foundation for comprehensive business metrics tracking in the Rag@UiT application. The metrics can be gradually implemented as new features are developed.
