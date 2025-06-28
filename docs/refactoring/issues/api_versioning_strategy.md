# 20. API Versioning Strategy

## Priority: Low

**Estimated Effort**: 3 days
**Python Version**: 3.10+
**Dependencies**: FastAPI, Pydantic

## Problem Statement

### Current Situation

The application has basic API versioning through a URL prefix (`/api/v1`) but lacks a comprehensive versioning strategy for handling breaking changes, deprecations, and client compatibility.

### Why It's a Problem

- **Breaking Changes**: No safe way to introduce breaking changes
- **Client Compatibility**: Cannot support multiple API versions
- **Deprecation Process**: No clear deprecation workflow
- **Version Discovery**: Clients cannot discover API capabilities
- **Migration Path**: No clear upgrade path for clients
- **Documentation**: Version differences not well documented

### Affected Modules

- `app/main.py` - Basic URL prefix only
- `app/api/` - All API routes
- `app/models.py` - Response models need versioning
- API documentation and client SDKs

### Technical Debt Assessment

- **Risk Level**: Low currently, increases with API maturity
- **Impact**: All API consumers
- **Cost of Delay**: Increases with number of clients

## Current Implementation Analysis

```python
# File: app/main.py (current basic versioning)
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# PROBLEM: Only URL prefix versioning
app.include_router(api_router, prefix=settings.API_V1_STR)  # "/api/v1"

# File: app/core/config.py
class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"  # That's it for versioning!

# Problems with current approach:
# 1. No version negotiation
# 2. No backward compatibility strategy
# 3. No deprecation warnings
# 4. No version-specific models
# 5. No API capability discovery

# Example breaking change scenario:
# Current v1 response:
{
    "id": "123",
    "title": "Quiz Title",
    "questions": ["q1", "q2"]  # Array of IDs
}

# New v2 needs:
{
    "id": "123",
    "title": "Quiz Title",
    "questions": [  # Array of objects
        {"id": "q1", "text": "Question 1"},
        {"id": "q2", "text": "Question 2"}
    ]
}
# No way to handle this transition!
```

### Current Client Issues

```python
# Client code breaks with API changes
response = requests.get("https://api.example.com/api/v1/quiz/123")
quiz = response.json()
# Assumes questions is array of strings - breaks if changed!
for question_id in quiz["questions"]:
    print(f"Question ID: {question_id}")

# No way to:
# - Detect API version
# - Handle multiple versions
# - Get deprecation warnings
# - Discover capabilities
```

### Python Anti-patterns Identified

- **No Version Strategy**: Just URL prefix
- **No Model Versioning**: Same models for all versions
- **No Deprecation Support**: Cannot warn about changes
- **No Content Negotiation**: Cannot use Accept headers
- **Missing Version Info**: No version in responses

## Proposed Solution

### Pythonic Approach

Implement a comprehensive API versioning strategy using FastAPI's advanced features, supporting multiple versioning methods, backward compatibility, and smooth migration paths.

### Versioning Methods

1. **URL Path Versioning**: `/api/v1/`, `/api/v2/` (current)
2. **Header Versioning**: `X-API-Version: 2`
3. **Accept Header**: `Accept: application/vnd.raguit.v2+json`
4. **Query Parameter**: `?version=2` (for testing)

### Code Examples

