"""Página simples pra escolher um rótulo salvo e ver o resultado da análise:
contém alérgeno escondido? e, quando há dado de composição suficiente, o
produto é de fato o que a denominação diz que é (ex.: "chocolate" cumpre a
regra de identidade vigente)?

Uso:
    uvicorn rotulai.webapp:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import rotulai.agents.chocolate  # noqa: F401 - garante o @register_agent
import rotulai.agents.laticinios  # noqa: F401 - garante o @register_agent
from rotulai.agents.decisor import DecisorAgent
from rotulai.agents.revisor import ReviewerAgent
from rotulai.config import settings
from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session, init_db
from rotulai.schemas import LabelInput

app = FastAPI(title="rotulAI")

_STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    # Protótipo em iteração rápida — sem isso o navegador serve a versão
    # antiga do index.html do cache e some com mudanças recém-feitas.
    return FileResponse(_STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/labels")
def list_labels() -> list[dict]:
    with get_session() as session:
        records = session.query(LabelRecord).order_by(LabelRecord.product_name).all()
        return [
            {
                "id": r.id,
                "product_name": r.product_name,
                "brand": r.brand,
                "declared_category": r.declared_category,
                "source": r.source,
            }
            for r in records
        ]


@app.get("/api/analyze/{label_id}")
def analyze(label_id: str) -> dict:
    with get_session() as session:
        record = session.get(LabelRecord, label_id)
        if record is None:
            raise HTTPException(status_code=404, detail="rótulo não encontrado")

        label = LabelInput(
            product_id=record.product_id,
            product_name=record.product_name,
            brand=record.brand,
            ingredients_text=record.ingredients_text,
            declared_category=record.declared_category,
            declared_composition=record.declared_composition or {},
            source=record.source,
        )

    findings = DecisorAgent().route(label)

    reviewer_result = None
    reviewer_error = None
    if settings.openai_api_key:
        try:
            verdict = ReviewerAgent().review(label, findings)
            reviewer_result = verdict.model_dump()
        except Exception as exc:  # chave inválida, API fora do ar, etc.
            reviewer_error = str(exc)
    else:
        reviewer_error = "OPENAI_API_KEY não configurada — mostrando só os achados brutos dos especialistas."

    return {
        "label": label.model_dump(),
        "findings": [f.model_dump() for f in findings],
        "reviewer": reviewer_result,
        "reviewer_error": reviewer_error,
    }


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
