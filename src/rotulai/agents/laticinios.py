from rotulai.agents.base import SemanticTermAgent
from rotulai.agents.registry import register_agent


@register_agent("laticinios")
class DairyAgent(SemanticTermAgent):
    """Detecta nomes técnicos/disfarçados de derivados de leite."""
