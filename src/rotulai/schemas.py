from typing import List, Optional

from pydantic import BaseModel, Field


class LabelInput(BaseModel):
    """Rótulo de um produto a ser analisado."""

    product_id: str
    product_name: str
    ingredients_text: str
    source: Optional[str] = None


class MatchedTerm(BaseModel):
    term_found: str
    known_hidden_name: str
    similarity: float


class AgentFinding(BaseModel):
    """Resultado de um agent especialista para uma categoria de alérgeno."""

    category: str
    hidden_allergen_detected: bool
    matches: List[MatchedTerm] = Field(default_factory=list)
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
