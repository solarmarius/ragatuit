"""
Constants for authentication module.
"""

# Token settings
TOKEN_TYPE = "Bearer"
TOKEN_EXPIRE_HOURS = 24
CANVAS_TOKEN_EXPIRE_HOURS = 1

# OAuth state
OAUTH_STATE_LENGTH = 32

# Error messages
ERROR_INVALID_CREDENTIALS = "Invalid credentials"
ERROR_USER_NOT_FOUND = "User not found"
ERROR_TOKEN_EXPIRED = "Token has expired"
ERROR_TOKEN_REFRESH_FAILED = "Token refresh failed - please login again"
