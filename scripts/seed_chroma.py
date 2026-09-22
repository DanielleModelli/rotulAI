"""Carrega os termos de data/allergen_terms/*.json nas coleções do ChromaDB.

As listas em data/allergen_terms/ são PLACEHOLDERS ilustrativos — devem ser
substituídas por uma base curada (nutricionista/regulatório) antes de uso real.

Uso:
    python scripts/seed_chroma.py
"""

from __future__ import annotations


import json
from pathlib import Path

from rotulai.db.chroma_client import get_terms_collection

DATA_DIR = Path(__file__).parent.parent / "data" / "allergen_terms"


def seed_category(category: str, terms: list[str]) -> None:
    collection = get_terms_collection(category)
    collection.upsert(
        ids=[f"{category}-{i}" for i in range(len(terms))],
        documents=terms,
    )
    print(f"[{category}] {len(terms)} termos carregados.")


def main() -> None:
    for json_file in DATA_DIR.glob("*.json"):
        category = json_file.stem
        terms = json.loads(json_file.read_text(encoding="utf-8"))
        seed_category(category, terms)


if __name__ == "__main__":
    main()
