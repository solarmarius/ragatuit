# 11. Caching Layer Implementation

## Priority: High

**Estimated Effort**: 3 days
**Python Version**: 3.10+
**Dependencies**: Redis, asyncio-redis, typing

## Problem Statement

### Current Situation

The application lacks a caching layer for expensive operations, causing repeated database queries, redundant LLM API calls, and slow response times for frequently accessed data like user quizzes, Canvas course content, and generated questions.

### Why It's a Problem

- **Performance Issues**: Repeated expensive operations slow down response times
- **Resource Waste**: Unnecessary database queries and LLM API calls
- **Cost Impact**: Repeated LLM calls increase operational costs
- **User Experience**: Slow page loads and interactions
- **Scalability Limits**: Database becomes bottleneck under load
- **API Rate Limits**: Excessive Canvas API calls may hit rate limits

### Affected Modules

- `app/crud.py` - Database operations without caching
- `app/services/mcq_generation.py` - No caching of generated questions
- `app/services/content_extraction.py` - Repeated Canvas API calls
- All API routes with frequent data access
- Database performance under load

### Technical Debt Assessment

- **Risk Level**: High - Performance and cost impact
- **Impact**: All data access operations and user experience
- **Cost of Delay**: Increases with user growth and data volume

## Current Implementation Analysis

```python
# File: app/crud.py (current - no caching)
def get_user_quizzes(session: Session, user_id: UUID) -> list[Quiz]:
    """
    Get all quizzes for a user.

    PROBLEM: Executes database query every time, even for unchanged data
    """
    statement = select(Quiz).where(Quiz.owner_id == user_id).order_by(desc(Quiz.created_at))
    return list(session.exec(statement).all())  # Always hits database

def get_quiz_questions(session: Session, quiz_id: UUID) -> list[Question]:
    """
    Get all questions for a quiz.

    PROBLEM: No caching of questions, even when they haven't changed
    """
    statement = select(Question).where(Question.quiz_id == quiz_id).order_by(Question.created_at)
    return list(session.exec(statement).all())

# File: app/services/content_extraction.py (current)
class ContentExtractionService:
    async def extract_content_for_modules(self, module_ids: list[int]) -> dict[str, Any]:
        """
        Extract content from Canvas modules.

        PROBLEM: Repeated API calls for same modules, no caching
        """
        extracted_content = {}
        for module_id in module_ids:
            # Always makes API call, even for recently fetched modules
            module_content = await self._fetch_module_items(module_id)
            extracted_content[str(module_id)] = module_content
        return extracted_content

# File: app/services/mcq_generation.py (current)
class MCQGenerationService:
    async def generate_mcqs_for_quiz(self, quiz_id: UUID, ...) -> dict[str, Any]:
        """
        Generate MCQs for a quiz.

        PROBLEM: No caching of generated questions or intermediate results
        """
        # Always regenerates questions, even for same content
        # No caching of LLM responses or processed content
        result = await self._execute_generation_workflow(...)
        return result
```

### Performance Impact

```python
# Current performance issues without caching:

# User dashboard loading:
# - 5 database queries for each quiz (no caching)
# - 200ms+ response time for 20 quiz list

# Content extraction:
# - Same Canvas modules fetched multiple times
# - 2-5 seconds for repeated extractions

# Question generation:
# - No reuse of similar content processing
# - $0.50+ for each generation, even for duplicate requests
```

### Python Anti-patterns Identified

- **No Memoization**: Expensive computations repeated
- **Missing Cache Invalidation**: No strategy for cache updates
- **No Cache Hierarchy**: All operations at same cache level
- **No Cache Warming**: Cold cache performance issues
- **No Cache Monitoring**: No visibility into cache effectiveness

## Proposed Solution

### Pythonic Approach

Implement a multi-layered caching system using Redis for distributed caching, in-memory caching for hot data, and intelligent cache invalidation strategies with proper async support and type safety.

### Design Patterns

- **Cache-Aside Pattern**: Application manages cache explicitly
- **Write-Through Cache**: Update cache on data changes
- **Cache Hierarchy**: Multiple cache levels (memory, Redis, DB)
- **Decorator Pattern**: Easy cache application to functions
- **Observer Pattern**: Cache invalidation on data changes

### Code Examples

