"""Coleta bruta de rótulos brasileiros do Open Food Facts.

Guarda tudo em um .jsonl para depois estratificar. Não decide nada sobre
gabarito: só baixa.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RotulAI-TCC/0.1 (pesquisa academica UFG)"
BASE = "https://br.openfoodfacts.org/cgi/search.pl"
CAMPOS = "code,product_name,brands,quantity,ingredients_text_pt,ingredients_text,allergens_tags,traces_tags,categories_tags"

PAT_DECL = re.compile(r"al[ée]rgicos?\s*[:\-]", re.I)


def busca_pagina(termo: str, page: int, page_size: int = 100) -> list[dict]:
    params = {
        "action": "process",
        "search_terms": termo,
        "page_size": page_size,
        "page": page,
        "fields": CAMPOS,
        "json": 1,
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r).get("products", [])
        except Exception as e:
            print(f"    tentativa {tentativa+1} falhou: {e}", file=sys.stderr)
            time.sleep(4 * (tentativa + 1))
    return []


TERMOS = [
    "leite", "chocolate", "biscoito", "pão", "iogurte", "queijo",
    "bolo", "achocolatado", "molho", "cereal", "sorvete", "requeijão",
    "margarina", "macarrão", "doce", "salgadinho", "barra", "bebida",
]


def main() -> None:
    saida = Path(sys.argv[1])
    vistos: dict[str, dict] = {}
    for termo in TERMOS:
        for page in (1, 2):
            prods = busca_pagina(termo, page)
            novos = 0
            for p in prods:
                code = p.get("code")
                texto = p.get("ingredients_text_pt") or p.get("ingredients_text") or ""
                if not code or not texto.strip():
                    continue
                if code not in vistos:
                    vistos[code] = p
                    novos += 1
            print(f"  [{termo} p{page}] +{novos} (total {len(vistos)})")
            time.sleep(1.5)

    with saida.open("w", encoding="utf-8") as f:
        for p in vistos.values():
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    com_decl = sum(
        1 for p in vistos.values()
        if PAT_DECL.search(p.get("ingredients_text_pt") or p.get("ingredients_text") or "")
    )
    print(f"\ntotal coletado: {len(vistos)}")
    print(f"com declaração 'ALÉRGICOS:' embutida: {com_decl}")
    print(f"gravado em {saida}")


if __name__ == "__main__":
    main()