```python
# File: app/core/versioning.py (NEW)
from enum import Enum
from typing import Optional, Dict, Any, Callable
from datetime import datetime, date
from functools import wraps
from fastapi import Request, Header, Query, HTTPException
from pydantic import BaseModel
import warnings

class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "1.0"
    V2 = "2.0"
    V3 = "3.0"  # Future

    @property
    def deprecated(self) -> bool:
        """Check if version is deprecated."""
        return self in DEPRECATED_VERSIONS

    @property
    def sunset_date(self) -> Optional[date]:
        """Get sunset date for deprecated versions."""
        return SUNSET_DATES.get(self)

    def __le__(self, other):
        """Compare versions for compatibility."""
        return float(self.value) <= float(other.value)

DEPRECATED_VERSIONS = {APIVersion.V1}
SUNSET_DATES = {
    APIVersion.V1: date(2025, 6, 1)  # 6 months notice
}

CURRENT_VERSION = APIVersion.V2
MINIMUM_VERSION = APIVersion.V1

class VersionConfig:
    """Configuration for API versioning."""

    def __init__(
        self,
        default_version: APIVersion = CURRENT_VERSION,
        header_name: str = "X-API-Version",
        accept_pattern: str = "application/vnd.raguit.v{version}+json",
        allow_query_param: bool = True,
        query_param_name: str = "api_version"
    ):
        self.default_version = default_version
        self.header_name = header_name
        self.accept_pattern = accept_pattern
        self.allow_query_param = allow_query_param
        self.query_param_name = query_param_name

version_config = VersionConfig()

def get_api_version(
    request: Request,
    x_api_version: Optional[str] = Header(None),
    accept: Optional[str] = Header(None),
    api_version: Optional[str] = Query(None)
) -> APIVersion:
    """
    Determine API version from request.

    Priority:
    1. Custom header (X-API-Version)
    2. Accept header with version
    3. Query parameter (if allowed)
    4. URL path version
    5. Default version
    """

    # 1. Check custom header
    if x_api_version:
        try:
            return APIVersion(x_api_version)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API version: {x_api_version}"
            )

    # 2. Check Accept header
    if accept and "vnd.raguit" in accept:
        import re
        pattern = r'application/vnd\.raguit\.v(\d+(?:\.\d+)?)\+json'
        match = re.search(pattern, accept)
        if match:
            try:
                return APIVersion(match.group(1))
            except ValueError:
                pass

    # 3. Check query parameter
    if version_config.allow_query_param and api_version:
        try:
            return APIVersion(api_version)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API version: {api_version}"
            )

    # 4. Check URL path
    path = request.url.path
    if "/api/v1/" in path:
        return APIVersion.V1
    elif "/api/v2/" in path:
        return APIVersion.V2

    # 5. Default
    return version_config.default_version

# File: app/core/deprecation.py (NEW)
class DeprecationWarning:
    """Handle API deprecation warnings."""

    @staticmethod
    def add_deprecation_headers(
        response: Response,
        version: APIVersion,
        alternative: Optional[str] = None
    ):
        """Add deprecation headers to response."""

        if version.deprecated:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = version.sunset_date.isoformat()

            if alternative:
                response.headers["Link"] = f'<{alternative}>; rel="alternate"'

            # Add warning header
            days_until_sunset = (version.sunset_date - date.today()).days
            warning_text = (
                f"API version {version.value} is deprecated and will be "
                f"removed on {version.sunset_date}. "
                f"Please upgrade to version {CURRENT_VERSION.value}."
            )
            response.headers["Warning"] = f'299 - "{warning_text}"'

# File: app/api/versioned_router.py (NEW)
from fastapi import APIRouter, Depends
from typing import Dict, Type, Callable

class VersionedAPIRouter(APIRouter):
    """Router with version-specific endpoint handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.versioned_routes: Dict[str, Dict[APIVersion, Callable]] = {}

    def add_api_route(
        self,
        path: str,
        endpoint: Callable,
        *,
        versions: list[APIVersion] = None,
        deprecated_in: Optional[APIVersion] = None,
        removed_in: Optional[APIVersion] = None,
        **kwargs
    ):
        """Add route with version support."""

        if versions is None:
            versions = [v for v in APIVersion]

        # Create version dispatcher
        @wraps(endpoint)
        async def versioned_endpoint(
            request: Request,
            version: APIVersion = Depends(get_api_version),
            **params
        ):
            # Check if version supports this endpoint
            if removed_in and version >= removed_in:
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint not available in API version {version.value}"
                )

            if version not in versions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint not available in API version {version.value}"
                )

            # Get version-specific handler
            handler = self.versioned_routes.get(path, {}).get(
                version, endpoint
            )

            # Execute handler
            result = await handler(**params)

            # Add deprecation warnings if needed
            if deprecated_in and version >= deprecated_in:
                response = params.get('response')
                if response:
                    DeprecationWarning.add_deprecation_headers(
                        response, version
                    )

            return result

        # Register route
        super().add_api_route(path, versioned_endpoint, **kwargs)

    def version_handler(
        self,
        path: str,
        version: APIVersion
    ):
        """Decorator for version-specific handlers."""

        def decorator(func: Callable):
            if path not in self.versioned_routes:
                self.versioned_routes[path] = {}
            self.versioned_routes[path][version] = func
            return func

        return decorator

# File: app/models/versioned.py (NEW - Version-specific models)
from pydantic import BaseModel, Field
from typing import Union, List

# V1 Models
class QuizV1(BaseModel):
    """Quiz model for API v1."""
    id: str
    title: str
    questions: List[str] = Field(
        description="List of question IDs"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "123",
                "title": "Sample Quiz",
                "questions": ["q1", "q2", "q3"]
            }
        }

class QuestionV1(BaseModel):
    """Question model for API v1."""
    id: str
    text: str
    answer: str

# V2 Models
class QuestionSummaryV2(BaseModel):
    """Question summary for embedding in quiz."""
    id: str
    text: str
    order: int

class QuizV2(BaseModel):
    """Quiz model for API v2 with embedded questions."""
    id: str
    title: str
    description: Optional[str] = None
    questions: List[QuestionSummaryV2] = Field(
        description="List of question objects with id and text"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "123",
                "title": "Sample Quiz",
                "description": "A sample quiz for testing",
                "questions": [
                    {"id": "q1", "text": "Question 1?", "order": 1},
                    {"id": "q2", "text": "Question 2?", "order": 2}
                ],
                "metadata": {
                    "difficulty": "medium",
                    "tags": ["sample", "test"]
                }
            }
        }

class QuestionV2(BaseModel):
    """Enhanced question model for API v2."""
    id: str
    text: str
    correct_answer: str
    incorrect_answers: List[str]
    explanation: Optional[str] = None
    difficulty: str = "medium"
    tags: List[str] = Field(default_factory=list)

# Model mapping
VERSION_MODELS = {
    APIVersion.V1: {
        "Quiz": QuizV1,
        "Question": QuestionV1,
    },
    APIVersion.V2: {
        "Quiz": QuizV2,
        "Question": QuestionV2,
    }
}

def get_model_for_version(
    model_name: str,
    version: APIVersion
) -> Type[BaseModel]:
    """Get appropriate model for API version."""

    version_models = VERSION_MODELS.get(version, {})
    model = version_models.get(model_name)

    if not model:
        raise ValueError(
            f"Model {model_name} not found for version {version}"
        )

    return model

# File: app/api/routes/v2/quiz.py (Version-specific routes)
from app.api.versioned_router import VersionedAPIRouter

router = VersionedAPIRouter(prefix="/quiz", tags=["quiz"])

@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
    version: APIVersion = Depends(get_api_version),
) -> Union[QuizV1, QuizV2]:
    """Get quiz with version-specific response."""

    # Get quiz from database
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Return version-specific response
    if version == APIVersion.V1:
        # V1: Return question IDs only
        return QuizV1(
            id=str(quiz.id),
            title=quiz.title,
            questions=[str(q.id) for q in quiz.questions]
        )
    else:
        # V2: Return question summaries
        return QuizV2(
            id=str(quiz.id),
            title=quiz.title,
            description=quiz.description,
            questions=[
                QuestionSummaryV2(
                    id=str(q.id),
                    text=q.question_text,
                    order=q.order
                )
                for q in sorted(quiz.questions, key=lambda x: x.order)
            ],
            metadata={
                "created_at": quiz.created_at.isoformat(),
                "question_count": len(quiz.questions),
                "approved_count": sum(1 for q in quiz.questions if q.is_approved)
            }
        )

# Version-specific handler for complex changes
@router.version_handler("/bulk-approve", APIVersion.V1)
async def bulk_approve_v1(
    quiz_id: UUID,
    question_ids: List[str],  # V1 uses strings
    session: SessionDep,
) -> dict:
    """V1 bulk approval with string IDs."""
    # Convert string IDs to UUIDs
    uuid_ids = [UUID(id) for id in question_ids]
    # Process...

@router.version_handler("/bulk-approve", APIVersion.V2)
async def bulk_approve_v2(
    quiz_id: UUID,
    request: BulkApprovalRequestV2,  # V2 uses request object
    session: SessionDep,
) -> BulkApprovalResponseV2:
    """V2 bulk approval with structured request/response."""
    # Process with new structure...

# File: app/api/version_adapter.py (NEW - Version adaptation)
class VersionAdapter:
    """Adapt between different API versions."""

    @staticmethod
    def adapt_response(
        data: Any,
        from_version: APIVersion,
        to_version: APIVersion
    ) -> Any:
        """Adapt response data between versions."""

        if from_version == to_version:
            return data

        # Define adaptation rules
        if from_version == APIVersion.V2 and to_version == APIVersion.V1:
            # Downgrade V2 to V1
            if isinstance(data, QuizV2):
                return QuizV1(
                    id=data.id,
                    title=data.title,
                    questions=[q.id for q in data.questions]
                )

        return data

# File: app/middleware/version_middleware.py (NEW)
class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware for API version handling."""

    async def dispatch(self, request: Request, call_next):
        # Determine version early
        version = await get_api_version(request)
        request.state.api_version = version

        # Check if version is supported
        if version < MINIMUM_VERSION:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"API version {version.value} is no longer supported. "
                            f"Minimum version is {MINIMUM_VERSION.value}"
                }
            )

        # Process request
        response = await call_next(request)

        # Add version headers
        response.headers["X-API-Version"] = version.value
        response.headers["X-API-Version-Latest"] = CURRENT_VERSION.value

        # Add deprecation warnings
        if version.deprecated:
            DeprecationWarning.add_deprecation_headers(response, version)

        return response

# File: app/docs/version_docs.py (NEW - Version-specific docs)
def custom_openapi():
    """Generate version-specific OpenAPI schema."""

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=CURRENT_VERSION.value,
        description=f"""
        # Rag@UiT API Documentation

        **Current Version**: {CURRENT_VERSION.value}
        **Minimum Supported Version**: {MINIMUM_VERSION.value}

        ## Versioning

        This API supports multiple versioning methods:

        1. **URL Path**: `/api/v1/`, `/api/v2/`
        2. **Header**: `X-API-Version: 2.0`
        3. **Accept**: `Accept: application/vnd.raguit.v2+json`
        4. **Query**: `?api_version=2.0` (for testing)

        ## Deprecation Policy

        - Deprecated versions receive 6 months notice
        - Deprecation warnings in headers
        - Sunset dates clearly communicated

        ## Version History

        ### Version 2.0 (Current)
        - Enhanced quiz model with embedded questions
        - Structured error responses
        - Bulk operations support

        ### Version 1.0 (Deprecated)
        - Basic quiz operations
        - Simple question ID references
        - **Sunset Date**: {SUNSET_DATES[APIVersion.V1]}
        """,
        routes=app.routes,
    )

    # Add version-specific examples
    for path_data in openapi_schema["paths"].values():
        for operation in path_data.values():
            if "responses" in operation:
                # Add version header to all responses
                for response in operation["responses"].values():
                    if "headers" not in response:
                        response["headers"] = {}
                    response["headers"]["X-API-Version"] = {
                        "description": "API version used for response",
                        "schema": {"type": "string", "example": CURRENT_VERSION.value}
                    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── versioning.py            # NEW: Version management
│   │   ├── deprecation.py           # NEW: Deprecation handling
│   │   └── config.py                # UPDATE: Version settings
│   ├── api/
│   │   ├── versioned_router.py      # NEW: Version-aware router
│   │   ├── version_adapter.py       # NEW: Version adaptation
│   │   ├── v1/                      # Version 1 routes
│   │   │   └── quiz.py
│   │   └── v2/                      # Version 2 routes
│   │       └── quiz.py
│   ├── models/
│   │   ├── versioned.py             # NEW: Version models
│   │   ├── v1/                      # V1 models
│   │   └── v2/                      # V2 models
│   ├── middleware/
│   │   └── version_middleware.py    # NEW: Version middleware
│   ├── docs/
│   │   └── version_docs.py          # NEW: Version docs
│   ├── main.py                      # UPDATE: Add versioning
│   └── tests/
│       └── test_versioning.py       # NEW: Version tests
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/api/test_versioning.py
import pytest
from fastapi.testclient import TestClient

def test_version_detection_methods(client: TestClient):
    """Test different version detection methods."""

    # URL path version
    response = client.get("/api/v1/health")
    assert response.headers["X-API-Version"] == "1.0"

    # Header version
    response = client.get(
        "/api/health",
        headers={"X-API-Version": "2.0"}
    )
    assert response.headers["X-API-Version"] == "2.0"

    # Accept header version
    response = client.get(
        "/api/health",
        headers={"Accept": "application/vnd.raguit.v2+json"}
    )
    assert response.headers["X-API-Version"] == "2.0"

    # Query parameter version
    response = client.get("/api/health?api_version=2.0")
    assert response.headers["X-API-Version"] == "2.0"

def test_deprecation_warnings(client: TestClient):
    """Test deprecation warnings for old versions."""

    response = client.get(
        "/api/v1/quiz/123",
        headers={"Authorization": "Bearer token"}
    )

    # Should have deprecation headers
    assert response.headers.get("Deprecation") == "true"
    assert "Sunset" in response.headers
    assert "Warning" in response.headers
    assert "deprecated" in response.headers["Warning"]

def test_version_specific_responses(client: TestClient, test_quiz):
    """Test different response formats by version."""

    # V1 response
    response_v1 = client.get(
        f"/api/v1/quiz/{test_quiz.id}",
        headers={"Authorization": "Bearer token"}
    )
    data_v1 = response_v1.json()
    assert isinstance(data_v1["questions"], list)
    assert isinstance(data_v1["questions"][0], str)  # IDs only

    # V2 response
    response_v2 = client.get(
        f"/api/v2/quiz/{test_quiz.id}",
        headers={"Authorization": "Bearer token"}
    )
    data_v2 = response_v2.json()
    assert isinstance(data_v2["questions"], list)
    assert isinstance(data_v2["questions"][0], dict)  # Objects
    assert "text" in data_v2["questions"][0]
    assert "metadata" in data_v2

def test_removed_endpoint(client: TestClient):
    """Test endpoint removed in newer version."""

    # Endpoint exists in v1
    response = client.get("/api/v1/legacy-endpoint")
    assert response.status_code != 404

    # Endpoint removed in v2
    response = client.get(
        "/api/legacy-endpoint",
        headers={"X-API-Version": "2.0"}
    )
    assert response.status_code == 404
    assert "not available in API version 2.0" in response.json()["detail"]

def test_version_negotiation_priority(client: TestClient):
    """Test version detection priority."""

    # Header should override URL path
    response = client.get(
        "/api/v1/health",
        headers={"X-API-Version": "2.0"}
    )
    assert response.headers["X-API-Version"] == "2.0"
```

