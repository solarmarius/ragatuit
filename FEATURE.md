# Canvas Login Implementation

## Overview of the Feature

This feature implements OAuth2 authentication flow with Canvas LMS, allowing teachers to securely authenticate and authorize the application to access their Canvas data. The backend will handle the OAuth2 authorization code exchange, token management, and provide secure API endpoints for frontend integration.

### User flow

1. Redirecting the user to the Canvas authorization page.
2. Handling the authorization code redirect (callback URL).
3. Exchanging the authorization code for an access token.
4. Managing the authenticated session securely.
5. Providing authenticated teachers access to features like quiz generation tied to their Canvas data.

### Key Components

- OAuth2 authorization URL generation
- Authorization code to access token exchange
- Secure token storage and management
- User session management
- Canvas API integration for user profile retrieval
- Token refresh mechanism

## Database Considerations

### New Models Required

#### CanvasToken Model

```python
# Pseudocode for CanvasToken model
class CanvasToken(SQLModel, table=True):
    id: UUID (primary key)
    user_id: UUID (foreign key to User)
    access_token: str (encrypted)
    refresh_token: str (encrypted, nullable)
    token_type: str (default: "Bearer")
    expires_at: datetime (nullable)
    scope: str (nullable)
    canvas_user_id: str (Canvas user identifier)
    canvas_base_url: str (Canvas instance URL)
    created_at: datetime
    updated_at: datetime
```

#### User Model Extensions

```python
# Add to existing User model
class User(UserBase, table=True):
    # ... existing fields ...
    canvas_user_id: str | None = None
    canvas_base_url: str | None = None
    canvas_tokens: list["CanvasToken"] = Relationship(back_populates="user")
```

### Database Schema Considerations

- Use encryption for storing access/refresh tokens
- Index on `user_id` and `canvas_user_id` for efficient lookups
- Consider token expiration cleanup strategy
- Add cascade delete for tokens when user is deleted

## API Design

### Configuration Endpoints

#### GET `/api/v1/canvas/config`

**Purpose**: Provide Canvas OAuth2 configuration to frontend
**Response**:

```json
{
  "authorization_url": "https://canvas.example.com/login/oauth2/auth",
  "client_id": "your_client_id",
  "redirect_uri": "https://yourapp.com/api/v1/canvas/callback",
  "scope": "url:GET|/api/v1/courses url:GET|/api/v1/users/:id/profile"
}
```

### Authentication Endpoints

#### GET `/api/v1/canvas/authorize`

**Purpose**: Generate Canvas OAuth2 authorization URL
**Parameters**:

- `canvas_base_url` (query): Canvas instance URL
- `state` (query, optional): CSRF protection state
  **Response**: Redirect to Canvas authorization URL

#### POST `/api/v1/canvas/callback`

**Purpose**: Handle OAuth2 callback and exchange code for tokens
**Request Body**:

```json
{
  "code": "authorization_code",
  "state": "csrf_state_token",
  "canvas_base_url": "https://canvas.example.com"
}
```

**Response**:

```json
{
  "access_token": "session_token",
  "user": {
    "id": "user_uuid",
    "canvas_user_id": "123456",
    "name": "Teacher Name",
    "email": "teacher@example.com"
  }
}
```

#### POST `/api/v1/canvas/refresh`

**Purpose**: Refresh expired Canvas tokens
**Headers**: `Authorization: Bearer <session_token>`
**Response**: Updated session token

#### DELETE `/api/v1/canvas/disconnect`

**Purpose**: Revoke Canvas tokens and disconnect account
**Headers**: `Authorization: Bearer <session_token>`
**Response**: Success message

### Canvas API Proxy Endpoints

#### GET `/api/v1/canvas/profile`

**Purpose**: Get current user's Canvas profile
**Headers**: `Authorization: Bearer <session_token>`
**Response**: Canvas user profile data

#### GET `/api/v1/canvas/courses`

**Purpose**: Get user's Canvas courses
**Headers**: `Authorization: Bearer <session_token>`
**Response**: List of Canvas courses

## Validation and Error Handling

### Input Validation

- **Canvas Base URL**: Validate URL format and whitelist known Canvas domains
- **Authorization Code**: Ensure non-empty string, reasonable length limits
- **State Parameter**: Validate CSRF token matches session state
- **Scope**: Validate requested scopes against allowed scopes

### Error Scenarios

