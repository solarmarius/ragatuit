# 18. Security Headers Implementation

## Priority: Medium

**Estimated Effort**: 1 day
**Python Version**: 3.10+
**Dependencies**: FastAPI, secure (python-secure)

## Problem Statement

### Current Situation

The application lacks essential security headers, leaving it vulnerable to various client-side attacks including XSS, clickjacking, MIME sniffing, and other security vulnerabilities.

### Why It's a Problem

- **XSS Vulnerability**: No Content Security Policy (CSP) protection
- **Clickjacking Risk**: Missing X-Frame-Options header
- **MIME Type Attacks**: No X-Content-Type-Options header
- **Information Disclosure**: Server version exposed in headers
- **HTTPS Issues**: No Strict-Transport-Security (HSTS)
- **Browser Features**: Missing modern security features

### Affected Modules

- `app/main.py` - Main application configuration
- `app/middleware/` - Security middleware missing
- All HTTP responses from the application

### Technical Debt Assessment

- **Risk Level**: Medium - Client-side security vulnerabilities
- **Impact**: All web-facing endpoints
- **Cost of Delay**: Increases with user base growth

## Current Implementation Analysis

```python
# File: app/main.py (current - no security headers)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.PROJECT_NAME)

# PROBLEM: Only CORS configured, no security headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File: Response headers (current output)
# HTTP/1.1 200 OK
# date: Mon, 15 Jan 2024 10:00:00 GMT
# server: uvicorn  # PROBLEM: Exposes server info
# content-type: application/json
# content-length: 123
# access-control-allow-origin: *
# access-control-allow-credentials: true
#
# MISSING:
# - X-Content-Type-Options
# - X-Frame-Options
# - X-XSS-Protection
# - Strict-Transport-Security
# - Content-Security-Policy
# - Referrer-Policy
# - Permissions-Policy
```

### Security Scan Results

```bash
# Security header analysis:
# ❌ Content-Security-Policy: Not set
# ❌ X-Frame-Options: Not set
# ❌ X-Content-Type-Options: Not set
# ❌ Strict-Transport-Security: Not set
# ❌ X-XSS-Protection: Not set (deprecated but still useful)
# ❌ Referrer-Policy: Not set
# ❌ Permissions-Policy: Not set
# ⚠️  Server header: Exposes version info
# ⚠️  X-Powered-By: May expose framework info

# OWASP ZAP scan findings:
# - Missing Anti-clickjacking Header
# - X-Content-Type-Options Header Missing
# - CSP Header Not Set
# - Server Version Disclosure
```

### Python Anti-patterns Identified

- **No Security by Default**: Relying on framework defaults
- **Information Leakage**: Exposing server/framework details
- **Missing Defense in Depth**: No layered security
- **No CSP Strategy**: Allowing all content sources

## Proposed Solution

### Pythonic Approach

Implement comprehensive security headers using FastAPI middleware with environment-specific configurations, following OWASP security best practices.

### Security Headers to Implement

1. **Content-Security-Policy (CSP)**: Prevent XSS attacks
2. **X-Frame-Options**: Prevent clickjacking
3. **X-Content-Type-Options**: Prevent MIME sniffing
4. **Strict-Transport-Security**: Force HTTPS
5. **Referrer-Policy**: Control referrer information
6. **Permissions-Policy**: Control browser features
7. **X-XSS-Protection**: Legacy XSS protection

### Code Examples