```python
# File: app/core/cache.py (NEW)
import asyncio
import json
import pickle
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Callable, TypeVar, Generic, Union
from functools import wraps
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("cache")

T = TypeVar('T')

class CacheLevel(str, Enum):
    """Cache level priorities."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"

class CacheStrategy(str, Enum):
    """Cache update strategies."""
    CACHE_ASIDE = "cache_aside"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"

@dataclass
class CacheConfig:
    """Configuration for cache behavior."""
    ttl_seconds: int = 300  # 5 minutes default
    max_size: Optional[int] = None
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    serialize_json: bool = True
    compress: bool = False
    namespace: str = "default"

class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

class InMemoryCache(CacheBackend):
    """In-memory cache implementation with LRU eviction."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check expiration
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            await self.delete(key)
            return None

        # Update access time for LRU
        self._access_times[key] = time.time()

        return entry["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            await self._evict_lru()

        expires_at = None
        if ttl:
            expires_at = time.time() + ttl

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time()
        }
        self._access_times[key] = time.time()

        return True

    async def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        deleted = key in self._cache
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        return deleted

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear memory cache."""
        if pattern:
            # Simple pattern matching (supports * wildcard)
            import fnmatch
            to_delete = [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
            for key in to_delete:
                await self.delete(key)
            return len(to_delete)
        else:
            count = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            return count

    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        return key in self._cache

    async def _evict_lru(self):
        """Evict least recently used item."""
        if not self._access_times:
            return

        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        await self.delete(lru_key)

class RedisCache(CacheBackend):
    """Redis-based cache implementation."""

    def __init__(self, redis_url: str, namespace: str = "cache"):
        self.redis_url = redis_url
        self.namespace = namespace
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client with connection pooling."""
        if not self._client:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Handle binary data
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
        return self._client

    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)

            data = await client.get(redis_key)
            if data is None:
                return None

            # Deserialize data
            try:
                return pickle.loads(data)
            except (pickle.PickleError, TypeError):
                # Fallback to string
                return data.decode('utf-8') if isinstance(data, bytes) else data

        except Exception as e:
            logger.error("redis_cache_get_error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)

            # Serialize data
            try:
                data = pickle.dumps(value)
            except (pickle.PickleError, TypeError):
                # Fallback to string
                data = str(value).encode('utf-8')

            if ttl:
                await client.setex(redis_key, ttl, data)
            else:
                await client.set(redis_key, data)

            return True

        except Exception as e:
            logger.error("redis_cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)
            result = await client.delete(redis_key)
            return result > 0

        except Exception as e:
            logger.error("redis_cache_delete_error", key=key, error=str(e))
            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear Redis cache entries."""
        try:
            client = await self._get_client()

            if pattern:
                redis_pattern = self._make_key(pattern)
                keys = await client.keys(redis_pattern)
                if keys:
                    return await client.delete(*keys)
                return 0
            else:
                # Clear all keys in namespace
                pattern = self._make_key("*")
                keys = await client.keys(pattern)
                if keys:
                    return await client.delete(*keys)
                return 0

        except Exception as e:
            logger.error("redis_cache_clear_error", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)
            return await client.exists(redis_key) > 0

        except Exception as e:
            logger.error("redis_cache_exists_error", key=key, error=str(e))
            return False

class MultiLevelCache:
    """Multi-level cache with L1 (memory) and L2 (Redis) caching."""

    def __init__(
        self,
        l1_cache: Optional[CacheBackend] = None,
        l2_cache: Optional[CacheBackend] = None,
        config: Optional[CacheConfig] = None
    ):
        self.l1_cache = l1_cache or InMemoryCache(max_size=500)
        self.l2_cache = l2_cache
        self.config = config or CacheConfig()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            logger.debug("cache_hit_l1", key=key)
            return value

        # Try L2 cache
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                logger.debug("cache_hit_l2", key=key)
                # Promote to L1 cache
                await self.l1_cache.set(key, value, self.config.ttl_seconds)
                return value

        logger.debug("cache_miss", key=key)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in multi-level cache."""
        cache_ttl = ttl or self.config.ttl_seconds

        # Set in L1 cache
        l1_success = await self.l1_cache.set(key, value, cache_ttl)

        # Set in L2 cache
        l2_success = True
        if self.l2_cache:
            l2_success = await self.l2_cache.set(key, value, cache_ttl)

        return l1_success and l2_success

    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels."""
        l1_deleted = await self.l1_cache.delete(key)
        l2_deleted = True

        if self.l2_cache:
            l2_deleted = await self.l2_cache.delete(key)

        return l1_deleted or l2_deleted

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear entries from all cache levels."""
        l1_cleared = await self.l1_cache.clear(pattern)
        l2_cleared = 0

        if self.l2_cache:
            l2_cleared = await self.l2_cache.clear(pattern)

        return l1_cleared + l2_cleared

class CacheManager:
    """Central cache manager with different cache configurations."""

    def __init__(self):
        self._caches: Dict[str, MultiLevelCache] = {}
        self._default_config = CacheConfig()

    def register_cache(
        self,
        name: str,
        config: Optional[CacheConfig] = None,
        l1_cache: Optional[CacheBackend] = None,
        l2_cache: Optional[CacheBackend] = None
    ):
        """Register a named cache with specific configuration."""
        cache_config = config or self._default_config

        # Create L2 cache if Redis is configured
        if not l2_cache and settings.REDIS_URL:
            l2_cache = RedisCache(settings.REDIS_URL, namespace=f"cache:{name}")

        self._caches[name] = MultiLevelCache(l1_cache, l2_cache, cache_config)

    def get_cache(self, name: str) -> MultiLevelCache:
        """Get cache by name."""
        if name not in self._caches:
            self.register_cache(name)
        return self._caches[name]

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all caches matching pattern."""
        for cache in self._caches.values():
            await cache.clear(pattern)

# Global cache manager instance
cache_manager = CacheManager()

# Cache decorators
def cached(
    cache_name: str = "default",
    ttl: int = 300,
    key_builder: Optional[Callable] = None,
    condition: Optional[Callable] = None
):
    """
    Decorator for caching function results.

    Args:
        cache_name: Name of cache to use
        ttl: Time to live in seconds
        key_builder: Custom function to build cache key
        condition: Function to determine if result should be cached
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            cache = cache_manager.get_cache(cache_name)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _build_default_key(func.__name__, args, kwargs)

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug("function_cache_hit", function=func.__name__, key=cache_key)
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result if condition is met
            should_cache = condition(result) if condition else True
            if should_cache:
                await cache.set(cache_key, result, ttl)
                logger.debug("function_cached", function=func.__name__, key=cache_key)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator

def cache_invalidate(cache_name: str = "default", key_pattern: str = "*"):
    """Decorator to invalidate cache after function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate cache
            cache = cache_manager.get_cache(cache_name)
            await cache.clear(key_pattern)

            logger.debug("cache_invalidated", function=func.__name__, pattern=key_pattern)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator

def _build_default_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Build default cache key from function name and arguments."""
    import hashlib

    # Convert args and kwargs to string representation
    key_parts = [func_name]

    for arg in args:
        if hasattr(arg, 'id'):  # Handle models with ID
            key_parts.append(f"{type(arg).__name__}:{arg.id}")
        else:
            key_parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        if hasattr(value, 'id'):
            key_parts.append(f"{key}:{type(value).__name__}:{value.id}")
        else:
            key_parts.append(f"{key}:{value}")

    # Create hash of key parts
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

# File: app/services/cached_crud.py (NEW)
from typing import List, Optional
from uuid import UUID

from app.core.cache import cached, cache_invalidate, cache_manager
from app.models import Quiz, Question, User
from app import crud

# Configure caches for different data types
cache_manager.register_cache("users", CacheConfig(ttl_seconds=600))  # 10 minutes
cache_manager.register_cache("quizzes", CacheConfig(ttl_seconds=300))  # 5 minutes
cache_manager.register_cache("questions", CacheConfig(ttl_seconds=180))  # 3 minutes
cache_manager.register_cache("canvas_content", CacheConfig(ttl_seconds=1800))  # 30 minutes

class CachedUserOperations:
    """User operations with caching."""

    @staticmethod
    @cached(cache_name="users", ttl=600)
    async def get_user(session, user_id: UUID) -> Optional[User]:
        """Get user with caching."""
        return crud.get_user(session, user_id)

    @staticmethod
    @cached(
        cache_name="users",
        ttl=300,
        key_builder=lambda session, email: f"user:email:{email}"
    )
    async def get_user_by_email(session, email: str) -> Optional[User]:
        """Get user by email with caching."""
        return crud.get_user_by_email(session, email)

    @staticmethod
    @cache_invalidate(cache_name="users", key_pattern="user:*")
    async def update_user(session, user: User, user_update) -> User:
        """Update user and invalidate cache."""
        return crud.update_user(session, user, user_update)

class CachedQuizOperations:
    """Quiz operations with intelligent caching."""

    @staticmethod
    @cached(
        cache_name="quizzes",
        ttl=300,
        key_builder=lambda session, user_id, **kwargs: f"user_quizzes:{user_id}:{hash(str(kwargs))}"
    )
    async def get_user_quizzes(
        session,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None
    ) -> List[Quiz]:
        """Get user quizzes with caching."""
        from app.repositories.quiz import QuizRepository
        from app.models.pagination import PaginationParams

        repo = QuizRepository(session)
        pagination = PaginationParams(skip=skip, limit=limit)
        quizzes, _ = repo.get_by_owner(user_id, pagination, status_filter)
        return quizzes

    @staticmethod
    @cached(cache_name="quizzes", ttl=600)
    async def get_quiz_by_id(session, quiz_id: UUID) -> Optional[Quiz]:
        """Get quiz by ID with caching."""
        return crud.get_quiz_by_id(session, quiz_id)

    @staticmethod
    @cached(
        cache_name="quizzes",
        ttl=900,  # Longer cache for quiz with questions
        key_builder=lambda session, quiz_id, approved_only=False: f"quiz_with_questions:{quiz_id}:{approved_only}"
    )
    async def get_quiz_with_questions(
        session,
        quiz_id: UUID,
        approved_only: bool = False
    ) -> Optional[Quiz]:
        """Get quiz with questions with caching."""
        from app.repositories.quiz import QuizRepository

        repo = QuizRepository(session)
        return repo.get_with_questions(quiz_id, approved_only)

    @staticmethod
    @cache_invalidate(cache_name="quizzes", key_pattern="*")
    async def create_quiz(session, quiz_data, owner_id: UUID) -> Quiz:
        """Create quiz and invalidate related caches."""
        quiz = crud.create_quiz(session, quiz_data, owner_id)

        # Also invalidate user quizzes cache
        user_cache = cache_manager.get_cache("quizzes")
        await user_cache.clear(f"user_quizzes:{owner_id}:*")

        return quiz

    @staticmethod
    @cache_invalidate(cache_name="quizzes", key_pattern="*")
    async def update_quiz(session, quiz: Quiz, quiz_update) -> Quiz:
        """Update quiz and invalidate caches."""
        updated_quiz = crud.update_quiz(session, quiz, quiz_update)

        # Invalidate specific quiz caches
        quiz_cache = cache_manager.get_cache("quizzes")
        await quiz_cache.clear(f"quiz_with_questions:{quiz.id}:*")

        return updated_quiz

class CachedQuestionOperations:
    """Question operations with caching."""

    @staticmethod
    @cached(
        cache_name="questions",
        ttl=180,
        key_builder=lambda session, quiz_id, **kwargs: f"quiz_questions:{quiz_id}:{hash(str(kwargs))}"
    )
    async def get_quiz_questions(
        session,
        quiz_id: UUID,
        approved_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Question]:
        """Get quiz questions with caching."""
        from app.repositories.question import QuestionRepository

        repo = QuestionRepository(session)
        return repo.get_by_quiz(quiz_id, approved_only, skip, limit)

    @staticmethod
    @cached(
        cache_name="questions",
        ttl=300,
        key_builder=lambda session, quiz_id: f"question_stats:{quiz_id}"
    )
    async def get_question_statistics(session, quiz_id: UUID) -> dict:
        """Get question statistics with caching."""
        from app.repositories.question import QuestionRepository

        repo = QuestionRepository(session)
        return repo.get_statistics(quiz_id)

    @staticmethod
    @cache_invalidate(cache_name="questions", key_pattern="*")
    async def approve_questions_bulk(session, question_ids: List[UUID]) -> int:
        """Bulk approve questions and invalidate caches."""
        from app.repositories.question import QuestionRepository

        repo = QuestionRepository(session)
        result = repo.bulk_approve(question_ids)

        # Invalidate quiz caches too (questions affect quiz state)
        quiz_cache = cache_manager.get_cache("quizzes")
        await quiz_cache.clear("quiz_with_questions:*")

        return result

# File: app/services/cached_content_extraction.py (NEW)
from typing import Dict, Any, List
from app.core.cache import cached, CacheConfig, cache_manager
from app.services.content_extraction import ContentExtractionService

# Configure Canvas content cache with longer TTL
cache_manager.register_cache(
    "canvas_content",
    CacheConfig(ttl_seconds=1800, namespace="canvas")  # 30 minutes
)

class CachedContentExtractionService(ContentExtractionService):
    """Content extraction service with caching."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = cache_manager.get_cache("canvas_content")

    @cached(
        cache_name="canvas_content",
        ttl=1800,
        key_builder=lambda self, module_id: f"module_items:{self.course_id}:{module_id}"
    )
    async def _fetch_module_items(self, module_id: int) -> List[Dict[str, Any]]:
        """Fetch module items with caching."""
        return await super()._fetch_module_items(module_id)

    @cached(
        cache_name="canvas_content",
        ttl=3600,  # 1 hour for page content
        key_builder=lambda self, page_url: f"page_content:{self.course_id}:{page_url}"
    )
    async def _fetch_page_content(self, page_url: str) -> Dict[str, Any]:
        """Fetch page content with caching."""
        return await super()._fetch_page_content(page_url)

    @cached(
        cache_name="canvas_content",
        ttl=7200,  # 2 hours for file content
        key_builder=lambda self, file_id: f"file_content:{self.course_id}:{file_id}"
    )
    async def _fetch_file_content(self, file_id: int) -> str:
        """Fetch file content with caching."""
        return await super()._fetch_file_content(file_id)

    async def extract_content_for_modules(self, module_ids: List[int]) -> Dict[str, Any]:
        """Extract content with intelligent caching."""
        cache_key = f"extracted_content:{self.course_id}:{hash(tuple(sorted(module_ids)))}"

        # Check if complete extraction is cached
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            logger.info(
                "content_extraction_cache_hit",
                course_id=self.course_id,
                module_count=len(module_ids)
            )
            return cached_result

        # Extract content (with individual module caching)
        result = await super().extract_content_for_modules(module_ids)

        # Cache the complete result
        await self.cache.set(cache_key, result, 1800)  # 30 minutes

        return result

# File: app/services/cached_mcq_generation.py (NEW)
from typing import Dict, Any
from uuid import UUID
from app.core.cache import cached, cache_manager, CacheConfig
from app.services.mcq_generation import MCQGenerationService

# Configure MCQ generation cache
cache_manager.register_cache(
    "mcq_generation",
    CacheConfig(ttl_seconds=3600, namespace="mcq")  # 1 hour
)

class CachedMCQGenerationService(MCQGenerationService):
    """MCQ generation service with caching."""

    @cached(
        cache_name="mcq_generation",
        ttl=3600,
        key_builder=lambda self, content, **kwargs: f"processed_content:{hash(content)}",
        condition=lambda result: len(result) > 100  # Only cache substantial content
    )
    async def _process_content_chunk(self, content: str) -> str:
        """Process content chunk with caching."""
        return await super()._process_content_chunk(content)

    @cached(
        cache_name="mcq_generation",
        ttl=7200,  # 2 hours for generated questions
        key_builder=lambda self, processed_content, model, temperature:
            f"generated_mcq:{hash(processed_content)}:{model}:{temperature}",
        condition=lambda result: result is not None  # Only cache successful generations
    )
    async def _generate_single_question(
        self,
        processed_content: str,
        model: str = "gpt-4",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate single question with caching."""
        return await super()._generate_single_question(processed_content, model, temperature)

    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float,
        session
    ) -> Dict[str, Any]:
        """Generate MCQs with intelligent caching."""

        # Build cache key based on quiz content and parameters
        quiz = session.get(Quiz, quiz_id)
        if not quiz or not quiz.content_dict:
            return await super().generate_mcqs_for_quiz(
                quiz_id, target_count, model, temperature, session
            )

        content_hash = hash(str(quiz.content_dict))
        cache_key = f"quiz_mcq_generation:{quiz_id}:{content_hash}:{target_count}:{model}:{temperature}"

        cache = cache_manager.get_cache("mcq_generation")
        cached_result = await cache.get(cache_key)

        if cached_result:
            logger.info(
                "mcq_generation_cache_hit",
                quiz_id=str(quiz_id),
                target_count=target_count
            )
            return cached_result

        # Generate questions
        result = await super().generate_mcqs_for_quiz(
            quiz_id, target_count, model, temperature, session
        )

        # Cache successful generation
        if result.get("status") == "completed":
            await cache.set(cache_key, result, 3600)  # 1 hour

        return result
```

