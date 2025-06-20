# Code Review: Essential Features Analysis for Rag@UiT

**Reviewer**: Senior Software Engineer
**Project**: Rag@UiT - Canvas LMS Quiz Generator
**Tech Stack**: FastAPI (Backend) + React + TypeScript (Frontend) + PostgreSQL + Docker
**Review Date**: June 2025

## Executive Summary

This comprehensive code review examines your Rag@UiT application to identify essential features that are critical for any robust software product. Your current implementation demonstrates solid foundations with Canvas OAuth integration, modern web frameworks, and containerized deployment. However, several critical features are missing that would elevate this from a functional prototype to a production-ready application.

## Current Architecture Strengths

Before identifying missing features, it's worth acknowledging your solid foundation:

- **Modern Tech Stack**: FastAPI with SQLModel, React with TypeScript, proper containerization
- **Security-First Approach**: JWT authentication, encrypted token storage, CORS configuration
- **Developer Experience**: Pre-commit hooks, comprehensive testing setup, code formatting tools
- **Canvas Integration**: Complete OAuth flow with token refresh mechanisms

---

## Essential Missing Features Analysis

### 1. **Comprehensive Logging and Observability**

#### Why Essential
Logging is the nervous system of any production application. Without proper logging, debugging issues becomes nearly impossible, performance bottlenecks go unnoticed, and security incidents remain invisible.

#### Current State
- Basic Sentry integration present but limited
- No structured logging framework
- No request/response logging
- No performance metrics collection

#### Implementation Plan

**Backend (FastAPI)**:
```python
# app/core/logging.py
import logging
import structlog
from fastapi import Request, Response
import time

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger = structlog.get_logger()
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent")
    )

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        "request_completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )

    return response
```

**Dependencies to add**:
```toml
# pyproject.toml
dependencies = [
    # ... existing deps
    "structlog>=23.1.0",
    "prometheus-client>=0.17.0",
]
```

---

### 2. **Application Health Monitoring & Metrics**

#### Why Essential
Health checks and metrics are fundamental for production deployment, load balancing, auto-scaling, and operational monitoring. Without them, you're flying blind in production.

#### Current State
- Basic health check endpoint exists
- No detailed health checks for dependencies
- No application metrics collection
- No performance monitoring

#### Implementation Plan