```python
# File: app/middleware/security_headers.py (NEW)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import hashlib
import secrets
from app.core.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements OWASP security header best practices.
    """

    def __init__(self, app, config: Optional[Dict[str, str]] = None):
        super().__init__(app)
        self.config = config or self._get_default_config()

    def _get_default_config(self) -> Dict[str, str]:
        """Get default security headers configuration."""

        # Environment-specific CSP
        csp_directives = self._build_csp_policy()

        return {
            # Content Security Policy
            "Content-Security-Policy": csp_directives,

            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Force HTTPS (only in production)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload"
                if settings.ENVIRONMENT == "production" else "",

            # XSS Protection (legacy but still useful)
            "X-XSS-Protection": "1; mode=block",

            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Permissions Policy (Feature Policy replacement)
            "Permissions-Policy": self._build_permissions_policy(),

            # Remove server identification
            "Server": "API",

            # Cache control for security
            "Cache-Control": "no-store, no-cache, must-revalidate, private",

            # Prevent DNS prefetch
            "X-DNS-Prefetch-Control": "off",

            # IE compatibility
            "X-UA-Compatible": "IE=edge",
        }

    def _build_csp_policy(self) -> str:
        """Build Content Security Policy based on environment."""

        # Base CSP directives
        csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],  # Allow inline styles for now
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'"],
            "media-src": ["'self'"],
            "object-src": ["'none'"],
            "frame-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
        }

        # Add allowed origins for API calls
        if settings.FRONTEND_URL:
            csp["connect-src"].append(settings.FRONTEND_URL)

        # Add Canvas domain for OAuth
        if settings.CANVAS_BASE_URL:
            csp["connect-src"].append(settings.CANVAS_BASE_URL)
            csp["frame-src"].append(settings.CANVAS_BASE_URL)  # For OAuth flow

        # Development additions
        if settings.ENVIRONMENT == "local":
            csp["script-src"].extend(["'unsafe-eval'", "'unsafe-inline'"])
            csp["connect-src"].extend(["ws://localhost:*", "http://localhost:*"])

        # Build CSP string
        csp_string = "; ".join(
            f"{directive} {' '.join(sources)}" if sources else directive
            for directive, sources in csp.items()
        )

        return csp_string

    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header."""

        # Restrictive permissions by default
        permissions = {
            "accelerometer": "()",
            "ambient-light-sensor": "()",
            "autoplay": "()",
            "battery": "()",
            "camera": "()",
            "cross-origin-isolated": "()",
            "display-capture": "()",
            "document-domain": "()",
            "encrypted-media": "()",
            "execution-while-not-rendered": "()",
            "execution-while-out-of-viewport": "()",
            "fullscreen": "()",
            "geolocation": "()",
            "gyroscope": "()",
            "keyboard-map": "()",
            "magnetometer": "()",
            "microphone": "()",
            "midi": "()",
            "navigation-override": "()",
            "payment": "()",
            "picture-in-picture": "()",
            "publickey-credentials-get": "()",
            "screen-wake-lock": "()",
            "sync-xhr": "()",
            "usb": "()",
            "web-share": "()",
            "xr-spatial-tracking": "()",
        }

        return ", ".join(f"{key}={value}" for key, value in permissions.items())

    async def dispatch(self, request: Request, call_next):
        # Generate nonce for inline scripts if needed
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce

        # Process request
        response = await call_next(request)

        # Add security headers
        for header, value in self.config.items():
            if value:  # Only add non-empty headers
                # Add nonce to CSP if present
                if header == "Content-Security-Policy" and hasattr(request.state, "csp_nonce"):
                    value = value.replace("'self'", f"'self' 'nonce-{nonce}'")

                response.headers[header] = value

        # Remove potentially dangerous headers
        headers_to_remove = ["X-Powered-By", "X-AspNet-Version"]
        for header in headers_to_remove:
            response.headers.pop(header, None)

        return response

# File: app/middleware/security.py (NEW - Additional security middleware)
from starlette.middleware.base import BaseHTTPMiddleware
import time
import hmac

class SecurityMiddleware(BaseHTTPMiddleware):
    """Additional security measures."""

    async def dispatch(self, request: Request, call_next):
        # Add request timestamp
        request.state.timestamp = time.time()

        # Validate content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not any(ct in content_type for ct in ["application/json", "multipart/form-data"]):
                return Response(
                    content={"error": "Invalid content type"},
                    status_code=415,
                    headers={"Content-Type": "application/json"}
                )

        # Process request
        response = await call_next(request)

        # Add timing header (useful for debugging)
        if settings.ENVIRONMENT == "local":
            duration = time.time() - request.state.timestamp
            response.headers["X-Process-Time"] = str(duration)

        return response

# File: app/main.py (UPDATED)
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.security import SecurityMiddleware

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Add security headers middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SecurityMiddleware)

# CORS middleware (already exists)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# File: app/core/config.py (UPDATED)
class Settings(BaseSettings):
    # Security header settings
    ENABLE_SECURITY_HEADERS: bool = True
    FRONTEND_URL: str = "https://app.example.com"
    CANVAS_BASE_URL: str = "https://canvas.example.com"

    # CSP settings
    CSP_REPORT_URI: Optional[str] = None  # For CSP violation reporting
    CSP_REPORT_ONLY: bool = False  # Test mode for CSP

    # HSTS settings
    HSTS_MAX_AGE: int = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = True

    # Feature flags
    ENABLE_FRAME_OPTIONS: bool = True
    ENABLE_XSS_PROTECTION: bool = True

# File: app/api/routes/health.py (Security headers validation endpoint)
@router.get("/security-headers")
async def check_security_headers(request: Request) -> dict:
    """Check which security headers are set (dev only)."""

    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404)

    # Make internal request to check headers
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:{settings.PORT}/api/v1/health",
            headers={"Host": request.headers.get("host")}
        )

    security_headers = {
        "Content-Security-Policy": "❌ Missing",
        "X-Frame-Options": "❌ Missing",
        "X-Content-Type-Options": "❌ Missing",
        "Strict-Transport-Security": "❌ Missing",
        "X-XSS-Protection": "❌ Missing",
        "Referrer-Policy": "❌ Missing",
        "Permissions-Policy": "❌ Missing",
    }

    for header in security_headers:
        if header in response.headers:
            security_headers[header] = f"✅ {response.headers[header][:50]}..."

    return {
        "headers_set": sum(1 for v in security_headers.values() if v.startswith("✅")),
        "total_headers": len(security_headers),
        "details": security_headers,
        "server_header": response.headers.get("Server", "Not disclosed"),
    }

# File: app/utils/csp_helpers.py (NEW - CSP utilities)
import hashlib
from typing import List

class CSPHelper:
    """Utilities for Content Security Policy management."""

    @staticmethod
    def hash_inline_script(script: str) -> str:
        """Generate CSP hash for inline script."""
        script_bytes = script.encode('utf-8')
        hash_value = hashlib.sha256(script_bytes).digest()
        return f"'sha256-{base64.b64encode(hash_value).decode()}'"

    @staticmethod
    def generate_script_tag(script: str, nonce: str) -> str:
        """Generate script tag with CSP nonce."""
        return f'<script nonce="{nonce}">{script}</script>'

    @staticmethod
    def validate_csp_report(report: dict) -> bool:
        """Validate CSP violation report."""
        required_fields = ["document-uri", "violated-directive", "blocked-uri"]
        return all(field in report.get("csp-report", {}) for field in required_fields)

# File: app/api/routes/csp.py (NEW - CSP reporting endpoint)
@router.post("/csp-report", include_in_schema=False)
async def handle_csp_report(request: Request):
    """Handle Content Security Policy violation reports."""

    try:
        report = await request.json()

        if CSPHelper.validate_csp_report(report):
            logger.warning(
                "csp_violation",
                document_uri=report["csp-report"]["document-uri"],
                violated_directive=report["csp-report"]["violated-directive"],
                blocked_uri=report["csp-report"]["blocked-uri"],
                source_file=report["csp-report"].get("source-file"),
                line_number=report["csp-report"].get("line-number"),
            )

        return Response(status_code=204)  # No Content
    except Exception as e:
        logger.error("csp_report_error", error=str(e))
        return Response(status_code=204)  # Still return 204 to not break CSP
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── middleware/
│   │   ├── security_headers.py      # NEW: Security headers
│   │   └── security.py              # NEW: Additional security
│   ├── core/
│   │   └── config.py                # UPDATE: Security settings
│   ├── utils/
│   │   └── csp_helpers.py           # NEW: CSP utilities
│   ├── api/
│   │   └── routes/
│   │       ├── health.py            # UPDATE: Add validation
│   │       └── csp.py               # NEW: CSP reporting
│   ├── main.py                      # UPDATE: Add middleware
│   └── tests/
│       └── test_security_headers.py # NEW: Security tests
```

