from rotulai.agents.base import SemanticTermAgent
from rotulai.agents.registry import register_agent


@register_agent("chocolate")
class ChocolateAgent(SemanticTermAgent):
    """Detecta nomes técnicos/disfarçados de derivados de cacau/chocolate."""