**Enhanced Health Checks** (`backend/app/api/routes/utils.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, text
import httpx
from app.core.db import get_session

@router.get("/health-check/detailed")
async def detailed_health_check(session: Session = Depends(get_session)):
    """Comprehensive health check including all dependencies"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",  # Add version to your config
        "checks": {}
    }

    # Database connectivity
    try:
        result = session.exec(text("SELECT 1")).first()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": "< 100"  # Measure actual time
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Canvas API connectivity
    try:
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get(f"{settings.CANVAS_BASE_URL}/api/v1/accounts", timeout=5.0)
            response_time = (time.time() - start_time) * 1000

            health_status["checks"]["canvas_api"] = {
                "status": "healthy" if response.status_code < 500 else "degraded",
                "response_time_ms": f"{response_time:.2f}"
            }
    except Exception as e:
        health_status["checks"]["canvas_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status
```

**Prometheus Metrics Integration**:
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
CANVAS_API_CALLS = Counter('canvas_api_calls_total', 'Canvas API calls', ['status'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(time.time() - start_time)

    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### 3. **Robust Error Handling & User Feedback**

#### Why Essential
Proper error handling is what separates amateur applications from professional ones. Users need clear feedback, developers need debugging information, and the system needs to gracefully handle failures.

#### Current State
- Basic error handling in auth flows
- Generic HTTP exceptions
- No user-friendly error messages
- No error tracking/analytics

#### Implementation Plan

**Global Exception Handler** (`backend/app/main.py`):
```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)

class CanvasAPIException(AppException):
    """Canvas API specific errors"""
    def __init__(self, message: str, canvas_error: str = None):
        super().__init__(
            message=f"Canvas API Error: {message}",
            error_code="CANVAS_API_ERROR",
            status_code=503
        )
        self.canvas_error = canvas_error

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": request.url.path
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unexpected_error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method
    )

    # Don't expose internal errors to users in production
    message = "An unexpected error occurred" if settings.ENVIRONMENT == "production" else str(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )
```

**Frontend Error Boundary** (`frontend/src/components/ErrorBoundary.tsx`):
```typescript
import React from 'react';
import { Alert, AlertIcon, Button, VStack, Text, Box } from '@chakra-ui/react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

export class ErrorBoundary extends React.Component<
  React.PropsWithChildren<{}>,
  ErrorBoundaryState
> {
  constructor(props: React.PropsWithChildren<{}>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Application Error:', error);
    console.error('Error Info:', errorInfo);

    // Send to error tracking service
    if (import.meta.env.PROD) {
      // Sentry.captureException(error, { extra: errorInfo });
    }

    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box p={6} maxW="md" mx="auto" mt={10}>
          <VStack spacing={4}>
            <Alert status="error">
              <AlertIcon />
              Something went wrong
            </Alert>

            <Text fontSize="sm" color="gray.600">
              We've been notified of this error and are working to fix it.
            </Text>

            <Button
              onClick={() => window.location.reload()}
              colorScheme="blue"
            >
              Reload Page
            </Button>

            {import.meta.env.DEV && (
              <Box as="pre" fontSize="xs" p={3} bg="gray.100" borderRadius="md" overflow="auto">
                {this.state.error?.stack}
              </Box>
            )}
          </VStack>
        </Box>
      );
    }

    return this.props.children;
  }
}
```

---

### 4. **Input Validation & Data Sanitization**

#### Why Essential
Input validation is your first line of defense against security vulnerabilities, data corruption, and application crashes. Every external input must be validated and sanitized.

#### Current State
- Basic Pydantic validation on API models
- No comprehensive input sanitization
- No file upload validation
- Limited frontend validation

#### Implementation Plan

**Enhanced Backend Validation** (`backend/app/core/validation.py`):
```python
from pydantic import BaseModel, Field, validator
import re
from typing import Optional
import bleach

class ValidationMixin:
    """Mixin for common validation patterns"""

    @validator('*', pre=True)
    def sanitize_strings(cls, v):
        """Sanitize all string inputs"""
        if isinstance(v, str):
            # Remove potential XSS
            v = bleach.clean(v, tags=[], attributes={}, strip=True)
            # Normalize whitespace
            v = re.sub(r'\s+', ' ', v).strip()
        return v

class EnhancedUserCreate(UserCreate, ValidationMixin):
    name: str = Field(..., min_length=1, max_length=255, regex=r'^[a-zA-Z0-9\s\-_.]+$')
    canvas_id: int = Field(..., gt=0)

    @validator('name')
    def validate_name(cls, v):
        if not v or v.isspace():
            raise ValueError('Name cannot be empty or only whitespace')
        return v.title()  # Proper case

class QuestionCreate(BaseModel, ValidationMixin):
    """Example for future question creation"""
    title: str = Field(..., min_length=5, max_length=500)
    content: str = Field(..., min_length=10, max_length=5000)
    difficulty: str = Field(..., regex=r'^(easy|medium|hard)$')

    @validator('content')
    def validate_content(cls, v):
        # Ensure question ends with a question mark or is a statement
        if not (v.endswith('?') or v.endswith('.') or v.endswith(':')):
            raise ValueError('Question content should end with proper punctuation')
        return v
```

**Frontend Form Validation** (`frontend/src/hooks/useFormValidation.ts`):
```typescript
import { useState, useCallback } from 'react';
import { z } from 'zod';

export const useFormValidation = <T extends Record<string, any>>(
  schema: z.ZodSchema<T>
) => {
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [isValid, setIsValid] = useState(false);

  const validate = useCallback((data: T) => {
    try {
      schema.parse(data);
      setErrors({});
      setIsValid(true);
      return true;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const fieldErrors: Partial<Record<keyof T, string>> = {};
        error.errors.forEach((err) => {
          const field = err.path[0] as keyof T;
          fieldErrors[field] = err.message;
        });
        setErrors(fieldErrors);
      }
      setIsValid(false);
      return false;
    }
  }, [schema]);

  return { errors, isValid, validate };
};

// Usage example for future forms
export const questionSchema = z.object({
  title: z.string()
    .min(5, 'Title must be at least 5 characters')
    .max(500, 'Title cannot exceed 500 characters'),
  content: z.string()
    .min(10, 'Question content must be at least 10 characters')
    .max(5000, 'Content cannot exceed 5000 characters'),
  difficulty: z.enum(['easy', 'medium', 'hard'], {
    errorMap: () => ({ message: 'Please select a difficulty level' })
  })
});
```

---

### 5. **Rate Limiting & API Protection**

#### Why Essential
Rate limiting prevents abuse, protects against DoS attacks, ensures fair usage, and maintains service quality for all users. This is especially critical when integrating with external APIs like Canvas.

#### Current State
- No rate limiting implemented
- No API abuse protection
- Vulnerable to Canvas API quota exhaustion

#### Implementation Plan

**Backend Rate Limiting** (`backend/app/core/rate_limit.py`):
```python
from fastapi import HTTPException, Request
import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Deque
import structlog

logger = structlog.get_logger()

class RateLimiter:
    def __init__(self):
        # Store requests per IP: {ip: deque of timestamps}
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def is_allowed(
        self,
        client_ip: str,
        limit: int = 100,  # requests per window
        window: int = 3600  # 1 hour in seconds
    ) -> bool:
        """Check if request is allowed under rate limit"""
        async with self.lock:
            now = time.time()
            window_start = now - window

            # Clean old requests outside the window
            while (self.requests[client_ip] and
                   self.requests[client_ip][0] < window_start):
                self.requests[client_ip].popleft()

            # Check if under limit
            if len(self.requests[client_ip]) >= limit:
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    current_requests=len(self.requests[client_ip]),
                    limit=limit
                )
                return False

            # Add current request
            self.requests[client_ip].append(now)
            return True

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host

    # Different limits for different endpoints
    if request.url.path.startswith("/api/v1/auth"):
        allowed = await rate_limiter.is_allowed(client_ip, limit=10, window=300)  # 10 per 5 min
    elif request.url.path.startswith("/api/v1/canvas"):
        allowed = await rate_limiter.is_allowed(client_ip, limit=50, window=3600)  # 50 per hour
    else:
        allowed = await rate_limiter.is_allowed(client_ip, limit=100, window=3600)  # General limit

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "retry_after": 3600
            }
        )

    return await call_next(request)

# Add to main.py
app.middleware("http")(rate_limit_middleware)
```

**Canvas API Rate Limiting** (`backend/app/core/canvas_client.py`):
```python
import asyncio
from datetime import datetime, timedelta
import httpx
from typing import Optional

class CanvasRateLimitedClient:
    """Rate-limited Canvas API client"""

    def __init__(self):
        self.requests_made = 0
        self.window_start = datetime.now()
        self.max_requests_per_hour = 3000  # Canvas typical limit
        self.lock = asyncio.Lock()

    async def make_request(
        self,
        method: str,
        url: str,
        headers: dict,
        **kwargs
    ) -> httpx.Response:
        """Make rate-limited request to Canvas API"""
        async with self.lock:
            now = datetime.now()

            # Reset counter if window has elapsed
            if now - self.window_start > timedelta(hours=1):
                self.requests_made = 0
                self.window_start = now

            # Check if we're approaching the limit
            if self.requests_made >= self.max_requests_per_hour * 0.9:  # 90% threshold
                logger.warning(
                    "canvas_rate_limit_approaching",
                    requests_made=self.requests_made,
                    limit=self.max_requests_per_hour
                )
                # Implement exponential backoff
                await asyncio.sleep(2 ** min(self.requests_made // 100, 6))

            self.requests_made += 1

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)

            # Check Canvas rate limit headers if present
            if 'X-Rate-Limit-Remaining' in response.headers:
                remaining = int(response.headers['X-Rate-Limit-Remaining'])
                if remaining < 100:  # Low threshold
                    logger.warning(
                        "canvas_rate_limit_low",
                        remaining=remaining
                    )

            return response

canvas_client = CanvasRateLimitedClient()
```

---

### 6. **Caching Strategy**

#### Why Essential
Caching reduces database load, improves response times, reduces external API calls, and provides better user experience. For a Canvas-integrated app, caching is crucial to avoid hitting API limits.

#### Current State
- No caching implemented
- Repeated Canvas API calls for same data
- Database queries not optimized with caching

#### Implementation Plan

**Redis Caching Layer** (`backend/app/core/cache.py`):
```python
import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import structlog

logger = structlog.get_logger()

class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value:
                return pickle.loads(value)
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Union[int, timedelta] = timedelta(hours=1)
    ) -> bool:
        """Set value in cache with TTL"""
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())

            await self.redis.set(key, pickle.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error("cache_exists_error", key=key, error=str(e))
            return False

cache = CacheManager()

# Decorator for caching function results
def cached(ttl: Union[int, timedelta] = timedelta(hours=1), key_prefix: str = ""):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug("cache_hit", function=func.__name__, key=cache_key)
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            logger.debug("cache_miss", function=func.__name__, key=cache_key)

            return result
        return wrapper
    return decorator
```

**Canvas Data Caching** (`backend/app/api/routes/canvas.py`):
```python
from app.core.cache import cached, cache
from datetime import timedelta

@router.get("/courses")
@cached(ttl=timedelta(minutes=30), key_prefix="canvas:courses:")
async def get_user_courses(current_user: CurrentUser):
    """Get user's Canvas courses with caching"""
    # Canvas course data doesn't change frequently
    canvas_token = await ensure_valid_canvas_token(session, current_user)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.CANVAS_BASE_URL}/api/v1/courses",
            headers={"Authorization": f"Bearer {canvas_token}"}
        )
        return response.json()

@router.get("/courses/{course_id}/modules")
@cached(ttl=timedelta(hours=6), key_prefix="canvas:modules:")
async def get_course_modules(course_id: int, current_user: CurrentUser):
    """Get course modules with long-term caching"""
    # Course modules change even less frequently
    canvas_token = await ensure_valid_canvas_token(session, current_user)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.CANVAS_BASE_URL}/api/v1/courses/{course_id}/modules",
            headers={"Authorization": f"Bearer {canvas_token}"}
        )
        return response.json()

# Cache invalidation when user data changes
async def invalidate_user_cache(user_id: str):
    """Invalidate all cached data for a user"""
    pattern = f"canvas:*:{user_id}:*"
    # This would require implementing cache pattern deletion
    await cache.delete_pattern(pattern)
```

**Frontend Query Caching** (Already using React Query, enhance configuration):
```typescript
// frontend/src/main.tsx - enhance existing QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
});
```

---

### 7. **Database Performance & Optimization**

#### Why Essential
Database performance is often the bottleneck in web applications. Proper indexing, query optimization, and connection management are essential for scalability.

#### Current State
- Basic SQLModel setup
- No database indexing strategy
- No query optimization
- No connection pooling configuration

#### Implementation Plan

**Database Indexes** (`backend/app/alembic/versions/add_performance_indexes.py`):
```python
"""Add performance indexes

Revision ID: perf_indexes_001
Revises: f19ecfe187cf
Create Date: 2025-06-20

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # User table indexes
    op.create_index('idx_users_canvas_id', 'user', ['canvas_id'])
    op.create_index('idx_users_created_at', 'user', ['created_at'])
    op.create_index('idx_users_updated_at', 'user', ['updated_at'])

    # Composite indexes for common queries
    op.create_index('idx_users_canvas_id_active', 'user', ['canvas_id', 'access_token'])

    # Future indexes for questions/quizzes when implemented
    # op.create_index('idx_questions_course_id', 'question', ['course_id'])
    # op.create_index('idx_questions_difficulty', 'question', ['difficulty'])
    # op.create_index('idx_quizzes_user_created', 'quiz', ['user_id', 'created_at'])

def downgrade():
    op.drop_index('idx_users_canvas_id')
    op.drop_index('idx_users_created_at')
    op.drop_index('idx_users_updated_at')
    op.drop_index('idx_users_canvas_id_active')
```

**Optimized Database Configuration** (`backend/app/core/db.py`):
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlmodel import Session

# Enhanced engine configuration
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    poolclass=QueuePool,
    pool_size=20,  # Connections to maintain
    max_overflow=30,  # Additional connections if needed
    pool_pre_ping=True,  # Validate connections
    pool_recycle=3600,  # Recycle connections every hour
    echo=settings.ENVIRONMENT == "local",  # SQL logging in development
    future=True,
)

# Query optimization utilities
class OptimizedQueries:
    @staticmethod
    def get_user_with_courses(session: Session, canvas_id: int):
        """Optimized query to get user with related data"""
        return session.exec(
            select(User)
            .where(User.canvas_id == canvas_id)
            .options(selectinload(User.courses))  # Eager load if relation exists
        ).first()

    @staticmethod
    def get_recent_users(session: Session, limit: int = 50):
        """Get recent users with proper indexing"""
        return session.exec(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
        ).all()
```

**Database Monitoring** (`backend/app/core/db_monitor.py`):
```python
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
import structlog

logger = structlog.get_logger()

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()
    logger.debug(
        "sql_query_start",
        statement=statement[:200] + "..." if len(statement) > 200 else statement
    )

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time

    if total > 1.0:  # Log slow queries
        logger.warning(
            "slow_query",
            duration=total,
            statement=statement[:200] + "..." if len(statement) > 200 else statement
        )

    logger.debug("sql_query_complete", duration=total)
```

---

### 8. **Security Headers & HTTPS Configuration**

#### Why Essential
Security headers protect against common web vulnerabilities like XSS, clickjacking, and man-in-the-middle attacks. They're essential for any web application handling sensitive data.

#### Current State
- Basic CORS configuration
- No security headers
- HTTPS handled by Traefik but not enforced in application

#### Implementation Plan

**Security Headers Middleware** (`backend/app/core/security_headers.py`):
```python
from fastapi import Request, Response

async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)

    # Security headers
    security_headers = {
        # Prevent XSS attacks
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",

        # HTTPS enforcement
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",

        # Content Security Policy - adjust based on your needs
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.sentry.io; "
            "frame-ancestors 'none'"
        ),

        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",

        # Permissions policy
        "Permissions-Policy": (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "fullscreen=(self)"
        )
    }

    for header, value in security_headers.items():
        response.headers[header] = value

    return response

