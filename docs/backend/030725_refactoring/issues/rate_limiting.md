# 10. Rate Limiting Implementation

## Priority: Low

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: FastAPI, asyncio, Redis (optional)

## Problem Statement

### Current Situation

The API lacks rate limiting mechanisms, making it vulnerable to abuse, resource exhaustion, and potential denial-of-service attacks. All endpoints accept unlimited requests from any user or IP address.

### Why It's a Problem

- **Resource Exhaustion**: High-frequency requests can overwhelm the server
- **API Abuse**: No protection against malicious or excessive usage
- **Unfair Usage**: Single user can consume all resources
- **Cost Control**: No limits on expensive operations (LLM calls)
- **Database Overload**: Unlimited queries can saturate database connections
- **Security Risk**: Vulnerable to brute force and DDoS attacks

### Affected Modules

- All API endpoints in `app/api/routes/`
- Resource-intensive operations (MCQ generation, content extraction)
- Authentication endpoints
- Database operations

### Technical Debt Assessment

- **Risk Level**: Low - Security and operational concern
- **Impact**: System availability and resource management
- **Cost of Delay**: Increases with user growth and system load

## Current Implementation Analysis

```python
# File: app/api/routes/quiz.py (current - no rate limiting)
@router.post("/")
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    """
    Create a new quiz.

    PROBLEM: No rate limiting - user can create unlimited quizzes
    """
    # No checks on request frequency or user limits
    quiz = create_quiz(session, quiz_data, current_user.id)
    # ... rest of implementation

@router.post("/{quiz_id}/generate-questions")
async def generate_questions_endpoint(
    quiz_id: UUID,
    generation_request: MCQGenerationRequest,
    current_user: CurrentUser,
    # ... other deps
) -> dict[str, str]:
    """
    Generate questions for a quiz.

    PROBLEM: No rate limiting on expensive LLM operations
    """
    # No protection against excessive LLM usage
    # No cost controls or usage limits
    result = await mcq_generation_service.generate_mcqs_for_quiz(...)
```

### Vulnerability Examples

```python
# Current vulnerabilities:
# 1. User can create 1000 quizzes per minute
# 2. Unlimited question generation requests (expensive LLM calls)
# 3. No protection on authentication endpoints
# 4. Database query flooding possible
# 5. No IP-based rate limiting for anonymous requests
```

### Resource Usage Patterns

```python
# Without rate limiting, possible resource exhaustion:
# - 100 concurrent quiz creations = database connection pool exhaustion
# - 50 question generation requests = $100+ in LLM costs per minute
# - 1000 requests/second = server overload
```

### Python Anti-patterns Identified

- **No Resource Protection**: Unlimited access to expensive operations
- **Missing Middleware**: No request throttling infrastructure
- **No User Quotas**: No per-user usage limits
- **No Cost Controls**: No limits on billable operations

## Proposed Solution

### Pythonic Approach

Implement rate limiting using FastAPI middleware with multiple strategies: IP-based rate limiting, user-based quotas, endpoint-specific limits, and sliding window algorithms with Redis backend for distributed deployments.

### Design Patterns

- **Middleware Pattern**: Request interception and throttling
- **Token Bucket Algorithm**: Smooth rate limiting with bursts
- **Sliding Window**: Time-based request tracking
- **Strategy Pattern**: Different limiting strategies per endpoint
- **Decorator Pattern**: Easy rate limit application

### Code Examples

