"""Garante que plugar um novo agent não exige tocar no DecisorAgent."""

from rotulai.agents.base import SpecialistAgent
from rotulai.agents.decisor import DecisorAgent
from rotulai.agents.registry import get_registered_agents, register_agent
from rotulai.schemas import AgentFinding, LabelInput


def test_agents_especialistas_reais_estao_registrados():
    assert {"chocolate", "laticinios"} <= set(get_registered_agents())


def test_decisor_descobre_agent_recem_registrado():
    @register_agent("gluten_teste")
    class FakeGlutenAgent(SpecialistAgent):
        def analyze(self, label: LabelInput) -> AgentFinding:
            return AgentFinding(category="gluten_teste", hidden_allergen_detected=False)

    decisor = DecisorAgent()

    assert "gluten_teste" in decisor.agents
    assert isinstance(decisor.agents["gluten_teste"], FakeGlutenAgent)


def test_route_chama_todos_os_agents_registrados():
    label = LabelInput(product_id="1", product_name="Teste", ingredients_text="agua, sal")
    fake_finding = AgentFinding(category="fake", hidden_allergen_detected=False)

    class FakeAgent(SpecialistAgent):
        category = "fake"

        def analyze(self, label: LabelInput) -> AgentFinding:
            return fake_finding

    decisor = DecisorAgent(agents={"fake": FakeAgent()})
    findings = decisor.route(label)

    assert findings == [fake_finding]