## Implementation Details

### Files to Create/Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── cache.py                 # NEW: Core caching infrastructure
│   │   └── config.py                # UPDATE: Add cache settings
│   ├── services/
│   │   ├── cached_crud.py           # NEW: Cached CRUD operations
│   │   ├── cached_content_extraction.py  # NEW: Cached content service
│   │   ├── cached_mcq_generation.py # NEW: Cached MCQ service
│   │   └── cache_warming.py         # NEW: Cache warming strategies
│   ├── middleware/
│   │   └── cache_middleware.py      # NEW: HTTP response caching
│   ├── api/
│   │   └── routes/
│   │       ├── quiz.py              # UPDATE: Use cached operations
│   │       └── cache_admin.py       # NEW: Cache management endpoints
│   └── tests/
│       ├── core/
│       │   └── test_cache.py        # NEW: Cache tests
│       └── services/
│           └── test_cached_operations.py  # NEW: Cached service tests
```

### Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Cache configuration
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_REDIS_URL: Optional[str] = None
    CACHE_MEMORY_MAX_SIZE: int = 1000

    # Cache TTL settings by type
    CACHE_USER_TTL: int = 600      # 10 minutes
    CACHE_QUIZ_TTL: int = 300      # 5 minutes
    CACHE_QUESTION_TTL: int = 180  # 3 minutes
    CACHE_CANVAS_CONTENT_TTL: int = 1800  # 30 minutes
    CACHE_MCQ_GENERATION_TTL: int = 3600  # 1 hour

    # Cache warming
    CACHE_WARMING_ENABLED: bool = True
    CACHE_WARMING_BATCH_SIZE: int = 50
```

