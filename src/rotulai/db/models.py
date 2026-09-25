import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LabelRecord(Base):
    """Rótulo salvo (independente de já ter sido analisado ou não)."""

    __tablename__ = "labels"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String, index=True)
    product_name: Mapped[str] = mapped_column(String)
    brand: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    ingredients_text: Mapped[str] = mapped_column(String)
    declared_category: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    declared_composition: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RuleRecord(Base):
    """Regra de identidade/composição (PIQ) de uma categoria de alimento.

    Regras de termo (alérgeno escondido) continuam no ChromaDB — isso aqui é
    só para regras quantitativas do tipo "campo X tem que ser >= valor Y para
    o produto poder se chamar Z", com a norma e vigência de cada uma.
    """

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category: Mapped[str] = mapped_column(String, index=True)
    applies_to: Mapped[str] = mapped_column(String, index=True)
    field: Mapped[str] = mapped_column(String)
    operator: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    on_fail_denomination: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    norma_referencia: Mapped[str] = mapped_column(String)
    vigente_de: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    vigente_ate: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class AnalysisResultRecord(Base):
    """Resultado final (já revisado pela LLM) de uma análise de rótulo."""

    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String, index=True)
    product_name: Mapped[str] = mapped_column(String)
    ingredients_text: Mapped[str] = mapped_column(String)

    contains_hidden_allergen: Mapped[bool] = mapped_column(Boolean)
    allergens_confirmed: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(String)

    specialist_findings: Mapped[list] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
