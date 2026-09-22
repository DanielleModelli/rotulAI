"""Calcula as métricas a partir das predições já gravadas.

Passo BARATO: não faz nenhuma chamada de API. Pode rodar quantas vezes for
preciso enquanto a análise é ajustada.

Uso:
    python scripts/eval/metrics.py
    python scripts/eval/metrics.py --sem-evidencia excluir
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import random
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GOLD = RAIZ / "data" / "eval" / "gold_v1.jsonl"
RUNS = RAIZ / "results" / "runs"
TABELAS = RAIZ / "results" / "tables"

REGULADAS = ("laticinios", "soja", "trigo")
ESTRATOS_POS = ("explicito", "oculto_na_base", "oculto_fora_base")


# ---------------------------------------------------------------- utilidades

def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("_", " ").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def carregar_gold() -> dict[str, dict]:
    return {
        json.loads(l)["product_id"]: json.loads(l)
        for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()
    }


def carregar_runs() -> dict[str, dict[str, dict]]:
    """condição -> product_id -> registro (fica a execução mais recente)."""
    runs: dict[str, dict[str, dict]] = defaultdict(dict)
    for arq in sorted(glob.glob(str(RUNS / "*.jsonl"))):
        cond = Path(arq).stem.split("_")[-1]
        for l in Path(arq).read_text(encoding="utf-8").splitlines():
            if l.strip():
                d = json.loads(l)
                runs[cond][d["product_id"]] = d
    return runs


# ------------------------------------------------------------------ métricas

def conta(pares) -> dict[str, int]:
    vp = sum(1 for e, p in pares if e and p)
    fp = sum(1 for e, p in pares if not e and p)
    fn = sum(1 for e, p in pares if e and not p)
    vn = sum(1 for e, p in pares if not e and not p)
    return {"vp": vp, "fp": fp, "fn": fn, "vn": vn}


def derivadas(c: dict[str, int]) -> dict[str, float]:
    vp, fp, fn, vn = c["vp"], c["fp"], c["fn"], c["vn"]
    prec = vp / (vp + fp) if vp + fp else 0.0
    rec = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (vp + vn) / max(1, vp + fp + fn + vn)
    return {"precisao": prec, "recall": rec, "f1": f1, "acuracia": acc}


def bootstrap_f1(por_rotulo: dict[str, list], reamostras: int = 2000) -> tuple[float, float]:
    """IC 95% reamostrando RÓTULOS, não decisões.

    As decisões das categorias de um mesmo rótulo não são independentes, então
    reamostrar decisão a decisão subestimaria a incerteza.
    """
    ids = list(por_rotulo)
    if not ids:
        return (0.0, 0.0)
    rng = random.Random(20260922)
    amostras = []
    for _ in range(reamostras):
        pares = []
        for _ in ids:
            pares.extend(por_rotulo[rng.choice(ids)])
        amostras.append(derivadas(conta(pares))["f1"])
    amostras.sort()
    return (amostras[int(0.025 * reamostras)], amostras[int(0.975 * reamostras) - 1])


def mcnemar(a: dict[str, bool], b: dict[str, bool]) -> tuple[int, int, float]:
    """Teste pareado. Devolve (b01, b10, p) pelo binomial exato bicaudal."""
    from math import comb

    b01 = sum(1 for k in a if a[k] and not b[k])
    b10 = sum(1 for k in a if not a[k] and b[k])
    n = b01 + b10
    if n == 0:
        return b01, b10, 1.0
    menor = min(b01, b10)
    p = sum(comb(n, i) for i in range(menor + 1)) / (2 ** n) * 2
    return b01, b10, min(1.0, p)


# ------------------------------------------------------------------ análises

def coletar(gold, runs, cond, excluir_sem_evidencia: bool):
    """Devolve (pares_globais, por_rotulo, por_estrato, acertos_por_decisao)."""
    pares, por_rotulo = [], defaultdict(list)
    por_estrato = defaultdict(list)
    acertos = {}

    for pid, g in gold.items():
        reg = runs.get(cond, {}).get(pid)
        if reg is None:
            continue
        sem_ev = set(g.get("sem_evidencia_no_texto") or [])
        for cat in REGULADAS:
            if excluir_sem_evidencia and cat in sem_ev:
                continue
            esperado = bool(g["gold"][cat]["presente"])
            predito = bool(reg["predito"][cat])
            pares.append((esperado, predito))
            por_rotulo[pid].append((esperado, predito))
            por_estrato[g["estratos"][cat]].append((esperado, predito))
            acertos[f"{pid}|{cat}"] = esperado == predito

    return pares, por_rotulo, por_estrato, acertos


def divergencias_conservadoras(gold, runs, cond) -> list[tuple[str, str, str]]:
    """Sistema aponta o que o fabricante não declarou: candidata a não conformidade."""
    fora = []
    for pid, g in gold.items():
        reg = runs.get(cond, {}).get(pid)
        if reg is None:
            continue
        for cat in REGULADAS:
            if not g["gold"][cat]["presente"] and reg["predito"][cat]:
                fora.append((g["product_name"] or pid, cat, g["gold"][cat]["declaracao"]))
    return fora


def tana(gold, runs, cond) -> tuple[int, int]:
    """Taxa de afirmação não ancorada: evidências citadas ausentes do rótulo."""
    citadas = ausentes = 0
    for pid, g in gold.items():
        reg = runs.get(cond, {}).get(pid)
        if reg is None:
            continue
        texto = normalizar(g["ingredients_text"])
        for ev in reg.get("evidencias", []):
            ev_n = normalizar(ev).strip()
            if len(ev_n) < 3:
                continue
            citadas += 1
            if ev_n not in texto:
                ausentes += 1
    return ausentes, citadas


# --------------------------------------------------------------------- saída

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-evidencia", choices=("incluir", "excluir"), default="incluir")
    args = ap.parse_args()
    excluir = args.sem_evidencia == "excluir"

    gold, runs = carregar_gold(), carregar_runs()
    conds = [c for c in ("c1", "c2", "c3") if c in runs]
    if not conds:
        raise SystemExit("nenhuma execução encontrada em results/runs/")

    TABELAS.mkdir(parents=True, exist_ok=True)
    rotulo_modo = "sem os casos sem evidência no texto" if excluir else "com todos os casos"
    print(f"=== Desempenho por condição ({rotulo_modo}) ===\n")

    acertos_por_cond, linhas_csv = {}, []
    for cond in conds:
        pares, por_rotulo, por_estrato, acertos = coletar(gold, runs, cond, excluir)
        acertos_por_cond[cond] = acertos
        c, d = conta(pares), derivadas(conta(pares))
        lo, hi = bootstrap_f1(por_rotulo)
        print(f"  {cond.upper()}  n={len(pares):3}  "
              f"precisao={d['precisao']:.3f}  recall={d['recall']:.3f}  "
              f"F1={d['f1']:.3f} [{lo:.3f}, {hi:.3f}]  acuracia={d['acuracia']:.3f}")
        print(f"        vp={c['vp']} fp={c['fp']} fn={c['fn']} vn={c['vn']}")
        linhas_csv.append({"condicao": cond, "n": len(pares), **c,
                           **{k: round(v, 4) for k, v in d.items()},
                           "f1_ic95_inf": round(lo, 4), "f1_ic95_sup": round(hi, 4)})

    print("\n=== Recall por estrato (é o que responde à pergunta de pesquisa) ===\n")
    print(f"  {'estrato':20} " + "  ".join(f"{c.upper():>12}" for c in conds))
    estrato_csv = []
    for est in ESTRATOS_POS:
        celulas, linha = [], {"estrato": est}
        for cond in conds:
            _, _, por_estrato, _ = coletar(gold, runs, cond, excluir)
            pares = por_estrato.get(est, [])
            r = derivadas(conta(pares))["recall"] if pares else float("nan")
            celulas.append(f"{r:.3f} (n={len(pares)})" if pares else "        -")
            linha[cond] = round(r, 4) if pares else None
        print(f"  {est:20} " + "  ".join(f"{c:>12}" for c in celulas))
        estrato_csv.append(linha)

    print("\n=== Falso positivo nos distratores ===\n")
    for cond in conds:
        _, _, por_estrato, _ = coletar(gold, runs, cond, excluir)
        pares = por_estrato.get("distrator", [])
        fp = sum(1 for e, p in pares if not e and p)
        print(f"  {cond.upper()}  {fp}/{len(pares)} distratores acionados")

    print("\n=== Alucinação: taxa de afirmação não ancorada (proxy) ===\n")
    for cond in conds:
        aus, tot = tana(gold, runs, cond)
        taxa = aus / tot if tot else 0.0
        print(f"  {cond.upper()}  {aus}/{tot} evidências citadas não constam do rótulo  ({taxa:.1%})")

    print("\n=== McNemar entre condições (pareado) ===\n")
    for i, a in enumerate(conds):
        for b in conds[i + 1:]:
            comuns = set(acertos_por_cond[a]) & set(acertos_por_cond[b])
            ca = {k: acertos_por_cond[a][k] for k in comuns}
            cb = {k: acertos_por_cond[b][k] for k in comuns}
            b01, b10, p = mcnemar(ca, cb)
            print(f"  {a.upper()} x {b.upper()}: {a.upper()} acerta só {b01}, "
                  f"{b.upper()} acerta só {b10}, p={p:.4f}")

    print("\n=== Divergências conservadoras (sistema aponta, fabricante não declarou) ===\n")
    for cond in conds:
        div = divergencias_conservadoras(gold, runs, cond)
        print(f"  {cond.upper()}: {len(div)} casos")
        for nome, cat, decl in div[:4]:
            print(f"      {nome[:52]:52} {cat:11} (declaração: {decl})")

    sufixo = "sem_evidencia_excluida" if excluir else "completo"
    with (TABELAS / f"desempenho_{sufixo}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas_csv[0]))
        w.writeheader(); w.writerows(linhas_csv)
    with (TABELAS / f"recall_por_estrato_{sufixo}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(estrato_csv[0]))
        w.writeheader(); w.writerows(estrato_csv)
    print(f"\ntabelas gravadas em results/tables/ (sufixo: {sufixo})")


if __name__ == "__main__":
    main()
