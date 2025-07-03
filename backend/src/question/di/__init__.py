"""Dependency injection module for question generation system."""

from .container import DIContainer, ServiceLifetime, ServiceScope, get_container

__all__ = [
    "DIContainer",
    "ServiceLifetime",
    "ServiceScope",
    "get_container",
]