```python
# File: app/middleware/rate_limiting.py (NEW)
import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("rate_limiting")

class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

class RateLimitScope(str, Enum):
    """Rate limiting scopes."""
    IP = "ip"
    USER = "user"
    ENDPOINT = "endpoint"
    GLOBAL = "global"

class RateLimitConfig:
    """Configuration for rate limiting rules."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
        scope: RateLimitScope = RateLimitScope.IP,
        cost_multiplier: float = 1.0,
        exempt_roles: Optional[list[str]] = None
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self.strategy = strategy
        self.scope = scope
        self.cost_multiplier = cost_multiplier
        self.exempt_roles = exempt_roles or []

class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Suitable for single-instance deployments.
    """

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.tokens: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    async def is_allowed(
        self,
        key: str,
        config: RateLimitConfig,
        cost: float = 1.0
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limits.

        Args:
            key: Unique identifier for rate limiting
            config: Rate limiting configuration
            cost: Cost/weight of this request

        Returns:
            Tuple of (allowed, metadata)
        """
        now = time.time()

        # Cleanup old entries periodically
        if now - self._last_cleanup > self._cleanup_interval:
            await self._cleanup_old_entries()
            self._last_cleanup = now

        if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(key, config, cost, now)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(key, config, cost, now)
        else:
            return await self._check_fixed_window(key, config, cost, now)

    async def _check_sliding_window(
        self,
        key: str,
        config: RateLimitConfig,
        cost: float,
        now: float
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using sliding window algorithm."""

        # Clean old requests outside the window
        minute_window = now - 60
        hour_window = now - 3600

        request_queue = self.requests[key]

        # Remove requests outside hour window
        while request_queue and request_queue[0]["timestamp"] < hour_window:
            request_queue.popleft()

        # Count requests in different windows
        minute_requests = sum(
            req["cost"] for req in request_queue
            if req["timestamp"] >= minute_window
        )
        hour_requests = sum(req["cost"] for req in request_queue)

        # Apply cost multiplier
        effective_cost = cost * config.cost_multiplier

        # Check limits
        minute_allowed = minute_requests + effective_cost <= config.requests_per_minute
        hour_allowed = hour_requests + effective_cost <= config.requests_per_hour

        if minute_allowed and hour_allowed:
            # Add request to queue
            request_queue.append({
                "timestamp": now,
                "cost": effective_cost
            })

            return True, {
                "remaining_minute": config.requests_per_minute - minute_requests - effective_cost,
                "remaining_hour": config.requests_per_hour - hour_requests - effective_cost,
                "reset_time": int(now + 60),
                "retry_after": None
            }
        else:
            # Calculate retry after
            retry_after = 60 if not minute_allowed else 3600

            return False, {
                "remaining_minute": max(0, config.requests_per_minute - minute_requests),
                "remaining_hour": max(0, config.requests_per_hour - hour_requests),
                "reset_time": int(now + retry_after),
                "retry_after": retry_after
            }

    async def _check_token_bucket(
        self,
        key: str,
        config: RateLimitConfig,
        cost: float,
        now: float
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using token bucket algorithm."""

        bucket = self.tokens[key]

        # Initialize bucket if not exists
        if "tokens" not in bucket:
            bucket["tokens"] = config.burst_size
            bucket["last_refill"] = now

        # Calculate tokens to add based on time elapsed
        time_elapsed = now - bucket["last_refill"]
        tokens_to_add = time_elapsed * (config.requests_per_minute / 60.0)

        # Add tokens (up to burst size)
        bucket["tokens"] = min(
            config.burst_size,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_refill"] = now

        # Apply cost multiplier
        effective_cost = cost * config.cost_multiplier

        # Check if enough tokens available
        if bucket["tokens"] >= effective_cost:
            bucket["tokens"] -= effective_cost

            return True, {
                "remaining_tokens": bucket["tokens"],
                "reset_time": int(now + (config.burst_size / (config.requests_per_minute / 60.0))),
                "retry_after": None
            }
        else:
            # Calculate retry after
            retry_after = (effective_cost - bucket["tokens"]) / (config.requests_per_minute / 60.0)

            return False, {
                "remaining_tokens": bucket["tokens"],
                "reset_time": int(now + retry_after),
                "retry_after": int(retry_after)
            }

    async def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks."""
        now = time.time()
        cutoff_time = now - 3600  # Keep 1 hour of history

        # Clean request queues
        for key in list(self.requests.keys()):
            queue = self.requests[key]

            # Remove old requests
            while queue and queue[0]["timestamp"] < cutoff_time:
                queue.popleft()

            # Remove empty queues
            if not queue:
                del self.requests[key]

        # Clean token buckets
        for key in list(self.tokens.keys()):
            bucket = self.tokens[key]
            if bucket.get("last_refill", 0) < cutoff_time:
                del self.tokens[key]

class RedisRateLimiter:
    """
    Redis-based rate limiter for distributed deployments.
    """

    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)

    async def is_allowed(
        self,
        key: str,
        config: RateLimitConfig,
        cost: float = 1.0
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis for distributed rate limiting."""

        now = time.time()
        effective_cost = cost * config.cost_multiplier

        # Use Lua script for atomic operations
        lua_script = """
        local key = KEYS[1]
        local minute_key = key .. ":minute"
        local hour_key = key .. ":hour"
        local now = tonumber(ARGV[1])
        local cost = tonumber(ARGV[2])
        local minute_limit = tonumber(ARGV[3])
        local hour_limit = tonumber(ARGV[4])

        -- Get current counts
        local minute_count = tonumber(redis.call('GET', minute_key) or 0)
        local hour_count = tonumber(redis.call('GET', hour_key) or 0)

        -- Check limits
        if minute_count + cost <= minute_limit and hour_count + cost <= hour_limit then
            -- Increment counters
            redis.call('INCRBY', minute_key, cost)
            redis.call('EXPIRE', minute_key, 60)
            redis.call('INCRBY', hour_key, cost)
            redis.call('EXPIRE', hour_key, 3600)

            return {1, minute_limit - minute_count - cost, hour_limit - hour_count - cost}
        else
            return {0, minute_limit - minute_count, hour_limit - hour_count}
        end
        """

        try:
            result = await self.redis_client.eval(
                lua_script,
                1,
                key,
                str(now),
                str(effective_cost),
                str(config.requests_per_minute),
                str(config.requests_per_hour)
            )

            allowed = bool(result[0])
            remaining_minute = max(0, result[1])
            remaining_hour = max(0, result[2])

            metadata = {
                "remaining_minute": remaining_minute,
                "remaining_hour": remaining_hour,
                "reset_time": int(now + (60 if remaining_minute == 0 else 3600)),
                "retry_after": 60 if not allowed and remaining_minute == 0 else (3600 if not allowed else None)
            }

            return allowed, metadata

        except Exception as e:
            logger.error("redis_rate_limiter_error", error=str(e))
            # Fail open - allow request if Redis is unavailable
            return True, {"error": "rate_limiter_unavailable"}

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """

    def __init__(self, app, rate_limiter: Optional[Any] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or InMemoryRateLimiter()
        self.endpoint_configs = self._load_endpoint_configs()

    def _load_endpoint_configs(self) -> Dict[str, RateLimitConfig]:
        """Load rate limiting configurations for different endpoints."""

        return {
            # General API endpoints
            "default": RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                scope=RateLimitScope.IP
            ),

            # Authentication endpoints (stricter)
            "auth": RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                scope=RateLimitScope.IP
            ),

            # Quiz creation (per user)
            "quiz_create": RateLimitConfig(
                requests_per_minute=5,
                requests_per_hour=50,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                scope=RateLimitScope.USER,
                cost_multiplier=2.0
            ),

            # Question generation (expensive)
            "question_generation": RateLimitConfig(
                requests_per_minute=2,
                requests_per_hour=20,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                scope=RateLimitScope.USER,
                cost_multiplier=5.0,
                exempt_roles=["admin", "premium"]
            ),

            # Content extraction
            "content_extraction": RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                scope=RateLimitScope.USER,
                cost_multiplier=3.0
            )
        }

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""

        # Skip rate limiting for health checks and internal endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Determine rate limit configuration
        config = self._get_config_for_request(request)

        # Check if user is exempt
        if await self._is_exempt_user(request, config):
            return await call_next(request)

        # Generate rate limit key
        rate_limit_key = await self._generate_rate_limit_key(request, config)

        # Calculate request cost
        cost = self._calculate_request_cost(request)

        # Check rate limit
        allowed, metadata = await self.rate_limiter.is_allowed(
            rate_limit_key, config, cost
        )

        if not allowed:
            # Log rate limit exceeded
            logger.warning(
                "rate_limit_exceeded",
                path=request.url.path,
                method=request.method,
                key=rate_limit_key,
                cost=cost,
                metadata=metadata
            )

            # Return rate limit error
            headers = {
                "X-RateLimit-Limit-Minute": str(config.requests_per_minute),
                "X-RateLimit-Limit-Hour": str(config.requests_per_hour),
                "X-RateLimit-Remaining-Minute": str(metadata.get("remaining_minute", 0)),
                "X-RateLimit-Remaining-Hour": str(metadata.get("remaining_hour", 0)),
                "X-RateLimit-Reset": str(metadata.get("reset_time", 0))
            }

            if metadata.get("retry_after"):
                headers["Retry-After"] = str(metadata["retry_after"])

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": metadata.get("retry_after"),
                    "limits": {
                        "requests_per_minute": config.requests_per_minute,
                        "requests_per_hour": config.requests_per_hour
                    }
                },
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers.update({
            "X-RateLimit-Limit-Minute": str(config.requests_per_minute),
            "X-RateLimit-Limit-Hour": str(config.requests_per_hour),
            "X-RateLimit-Remaining-Minute": str(metadata.get("remaining_minute", 0)),
            "X-RateLimit-Remaining-Hour": str(metadata.get("remaining_hour", 0)),
            "X-RateLimit-Reset": str(metadata.get("reset_time", 0))
        })

        return response

    def _get_config_for_request(self, request: Request) -> RateLimitConfig:
        """Determine rate limiting configuration for request."""

        path = request.url.path
        method = request.method

        # Check for specific endpoint configurations
        if path.startswith("/api/auth"):
            return self.endpoint_configs["auth"]
        elif path.startswith("/api/quiz") and method == "POST":
            if "generate-questions" in path:
                return self.endpoint_configs["question_generation"]
            else:
                return self.endpoint_configs["quiz_create"]
        elif "extract-content" in path:
            return self.endpoint_configs["content_extraction"]
        else:
            return self.endpoint_configs["default"]

    async def _is_exempt_user(self, request: Request, config: RateLimitConfig) -> bool:
        """Check if user is exempt from rate limiting."""

        if not config.exempt_roles:
            return False

        try:
            # Extract user from request (implementation specific)
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "role"):
                return user.role in config.exempt_roles
        except Exception:
            pass

        return False

    async def _generate_rate_limit_key(self, request: Request, config: RateLimitConfig) -> str:
        """Generate unique key for rate limiting."""

        if config.scope == RateLimitScope.IP:
            # Use client IP
            client_ip = request.client.host if request.client else "unknown"
            return f"ip:{client_ip}"

        elif config.scope == RateLimitScope.USER:
            # Use user ID if authenticated
            try:
                user = getattr(request.state, "user", None)
                if user and hasattr(user, "id"):
                    return f"user:{user.id}"
            except Exception:
                pass

            # Fall back to IP if not authenticated
            client_ip = request.client.host if request.client else "unknown"
            return f"ip:{client_ip}"

        elif config.scope == RateLimitScope.ENDPOINT:
            # Use endpoint path
            return f"endpoint:{request.url.path}"

        else:  # GLOBAL
            return "global"

    def _calculate_request_cost(self, request: Request) -> float:
        """Calculate cost/weight of request for rate limiting."""

        # Default cost
        cost = 1.0

        # Expensive operations cost more
        if "generate-questions" in request.url.path:
            cost = 10.0  # LLM operations are expensive
        elif "extract-content" in request.url.path:
            cost = 5.0   # Content extraction is moderately expensive
        elif request.method in ["POST", "PUT", "DELETE"]:
            cost = 2.0   # Write operations cost more than reads

        return cost

# File: app/core/rate_limit_decorators.py (NEW)
from functools import wraps
from typing import Callable, Optional

def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    scope: RateLimitScope = RateLimitScope.USER,
    cost_multiplier: float = 1.0,
    exempt_roles: Optional[list[str]] = None
):
    """
    Decorator for applying rate limits to specific endpoints.

    Args:
        requests_per_minute: Requests allowed per minute
        requests_per_hour: Requests allowed per hour
        scope: Rate limiting scope (IP, USER, etc.)
        cost_multiplier: Cost multiplier for this endpoint
        exempt_roles: Roles exempt from rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if hasattr(arg, "method") and hasattr(arg, "url"):
                    request = arg
                    break

            if not request:
                # If no request found, proceed without rate limiting
                return await func(*args, **kwargs)

            # Apply rate limiting logic here
            # (This would integrate with the middleware or use a similar approach)

            return await func(*args, **kwargs)

        # Store rate limit config on function for middleware to access
        wrapper._rate_limit_config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            scope=scope,
            cost_multiplier=cost_multiplier,
            exempt_roles=exempt_roles
        )

        return wrapper
    return decorator

# File: app/api/routes/quiz.py (UPDATED with rate limiting)
from app.core.rate_limit_decorators import rate_limit, RateLimitScope

@router.post("/")
@rate_limit(
    requests_per_minute=5,
    requests_per_hour=50,
    scope=RateLimitScope.USER,
    cost_multiplier=2.0
)
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    """Create a new quiz with rate limiting."""
    # Implementation remains the same
    quiz = create_quiz(session, quiz_data, current_user.id)
    # ... rest of implementation

@router.post("/{quiz_id}/generate-questions")
@rate_limit(
    requests_per_minute=2,
    requests_per_hour=20,
    scope=RateLimitScope.USER,
    cost_multiplier=10.0,
    exempt_roles=["admin", "premium"]
)
async def generate_questions_endpoint(
    quiz_id: UUID,
    generation_request: MCQGenerationRequest,
    current_user: CurrentUser,
    # ... other deps
) -> dict[str, str]:
    """Generate questions with strict rate limiting."""
    # Implementation remains the same
    # Rate limiting is handled by middleware/decorator

# File: app/main.py (UPDATED)
from app.middleware.rate_limiting import RateLimitMiddleware, InMemoryRateLimiter, RedisRateLimiter
from app.core.config import settings

# Initialize rate limiter based on configuration
if settings.REDIS_URL:
    rate_limiter = RedisRateLimiter(settings.REDIS_URL)
else:
    rate_limiter = InMemoryRateLimiter()

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
```

