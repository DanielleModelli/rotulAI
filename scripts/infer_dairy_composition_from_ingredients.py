"""Infere `gordura_nao_lactea_pct` e `proteina_nao_lactea_pct` de rótulos de
laticínios (manteiga, queijo, requeijão) a partir da PRESENÇA/AUSÊNCIA de
palavras-chave na própria lista de ingredientes — não é medição de
laboratório, mas é um dado real: a RDC 727/2022 exige que a lista de
ingredientes seja **completa**, então se "gordura vegetal" não aparece em
lugar nenhum do rótulo, é legítimo tratar isso como 0%; se aparece, é
legítimo tratar como "presente" (> 0, o suficiente pra violar a regra
`<= 0%` do RIISPOA — não temos como saber o percentual exato só pela
presença, só que ele é maior que zero).

Diferente de `enrich_cocoa_pct.py` (que só funciona pros poucos rótulos que
declaram um número explícito), isso funciona pra qualquer rótulo com lista
de ingredientes completa — é por isso que cobre muito mais produtos.

Uso:
    python scripts/infer_dairy_composition_from_ingredients.py
"""

from __future__ import annotations

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session

_KEYWORDS_BY_FIELD = {
    "gordura_nao_lactea_pct": [
        "gordura vegetal",
        "gorduras vegetais",
        "óleo vegetal",
        "óleos vegetais",
        "gordura hidrogenada",
    ],
    "proteina_nao_lactea_pct": [
        "proteína de soja",
        "proteína vegetal",
        "proteína texturizada",
    ],
}

_APPLIES_TO = {"manteiga", "queijo", "requeijao", "composto_lacteo"}


def _infer(ingredients_text: str, keywords: list[str]) -> float:
    lowered = ingredients_text.lower()
    return 1.0 if any(keyword in lowered for keyword in keywords) else 0.0


def main() -> None:
    updated = 0
    with get_session() as session:
        labels = session.query(LabelRecord).filter(LabelRecord.declared_category.in_(_APPLIES_TO)).all()
        for label in labels:
            composition = dict(label.declared_composition or {})
            changed = False
            for field, keywords in _KEYWORDS_BY_FIELD.items():
                if field in composition:
                    continue
                composition[field] = _infer(label.ingredients_text, keywords)
                changed = True
            if changed:
                label.declared_composition = composition
                print(f"[{label.product_name}] {composition}")
                updated += 1
        session.commit()
    print(f"\n{updated} rótulos completados por inferência da lista de ingredientes.")


if __name__ == "__main__":
    main()
