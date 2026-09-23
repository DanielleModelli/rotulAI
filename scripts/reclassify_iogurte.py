"""Marca `declared_category="iogurte"` nos rótulos já salvos cujo
`product_name` literalmente contém "iogurte" — o seed original do Open Food
Facts (`seed_labels_openfoodfacts.py`) só mapeia categorias amplas do OFF
(chocolates/cheeses/butters/dairies), então produtos de iogurte entraram
sem denominação declarada. Só reclassifica quando o nome já diz isso — não
adivinha a partir dos ingredientes (ex.: "Danone Natural Desnatado" não é
tocado, mesmo parecendo um iogurte, porque o nome não afirma isso).

Uso:
    python scripts/reclassify_iogurte.py
"""

from __future__ import annotations

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session


def main() -> None:
    updated = 0
    with get_session() as session:
        labels = session.query(LabelRecord).filter(LabelRecord.declared_category.is_(None)).all()
        for label in labels:
            if "iogurte" in label.product_name.lower():
                label.declared_category = "iogurte"
                print(f"[{label.product_name}] declared_category = iogurte")
                updated += 1
        session.commit()
    print(f"\n{updated} rótulos reclassificados como iogurte.")


if __name__ == "__main__":
    main()