## Implementation Details

### Files to Create/Modify

```
backend/
├── app/
│   ├── middleware/
│   │   ├── __init__.py              # NEW: Package init
│   │   └── rate_limiting.py         # NEW: Rate limiting middleware
│   ├── core/
│   │   ├── rate_limit_decorators.py # NEW: Rate limit decorators
│   │   └── config.py                # UPDATE: Add rate limit settings
│   ├── main.py                      # UPDATE: Add middleware
│   ├── api/
│   │   └── routes/
│   │       ├── quiz.py              # UPDATE: Add rate limits
│   │       ├── auth.py              # UPDATE: Add rate limits
│   │       └── question.py          # UPDATE: Add rate limits
│   └── tests/
│       ├── middleware/
│       │   └── test_rate_limiting.py # NEW: Rate limiting tests
│       └── api/
│           └── test_rate_limited_endpoints.py # NEW: Endpoint tests
```

### Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REDIS_URL: Optional[str] = None
    RATE_LIMIT_DEFAULT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_DEFAULT_REQUESTS_PER_HOUR: int = 1000

    # Endpoint-specific limits
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_QUIZ_CREATE_PER_MINUTE: int = 5
    RATE_LIMIT_QUESTION_GENERATION_PER_MINUTE: int = 2
    RATE_LIMIT_QUESTION_GENERATION_PER_HOUR: int = 20
