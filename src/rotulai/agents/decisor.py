from __future__ import annotations
from rotulai.agents.base import SpecialistAgent
from rotulai.agents.registry import get_registered_agents
from rotulai.schemas import AgentFinding, LabelInput


class DecisorAgent:
    """Orquestra os agents especialistas.

    Hoje roda todos os agents registrados em cada rótulo (só temos duas
    categorias). Conforme mais agents forem plugados, dá pra evoluir a
    lógica de `route` para pré-filtrar quais categorias fazem sentido para
    um dado rótulo (ex.: por tipo de produto) sem tocar nos agents em si.
    """

    def __init__(self, agents: dict[str, SpecialistAgent] | None = None):
        self.agents = agents or {
            category: agent_cls() for category, agent_cls in get_registered_agents().items()
        }

    def route(self, label: LabelInput) -> list[AgentFinding]:
        return [agent.analyze(label) for agent in self.agents.values()]
