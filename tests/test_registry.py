"""Garante que plugar um novo agent não exige tocar no DecisorAgent."""

from unittest.mock import patch

from rotulai.agents.base import SpecialistAgent
from rotulai.agents.decisor import DecisorAgent
from rotulai.agents.registry import get_registered_agents, register_agent
from rotulai.schemas import AgentFinding, LabelInput


def test_agents_especialistas_reais_estao_registrados():
    assert {"laticinios", "soja", "trigo", "chocolate"} <= set(get_registered_agents())


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


def test_route_com_categoria_declarada_roda_so_o_agent_dono():
    label = LabelInput(
        product_id="1",
        product_name="Queijo Teste",
        ingredients_text="leite, sal",
        declared_category="queijo",
    )
    chocolate_finding = AgentFinding(category="chocolate", hidden_allergen_detected=False)
    laticinios_finding = AgentFinding(category="laticinios", hidden_allergen_detected=False)

    class FakeChocolateAgent(SpecialistAgent):
        category = "chocolate"

        def analyze(self, label: LabelInput) -> AgentFinding:
            return chocolate_finding

    class FakeDairyAgent(SpecialistAgent):
        category = "laticinios"

        def analyze(self, label: LabelInput) -> AgentFinding:
            return laticinios_finding

    decisor = DecisorAgent(agents={"chocolate": FakeChocolateAgent(), "laticinios": FakeDairyAgent()})

    with patch("rotulai.agents.decisor.get_category_for_denomination", return_value="laticinios"):
        findings = decisor.route(label)

    assert findings == [laticinios_finding]