1. **Invalid Canvas Instance**: Return 400 with clear error message
2. **Authorization Denied**: Return 401 with user-friendly message
3. **Invalid Authorization Code**: Return 400 with OAuth error details
4. **Token Expiration**: Return 401 and trigger refresh flow
5. **Canvas API Errors**: Proxy error codes with sanitized messages
6. **Network Timeouts**: Return 503 with retry guidance

### Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "CANVAS_AUTH_FAILED",
  "canvas_error": {
    "error": "invalid_grant",
    "error_description": "Canvas error details"
  }
}
```

## Security Considerations

### Token Security

- **Encryption at Rest**: Encrypt access/refresh tokens in database using application secret key
- **Secure Transmission**: Use HTTPS for all OAuth2 flows
- **Token Scope Limitation**: Request minimal necessary scopes
- **Token Expiration**: Implement proper token lifecycle management

### CSRF Protection

- Generate and validate state parameters in OAuth2 flow
- Store state in secure session storage
- Validate state parameter in callback

### Session Management

- Use secure HTTP-only cookies for session tokens
- Implement session timeout and renewal
- Store minimal user data in sessions

### Canvas API Security

- Validate all Canvas API responses
- Implement rate limiting for Canvas API calls
- Sanitize Canvas data before storage
- Never expose Canvas tokens to frontend

### Configuration Security

- Store Canvas client secret in environment variables
- Use different Canvas apps for development/production
- Implement Canvas webhook signature validation (future enhancement)

## Testing Strategy

### Unit Tests

- OAuth2 URL generation with various parameters
- Token encryption/decryption functionality
- Canvas API response parsing
- Error handling for various OAuth2 scenarios

### Integration Tests

- Full OAuth2 flow with mocked Canvas responses
- Token refresh mechanism
- Canvas API proxy endpoints
- Database token storage and retrieval

### Security Tests

- CSRF attack prevention
- Token encryption verification
- Input validation boundary testing
- Session security validation

### End-to-End Tests

- Complete login flow with test Canvas instance
- Token expiration and refresh scenarios
- Multiple Canvas instance support
- Logout and token revocation

## Implementation Structure

### File Organization

```
app/
├── api/routes/
│   ├── canvas.py              # Canvas OAuth2 and API routes
│   └── auth.py                # Enhanced with Canvas auth
├── core/
│   ├── canvas.py              # Canvas OAuth2 client
│   ├── encryption.py          # Token encryption utilities
│   └── config.py              # Canvas configuration
├── models.py                  # CanvasToken model additions
├── crud.py                    # Canvas token CRUD operations
├── schemas/
│   ├── canvas.py              # Canvas request/response models
│   └── __init__.py
└── tests/
    ├── test_canvas_oauth.py   # Canvas OAuth2 tests
    ├── test_canvas_api.py     # Canvas API proxy tests
    └── test_canvas_security.py # Security-focused tests
```

### Required Dependencies

- `requests` or `httpx`: HTTP client for Canvas API calls
- `cryptography`: Token encryption
- `pydantic[email]`: URL validation
- `python-jose` or `pyjwt`: JWT handling for sessions

## Potential Pitfalls and Edge Cases

### Canvas Instance Variations

- Different Canvas deployments may have different OAuth2 endpoints
- Handle both canvas.instructure.com and self-hosted instances
- Validate Canvas API version compatibility

### Token Management Complexities

- Canvas tokens may not include refresh tokens
- Handle graceful degradation when tokens expire
- Implement token cleanup for inactive users

### Network and API Issues

- Canvas API rate limiting and retry logic
- Handle Canvas maintenance windows
- Implement circuit breaker pattern for Canvas API calls

### User Experience Considerations

- Handle users with multiple Canvas accounts
- Graceful handling of authorization denials
- Clear error messages for Canvas-specific issues

### Scaling Considerations

- Database indexing strategy for large user bases
- Token storage encryption performance
- Canvas API call caching strategy

### Compliance and Privacy

- FERPA compliance for educational data
- Data retention policies for Canvas tokens
- User consent and data usage transparency

## Future Enhancements

### Advanced Features

- Canvas webhook integration for real-time updates
- Support for Canvas LTI (Learning Tools Interoperability)
- Canvas course synchronization
- Bulk operations with Canvas API

### Monitoring and Observability

- Canvas API call metrics and logging
- Token usage analytics
- OAuth2 flow success/failure rates
- Performance monitoring for Canvas operations

This implementation plan provides a comprehensive foundation for integrating Canvas OAuth2 authentication while maintaining security, scalability, and user experience standards.
