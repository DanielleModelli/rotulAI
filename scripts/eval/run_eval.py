"""Roda as condições experimentais sobre o conjunto de avaliação.

Este é o passo CARO. Ele só produz predições brutas; nenhuma métrica é
calculada aqui. Assim, ajustar uma fórmula não custa uma única chamada nova de
API. O cálculo fica em metrics.py, que lê os arquivos gravados por este script.

Uso:
    python scripts/eval/run_eval.py --condicao c3
    python scripts/eval/run_eval.py --condicao c1 --limite 5   # piloto
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rotulai.agents.revisor import ReviewerAgent
from rotulai.config import settings
from rotulai.eval.condicoes import CONDICOES, SYSTEM_PROMPT, Condicoes
from rotulai.schemas import LabelInput

RAIZ = Path(__file__).resolve().parents[2]
GOLD = RAIZ / "data" / "eval" / "gold_v1.jsonl"
SAIDA = RAIZ / "results" / "runs"
CACHE = RAIZ / "results" / "cache"


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "desconhecido"


def chave_cache(product_id: str, condicao: str, modelo: str, limiar: float, tag: str = "") -> str:
    crua = f"{product_id}|{condicao}|{modelo}|{limiar}|{tag}|{hashlib.sha1(SYSTEM_PROMPT.encode()).hexdigest()[:8]}"
    return hashlib.sha1(crua.encode()).hexdigest()


class Limitador:
    """Espaça as chamadas. A camada gratuita do Gemini limita por minuto."""

    def __init__(self, por_minuto: int):
        self._intervalo = 60.0 / por_minuto if por_minuto > 0 else 0.0
        self._ultima = 0.0

    def espera(self) -> None:
        if not self._intervalo:
            return
        falta = self._intervalo - (time.monotonic() - self._ultima)
        if falta > 0:
            time.sleep(falta)
        self._ultima = time.monotonic()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condicao", required=True, choices=CONDICOES)
    ap.add_argument("--gold", type=Path, default=GOLD)
    ap.add_argument("--limite", type=int, default=0, help="0 = todos")
    ap.add_argument("--rpm", type=int, default=10, help="chamadas por minuto")
    ap.add_argument("--tentativas", type=int, default=4)
    ap.add_argument("--tag", default="", help="rotula a execução; entra na chave de cache e no nome do arquivo")
    args = ap.parse_args()

    SAIDA.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    rotulos = [json.loads(l) for l in args.gold.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limite:
        rotulos = rotulos[: args.limite]

    revisor = ReviewerAgent()
    condicoes = Condicoes(revisor, limiar=settings.similarity_threshold)
    executar = getattr(condicoes, args.condicao)
    limitador = Limitador(args.rpm)
    sha = git_sha()

    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    nome = args.condicao + (args.tag or "")
    destino = SAIDA / f"{carimbo}_{nome}.jsonl"

    ok = erros = cacheados = 0
    with destino.open("w", encoding="utf-8") as saida:
        for i, r in enumerate(rotulos, 1):
            pid = r["product_id"]
            ck = chave_cache(pid, args.condicao, revisor.model, settings.similarity_threshold, args.tag)
            arquivo_cache = CACHE / f"{ck}.json"

            if arquivo_cache.exists():
                registro = json.loads(arquivo_cache.read_text(encoding="utf-8"))
                cacheados += 1
            else:
                label = LabelInput(
                    product_id=pid,
                    product_name=r["product_name"] or "(sem nome)",
                    ingredients_text=r["ingredients_text"],
                )
                for tentativa in range(1, args.tentativas + 1):
                    try:
                        limitador.espera()
                        veredito, findings, meta = executar(label)
                        break
                    except Exception as e:  # rede, cota, schema
                        if tentativa == args.tentativas:
                            print(f"  [{i}/{len(rotulos)}] {pid} FALHOU: {e}", file=sys.stderr)
                            erros += 1
                            veredito = findings = meta = None
                            break
                        espera = 5 * tentativa
                        print(f"  [{i}/{len(rotulos)}] {pid} tentativa {tentativa} falhou ({type(e).__name__}); "
                              f"aguardando {espera}s", file=sys.stderr)
                        time.sleep(espera)

                if veredito is None:
                    continue

                registro = {
                    "product_id": pid,
                    "condicao": nome,
                    "predito": veredito.por_categoria(),
                    "evidencias": veredito.evidencias,
                    "justificativa": veredito.justificativa,
                    "confianca": veredito.confianca,
                    "achados": [f.model_dump() for f in findings],
                    "limiar_usado": settings.similarity_threshold,
                    "modelo_embedding": settings.embedding_model,
                    "git_sha": sha,
                    "executado_em": datetime.now(timezone.utc).isoformat(),
                    **meta,
                }
                arquivo_cache.write_text(
                    json.dumps(registro, ensure_ascii=False), encoding="utf-8"
                )

            saida.write(json.dumps(registro, ensure_ascii=False) + "\n")
            ok += 1
            if i % 10 == 0 or i == len(rotulos):
                print(f"  [{i}/{len(rotulos)}] ok={ok} cache={cacheados} erros={erros}")

    print(f"\ncondição {args.condicao}: {ok} gravados ({cacheados} de cache), {erros} erros")
    print(f"-> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