### Dependencies

```toml
# pyproject.toml additions
[project.dependencies]
redis = {version = ">=4.0.0", optional = true}

[project.optional-dependencies]
cache = ["redis>=4.0.0"]
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_cache.py
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock

from app.core.cache import (
    InMemoryCache,
    RedisCache,
    MultiLevelCache,
    CacheManager,
    cached,
    cache_invalidate
)

@pytest.mark.asyncio
async def test_in_memory_cache_basic_operations():
    """Test basic in-memory cache operations."""
    cache = InMemoryCache(max_size=10)

    # Test set and get
    await cache.set("test_key", "test_value", ttl=60)
    value = await cache.get("test_key")
    assert value == "test_value"

    # Test expiration
    await cache.set("expire_key", "expire_value", ttl=1)
    await asyncio.sleep(1.1)
    value = await cache.get("expire_key")
    assert value is None

    # Test delete
    await cache.set("delete_key", "delete_value")
    assert await cache.exists("delete_key") is True
    await cache.delete("delete_key")
    assert await cache.exists("delete_key") is False

@pytest.mark.asyncio
async def test_in_memory_cache_lru_eviction():
    """Test LRU eviction in memory cache."""
    cache = InMemoryCache(max_size=3)

    # Fill cache
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.set("key3", "value3")

    # Access key1 to make it recently used
    await cache.get("key1")

    # Add key4, should evict key2 (least recently used)
    await cache.set("key4", "value4")

    assert await cache.exists("key1") is True
    assert await cache.exists("key2") is False
    assert await cache.exists("key3") is True
    assert await cache.exists("key4") is True

@pytest.mark.asyncio
async def test_multi_level_cache():
    """Test multi-level cache behavior."""
    l1_cache = InMemoryCache(max_size=5)
    l2_cache = Mock()
    l2_cache.get = AsyncMock(return_value=None)
    l2_cache.set = AsyncMock(return_value=True)

    cache = MultiLevelCache(l1_cache, l2_cache)

    # Test cache miss and promotion
    l2_cache.get.return_value = "l2_value"

    value = await cache.get("test_key")
    assert value == "l2_value"

    # Should be promoted to L1
    l1_value = await l1_cache.get("test_key")
    assert l1_value == "l2_value"

def test_cached_decorator():
    """Test cached decorator functionality."""
    call_count = 0

    @cached(cache_name="test", ttl=60)
    async def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    async def test_caching():
        # First call should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different argument should execute function
        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    asyncio.run(test_caching())

# File: app/tests/services/test_cached_operations.py
def test_cached_quiz_operations(db_session, test_user):
    """Test cached quiz operations."""
    from app.services.cached_crud import CachedQuizOperations

    async def test_quiz_caching():
        # Create test quiz
        quiz_data = QuizCreate(
            title="Test Quiz",
            canvas_course_id=123,
            selected_modules={"456": "Module"}
        )

        # First call should hit database
        quiz = await CachedQuizOperations.create_quiz(
            db_session, quiz_data, test_user.id
        )

        # Second call should use cache
        cached_quiz = await CachedQuizOperations.get_quiz_by_id(
            db_session, quiz.id
        )

        assert cached_quiz.id == quiz.id
        assert cached_quiz.title == quiz.title

    asyncio.run(test_quiz_caching())

def test_cache_invalidation(db_session, test_user, test_quiz):
    """Test cache invalidation on updates."""
    from app.services.cached_crud import CachedQuizOperations

    async def test_invalidation():
        # Cache quiz
        cached_quiz = await CachedQuizOperations.get_quiz_by_id(
            db_session, test_quiz.id
        )

        # Update quiz (should invalidate cache)
        updated_quiz = await CachedQuizOperations.update_quiz(
            db_session, test_quiz, {"title": "Updated Title"}
        )

        # Next get should reflect update
        fresh_quiz = await CachedQuizOperations.get_quiz_by_id(
            db_session, test_quiz.id
        )

        assert fresh_quiz.title == "Updated Title"

    asyncio.run(test_invalidation())
```

