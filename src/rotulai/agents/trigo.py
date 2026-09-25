from rotulai.agents.base import SemanticTermAgent
from rotulai.agents.registry import register_agent


@register_agent("trigo")
class WheatAgent(SemanticTermAgent):
    """Detecta nomes técnicos/disfarçados de trigo, centeio, cevada e aveia."""
