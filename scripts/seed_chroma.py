"""Carrega os termos de data/allergen_terms/*.json nas coleções do ChromaDB.

Cada arquivo traz a categoria, se ela é de declaração obrigatória pela
RDC 26/2015, as fontes usadas na curadoria e os termos com a origem de cada um.
A origem é o que permite ao relatório declarar a proporção de vocabulário
normativo, de publicação oficial e de conhecimento de domínio.

Uso:
    python scripts/seed_chroma.py
"""

from __future__ import annotations


import json
from pathlib import Path

from rotulai.db.chroma_client import get_terms_collection

DATA_DIR = Path(__file__).parent.parent / "data" / "allergen_terms"


def carregar(json_file: Path) -> tuple[list[str], list[str]]:
    """Devolve (termos, fontes) do arquivo da categoria.

    Aceita o formato antigo (lista simples de strings), em que a origem de
    cada termo é desconhecida.
    """
    dados = json.loads(json_file.read_text(encoding="utf-8"))
    if isinstance(dados, list):
        return [str(t) for t in dados], ["desconhecida"] * len(dados)
    entradas = dados["termos"]
    return [e["termo"] for e in entradas], [e.get("fonte", "desconhecida") for e in entradas]


def seed_category(category: str, terms: list[str], fontes: list[str]) -> None:
    collection = get_terms_collection(category)
    collection.upsert(
        ids=[f"{category}-{i}" for i in range(len(terms))],
        documents=terms,
        metadatas=[{"fonte": f} for f in fontes],
    )
    resumo = ", ".join(f"{fontes.count(f)} {f}" for f in sorted(set(fontes)))
    print(f"[{category}] {len(terms)} termos carregados ({resumo}).")


def main() -> None:
    for json_file in sorted(DATA_DIR.glob("*.json")):
        terms, fontes = carregar(json_file)
        seed_category(json_file.stem, terms, fontes)


if __name__ == "__main__":
    main()
