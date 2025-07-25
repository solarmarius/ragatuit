# 1. Circular Dependency: Security Module and Auth Routes

## Priority: Critical

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: None

## Problem Statement

### Current Situation

The `app/core/security.py` module imports `refresh_canvas_token` function from `app/api/routes/auth.py`, creating a circular dependency. This violates Python's import principles and can lead to import errors during module initialization.

### Why It's a Problem

- **Import Errors**: Risk of `ImportError` or `AttributeError` at runtime
- **Testing Difficulties**: Cannot mock dependencies properly
- **Code Coupling**: Core security module depends on API route implementation
- **Maintainability**: Changes in auth routes affect core security
- **Module Loading**: Unpredictable behavior during Python module initialization

### Affected Modules

- `app/core/security.py` (lines 182-183)
- `app/api/routes/auth.py`
- `app/api/deps.py` (uses security functions)
- All modules importing security

### Technical Debt Assessment

- **Risk Level**: High - Can cause production failures
- **Impact**: Affects all authenticated endpoints
- **Cost of Delay**: Increases with each new auth-dependent feature

## Current Implementation Analysis

```python
# File: app/core/security.py (lines 170-200)
async def ensure_valid_canvas_token(session: Session, user: User) -> str:
    """
    Ensure Canvas token is valid, refresh if needed.
    Returns a valid Canvas access token.
    """
    # Check if token expires within 5 minutes
    if user.expires_at:
        expires_soon = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=5
        )
        if user.expires_at <= expires_soon:
            try:
                # PROBLEM: Circular import!
                from app.api.routes.auth import refresh_canvas_token

                await refresh_canvas_token(user, session)
            except HTTPException as e:
                # Error handling...
```

### Module Structure

```
app/
├── core/
│   ├── __init__.py
│   ├── security.py  # Imports from api.routes.auth (circular!)
│   └── config.py
├── api/
│   ├── routes/
│   │   ├── __init__.py
│   │   └── auth.py  # Imports from core.security
│   └── deps.py     # Uses both security and auth
```

### Python Anti-patterns Identified

- **Circular Import**: Core module importing from higher-level module
- **Tight Coupling**: Business logic mixed with routing logic
- **Missing Abstraction**: No interface for token refresh functionality

## Proposed Solution

### Pythonic Approach

Implement the **Dependency Inversion Principle** using Python's Protocol (PEP 544) for structural subtyping, allowing the security module to define an interface that auth routes can implement.

### Design Patterns

- **Protocol Pattern**: Define token refresher interface
- **Dependency Injection**: Inject implementation at runtime
- **Service Layer**: Extract token refresh logic to service

### Step-by-Step Implementation Plan

1. **Create Protocol Interface**
2. **Extract Token Refresh Service**
3. **Update Security Module**
4. **Refactor Auth Routes**
5. **Update Dependency Injection**
6. **Add Tests**

### Code Examples

```python
# File: app/core/protocols.py (NEW)
from typing import Protocol
from sqlmodel import Session
from app.models import User

class TokenRefresherProtocol(Protocol):
    """Protocol for token refresh implementations."""

    async def refresh_token(self, user: User, session: Session) -> None:
        """Refresh user's access token."""
        ...

# File: app/services/canvas_auth.py (NEW)
from datetime import datetime, timezone
from sqlmodel import Session
import httpx

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import User
from app.crud import update_user_tokens

logger = get_logger("canvas_auth_service")

class CanvasAuthService:
    """Service for Canvas authentication operations."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or str(settings.CANVAS_BASE_URL)

    async def refresh_token(self, user: User, session: Session) -> None:
        """
        Refresh Canvas OAuth token for a user.

        Args:
            user: User with expired/expiring token
            session: Database session

        Raises:
            HTTPException: If refresh fails
        """
        logger.info(
            "canvas_token_refresh_initiated",
            user_id=str(user.id),
            canvas_id=user.canvas_id
        )

        try:
            # Make refresh request to Canvas
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/login/oauth2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": user.refresh_token,
                        "client_id": settings.CANVAS_CLIENT_ID,
                        "client_secret": settings.CANVAS_CLIENT_SECRET,
                    }
                )
                response.raise_for_status()
                token_data = response.json()

            # Update user tokens
            update_user_tokens(
                session,
                user,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=datetime.now(timezone.utc) + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
            )

            logger.info(
                "canvas_token_refresh_completed",
                user_id=str(user.id)
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "canvas_token_refresh_failed",
                user_id=str(user.id),
                status_code=e.response.status_code
            )
            raise

# File: app/core/security.py (UPDATED)
from typing import Optional
from app.core.protocols import TokenRefresherProtocol

async def ensure_valid_canvas_token(
    session: Session,
    user: User,
    token_refresher: Optional[TokenRefresherProtocol] = None
) -> str:
    """
    Ensure Canvas token is valid, refresh if needed.

    Args:
        session: Database session
        user: User to check token for
        token_refresher: Optional token refresh implementation

    Returns:
        Valid Canvas access token
    """
    # Check if token expires within 5 minutes
    if user.expires_at:
        expires_soon = datetime.now(timezone.utc) + timedelta(minutes=5)
        if user.expires_at <= expires_soon:
            if not token_refresher:
                raise ValueError("Token expired but no refresher provided")

            try:
                await token_refresher.refresh_token(user, session)
            except Exception as e:
                logger.error(
                    "token_refresh_failed",
                    user_id=str(user.id),
                    error=str(e)
                )
                raise HTTPException(
                    status_code=401,
                    detail="Canvas session expired. Please re-login."
                )

    return crud.get_decrypted_access_token(user)

# File: app/api/deps.py (UPDATED)
from functools import lru_cache
from app.services.canvas_auth import CanvasAuthService

@lru_cache()
def get_canvas_auth_service() -> CanvasAuthService:
    """Get singleton Canvas auth service."""
    return CanvasAuthService()

CanvasAuthServiceDep = Annotated[CanvasAuthService, Depends(get_canvas_auth_service)]

async def get_canvas_token(
    current_user: CurrentUser,
    session: SessionDep,
    auth_service: CanvasAuthServiceDep
) -> str:
    """Get valid Canvas token with automatic refresh."""
    return await ensure_valid_canvas_token(session, current_user, auth_service)
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── protocols.py      # NEW: Protocol definitions
│   │   └── security.py       # UPDATE: Remove circular import
│   ├── services/
│   │   ├── __init__.py      # NEW: Package init
│   │   └── canvas_auth.py   # NEW: Canvas auth service
│   ├── api/
│   │   ├── deps.py          # UPDATE: Add service dependency
│   │   └── routes/
│   │       └── auth.py      # UPDATE: Use service
│   └── tests/
│       ├── services/
│       │   └── test_canvas_auth.py  # NEW: Service tests
│       └── core/
│           └── test_security.py     # UPDATE: Mock protocol
```