# Add to main.py
app.middleware("http")(security_headers_middleware)
```

**Enhanced Environment Security** (`backend/app/core/config.py` additions):
```python
class Settings(BaseSettings):
    # ... existing settings

    # Security settings
    SECURE_COOKIES: bool = True
    SAME_SITE_COOKIES: str = "lax"
    HTTPS_ONLY: bool = False  # Set to True in production

    # API Security
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    @computed_field
    @property
    def COOKIE_SECURE(self) -> bool:
        return self.HTTPS_ONLY and self.ENVIRONMENT != "local"

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        if self.ENVIRONMENT == "production":
            if not self.HTTPS_ONLY:
                raise ValueError("HTTPS must be enabled in production")
            if "localhost" in self.ALLOWED_HOSTS:
                raise ValueError("localhost not allowed in production ALLOWED_HOSTS")
        return self
```

---

### 9. **Comprehensive Testing Strategy**

#### Why Essential
Testing ensures code reliability, prevents regressions, enables confident refactoring, and is essential for maintaining code quality as the application grows.

#### Current State
- Basic test structure exists
- Limited test coverage
- No integration tests for Canvas API
- No performance/load testing

#### Implementation Plan

**Enhanced Test Configuration** (`backend/app/tests/conftest.py` additions):
```python
import pytest
import asyncio
from httpx import AsyncClient
from sqlmodel import create_engine, Session
from sqlmodel.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.db import get_session
from app.core.config import settings