### Performance Tests

```python
# File: app/tests/performance/test_cache_performance.py
@pytest.mark.performance
def test_cache_performance_improvement():
    """Test cache performance improvement."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    # Mock slow operation
    call_count = 0

    @cached(cache_name="performance_test", ttl=300)
    async def slow_operation(x: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate slow operation
        return x * 2

    async def test_performance():
        # Warm cache
        await slow_operation(1)

        # Measure cached vs uncached performance
        start_time = time.time()

        # 100 cached calls should be much faster
        tasks = [slow_operation(1) for _ in range(100)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()

        # Should complete quickly due to caching
        assert end_time - start_time < 1.0  # Much less than 10 seconds without cache
        assert all(r == 2 for r in results)
        assert call_count == 1  # Only called once

    asyncio.run(test_performance())

@pytest.mark.performance
def test_concurrent_cache_access():
    """Test cache performance under concurrent access."""

    async def concurrent_access_test():
        cache = InMemoryCache(max_size=100)

        async def worker(worker_id: int):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                await cache.set(key, f"value_{i}")
                value = await cache.get(key)
                assert value == f"value_{i}"

        # Run 10 workers concurrently
        start_time = time.time()
        tasks = [worker(i) for i in range(10)]
        await asyncio.gather(*tasks)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 5.0

    asyncio.run(concurrent_access_test())
```