### Configuration Examples

```python
# Production configuration
SECURITY_HEADERS_PRODUCTION = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' https://cdn.example.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.example.com wss://api.example.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests; "
        "block-all-mixed-content"
    ),
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# Development configuration
SECURITY_HEADERS_DEVELOPMENT = {
    "Content-Security-Policy": (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "connect-src 'self' http://localhost:* ws://localhost:*"
    ),
    # Less restrictive for development
}
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/middleware/test_security_headers.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_security_headers_present(client: TestClient):
    """Test all security headers are present."""

    response = client.get("/api/v1/health")

    # Check required headers
    assert "Content-Security-Policy" in response.headers
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers

def test_server_header_masked(client: TestClient):
    """Test server information is not disclosed."""

    response = client.get("/api/v1/health")

    # Should not contain version info
    assert response.headers.get("Server") == "API"
    assert "X-Powered-By" not in response.headers
    assert "X-AspNet-Version" not in response.headers

def test_csp_nonce_generation(client: TestClient):
    """Test CSP nonce is properly generated."""

    response = client.get("/api/v1/health")

    csp_header = response.headers.get("Content-Security-Policy", "")
    # Should contain nonce if inline scripts are used
    if "'nonce-" in csp_header:
        assert len(csp_header.split("'nonce-")[1].split("'")[0]) >= 16

def test_hsts_header_production():
    """Test HSTS header in production mode."""

    with patch("app.core.config.settings.ENVIRONMENT", "production"):
        client = TestClient(app)
        response = client.get("/api/v1/health")

        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts

@pytest.mark.parametrize("method,content_type,expected_status", [
    ("POST", "application/json", 200),
    ("POST", "text/plain", 415),
    ("PUT", "application/json", 200),
    ("PUT", "text/html", 415),
    ("GET", "anything", 200),  # GET doesn't check content-type
])
def test_content_type_validation(
    client: TestClient,
    method: str,
    content_type: str,
    expected_status: int
):
    """Test content type validation."""

    response = client.request(
        method,
        "/api/v1/test-endpoint",
        headers={"Content-Type": content_type},
        json={"test": "data"} if method != "GET" else None
    )

    assert response.status_code == expected_status
```

