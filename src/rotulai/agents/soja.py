from rotulai.agents.base import SemanticTermAgent
from rotulai.agents.registry import register_agent


@register_agent("soja")
class SoyAgent(SemanticTermAgent):
    """Detecta nomes técnicos/disfarçados de derivados de soja."""