### Integration Tests

```python
# File: app/tests/integration/test_end_to_end_caching.py
@pytest.mark.integration
def test_end_to_end_quiz_caching(client, test_user):
    """Test end-to-end caching in API endpoints."""

    headers = {"Authorization": f"Bearer {test_user.access_token}"}

    # Create quiz
    quiz_data = {
        "title": "Cached Quiz Test",
        "canvas_course_id": 123,
        "selected_modules": {"456": "Module"}
    }

    response = client.post("/api/quiz/", json=quiz_data, headers=headers)
    assert response.status_code == 201
    quiz_id = response.json()["id"]

    # First GET should populate cache
    start_time = time.time()
    response1 = client.get(f"/api/quiz/{quiz_id}", headers=headers)
    first_request_time = time.time() - start_time

    assert response1.status_code == 200

    # Second GET should be faster (cached)
    start_time = time.time()
    response2 = client.get(f"/api/quiz/{quiz_id}", headers=headers)
    second_request_time = time.time() - start_time

    assert response2.status_code == 200
    assert response1.json() == response2.json()

    # Cached request should be significantly faster
    assert second_request_time < first_request_time * 0.5
```

## Code Quality Improvements

### Cache Monitoring

```python
# File: app/api/routes/cache_admin.py
from fastapi import APIRouter, Depends, HTTPException
from app.core.cache import cache_manager

router = APIRouter(prefix="/admin/cache", tags=["cache"])

@router.get("/stats")
async def get_cache_stats():
    """Get cache statistics."""
    stats = {}

    for name, cache in cache_manager._caches.items():
        # Get cache-specific stats
        stats[name] = {
            "type": "multi_level",
            "l1_size": len(cache.l1_cache._cache) if hasattr(cache.l1_cache, '_cache') else 0,
            "l2_connected": cache.l2_cache is not None
        }

    return stats

@router.post("/clear/{cache_name}")
async def clear_cache(cache_name: str, pattern: str = "*"):
    """Clear specific cache."""
    if cache_name not in cache_manager._caches:
        raise HTTPException(404, f"Cache '{cache_name}' not found")

    cache = cache_manager.get_cache(cache_name)
    cleared_count = await cache.clear(pattern)

    return {"message": f"Cleared {cleared_count} entries from {cache_name}"}

@router.post("/warm")
async def warm_caches():
    """Warm up caches with frequently accessed data."""
    # Implementation for cache warming
    pass
```

