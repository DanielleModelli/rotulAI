from __future__ import annotations
from rotulai.agents.base import SpecialistAgent

_REGISTRY: dict[str, type[SpecialistAgent]] = {}


def register_agent(category: str):
    """Decorator que registra um agent especialista sob uma categoria.

    Uso:
        @register_agent("gluten")
        class GlutenAgent(SpecialistAgent):
            ...
    """

    def decorator(cls: type[SpecialistAgent]) -> type[SpecialistAgent]:
        cls.category = category
        _REGISTRY[category] = cls
        return cls

    return decorator


def get_registered_agents() -> dict[str, type[SpecialistAgent]]:
    return dict(_REGISTRY)
