"""Schema de saída das condições experimentais.

Difere do ReviewVerdict de produção de propósito: um booleano por categoria
elimina a normalização de texto livre, que é onde um erro silencioso
corromperia todas as métricas. As três condições usam este mesmo schema, então
a comparação continua controlada.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

CATEGORIAS = ("laticinios", "soja", "trigo", "chocolate")


class VereditoAvaliacao(BaseModel):
    """Decisão por categoria sobre um rótulo."""

    laticinios: bool = Field(description="Há leite ou derivado de leite nos ingredientes?")
    soja: bool = Field(description="Há soja ou derivado de soja nos ingredientes?")
    trigo: bool = Field(description="Há trigo, centeio, cevada, aveia ou glúten nos ingredientes?")
    chocolate: bool = Field(description="Há cacau ou derivado de cacau nos ingredientes?")

    evidencias: list[str] = Field(
        default_factory=list,
        description=(
            "Os ingredientes do rótulo que sustentam as respostas acima, copiados "
            "literalmente da lista de ingredientes fornecida."
        ),
    )
    justificativa: str = Field(description="Explicação curta do veredito.")
    confianca: float = Field(description="Confiança de 0 a 1.")

    def por_categoria(self) -> dict[str, bool]:
        return {c: getattr(self, c) for c in CATEGORIAS}
