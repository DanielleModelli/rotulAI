"""Varredura de limiar sobre a camada de recuperação, sem chamar a API.

A condição C3 gravou TODAS as similaridades, sem corte. Isso permite medir,
para cada limiar, o que a recuperação entregaria ao revisor: quantos positivos
ela capturaria e quanto ruído injetaria.

Atenção ao que isto mede. É o desempenho da RECUPERAÇÃO isolada, tratando
"existe correspondência acima do limiar" como predição. Não é o desempenho do
sistema completo, porque o revisor não foi reexecutado em cada limiar. Serve
para escolher o ponto operacional e para mostrar o custo da permissividade.

Uso:
    python scripts/eval/threshold_sweep.py
"""

from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REGULADAS = ("laticinios", "soja", "trigo")
LIMIARES = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]


def carregar():
    gold = {
        json.loads(l)["product_id"]: json.loads(l)
        for l in (RAIZ / "data/eval/gold_v1.jsonl").read_text(encoding="utf-8").splitlines()
    }
    c3 = {}
    for arq in sorted(glob.glob(str(RAIZ / "results/runs/*_c3.jsonl"))):
        for l in Path(arq).read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            c3[d["product_id"]] = d
    return gold, c3


def sim_maxima(registro, categoria: float) -> float:
    """Maior similaridade recuperada para a categoria, ou 0 se nenhuma."""
    melhor = 0.0
    for achado in registro["achados"]:
        if achado["category"] != categoria:
            continue
        for m in achado["matches"]:
            melhor = max(melhor, m["similarity"])
    return melhor


def main() -> None:
    gold, c3 = carregar()
    linhas = []

    for limiar in LIMIARES:
        vp = fp = fn = vn = 0
        fp_distrator = 0
        rec_oculto = [0, 0]
        for pid, g in gold.items():
            reg = c3.get(pid)
            if reg is None:
                continue
            for cat in REGULADAS:
                esperado = bool(g["gold"][cat]["presente"])
                predito = sim_maxima(reg, cat) >= limiar
                vp += esperado and predito
                fp += (not esperado) and predito
                fn += esperado and (not predito)
                vn += (not esperado) and (not predito)
                if g["estratos"][cat] == "distrator" and predito:
                    fp_distrator += 1
                if g["estratos"][cat] == "oculto_na_base":
                    rec_oculto[1] += 1
                    rec_oculto[0] += predito

        prec = vp / (vp + fp) if vp + fp else 0.0
        rec = vp / (vp + fn) if vp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        linhas.append({
            "limiar": limiar, "precisao": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4), "vp": vp, "fp": fp, "fn": fn, "vn": vn,
            "fp_distratores": fp_distrator,
            "recall_oculto_na_base": round(rec_oculto[0] / rec_oculto[1], 4) if rec_oculto[1] else None,
        })

    destino = RAIZ / "results/tables/varredura_limiar.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)

    print("Recuperação isolada, por limiar (o revisor não foi reexecutado):\n")
    print(f"  {'limiar':>7} {'precisão':>9} {'recall':>8} {'F1':>7} {'FP distr.':>10} {'rec. oculto':>12}")
    for r in linhas:
        marca = "  <- em uso" if abs(r["limiar"] - 0.35) < 1e-9 else ""
        print(f"  {r['limiar']:>7.2f} {r['precisao']:>9.3f} {r['recall']:>8.3f} "
              f"{r['f1']:>7.3f} {r['fp_distratores']:>10} {r['recall_oculto_na_base']:>12.3f}{marca}")

    melhor = max(linhas, key=lambda r: r["f1"])
    print(f"\n  melhor F1 da recuperação: {melhor['f1']:.3f} no limiar {melhor['limiar']:.2f}")
    print(f"  -> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
