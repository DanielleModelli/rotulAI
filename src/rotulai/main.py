"""Exemplo de execução ponta a ponta com um rótulo fictício.

Pré-requisitos: `docker compose up -d`, `python scripts/seed_chroma.py`,
ANTHROPIC_API_KEY configurada no .env.
"""

from rotulai.db.postgres_client import init_db
from rotulai.pipeline import analyze_label
from rotulai.schemas import LabelInput

EXEMPLO = LabelInput(
    product_id="demo-001",
    product_name="Barra de cereal sabor morango",
    ingredients_text=(
        "Flocos de arroz, açúcar, xarope de glucose, gordura vegetal, "
        "soro de leite em pó, aroma artificial de morango, lecitina de soja, "
        "sal"
    ),
    source="exemplo_demo",
)


def main() -> None:
    init_db()
    result = analyze_label(EXEMPLO)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