# Test database
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
async def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

# Mock Canvas API responses
@pytest.fixture
def mock_canvas_api():
    """Mock Canvas API responses for testing"""
    mock_responses = {
        "token_response": {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600,
            "user": {
                "id": 12345,
                "name": "Test User"
            }
        },
        "courses_response": [
            {
                "id": 1,
                "name": "Test Course",
                "course_code": "TEST101"
            }
        ]
    }
    return mock_responses
```

**API Integration Tests** (`backend/app/tests/api/test_canvas_integration.py`):
```python
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_canvas_oauth_flow(client: AsyncClient, mock_canvas_api):
    """Test complete Canvas OAuth flow"""

    # Test login redirect
    response = await client.get("/api/v1/auth/login/canvas")
    assert response.status_code == 307
    assert "canvas" in response.headers["location"]

    # Mock Canvas token exchange
    with patch("app.api.routes.auth.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_canvas_api["token_response"]
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        # Test callback
        response = await client.get(
            "/api/v1/auth/callback/canvas?code=test_code&state=test_state"
        )
        assert response.status_code == 307
        assert "login/success" in response.headers["location"]

@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient):
    """Test API rate limiting"""
    # Make requests up to the limit
    for i in range(10):
        response = await client.get("/api/v1/auth/login/canvas")
        if i < 9:
            assert response.status_code in [200, 307]  # Normal responses
        else:
            assert response.status_code == 429  # Rate limited
