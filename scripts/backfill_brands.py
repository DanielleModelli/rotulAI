"""Completa `brand` dos rótulos já salvos (fonte openfoodfacts) que foram
carregados antes desse campo existir — re-consulta cada produto pelo
código de barras (`product_id`) só pra pegar `brands`, sem tocar em nenhum
outro campo (declared_category, declared_composition etc. ficam intactos).

Uso:
    python scripts/backfill_brands.py
"""

from __future__ import annotations

import html
import time

import requests

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session

USER_AGENT = "rotulAI-seed-script/1.0 (+https://github.com/; seed de rótulos para pesquisa)"
PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"


def _fetch_brand(code: str) -> str | None:
    try:
        response = requests.get(
            PRODUCT_URL.format(code=code),
            params={"fields": "brands"},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        response.raise_for_status()
        brands_raw = response.json().get("product", {}).get("brands") or ""
        return html.unescape(brands_raw.split(",")[0].strip()) or None
    except (requests.RequestException, ValueError):
        return None


def main() -> None:
    updated = 0
    with get_session() as session:
        labels = (
            session.query(LabelRecord)
            .filter(LabelRecord.source == "openfoodfacts", LabelRecord.brand.is_(None))
            .all()
        )
        for label in labels:
            time.sleep(0.25)
            brand = _fetch_brand(label.product_id)
            if brand:
                label.brand = brand
                print(f"[{label.product_name}] brand = {brand}")
                updated += 1
        session.commit()
    print(f"\n{updated} rótulos completados com marca.")


if __name__ == "__main__":
    main()
