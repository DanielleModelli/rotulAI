"""Conformidade de identidade do produto, a segunda frente do sistema.

Esta frente responde a uma pergunta diferente da detecção de alérgeno. Ali a
pergunta é lexical e semântica ("este ingrediente é um derivado de leite?"), e a
evidência vem de busca vetorial sobre vocabulário curado. Aqui a pergunta é
quantitativa e normativa ("este produto pode se chamar manteiga?"), e a evidência
vem de regras de composição com limite numérico (Lei do Chocolate, RIISPOA).

Os verificadores foram escritos na frente de interface e estão reproduzidos aqui
sem alteração de comportamento. O que muda é o lugar: eles saem de dentro do
agente especialista de alérgeno e passam a compor um auditor próprio.

Essa separação não é organização cosmética. O prompt da condição C3 serializa o
AgentFinding literalmente, de modo que qualquer campo acrescentado a ele entra no
texto enviado ao modelo e altera os resultados publicados no relatório. Mantendo
as duas saídas em schemas distintos, a garantia deixa de depender de disciplina e
passa a ser estrutural, e o teste tests/test_prompt_congelado.py a verifica.
"""

from __future__ import annotations

from rotulai.agents.utils import compare, find_ingredient_position, split_ingredients
from rotulai.db.postgres_client import get_active_rules
from rotulai.schemas import (
    IdentityReport,
    IdentityRuleResult,
    IngredientPositionSignal,
    LabelInput,
    Rule,
)

_POSITION_SIGNAL_KEYWORDS = {
    "chocolate": ["cacau", "cocoa"],
}


class IngredientPositionChecker:
    """Sinal informal (não é regra legal): em que posição da lista de
    ingredientes aparece o ingrediente-chave da categoria (ex.: cacau, pra
    chocolate). Como a lista é obrigatoriamente ordenada por proporção
    decrescente (RDC 727/2022, Art. 11), quanto mais cedo aparece, maior a
    proporção provável — mas isso não é regra de identidade formal e não
    substitui a checagem de `IdentityRuleChecker`.
    """

    def __init__(self, category: str):
        self.keywords = _POSITION_SIGNAL_KEYWORDS.get(category, [])

    def check(self, label: LabelInput) -> IngredientPositionSignal | None:
        if not self.keywords or label.declared_category is None:
            return None

        ingredients = split_ingredients(label.ingredients_text)
        found = find_ingredient_position(ingredients, self.keywords)
        if found is None:
            return None

        keyword, position = found
        return IngredientPositionSignal(
            keyword_matched=keyword,
            position=position,
            total_ingredients=len(ingredients),
            note=(
                f"'{keyword}' aparece na posição {position} de {len(ingredients)} "
                "ingredientes. A lista é ordenada por proporção decrescente "
                "(RDC 727/2022, Art. 11) — quanto mais cedo, maior a proporção "
                "provável. Isso é um indício, não uma regra de identidade formal."
            ),
        )


class IdentityRuleChecker:
    """Confere os campos de composição declarados de um rótulo (ex.: % de
    sólidos de cacau) contra as regras de identidade/PIQ vigentes para a
    categoria (ex.: Lei do Chocolate, RIISPOA) — diferente da detecção de
    alérgeno escondido, que é feita por `SemanticTermAgent` via ChromaDB.

    Só roda quando o rótulo declara `declared_category` (ex.: "chocolate",
    "queijo"): sem isso não há denominação-alvo contra a qual balizar as
    regras, então a checagem é pulada (lista vazia), não um erro.
    """

    def __init__(self, category: str, rules: list[Rule] | None = None):
        self.category = category
        self._rules = rules

    def _load_rules(self) -> list[Rule]:
        if self._rules is None:
            self._rules = get_active_rules(self.category)
        return self._rules

    def check(self, label: LabelInput) -> list[IdentityRuleResult]:
        if not label.declared_category:
            return []

        applicable = [r for r in self._load_rules() if r.applies_to == label.declared_category]
        results = []
        for rule in applicable:
            observed = label.declared_composition.get(rule.field)
            passed = compare(observed, rule.operator, rule.value) if observed is not None else None
            results.append(
                IdentityRuleResult(
                    rule_id=rule.id,
                    applies_to=rule.applies_to,
                    field=rule.field,
                    operator=rule.operator,
                    expected_value=rule.value,
                    observed_value=observed,
                    unit=rule.unit,
                    passed=passed,
                    on_fail_denomination=rule.on_fail_denomination,
                    norma_referencia=rule.norma_referencia,
                    notes=rule.notes,
                )
            )
        return results


class IdentityAuditor:
    """Ponto único de entrada da frente de identidade.

    Roda em paralelo ao DecisorAgent, sobre o mesmo rótulo, e devolve um
    relatório próprio. Não toca no caminho de alérgeno e não alimenta o prompt
    do revisor.

    Devolve None quando o rótulo não declara categoria, porque sem denominação
    declarada não há norma de identidade aplicável. Ausência de regra não é
    conformidade, e o chamador precisa poder distinguir as duas coisas.
    """

    def __init__(self, rules: list[Rule] | None = None):
        self._rules = rules

    def audit(self, label: LabelInput) -> IdentityReport | None:
        categoria = label.declared_category
        if not categoria:
            return None

        resultados = IdentityRuleChecker(categoria, self._rules).check(label)
        sinal = IngredientPositionChecker(categoria).check(label)

        avaliadas = [r for r in resultados if r.passed is not None]
        violadas = [r for r in avaliadas if r.passed is False]

        return IdentityReport(
            declared_category=categoria,
            rule_results=resultados,
            ingredient_position_signal=sinal,
            rules_evaluated=len(avaliadas),
            rules_violated=len(violadas),
            denomination_at_risk=bool(violadas),
            suggested_denomination=violadas[0].on_fail_denomination if violadas else None,
        )
