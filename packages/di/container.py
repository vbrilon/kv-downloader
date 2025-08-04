"""Simple dependency injection container"""

from typing import Any, Dict, Callable, TypeVar, Type

T = TypeVar('T')


class DIContainer:
    """Lightweight dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Dict] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T], singleton: bool = False) -> None:
        """Register a factory function for an interface"""
        self._services[interface.__name__] = {
            'factory': factory,
            'singleton': singleton,
            'type': 'factory'
        }
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a concrete instance (always singleton)"""
        self._singletons[interface.__name__] = instance
        self._services[interface.__name__] = {
            'singleton': True,
            'type': 'instance'
        }
    
    def get(self, interface: Type[T]) -> T:
        """Get an instance of the requested interface"""
        service_name = interface.__name__
        
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        
        service_info = self._services[service_name]
        
        # Return existing singleton instance
        if service_info['singleton'] and service_name in self._singletons:
            return self._singletons[service_name]
        
        # Handle registered instances
        if service_info['type'] == 'instance':
            return self._singletons[service_name]
        
        # Create new instance using factory
        if service_info['type'] == 'factory':
            instance = service_info['factory']()
            
            # Store singleton
            if service_info['singleton']:
                self._singletons[service_name] = instance
            
            return instance
        
        raise ValueError(f"Unknown service type for {service_name}")
    
    def has(self, interface: Type[T]) -> bool:
        """Check if interface is registered"""
        return interface.__name__ in self._services