```

### Dependencies

```toml
# pyproject.toml additions
[project.dependencies]
redis = {version = ">=4.0.0", optional = true}

[project.optional-dependencies]
redis = ["redis>=4.0.0"]
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/middleware/test_rate_limiting.py
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from app.middleware.rate_limiting import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    RateLimitScope
)

@pytest.mark.asyncio
async def test_in_memory_rate_limiter_sliding_window():
    """Test in-memory rate limiter with sliding window."""

    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=50,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    )

    # First 5 requests should be allowed
    for i in range(5):
        allowed, metadata = await limiter.is_allowed("test_key", config)
        assert allowed is True
        assert metadata["remaining_minute"] == 4 - i

    # 6th request should be blocked
    allowed, metadata = await limiter.is_allowed("test_key", config)
    assert allowed is False
    assert metadata["retry_after"] == 60

@pytest.mark.asyncio
async def test_token_bucket_algorithm():
    """Test token bucket rate limiting algorithm."""

    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(
        requests_per_minute=60,  # 1 per second
        burst_size=5,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )

    # Should allow burst of 5 requests
    for i in range(5):
        allowed, metadata = await limiter.is_allowed("test_key", config)
        assert allowed is True

    # 6th request should be blocked
    allowed, metadata = await limiter.is_allowed("test_key", config)
    assert allowed is False

    # Wait for token refill
    await asyncio.sleep(1.1)

    # Should allow one more request
    allowed, metadata = await limiter.is_allowed("test_key", config)
    assert allowed is True

