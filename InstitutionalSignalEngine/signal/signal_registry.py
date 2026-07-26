"""
Signal registry module for the Institutional Signal Intelligence Engine.

Manages the registration, lifecycle, and retrieval of signal providers.
Strictly isolated from signal generation, indicator calculation, and 
business logic. Allows the SignalEngine to remain agnostic of individual 
signal modules.
"""

import threading
from typing import Any, Dict, List, Tuple

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from signal.signal_models import SignalResult


@runtime_checkable
class SignalProvider(Protocol):
    """
    Protocol defining the strict contract for all signal providers.
    Ensures type safety and structural subtyping without requiring 
    inheritance from a base class.
    """
    name: str
    
    def generate(self, features: Any) -> SignalResult:
        """
        Generates a signal result based on the provided market features.
        
        Args:
            features: The current market feature snapshot.
            
        Returns:
            A standardized SignalResult.
        """
        ...


class SignalRegistry:
    """
    Thread-safe registry for managing signal providers.
    Supports registration, enabling/disabling, and ordered retrieval 
    of signal providers to ensure deterministic execution priority.
    """

    def __init__(self) -> None:
        """Initializes the signal registry with an empty state and a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.RLock()
        self._providers: Dict[str, SignalProvider] = {}
        self._enabled_order: List[str] = []

    def register(self, provider: SignalProvider) -> None:
        """
        Registers a new signal provider.
        
        Args:
            provider: The signal provider instance. Must satisfy the SignalProvider Protocol.
                      
        Raises:
            ValidationError: If the provider is invalid or its name is already registered.
        """
        self._validate_provider(provider)
        name = provider.name
        
        with self._lock:
            if name in self._providers:
                self._logger.warning(f"Duplicate registration attempt for provider: '{name}'.")
                raise ValidationError(f"Signal provider '{name}' is already registered.")
                
            self._providers[name] = provider
            self._enabled_order.append(name)
            self._logger.info(f"Registered and enabled signal provider: '{name}'.")

    def unregister(self, provider_name: str) -> None:
        """
        Removes a signal provider from the registry.
        
        Args:
            provider_name: The name of the provider to remove.
        """
        with self._lock:
            if provider_name in self._providers:
                del self._providers[provider_name]
                if provider_name in self._enabled_order:
                    self._enabled_order.remove(provider_name)
                self._logger.info(f"Unregistered signal provider: '{provider_name}'.")
            else:
                self._logger.warning(f"Attempted to unregister unknown provider: '{provider_name}'.")

    def enable(self, provider_name: str) -> None:
        """
        Enables a registered signal provider. Appends to execution order 
        if not already enabled.
        
        Args:
            provider_name: The name of the provider to enable.
            
        Raises:
            ValidationError: If the provider is not registered.
        """
        with self._lock:
            if provider_name not in self._providers:
                raise ValidationError(f"Cannot enable unknown provider: '{provider_name}'.")
            if provider_name not in self._enabled_order:
                self._enabled_order.append(provider_name)
                self._logger.info(f"Enabled signal provider: '{provider_name}'.")

    def disable(self, provider_name: str) -> None:
        """
        Disables a registered signal provider without removing it from the registry.
        
        Args:
            provider_name: The name of the provider to disable.
        """
        with self._lock:
            if provider_name in self._enabled_order:
                self._enabled_order.remove(provider_name)
                self._logger.info(f"Disabled signal provider: '{provider_name}'.")

    def is_enabled(self, provider_name: str) -> bool:
        """
        Checks if a provider is registered and enabled.
        
        Args:
            provider_name: The name of the provider.
            
        Returns:
            True if the provider is registered and enabled, False otherwise.
        """
        with self._lock:
            return provider_name in self._enabled_order

    def get(self, provider_name: str) -> SignalProvider:
        """
        Retrieves a specific signal provider by name.
        
        Args:
            provider_name: The name of the provider.
            
        Returns:
            The provider instance.
            
        Raises:
            ValidationError: If the provider is not registered.
        """
        with self._lock:
            if provider_name not in self._providers:
                raise ValidationError(f"Signal provider '{provider_name}' is not registered.")
            return self._providers[provider_name]

    def get_all(self) -> Tuple[SignalProvider, ...]:
        """
        Retrieves all registered signal providers in an immutable tuple.
        Order is based on registration sequence.
        
        Returns:
            A tuple of all registered provider instances.
        """
        with self._lock:
            return tuple(self._providers.values())

    def get_enabled(self) -> Tuple[SignalProvider, ...]:
        """
        Retrieves all enabled signal providers in an immutable tuple.
        Order is strictly maintained based on enablement sequence to 
        ensure deterministic execution priority.
        
        Returns:
            A tuple of all enabled provider instances.
        """
        with self._lock:
            return tuple(self._providers[name] for name in self._enabled_order)

    def clear(self) -> None:
        """Clears all registered and enabled signal providers."""
        with self._lock:
            self._providers.clear()
            self._enabled_order.clear()
            self._logger.info("Cleared all signal providers from the registry.")

    def _validate_provider(self, provider: Any) -> None:
        """
        Validates that the provider meets the required SignalProvider Protocol.
        
        Args:
            provider: The provider instance to validate.
            
        Raises:
            ValidationError: If the provider lacks required attributes or methods.
        """
        if not isinstance(provider, SignalProvider):
            raise ValidationError(
                "Signal provider must satisfy the SignalProvider Protocol "
                "(requires 'name' attribute and 'generate' method)."
            )
            
        if not provider.name or not isinstance(provider.name, str):
            raise ValidationError("Signal provider 'name' must be a non-empty string.")