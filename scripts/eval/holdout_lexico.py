"""Hold-out do léxico: mede se o sistema generaliza além da base curada.

O estrato "oculto fora da base" do conjunto não serve a essa medição, porque
ele colapsou nos casos em que NENHUM termo de alérgeno aparece no texto, e ali
o sistema não tem como acertar: a informação não está na entrada.

A medição correta é por retirada. Removem-se da base exatamente os termos que
sustentam as detecções do estrato "oculto na base" e reexecuta-se a condição
C3. Se o recall se mantiver, há generalização semântica. Se cair para perto de
zero, o desempenho é cobertura de dicionário.

Uso:
    CHROMA_MODE=local CHROMA_PATH=.chroma_holdout \
      python scripts/eval/holdout_lexico.py
    CHROMA_MODE=local CHROMA_PATH=.chroma_holdout \
      python scripts/eval/run_eval.py --condicao c3 --tag holdout
"""

from __future__ import annotations

import json
from pathlib import Path

from rotulai.db.chroma_client import get_terms_collection

RAIZ = Path(__file__).resolve().parents[2]
TERMOS = RAIZ / "data" / "allergen_terms"
GOLD = RAIZ / "data" / "eval" / "gold_v1.jsonl"


def termos_a_remover() -> dict[str, set[str]]:
    """Os termos da base que sustentam as detecções do estrato oculto_na_base."""
    fora: dict[str, set[str]] = {}
    for linha in GOLD.read_text(encoding="utf-8").splitlines():
        g = json.loads(linha)
        for cat, est in g["estratos"].items():
            if est == "oculto_na_base":
                fora.setdefault(cat, set()).update(g["gold"][cat].get("evidencia_base") or [])
    return fora


def main() -> None:
    remover = termos_a_remover()
    print("Termos retirados da base (hold-out):")
    for cat, ts in sorted(remover.items()):
        print(f"  {cat}: {sorted(ts)}")

    registro = {}
    for arquivo in sorted(TERMOS.glob("*.json")):
        categoria = arquivo.stem
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        entradas = dados["termos"] if isinstance(dados, dict) else dados
        todos = [e["termo"] if isinstance(e, dict) else e for e in entradas]

        alvo = {t.lower() for t in remover.get(categoria, set())}
        # o gabarito guarda o termo já normalizado; compara sem acento
        import unicodedata

        def norm(s: str) -> str:
            s = unicodedata.normalize("NFD", s.lower())
            return "".join(c for c in s if unicodedata.category(c) != "Mn")

        # Remove a FAMÍLIA morfológica, e não só o termo exato. Tirar "lecitina"
        # deixando "lecitina de soja" na base não testa generalização nenhuma:
        # o ingrediente ainda casa com um termo quase idêntico.
        raizes = {norm(t) for t in alvo}
        def e_da_familia(termo: str) -> bool:
            n = norm(termo)
            return any(r in n or n in r for r in raizes)
        mantidos = [t for t in todos if not e_da_familia(t)]

        colecao = get_terms_collection(categoria)
        colecao.upsert(
            ids=[f"{categoria}-{i}" for i in range(len(mantidos))],
            documents=mantidos,
        )
        registro[categoria] = {"antes": len(todos), "depois": len(mantidos),
                               "removidos": sorted(set(todos) - set(mantidos))}
        print(f"  [{categoria}] {len(todos)} -> {len(mantidos)} termos")

    destino = RAIZ / "results" / "tables" / "holdout_termos_removidos.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n-> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
