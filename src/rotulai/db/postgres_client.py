from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rotulai.config import settings
from rotulai.db.models import AnalysisResultRecord, Base
from rotulai.schemas import AnalysisResult

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
