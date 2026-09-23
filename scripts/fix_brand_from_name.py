"""Completa `brand` de casos pontuais em que o campo estruturado `brands`
do Open Food Facts veio vazio, mas a marca está escrita, sem ambiguidade,
no próprio `product_name` (ex.: "LINDT Chocolate Amargo..."). Diferente de
`backfill_brands.py` (que consulta a API), isso é uma correção manual e
pequena — mapeamento explícito por id, não uma heurística de extração
genérica (extrair "a primeira palavra maiúscula" como marca daria muito
falso positivo, ex. "Chocolate", "Extra").

Uso:
    python scripts/fix_brand_from_name.py
"""

from __future__ import annotations

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session

_BRAND_BY_ID = {
    "openfoodfacts-7908320902383": "Lindt",  # "LINDT Chocolate Amargo Extrafino Excellence - 70% Cacau"
    "openfoodfacts-7891515557423": "Qualy",  # "Manteiga Extra Com Sal Qualy Pote 500g"
    "openfoodfacts-7891025120230": "Danone",  # "Iogurte Integral Natural Danone Copo 160g"
}


def main() -> None:
    updated = 0
    with get_session() as session:
        for label_id, brand in _BRAND_BY_ID.items():
            record = session.get(LabelRecord, label_id)
            if record is not None and not record.brand:
                record.brand = brand
                print(f"[{record.product_name}] brand = {brand}")
                updated += 1
        session.commit()
    print(f"\n{updated} rótulos corrigidos.")


if __name__ == "__main__":
    main()
