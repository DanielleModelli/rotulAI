"""Carrega as regras de identidade/composição de data/rules/*.json no Postgres.

As regras de chocolate vêm da Lei 15.404/2026 (ainda não vigente — ver
`vigente_de` de cada uma) e as de laticínios do RIISPOA (Decreto 9.013/2017)
e normas correlatas do MAPA. Ver data/rules/*.json para as fontes exatas.

Uso:
    python scripts/seed_rules.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rotulai.db.models import RuleRecord
from rotulai.db.postgres_client import get_session, init_db

DATA_DIR = Path(__file__).parent.parent / "data" / "rules"

_DATE_FIELDS = ("vigente_de", "vigente_ate")


def _parse_dates(rule: dict) -> dict:
    return {
        **rule,
        **{
            field: datetime.fromisoformat(rule[field].replace("Z", "+00:00"))
            for field in _DATE_FIELDS
            if rule.get(field)
        },
    }


def seed_category(category: str, rules: list[dict]) -> None:
    with get_session() as session:
        for rule in rules:
            session.merge(RuleRecord(**_parse_dates(rule)))
        session.commit()
    print(f"[{category}] {len(rules)} regras carregadas.")


def main() -> None:
    init_db()
    for json_file in DATA_DIR.glob("*.json"):
        category = json_file.stem
        rules = json.loads(json_file.read_text(encoding="utf-8"))
        seed_category(category, rules)


if __name__ == "__main__":
    main()
