"""Popula a tabela `labels` com rótulos reais de produtos brasileiros do
Open Food Facts (openfoodfacts.org), como seed inicial para testar os agents
contra ingredientes de verdade (em vez do único exemplo fictício em main.py).

Fonte: Open Food Facts, licença ODbL (uso comercial permitido; exige
atribuição e, só se você redistribuir publicamente uma base de dados
derivada, que ela também seja aberta). https://world.openfoodfacts.org/data

Como funciona:
  1. A API de busca (search-a-licious) filtra por categoria + país, mas não
     devolve o texto de ingredientes — só metadados/tags normalizadas.
  2. Por isso, para cada produto encontrado, buscamos o rótulo completo
     (com `ingredients_text_pt`) no endpoint de produto por código de barras.
  3. Produtos sem ingredientes preenchidos (comum no OFF, é colaborativo e
     incompleto) são descartados.

`declared_category` é preenchido com a denominação mais provável da
categoria OFF (ex.: "en:chocolates" -> "chocolate", "en:cheeses" ->
"queijo") só para poder exercitar o `IdentityRuleChecker` — é uma
aproximação: o mapeamento é por categoria ampla do OFF, não confirma que o
produto de fato ostenta aquela denominação no rótulo. `declared_composition`
fica vazio: o OFF não traz de forma confiável campos como "% de sólidos de
cacau" — quem for validar identidade de verdade precisa completar isso a
partir do rótulo real (foto/embalagem).

Uso:
    python scripts/seed_labels_openfoodfacts.py [--per-category N]
"""

from __future__ import annotations

import argparse
import html
import time

import requests

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session, init_db

USER_AGENT = "rotulAI-seed-script/1.0 (+https://github.com/; seed de rótulos para pesquisa)"
SEARCH_URL = "https://search.openfoodfacts.org/search"
PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"

# tag OFF -> declared_category usado pelas regras de identidade em data/rules/
CATEGORY_MAP = {
    "en:chocolates": "chocolate",
    "en:cheeses": "queijo",
    "en:butters": "manteiga",
    "en:dairies": None,  # guarda-chuva de laticínios em geral, sem denominação específica
}


def _search_codes(off_category_tag: str, limit: int) -> list[str]:
    query = f'categories_tags:"{off_category_tag}" AND countries_tags:"en:brazil"'
    response = requests.get(
        SEARCH_URL,
        params={"q": query, "page_size": min(limit, 100)},
        headers={"User-Agent": USER_AGENT},
        timeout=25,
    )
    response.raise_for_status()
    return [hit["code"] for hit in response.json().get("hits", []) if hit.get("code")]


def _fetch_label_fields(code: str) -> dict | None:
    try:
        response = requests.get(
            PRODUCT_URL.format(code=code),
            params={
                "fields": "code,product_name,product_name_pt,ingredients_text_pt,ingredients_text,brands"
            },
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("product")
    except (requests.RequestException, ValueError):
        return None


def seed_category(off_category_tag: str, declared_category: str | None, per_category: int) -> int:
    saved = 0
    for code in _search_codes(off_category_tag, per_category):
        time.sleep(0.25)  # não martelar a API pública com requisições sequenciais
        product = _fetch_label_fields(code)
        if not product:
            continue

        ingredients_text = product.get("ingredients_text_pt") or product.get("ingredients_text")
        product_name = product.get("product_name_pt") or product.get("product_name")
        if not ingredients_text or not product_name:
            continue

        brands_raw = product.get("brands") or ""
        brand = html.unescape(brands_raw.split(",")[0].strip()) or None

        with get_session() as session:
            session.merge(
                LabelRecord(
                    id=f"openfoodfacts-{code}",
                    product_id=code,
                    product_name=html.unescape(product_name),
                    brand=brand,
                    ingredients_text=html.unescape(ingredients_text),
                    declared_category=declared_category,
                    declared_composition={},
                    source="openfoodfacts",
                )
            )
            session.commit()
        saved += 1

    print(f"[{off_category_tag} -> {declared_category}] {saved} rótulos salvos.")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-category", type=int, default=40)
    args = parser.parse_args()

    init_db()
    total = sum(
        seed_category(tag, declared_category, args.per_category)
        for tag, declared_category in CATEGORY_MAP.items()
    )
    print(f"Total: {total} rótulos.")


if __name__ == "__main__":
    main()
