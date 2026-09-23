from __future__ import annotations
from abc import ABC, abstractmethod

from rotulai.config import settings
from rotulai.db.chroma_client import get_terms_collection, semantic_match
from rotulai.db.postgres_client import get_active_rules
from rotulai.schemas import (
    AgentFinding,
    IdentityRuleResult,
    IngredientPositionSignal,
    LabelInput,
    MatchedTerm,
    Rule,
)
from rotulai.agents.utils import compare, find_ingredient_position, split_ingredients

# Palavras-chave do ingrediente "principal" de cada categoria, usadas só pro
# sinal informal de posição na lista (ver IngredientPositionChecker) — não
# tem relação com as regras de identidade (essas ficam em `rules`).
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


class SpecialistAgent(ABC):
    """Interface que todo agent especialista (laticínios, chocolate, ...) implementa.

    Para plugar uma nova categoria de alérgeno:
      1. Criar uma classe que herde de SpecialistAgent (ou de SemanticTermAgent,
         abaixo, se a detecção for por similaridade semântica no ChromaDB).
      2. Decorá-la com @register_agent("nome_da_categoria").
      3. Implementar analyze() (dispensável se herdar de SemanticTermAgent).
    O DecisorAgent descobre agents novos automaticamente via registry — não
    precisa alterar nada fora do arquivo do novo agent.
    """

    category: str

    @abstractmethod
    def analyze(self, label: LabelInput) -> AgentFinding: ...


class SemanticTermAgent(SpecialistAgent):
    """Implementação padrão: compara cada ingrediente do rótulo contra a
    coleção de termos conhecidos (nomes disfarçados/técnicos) da própria
    categoria no ChromaDB, via similaridade semântica.

    Cobre a maioria dos casos de "achar nome escondido de alérgeno". Um novo
    agent só precisa herdar disso e ser registrado — sem reimplementar a
    busca vetorial.
    """

    def __init__(self, threshold: float | None = None):
        self.threshold = threshold if threshold is not None else settings.similarity_threshold
        self.collection = get_terms_collection(self.category)
        self.identity_checker = IdentityRuleChecker(self.category)
        self.position_checker = IngredientPositionChecker(self.category)

    def analyze(self, label: LabelInput) -> AgentFinding:
        matches: list[MatchedTerm] = []
        for ingredient in split_ingredients(label.ingredients_text):
            for document, _metadata, similarity in semantic_match(self.collection, ingredient):
                if similarity >= self.threshold:
                    matches.append(
                        MatchedTerm(
                            term_found=ingredient,
                            known_hidden_name=document,
                            similarity=round(similarity, 3),
                        )
                    )

        return AgentFinding(
            category=self.category,
            hidden_allergen_detected=len(matches) > 0,
            matches=matches,
            identity_rule_results=self.identity_checker.check(label),
            ingredient_position_signal=self.position_checker.check(label),
        )