### Cache Warming Strategy

```python
# File: app/services/cache_warming.py
import asyncio
from typing import List
from app.core.cache import cache_manager
from app.services.cached_crud import CachedQuizOperations, CachedUserOperations

class CacheWarmingService:
    """Service for warming up caches with frequently accessed data."""

    async def warm_user_caches(self, user_ids: List[UUID]):
        """Warm user-related caches."""
        tasks = []

        for user_id in user_ids:
            # Warm user cache
            tasks.append(self._warm_user_data(user_id))

            # Warm user quizzes cache
            tasks.append(self._warm_user_quizzes(user_id))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _warm_user_data(self, user_id: UUID):
        """Warm individual user data."""
        try:
            with get_session() as session:
                await CachedUserOperations.get_user(session, user_id)
        except Exception as e:
            logger.warning("cache_warming_failed", user_id=str(user_id), error=str(e))

    async def _warm_user_quizzes(self, user_id: UUID):
        """Warm user quizzes cache."""
        try:
            with get_session() as session:
                await CachedQuizOperations.get_user_quizzes(session, user_id)
        except Exception as e:
            logger.warning("quiz_cache_warming_failed", user_id=str(user_id), error=str(e))
```

## Migration Strategy

### Phase 1: Infrastructure Setup (Day 1)

