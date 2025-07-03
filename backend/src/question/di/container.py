"""Dependency injection container for question generation system."""

from collections.abc import Callable
from typing import Any, TypeVar, cast

from src.logging_config import get_logger

logger = get_logger("di_container")

T = TypeVar("T")


class ServiceLifetime:
    """Service lifetime constants."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """Descriptor for a registered service."""

    def __init__(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
        instance: T | None = None,
        lifetime: str = ServiceLifetime.TRANSIENT,
    ):
        """
        Initialize service descriptor.

        Args:
            service_type: Service interface/type
            implementation: Implementation class
            factory: Factory function to create instance
            instance: Pre-created instance (for singleton)
            lifetime: Service lifetime
        """
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime

        # Validation
        if not any([implementation, factory, instance]):
            raise ValueError("Must provide implementation, factory, or instance")


class DIContainer:
    """
    Dependency injection container for managing service dependencies.

    Provides service registration, resolution, and lifetime management
    with support for singleton, transient, and scoped lifetimes.
    """

    def __init__(self) -> None:
        """Initialize DI container."""
        self._services: dict[type[Any], ServiceDescriptor] = {}
        self._instances: dict[type[Any], Any] = {}
        self._scope_instances: dict[str, dict[type[Any], Any]] = {}
        self._current_scope: str | None = None

    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
        instance: T | None = None,
    ) -> "DIContainer":
        """
        Register a singleton service.

        Args:
            service_type: Service interface/type
            implementation: Implementation class
            factory: Factory function
            instance: Pre-created instance

        Returns:
            Self for chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON,
        )

        self._services[service_type] = descriptor

        # If instance provided, store it immediately
        if instance is not None:
            self._instances[service_type] = instance

        logger.debug(
            "service_registered_singleton",
            service_type=service_type.__name__,
            implementation=implementation.__name__ if implementation else None,
            has_factory=factory is not None,
            has_instance=instance is not None,
        )

        return self

    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
    ) -> "DIContainer":
        """
        Register a transient service (new instance each time).

        Args:
            service_type: Service interface/type
            implementation: Implementation class
            factory: Factory function

        Returns:
            Self for chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=ServiceLifetime.TRANSIENT,
        )

        self._services[service_type] = descriptor

        logger.debug(
            "service_registered_transient",
            service_type=service_type.__name__,
            implementation=implementation.__name__ if implementation else None,
            has_factory=factory is not None,
        )

        return self

    def register_scoped(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
    ) -> "DIContainer":
        """
        Register a scoped service (one instance per scope).

        Args:
            service_type: Service interface/type
            implementation: Implementation class
            factory: Factory function

        Returns:
            Self for chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=ServiceLifetime.SCOPED,
        )

        self._services[service_type] = descriptor

        logger.debug(
            "service_registered_scoped",
            service_type=service_type.__name__,
            implementation=implementation.__name__ if implementation else None,
            has_factory=factory is not None,
        )

        return self

    def resolve(self, service_type: type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            service_type: Service type to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered
        """
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        # Handle different lifetimes
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._resolve_singleton(service_type, descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._resolve_scoped(service_type, descriptor)
        else:  # TRANSIENT
            return self._resolve_transient(service_type, descriptor)

    def try_resolve(self, service_type: type[T]) -> T | None:
        """
        Try to resolve a service instance.

        Args:
            service_type: Service type to resolve

        Returns:
            Service instance or None if not registered
        """
        try:
            return self.resolve(service_type)
        except ValueError:
            return None

    def is_registered(self, service_type: type[Any]) -> bool:
        """
        Check if a service type is registered.

        Args:
            service_type: Service type to check

        Returns:
            True if registered, False otherwise
        """
        return service_type in self._services

    def create_scope(self, scope_id: str | None = None) -> "ServiceScope":
        """
        Create a new service scope.

        Args:
            scope_id: Optional scope identifier

        Returns:
            Service scope context manager
        """
        if scope_id is None:
            import uuid

            scope_id = str(uuid.uuid4())

        return ServiceScope(self, scope_id)

    def enter_scope(self, scope_id: str) -> None:
        """
        Enter a service scope.

        Args:
            scope_id: Scope identifier
        """
        self._current_scope = scope_id
        if scope_id not in self._scope_instances:
            self._scope_instances[scope_id] = {}

        logger.debug("scope_entered", scope_id=scope_id)

    def exit_scope(self, scope_id: str) -> None:
        """
        Exit a service scope and dispose scoped instances.

        Args:
            scope_id: Scope identifier
        """
        if scope_id in self._scope_instances:
            # Dispose scoped instances
            for instance in self._scope_instances[scope_id].values():
                if hasattr(instance, "dispose"):
                    try:
                        instance.dispose()
                    except Exception as e:
                        logger.warning(
                            "scope_instance_disposal_failed",
                            scope_id=scope_id,
                            instance_type=type(instance).__name__,
                            error=str(e),
                        )

            del self._scope_instances[scope_id]

        if self._current_scope == scope_id:
            self._current_scope = None

        logger.debug("scope_exited", scope_id=scope_id)

    def get_registered_services(self) -> dict[type[Any], ServiceDescriptor]:
        """
        Get all registered services.

        Returns:
            Dictionary of registered services
        """
        return self._services.copy()

    def clear(self) -> None:
        """Clear all registered services and instances."""
        # Dispose singleton instances
        for instance in self._instances.values():
            if hasattr(instance, "dispose"):
                try:
                    instance.dispose()
                except Exception as e:
                    logger.warning(
                        "singleton_disposal_failed",
                        instance_type=type(instance).__name__,
                        error=str(e),
                    )

        # Clear all scopes
        for scope_id in list(self._scope_instances.keys()):
            self.exit_scope(scope_id)

        self._services.clear()
        self._instances.clear()
        self._scope_instances.clear()
        self._current_scope = None

        logger.info("di_container_cleared")

    def _resolve_singleton(
        self, service_type: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Resolve singleton service."""
        if service_type in self._instances:
            return cast(T, self._instances[service_type])

        # Create instance
        instance = self._create_instance(descriptor)
        self._instances[service_type] = instance

        logger.debug("singleton_instance_created", service_type=service_type.__name__)

        return cast(T, instance)

    def _resolve_scoped(
        self, service_type: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Resolve scoped service."""
        if not self._current_scope:
            raise ValueError("No active scope for scoped service resolution")

        scope_instances = self._scope_instances[self._current_scope]

        if service_type in scope_instances:
            return cast(T, scope_instances[service_type])

        # Create instance
        instance = self._create_instance(descriptor)
        scope_instances[service_type] = instance

        logger.debug(
            "scoped_instance_created",
            service_type=service_type.__name__,
            scope_id=self._current_scope,
        )

        return cast(T, instance)

    def _resolve_transient(
        self, service_type: type[T], descriptor: ServiceDescriptor
    ) -> T:
        """Resolve transient service."""
        instance = self._create_instance(descriptor)

        logger.debug("transient_instance_created", service_type=service_type.__name__)

        return cast(T, instance)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance using descriptor."""
        try:
            if descriptor.instance is not None:
                return descriptor.instance
            elif descriptor.factory is not None:
                # Call factory with dependency injection
                return self._call_with_injection(descriptor.factory)
            elif descriptor.implementation is not None:
                # Create instance with dependency injection
                return self._create_with_injection(descriptor.implementation)
            else:
                raise ValueError("No way to create instance")

        except Exception as e:
            logger.error(
                "service_instance_creation_failed",
                service_type=descriptor.service_type.__name__,
                error=str(e),
                exc_info=True,
            )
            raise

    def _create_with_injection(self, implementation_type: type[T]) -> T:
        """Create instance with constructor dependency injection."""
        import inspect

        # Get constructor signature
        signature = inspect.signature(implementation_type.__init__)

        # Resolve dependencies
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            if param.annotation and param.annotation != inspect.Parameter.empty:
                # Try to resolve parameter type
                try:
                    dependency = self.resolve(param.annotation)
                    kwargs[param_name] = dependency
                except ValueError:
                    # Check if parameter has default value
                    if param.default == inspect.Parameter.empty:
                        logger.warning(
                            "dependency_resolution_failed",
                            implementation=implementation_type.__name__,
                            parameter=param_name,
                            parameter_type=param.annotation.__name__
                            if hasattr(param.annotation, "__name__")
                            else str(param.annotation),
                        )
                        # Continue without this dependency

        return implementation_type(**kwargs)

    def _call_with_injection(self, factory: Callable[..., T]) -> T:
        """Call factory function with dependency injection."""
        import inspect

        # Get factory signature
        signature = inspect.signature(factory)

        # Resolve dependencies
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param.annotation and param.annotation != inspect.Parameter.empty:
                # Try to resolve parameter type
                try:
                    dependency = self.resolve(param.annotation)
                    kwargs[param_name] = dependency
                except ValueError:
                    # Check if parameter has default value
                    if param.default == inspect.Parameter.empty:
                        logger.warning(
                            "factory_dependency_resolution_failed",
                            factory=factory.__name__,
                            parameter=param_name,
                            parameter_type=param.annotation.__name__
                            if hasattr(param.annotation, "__name__")
                            else str(param.annotation),
                        )

        return factory(**kwargs)


class ServiceScope:
    """Context manager for service scopes."""

    def __init__(self, container: DIContainer, scope_id: str):
        """
        Initialize service scope.

        Args:
            container: DI container
            scope_id: Scope identifier
        """
        self.container = container
        self.scope_id = scope_id

    def __enter__(self) -> "ServiceScope":
        """Enter the scope."""
        self.container.enter_scope(self.scope_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the scope."""
        self.container.exit_scope(self.scope_id)


# Global DI container instance
_default_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Get the default DI container instance."""
    global _default_container

    if _default_container is None:
        _default_container = DIContainer()
        _configure_default_container(_default_container)

    return _default_container


def _configure_default_container(container: DIContainer) -> None:
    """Configure the default container with services."""
    from ..config import get_configuration_service
    from ..providers import get_llm_provider_registry
    from ..services import (
        ContentProcessingService,
        GenerationOrchestrationService,
        QuestionPersistenceService,
    )
    from ..templates import get_template_manager
    from ..types import get_question_type_registry
    from ..workflows import get_workflow_registry

    # Register core services as singletons
    container.register_singleton(
        type(get_configuration_service()), instance=get_configuration_service()
    )

    container.register_singleton(
        type(get_llm_provider_registry()), instance=get_llm_provider_registry()
    )

    container.register_singleton(
        type(get_template_manager()), instance=get_template_manager()
    )

    container.register_singleton(
        type(get_question_type_registry()), instance=get_question_type_registry()
    )

    container.register_singleton(
        type(get_workflow_registry()), instance=get_workflow_registry()
    )

    # Register application services as transient
    container.register_transient(
        ContentProcessingService, implementation=ContentProcessingService
    )

    container.register_transient(
        GenerationOrchestrationService, implementation=GenerationOrchestrationService
    )

    container.register_transient(
        QuestionPersistenceService, implementation=QuestionPersistenceService
    )

    logger.info(
        "default_container_configured",
        registered_services=len(container.get_registered_services()),
    )