### Integration Tests

```python
# File: app/tests/integration/test_version_compatibility.py
@pytest.mark.integration
def test_client_version_compatibility(live_api_url):
    """Test that different client versions work."""

    # V1 client
    v1_client = APIClientV1(live_api_url)
    quiz = v1_client.get_quiz("123")
    assert isinstance(quiz.questions, list)

    # V2 client
    v2_client = APIClientV2(live_api_url)
    quiz = v2_client.get_quiz("123")
    assert hasattr(quiz.questions[0], 'text')

def test_gradual_migration(client: TestClient):
    """Test gradual migration scenario."""

    # Start with v1
    response = client.get(
        "/api/v1/quiz/123",
        headers={"Authorization": "Bearer token"}
    )
    assert response.headers.get("Deprecation") == "true"
    sunset_date = response.headers["Sunset"]

    # Client can check sunset date
    from datetime import datetime
    sunset = datetime.fromisoformat(sunset_date)
    days_remaining = (sunset.date() - datetime.today().date()).days
    assert days_remaining > 0

    # Client can test v2
    response_v2 = client.get(
        "/api/quiz/123",
        headers={
            "Authorization": "Bearer token",
            "X-API-Version": "2.0"
        }
    )
    assert response_v2.status_code == 200
    assert "Deprecation" not in response_v2.headers
```

