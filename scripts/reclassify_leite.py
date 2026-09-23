"""Marca `declared_category` nos rótulos de leite em pó/leite condensado
já salvos, a partir do que o próprio nome do produto já declara — mesmo
espírito de `reclassify_iogurte.py`.

"Leite Condensado Semidesnatado" é mapeado para
`leite_condensado_parcialmente_desnatado` assumindo que "semidesnatado" é
sinônimo comercial de "parcialmente desnatado" — a IN 47/2018 não lista
"semidesnatado" como uma das 4 denominações oficiais, então essa
equivalência é uma aproximação (ver nota na regra correspondente em
`data/rules/laticinios.json`), não uma certeza.

Uso:
    python scripts/reclassify_leite.py
"""

from __future__ import annotations

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session

_MAPPING = [
    ("leite em pó integral", "leite_em_po_integral"),
    ("leite condensado semidesnatado", "leite_condensado_parcialmente_desnatado"),
]


def main() -> None:
    updated = 0
    with get_session() as session:
        labels = session.query(LabelRecord).filter(LabelRecord.declared_category.is_(None)).all()
        for label in labels:
            lowered = label.product_name.lower()
            for needle, category in _MAPPING:
                if needle in lowered:
                    label.declared_category = category
                    print(f"[{label.product_name}] declared_category = {category}")
                    updated += 1
                    break
        session.commit()
    print(f"\n{updated} rótulos reclassificados.")


if __name__ == "__main__":
    main()