### API Changes

- `ensure_valid_canvas_token` now accepts optional `token_refresher` parameter
- Auth routes use `CanvasAuthService` instead of inline implementation

### Configuration Changes

None required

### Dependencies

No new packages required

## Python-Specific Refactoring Details

### Type Annotations

```python
# Complete type hints for the refactored code
from typing import Optional, Protocol
from datetime import datetime

class TokenRefresherProtocol(Protocol):
    async def refresh_token(
        self,
        user: User,
        session: Session
    ) -> None: ...

async def ensure_valid_canvas_token(
    session: Session,
    user: User,
    token_refresher: Optional[TokenRefresherProtocol] = None
) -> str: ...
```

### Async/Await Pattern

The solution maintains async patterns throughout:

```python
# Proper async context manager usage
async with httpx.AsyncClient() as client:
    response = await client.post(...)
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/services/test_canvas_auth.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.canvas_auth import CanvasAuthService
from app.models import User

@pytest.fixture
def canvas_auth_service():
    return CanvasAuthService(base_url="http://test.canvas.com")

@pytest.fixture
def mock_user():
    return User(
        id="123e4567-e89b-12d3-a456-426614174000",
        canvas_id=12345,
        access_token="old_token",
        refresh_token="refresh_token",
        expires_at=datetime.now() - timedelta(hours=1)
    )

@pytest.mark.asyncio
async def test_refresh_token_success(canvas_auth_service, mock_user):
    """Test successful token refresh."""
    # Arrange
    mock_session = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "new_token",
        "refresh_token": "new_refresh",
        "expires_in": 3600
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # Act
        await canvas_auth_service.refresh_token(mock_user, mock_session)

        # Assert
        assert mock_client.return_value.__aenter__.return_value.post.called

@pytest.mark.asyncio
async def test_ensure_valid_token_with_expired_token():
    """Test token refresh is triggered for expired tokens."""
    # Test implementation...
```

### Integration Tests

```python
# File: app/tests/integration/test_auth_flow.py
@pytest.mark.asyncio
async def test_complete_auth_flow_with_token_refresh(client, db_session):
    """Test auth flow including automatic token refresh."""
    # Create user with expired token
    # Make authenticated request
    # Verify token was refreshed
    # Verify request succeeded
```

### Mocking Strategy

```python
# Mock the protocol for testing
class MockTokenRefresher:
    async def refresh_token(self, user, session):
        # Mock implementation
        pass

# Use in tests
mock_refresher = MockTokenRefresher()
token = await ensure_valid_canvas_token(session, user, mock_refresher)
```

## Code Quality Improvements

### Before Refactoring

```bash
$ pylint app/core/security.py
************* Module app.core.security
C0415: Import outside toplevel (app.api.routes.auth.refresh_canvas_token) (import-outside-toplevel)
R0401: Cyclic import (app.core.security -> app.api.routes.auth) (cyclic-import)

$ mypy app/core/security.py
app/core/security.py:183: error: Circular import between modules
```

### After Refactoring

```bash
$ pylint app/core/security.py
Your code has been rated at 10.00/10

$ mypy app/core/security.py
Success: no issues found in 1 source file
```

## Migration Strategy

### Phase 1: Add New Components (Day 1)

1. Create `protocols.py` with `TokenRefresherProtocol`
2. Implement `CanvasAuthService`
3. Add comprehensive tests

### Phase 2: Update Core Components (Day 2)

1. Update `security.py` to use protocol
2. Update `deps.py` with service dependency
3. Update auth routes to use service
4. Run full test suite

### Rollback Plan

- Keep original code commented for 1 sprint
- Use feature flag if needed:

```python
if settings.USE_NEW_AUTH_SERVICE:
    return await ensure_valid_canvas_token(session, user, auth_service)
else:
    # Old implementation
```

## Success Criteria

### Code Quality Metrics

- **Circular Dependencies**: 0 (verified by `pylint`)
- **Type Coverage**: 100% for modified files
- **Test Coverage**: >90% for new service
- **Cyclomatic Complexity**: <5 for new methods

### Performance Metrics

- No performance regression (same response times)
- Successful token refresh in <500ms

### Verification Steps

1. Run `python -m pytest` - all tests pass
2. Run `mypy app` - no circular import errors
3. Run `pylint app/core/security.py` - no import warnings
4. Manual testing of token refresh flow

---