1. Implement core caching infrastructure
2. Add Redis configuration and connection handling
3. Create comprehensive tests

### Phase 2: Gradual Cache Integration (Day 2)

1. Start with read-heavy operations (user quizzes, questions)
2. Add caching to content extraction service
3. Monitor cache hit rates and performance improvement

### Phase 3: Advanced Caching (Day 3)

1. Add MCQ generation result caching
2. Implement cache warming strategies
3. Add cache administration endpoints

### Feature Flag Implementation

```python
# Gradual rollout with feature flags
if settings.CACHE_ENABLED:
    # Use cached operations
    from app.services.cached_crud import CachedQuizOperations as QuizOps
else:
    # Use direct CRUD operations
    import app.crud as QuizOps
```

## Success Criteria

### Performance Metrics

- **Response Time Improvement**: 50-80% faster for cached operations
- **Database Load Reduction**: 60-70% fewer database queries
- **Cache Hit Rate**: >80% for frequently accessed data
- **Memory Usage**: Controlled memory growth with LRU eviction

### Cost Metrics

- **LLM API Cost Reduction**: 40-60% fewer redundant API calls
- **Database Resource Usage**: 50% reduction in query load
- **Server Response Capacity**: 2-3x more requests with same resources

### Operational Metrics

- **Cache Availability**: >99.9% uptime for Redis cache
- **Cache Warming Effectiveness**: <5s cold start times
- **Monitoring Coverage**: Complete visibility into cache performance

---
