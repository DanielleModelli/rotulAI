from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LabelInput(BaseModel):
    """Rótulo de um produto a ser analisado.

    `declared_category` é a denominação que o rótulo usa (ex.: "chocolate",
    "achocolatado", "queijo") e `declared_composition` são os valores
    declarados/medidos relevantes para regras de identidade (ex.:
    {"solidos_totais_cacau_pct": 20}). Ambos são opcionais — sem eles, o
    rótulo ainda passa pela detecção de alérgeno escondido, só não roda a
    checagem de regra de identidade/composição.
    """

    product_id: str
    product_name: str
    brand: Optional[str] = None
    ingredients_text: str
    declared_category: Optional[str] = None
    declared_composition: dict[str, float] = Field(default_factory=dict)
    source: Optional[str] = None


class MatchedTerm(BaseModel):
    term_found: str
    known_hidden_name: str
    similarity: float


class Rule(BaseModel):
    """Regra de identidade/composição (PIQ) para uma categoria de alimento.

    Diferente da detecção de alérgeno escondido (matching semântico de termos
    no ChromaDB), isso é uma checagem quantitativa: um campo declarado do
    rótulo (`field`) comparado contra um limiar (`operator`/`value`) exigido
    pela norma para que o produto possa usar a denominação `applies_to`.
    """

    id: str
    category: str
    applies_to: str
    field: str
    operator: str
    value: float
    unit: Optional[str] = None
    on_fail_denomination: Optional[str] = None
    norma_referencia: str
    vigente_de: Optional[datetime] = None
    vigente_ate: Optional[datetime] = None
    notes: Optional[str] = None


class IdentityRuleResult(BaseModel):
    """Resultado da checagem de uma regra de identidade contra um rótulo.

    `passed` é `None` quando o rótulo não declarou `field` em
    `declared_composition` — isso é "sem dado para avaliar", não "violou a
    regra". Só é `True`/`False` quando havia um valor declarado para comparar.
    """

    rule_id: str
    applies_to: str
    field: str
    operator: str
    expected_value: float
    observed_value: Optional[float] = None
    unit: Optional[str] = None
    passed: Optional[bool]
    on_fail_denomination: Optional[str] = None
    norma_referencia: str
    notes: Optional[str] = None


class IngredientPositionSignal(BaseModel):
    """Indício informal (não é regra legal) de que o ingrediente-chave da
    categoria (ex.: cacau, pra chocolate) aparece cedo ou tarde na lista de
    ingredientes. Como a lista é obrigatoriamente ordenada por proporção
    decrescente (RDC 727/2022, Art. 11 — regra geral, vale pra qualquer
    alimento), a posição é um sinal indireto de quantidade quando o rótulo
    não declara o percentual exato.
    """

    keyword_matched: str
    position: int
    total_ingredients: int
    note: str


class AgentFinding(BaseModel):
    """Resultado de um agent especialista para uma categoria de alérgeno."""

    category: str
    hidden_allergen_detected: bool
    matches: List[MatchedTerm] = Field(default_factory=list)
    identity_rule_results: List[IdentityRuleResult] = Field(default_factory=list)
    ingredient_position_signal: Optional[IngredientPositionSignal] = None
    notes: Optional[str] = None


class ReviewVerdict(BaseModel):
    """Veredito final do agent revisor (LLM), consolidando os achados."""

    contains_hidden_allergen: bool
    allergens_confirmed: List[str]
    confidence: float
    reasoning: str
    flagged_false_positives: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Registro completo de uma análise, pronto para persistir no Postgres."""

    label: LabelInput
    findings: List[AgentFinding]
    verdict: ReviewVerdict
