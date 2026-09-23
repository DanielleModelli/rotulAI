from __future__ import annotations
from rotulai.agents.base import SpecialistAgent
from rotulai.agents.registry import get_registered_agents
from rotulai.db.postgres_client import get_category_for_denomination
from rotulai.schemas import AgentFinding, LabelInput


class DecisorAgent:
    """Orquestra os agents especialistas.

    Pré-filtro: se o rótulo já declara `declared_category` (ex.: "queijo",
    "chocolate_ao_leite") e a gente sabe a qual agent essa denominação
    pertence (via `rules`), roda só esse agent — não faz sentido nenhum o
    `ChocolateAgent` rodar num queijo. Sem `declared_category` (ou sem
    denominação reconhecida), roda todos os agents registrados — é a rede
    de segurança pra quando não se sabe de antemão o que o rótulo é, onde
    "rodar tudo" ainda faz sentido (ex.: contaminação cruzada inesperada).
    """

    def __init__(self, agents: dict[str, SpecialistAgent] | None = None):
        self.agents = agents or {
            category: agent_cls() for category, agent_cls in get_registered_agents().items()
        }

    def route(self, label: LabelInput) -> list[AgentFinding]:
        relevant = self.agents
        if label.declared_category:
            owner = get_category_for_denomination(label.declared_category)
            if owner in self.agents:
                relevant = {owner: self.agents[owner]}
        return [agent.analyze(label) for agent in relevant.values()]