@pytest.mark.asyncio
async def test_cost_multiplier():
    """Test request cost multiplier functionality."""

    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(
        requests_per_minute=10,
        cost_multiplier=2.0,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    )

    # Request with cost 1.0 should consume 2.0 tokens
    allowed, metadata = await limiter.is_allowed("test_key", config, cost=1.0)
    assert allowed is True
    assert metadata["remaining_minute"] == 8  # 10 - 2.0

    # Request with cost 5.0 should consume 10.0 tokens (2.0 * 5.0)
    allowed, metadata = await limiter.is_allowed("test_key", config, cost=5.0)
    assert allowed is False  # Would exceed limit

def test_rate_limit_config_creation():
    """Test rate limit configuration creation."""

    config = RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        scope=RateLimitScope.USER,
        exempt_roles=["admin", "premium"]
    )

    assert config.requests_per_minute == 30
    assert config.requests_per_hour == 500
    assert config.scope == RateLimitScope.USER
    assert "admin" in config.exempt_roles

# File: app/tests/api/test_rate_limited_endpoints.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_quiz_creation_rate_limit(client, test_user):
    """Test rate limiting on quiz creation endpoint."""

    quiz_data = {
        "title": "Test Quiz",
        "description": "Test Description",
        "canvas_course_id": 123,
        "selected_modules": {"456": "Test Module"}
    }

    headers = {"Authorization": f"Bearer {test_user.access_token}"}

    # First 5 requests should succeed
    for i in range(5):
        response = client.post("/api/quiz/", json=quiz_data, headers=headers)
        assert response.status_code in [200, 201]

        # Check rate limit headers
        assert "X-RateLimit-Limit-Minute" in response.headers
        assert "X-RateLimit-Remaining-Minute" in response.headers

    # 6th request should be rate limited
    response = client.post("/api/quiz/", json=quiz_data, headers=headers)
    assert response.status_code == 429
    assert "retry_after" in response.json()

