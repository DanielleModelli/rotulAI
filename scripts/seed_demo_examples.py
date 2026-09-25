"""Insere exemplos ILUSTRATIVOS (não são produtos reais do Open Food Facts)
pra demonstrar o caso de um produto que FALHA a regra de identidade — os 42
rótulos reais que declaram % de cacau no próprio texto (ver
`enrich_cocoa_pct.py`) por acaso só cobrem casos que passam (fabricante só
anuncia o % quando é alto). `source="exemplo_demo"` marca claramente que não
vieram do Open Food Facts, do mesmo jeito que o exemplo fictício de
`main.py`.

Uso:
    python scripts/seed_demo_examples.py
"""

from __future__ import annotations

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session

EXAMPLES = [
    LabelRecord(
        id="demo-achocolatado-baixo-cacau",
        product_id="demo-achocolatado-baixo-cacau",
        product_name="Barra sabor chocolate (exemplo ilustrativo)",
        ingredients_text=(
            "açúcar, gordura vegetal, cereal de arroz, cacau em pó, "
            "soro de leite, emulsificante lecitina de soja, aromatizante"
        ),
        declared_category="chocolate",
        declared_composition={"solidos_totais_cacau_pct": 12},
        source="exemplo_demo",
    ),
]


def main() -> None:
    with get_session() as session:
        for record in EXAMPLES:
            session.merge(record)
        session.commit()
    print(f"{len(EXAMPLES)} exemplo(s) ilustrativo(s) inserido(s).")


if __name__ == "__main__":
    main()