```

**Performance Tests** (`backend/app/tests/performance/test_load.py`):
```python
import pytest
import asyncio
import time
from httpx import AsyncClient

@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_user_creation(client: AsyncClient):
    """Test concurrent user creation performance"""

    async def create_user(user_id: int):
        start_time = time.time()
        # Simulate user creation
        response = await client.post("/api/v1/users/", json={
            "canvas_id": user_id,
            "name": f"Test User {user_id}",
            "access_token": f"token_{user_id}",
            "refresh_token": f"refresh_{user_id}"
        })
        end_time = time.time()
        return response.status_code, end_time - start_time

    # Create 50 users concurrently
    tasks = [create_user(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    # Assert all requests succeeded
    success_count = sum(1 for status, _ in results if status == 200)
    assert success_count >= 45  # Allow for some failures

    # Assert reasonable response times
    avg_time = sum(time for _, time in results) / len(results)
    assert avg_time < 1.0  # Average under 1 second
```

**Frontend Testing Enhancement** (`frontend/tests/integration/api.spec.ts`):
```typescript
import { test, expect } from '@playwright/test';

test.describe('API Integration', () => {
  test('handles authentication flow', async ({ page, context }) => {
    // Start at login page
    await page.goto('/login');

    // Click Canvas login button
    await page.click('[data-testid="canvas-login-button"]');

    // Should redirect to Canvas (in test, mock this)
    await expect(page).toHaveURL(/.*canvas.*/);

    // Mock successful callback
    await page.goto('/login/success?token=mock_jwt_token');

    // Should be redirected to dashboard
    await expect(page).toHaveURL('/dashboard');

    // Should show user info
    await expect(page.locator('[data-testid="user-name"]')).toBeVisible();
  });

  test('handles API errors gracefully', async ({ page }) => {
    // Mock API to return errors
    await page.route('**/api/v1/**', route => {
      route.fulfill({ status: 500, body: 'Server Error' });
    });

    await page.goto('/dashboard');

    // Should show error boundary
    await expect(page.locator('[data-testid="error-boundary"]')).toBeVisible();

    // Should have reload button
    await expect(page.locator('button:has-text("Reload")')).toBeVisible();
  });
});
```

---

## Implementation Priority & Timeline

### Phase 1 (Immediate - 1-2 weeks)
1. **Logging & Observability** - Essential for debugging current issues
2. **Error Handling** - Critical for user experience
3. **Security Headers** - Basic security hygiene

### Phase 2 (Short-term - 2-4 weeks)
4. **Health Monitoring** - Required for production deployment
5. **Input Validation** - Security and data integrity
6. **Rate Limiting** - Protect Canvas API integration

### Phase 3 (Medium-term - 1-2 months)
7. **Caching Strategy** - Performance optimization
8. **Database Optimization** - Scalability preparation
9. **Comprehensive Testing** - Long-term maintainability

## Conclusion

Your Rag@UiT application has a solid foundation with modern frameworks and good architectural decisions. However, implementing these essential features will transform it from a functional prototype into a production-ready, enterprise-grade application.

The most critical immediate needs are logging, error handling, and security headers. These provide the foundation for operating and debugging a production system. The remaining features can be implemented iteratively based on your specific performance and scalability requirements.

Remember: **These features aren't optional extras—they're essential components of any robust software product.** Implementing them early will save countless hours of debugging, security incidents, and user frustration down the line.

Each feature includes specific implementation plans tailored to your current FastAPI + React + TypeScript stack, making them immediately actionable for your development process.
