from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import Session, sessionmaker

from rotulai.config import settings
from rotulai.db.models import AnalysisResultRecord, Base, LabelRecord, RuleRecord
from rotulai.schemas import AnalysisResult, LabelInput, Rule

_engine = create_engine(settings.database_url)
_SessionLocal = sessionmaker(bind=_engine)


def init_db() -> None:
    """Cria as tabelas se não existirem. Para evoluções futuras de schema,
    trocar por Alembic.
    """
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    return _SessionLocal()


def save_analysis_result(result: AnalysisResult) -> AnalysisResultRecord:
    record = AnalysisResultRecord(
        product_id=result.label.product_id,
        product_name=result.label.product_name,
        ingredients_text=result.label.ingredients_text,
        contains_hidden_allergen=result.verdict.contains_hidden_allergen,
        allergens_confirmed=result.verdict.allergens_confirmed,
        confidence=result.verdict.confidence,
        reasoning=result.verdict.reasoning,
        specialist_findings=[f.model_dump() for f in result.findings],
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def save_label(label: LabelInput) -> LabelRecord:
    record = LabelRecord(
        product_id=label.product_id,
        product_name=label.product_name,
        brand=label.brand,
        ingredients_text=label.ingredients_text,
        declared_category=label.declared_category,
        declared_composition=label.declared_composition,
        source=label.source,
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def _record_to_rule(record: RuleRecord) -> Rule:
    return Rule(
        id=record.id,
        category=record.category,
        applies_to=record.applies_to,
        field=record.field,
        operator=record.operator,
        value=record.value,
        unit=record.unit,
        on_fail_denomination=record.on_fail_denomination,
        norma_referencia=record.norma_referencia,
        vigente_de=record.vigente_de,
        vigente_ate=record.vigente_ate,
        notes=record.notes,
    )


def get_category_for_denomination(applies_to: str) -> str | None:
    """A qual categoria de agent (ex.: "chocolate", "laticinios") pertence
    uma denominação (ex.: "queijo", "chocolate_ao_leite") — usado pra rotear
    o `DecisorAgent` só pro especialista relevante quando o rótulo já
    declara sua denominação. Olha em `rules` independente de vigência (a
    denominação pertence à mesma categoria de agent seja qual for a norma
    vigente hoje).
    """
    with get_session() as session:
        record = session.query(RuleRecord).filter(RuleRecord.applies_to == applies_to).first()
        return record.category if record else None


def get_active_rules(category: str, as_of: datetime | None = None) -> list[Rule]:
    """Regras de identidade/composição de uma categoria, vigentes em `as_of`
    (default: agora). Uma regra sem `vigente_de`/`vigente_ate` é sempre ativa;
    isso é o que permite, por exemplo, a Lei do chocolate já estar cadastrada
    mas só "entrar em ação" na data em que passa a valer.
    """
    as_of = as_of or datetime.now(timezone.utc)
    with get_session() as session:
        records = (
            session.query(RuleRecord)
            .filter(
                RuleRecord.category == category,
                or_(RuleRecord.vigente_de.is_(None), RuleRecord.vigente_de <= as_of),
                or_(RuleRecord.vigente_ate.is_(None), RuleRecord.vigente_ate >= as_of),
            )
            .all()
        )
        return [_record_to_rule(record) for record in records]
