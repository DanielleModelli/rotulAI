"""Completa `declared_composition` dos rótulos de chocolate já salvos com o
% de sólidos totais de cacau, quando ele já aparece — de verdade — no nome
ou no texto de ingredientes do produto (ex.: "Talento Dark 50% Cacau",
"Cocoa solids 31% minimum"). Não inventa número: só extrai o que o próprio
rótulo já declara.

Isso não resolve todos os rótulos (a maioria não declara % em lugar
nenhum) — para esses, `IdentityRuleChecker` continua respondendo
"sem dado pra avaliar" (`passed=None`), o que é o comportamento correto.

Uso:
    python scripts/enrich_cocoa_pct.py
"""

from __future__ import annotations

import re

from rotulai.db.models import LabelRecord
from rotulai.db.postgres_client import get_session

_PATTERNS = [
    re.compile(r"(\d{1,3})\s*%\s*(?:de\s+)?cacau", re.IGNORECASE),
    re.compile(r"cocoa solids\s*(\d{1,3})\s*%", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*%\s*cocoa", re.IGNORECASE),
]


def extract_cocoa_pct(text: str) -> float | None:
    for pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def main() -> None:
    updated = 0
    with get_session() as session:
        labels = session.query(LabelRecord).filter(LabelRecord.declared_category == "chocolate").all()
        for label in labels:
            if "solidos_totais_cacau_pct" in (label.declared_composition or {}):
                continue
            pct = extract_cocoa_pct(f"{label.product_name} {label.ingredients_text}")
            if pct is None:
                continue
            label.declared_composition = {**(label.declared_composition or {}), "solidos_totais_cacau_pct": pct}
            print(f"[{label.product_name}] solidos_totais_cacau_pct = {pct}%")
            updated += 1
        session.commit()
    print(f"\n{updated} rótulos completados com % de cacau extraído do próprio texto.")


if __name__ == "__main__":
    main()