### Integration Tests

```python
# File: app/tests/integration/test_security_integration.py
import pytest
from app.tests.security_scanner import SecurityScanner

@pytest.mark.security
def test_owasp_security_headers(live_server_url):
    """Test against OWASP security header requirements."""

    scanner = SecurityScanner(live_server_url)
    results = scanner.scan_headers("/api/v1/health")

    # All critical headers should pass
    assert results["content-security-policy"]["present"]
    assert results["x-frame-options"]["value"] == "DENY"
    assert results["x-content-type-options"]["value"] == "nosniff"
    assert results["strict-transport-security"]["present"]

    # Security score should be high
    assert results["security_score"] >= 80  # Out of 100

def test_csp_report_endpoint(client: TestClient):
    """Test CSP violation reporting."""

    csp_report = {
        "csp-report": {
            "document-uri": "https://app.example.com/",
            "violated-directive": "script-src",
            "blocked-uri": "https://evil.com/script.js",
            "source-file": "https://app.example.com/index.html",
            "line-number": 10
        }
    }

    response = client.post(
        "/api/v1/csp-report",
        json=csp_report,
        headers={"Content-Type": "application/csp-report"}
    )

    assert response.status_code == 204

def test_permissions_policy_features(client: TestClient):
    """Test Permissions Policy blocks features."""

    response = client.get("/api/v1/health")

    permissions = response.headers.get("Permissions-Policy", "")

    # Should block dangerous features
    assert "geolocation=()" in permissions
    assert "camera=()" in permissions
    assert "microphone=()" in permissions
```

## Code Quality Improvements

### Security Header Monitoring

```python
# Monitor security header effectiveness
from prometheus_client import Counter

csp_violations = Counter(
    'csp_violations_total',
    'Content Security Policy violations',
    ['directive', 'blocked_uri']
)

security_header_missing = Counter(
    'security_header_missing_total',
    'Requests with missing security headers',
    ['header_name']
)
```

### Security Testing Tools

```python
# File: app/tests/security_scanner.py
import requests
from typing import Dict, Any

class SecurityScanner:
    """Security header scanner for testing."""

    SECURITY_HEADERS = {
        "content-security-policy": {"required": True, "score": 25},
        "x-frame-options": {"required": True, "score": 20},
        "x-content-type-options": {"required": True, "score": 15},
        "strict-transport-security": {"required": True, "score": 20},
        "referrer-policy": {"required": True, "score": 10},
        "permissions-policy": {"required": True, "score": 10},
    }

    def scan_headers(self, url: str) -> Dict[str, Any]:
        """Scan URL for security headers."""
        response = requests.get(url, verify=True)
        results = {}
        total_score = 0

        for header, config in self.SECURITY_HEADERS.items():
            header_value = response.headers.get(header, "")
            present = bool(header_value)

            results[header] = {
                "present": present,
                "value": header_value[:100] if present else None,
                "required": config["required"],
                "passed": present if config["required"] else True
            }

            if present:
                total_score += config["score"]

        results["security_score"] = total_score
        results["grade"] = self._calculate_grade(total_score)

        return results

    def _calculate_grade(self, score: int) -> str:
        """Calculate security grade."""
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"
```

## Migration Strategy

### Phase 1: Add Basic Headers
1. Implement SecurityHeadersMiddleware
2. Add basic headers (X-Frame-Options, X-Content-Type-Options)
3. Test in development

### Phase 2: Implement CSP
1. Design CSP policy for application
2. Test in report-only mode
3. Monitor violations
4. Enable enforcement

### Phase 3: Full Security Headers
1. Add remaining headers
2. Configure for each environment
3. Set up monitoring

### Rollback Plan

```python
# Feature flag for security headers
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

# Environment-specific activation
if settings.ENVIRONMENT == "production":
    # Strict headers
    config = SECURITY_HEADERS_PRODUCTION
else:
    # Relaxed headers for development
    config = SECURITY_HEADERS_DEVELOPMENT
```

## Success Criteria

### Security Metrics

- **Header Coverage**: 100% of security headers implemented
- **CSP Violations**: <1% legitimate violations after tuning
- **Security Score**: A grade (90+) on security scanners
- **Performance Impact**: <1ms latency added

### Compliance Metrics

- **OWASP Compliance**: Pass all header checks
- **Security Audit**: No header-related findings
- **Browser Compatibility**: Works in 95%+ of browsers

---