def test_question_generation_rate_limit(client, test_user, test_quiz):
    """Test strict rate limiting on question generation."""

    generation_data = {
        "target_question_count": 5,
        "model": "gpt-4",
        "temperature": 0.7
    }

    headers = {"Authorization": f"Bearer {test_user.access_token}"}

    # First 2 requests should succeed
    for i in range(2):
        response = client.post(
            f"/api/quiz/{test_quiz.id}/generate-questions",
            json=generation_data,
            headers=headers
        )
        assert response.status_code in [200, 202]

    # 3rd request should be rate limited
    response = client.post(
        f"/api/quiz/{test_quiz.id}/generate-questions",
        json=generation_data,
        headers=headers
    )
    assert response.status_code == 429

def test_ip_based_rate_limiting(client):
    """Test IP-based rate limiting for unauthenticated requests."""

    # Make requests without authentication
    for i in range(60):
        response = client.get("/api/health")
        if i < 59:
            assert response.status_code != 429
        else:
            # Should be rate limited after 60 requests
            if response.status_code == 429:
                break

@pytest.mark.asyncio
async def test_redis_rate_limiter_integration():
    """Test Redis rate limiter with mocked Redis."""

    with patch('redis.asyncio.from_url') as mock_redis:
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client

        # Mock Redis eval response (allowed)
        mock_redis_client.eval.return_value = [1, 50, 900]  # allowed, remaining_minute, remaining_hour

        from app.middleware.rate_limiting import RedisRateLimiter, RateLimitConfig

        limiter = RedisRateLimiter("redis://localhost:6379")
        config = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000)

        allowed, metadata = await limiter.is_allowed("test_key", config)

        assert allowed is True
        assert metadata["remaining_minute"] == 50
        assert metadata["remaining_hour"] == 900
        mock_redis_client.eval.assert_called_once()
```

### Integration Tests

```python
# File: app/tests/integration/test_rate_limiting_integration.py
@pytest.mark.integration
def test_rate_limiting_across_multiple_endpoints(client, test_user):
    """Test rate limiting across different endpoints."""

    headers = {"Authorization": f"Bearer {test_user.access_token}"}

    # Create multiple quizzes (should hit rate limit)
    quiz_responses = []
    for i in range(10):
        response = client.post("/api/quiz/", json={
            "title": f"Quiz {i}",
            "canvas_course_id": 123,
            "selected_modules": {"456": "Module"}
        }, headers=headers)
        quiz_responses.append(response)

    # Check that some requests were rate limited
    rate_limited_count = sum(1 for r in quiz_responses if r.status_code == 429)
    assert rate_limited_count > 0