## Migration Strategy

### Phase 1: Add Versioning Infrastructure
1. Implement versioning core
2. Add version detection
3. Create version middleware

### Phase 2: Create Version-Specific Code
1. Split models by version
2. Create versioned routes
3. Add adaptation layer

### Phase 3: Deprecation Process
1. Mark v1 as deprecated
2. Add sunset dates
3. Monitor usage

### Client Migration Guide

```python
# Client migration example
class QuizClient:
    def __init__(self, base_url: str, version: str = "2.0"):
        self.base_url = base_url
        self.version = version
        self.session = requests.Session()
        self.session.headers["X-API-Version"] = version

    def check_deprecation(self, response):
        """Check for deprecation warnings."""
        if response.headers.get("Deprecation") == "true":
            sunset = response.headers.get("Sunset")
            warning = response.headers.get("Warning")
            logger.warning(
                f"API version {self.version} is deprecated. "
                f"Sunset: {sunset}. {warning}"
            )

    def get_quiz(self, quiz_id: str):
        response = self.session.get(f"{self.base_url}/quiz/{quiz_id}")
        self.check_deprecation(response)
        return response.json()
```

## Success Criteria

### Versioning Metrics

- **Version Adoption**: Track % of requests per version
- **Deprecation Effectiveness**: >90% migrate before sunset
- **Backward Compatibility**: 100% v1 clients continue working
- **Version Discovery**: Clients can detect capabilities

### Operational Metrics

- **Migration Time**: <30 days average for clients
- **Support Tickets**: <5% increase during migration
- **API Stability**: No breaking changes without version

### Monitoring

```python
# Prometheus metrics for version tracking
from prometheus_client import Counter, Histogram

api_requests_by_version = Counter(
    'api_requests_by_version',
    'API requests by version',
    ['version', 'endpoint', 'method']
)

deprecated_api_usage = Counter(
    'deprecated_api_usage',
    'Usage of deprecated API versions',
    ['version', 'endpoint']
)

version_migration_gauge = Gauge(
    'api_version_distribution',
    'Distribution of API versions in use',
    ['version']
)
```

---