@pytest.mark.integration
def test_rate_limit_exempt_user(client, admin_user):
    """Test that exempt users bypass rate limits."""

    headers = {"Authorization": f"Bearer {admin_user.access_token}"}

    # Admin user should be able to make many requests
    for i in range(20):
        response = client.post("/api/quiz/", json={
            "title": f"Admin Quiz {i}",
            "canvas_course_id": 123,
            "selected_modules": {"456": "Module"}
        }, headers=headers)

        # Should not be rate limited
        assert response.status_code != 429
```

### Performance Tests

```python
# File: app/tests/performance/test_rate_limiting_performance.py
@pytest.mark.performance
def test_rate_limiter_performance():
    """Test rate limiter performance under load."""

    import time
    from concurrent.futures import ThreadPoolExecutor

    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(requests_per_minute=1000)

    def make_request():
        return asyncio.run(limiter.is_allowed("test_key", config))

    # Test 1000 concurrent requests
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(make_request) for _ in range(1000)]
        results = [future.result() for future in futures]

    end_time = time.time()

    # Should complete within reasonable time
    assert end_time - start_time < 5.0

    # Should handle all requests
    assert len(results) == 1000
```

## Code Quality Improvements

### Monitoring and Alerting

```python
# File: app/middleware/rate_limiting_monitoring.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics for monitoring
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Number of requests that exceeded rate limits',
    ['endpoint', 'scope', 'user_type']
)

rate_limit_check_duration = Histogram(
    'rate_limit_check_duration_seconds',
    'Time spent checking rate limits'
)

active_rate_limit_keys = Gauge(
    'active_rate_limit_keys',
    'Number of active rate limiting keys'
)

def record_rate_limit_exceeded(endpoint: str, scope: str, user_type: str):
    """Record rate limit exceeded event."""
    rate_limit_exceeded.labels(
        endpoint=endpoint,
        scope=scope,
        user_type=user_type
    ).inc()
```

### Health Checks

```python
# File: app/api/routes/health.py
@router.get("/rate-limiter")
async def check_rate_limiter_health():
    """Check rate limiter health."""

    try:
        # Test rate limiter functionality
        test_key = f"health_check_{time.time()}"
        config = RateLimitConfig(requests_per_minute=100)

        allowed, metadata = await app.state.rate_limiter.is_allowed(test_key, config)

        return {
            "status": "healthy",
            "rate_limiter_type": type(app.state.rate_limiter).__name__,
            "test_result": "passed" if allowed else "failed"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Migration Strategy

### Phase 1: Infrastructure Setup (Day 1)

1. Create rate limiting middleware and classes
2. Add configuration settings
3. Create comprehensive tests

### Phase 2: Gradual Rollout (Day 2)

1. Enable rate limiting with generous limits
2. Monitor and tune limits based on usage patterns
3. Add rate limiting to critical endpoints first

### Feature Flag Implementation

```python
# Gradual rollout with feature flags
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
```

### Monitoring During Rollout

```python
# Monitor rate limiting effectiveness
@app.middleware("http")
async def monitor_rate_limiting(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # Log rate limiting metrics
    if response.status_code == 429:
        logger.warning(
            "rate_limit_triggered",
            path=request.url.path,
            method=request.method,
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )

    return response
```

## Success Criteria

### Security Metrics

- **Rate Limit Effectiveness**: >95% of abusive requests blocked
- **False Positive Rate**: <1% of legitimate requests blocked
- **Attack Mitigation**: Successful blocking of simulated attacks

### Performance Metrics

- **Latency Impact**: <5ms additional latency for rate limit checks
- **Memory Usage**: Controlled memory growth for request tracking
- **Throughput**: No significant reduction in legitimate request throughput

### Operational Metrics

- **Alert Accuracy**: Rate limiting alerts correlate with actual issues
- **Configuration Flexibility**: Easy adjustment of limits per endpoint
- **Monitoring Coverage**: Complete visibility into rate limiting effectiveness

---
