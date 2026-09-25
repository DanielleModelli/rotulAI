#!/usr/bin/env python3
"""Congela o sha256 dos prompts das três condições publicadas no relatório.

Motivo. A condição C3 monta o prompt serializando o AgentFinding literalmente
(`json.dumps([f.model_dump() for f in findings])`). Qualquer campo acrescentado
ao schema entra no prompt e muda o que o modelo recebeu, sem que o git marque
conflito, porque a linha que serializa não é tocada. Os números do relatório
deixariam de ser reproduzíveis em silêncio.

Este script grava a impressão digital dos prompts efetivamente usados. O teste
tests/test_prompt_congelado.py compara contra ela a cada alteração.

Nenhuma chamada de API é feita: os achados brutos estão gravados em
results/runs/*_c3.jsonl com limiar zero, e o filtro do limiar é reaplicado aqui.

Uso:  PYTHONPATH=src python3 scripts/eval/congelar_prompts.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rotulai.eval.condicoes import (
    SYSTEM_PROMPT,
    _acima_do_limiar,
    prompt_c1,
    prompt_c2,
    prompt_c3,
)
from rotulai.schemas import AgentFinding, LabelInput

RAIZ = Path(__file__).resolve().parents[2]
GOLD = RAIZ / "data" / "eval" / "gold_v1.jsonl"
RUNS = RAIZ / "results" / "runs"
SAIDA = RAIZ / "tests" / "fixtures" / "prompts_congelados.json"

# a execução publicada no relatório, uma por condição
EXECUCOES = {
    "c1": "20260922-1946_c1.jsonl",
    "c2": "20260922-1949_c2.jsonl",
    "c3": "20260922-1953_c3.jsonl",
}


def sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def carregar_rotulos() -> dict[str, LabelInput]:
    rotulos = {}
    for linha in GOLD.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        d = json.loads(linha)
        rotulos[d["product_id"]] = LabelInput(
            product_id=d["product_id"],
            # mesmo tratamento do run_eval.py: rótulo sem nome vira "(sem nome)"
            product_name=d["product_name"] or "(sem nome)",
            ingredients_text=d["ingredients_text"],
        )
    return rotulos


def main() -> None:
    rotulos = carregar_rotulos()
    congelado: dict[str, object] = {
        "_aviso": (
            "Se o teste que consome este arquivo falhar, NÃO ajuste o arquivo. "
            "Os prompts mudaram, e com eles os números publicados no relatório."
        ),
        "system_prompt_sha256": sha(SYSTEM_PROMPT),
        "campos_agent_finding": sorted(AgentFinding.model_fields),
        "prompts": {},
    }

    total = 0
    for condicao, arquivo in EXECUCOES.items():
        caminho = RUNS / arquivo
        if not caminho.exists():
            raise SystemExit(f"execução não encontrada: {caminho}")

        por_rotulo: dict[str, str] = {}
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            reg = json.loads(linha)
            pid = reg["product_id"]
            label = rotulos.get(pid)
            if label is None:
                raise SystemExit(f"rótulo {pid} não está no gold")

            if condicao == "c1":
                texto = prompt_c1(label)
            elif condicao == "c2":
                texto = prompt_c2(label)
            else:
                brutos = [AgentFinding.model_validate(a) for a in reg["achados"]]
                limiar = reg["limiar_usado"]
                texto = prompt_c3(label, [_acima_do_limiar(f, limiar) for f in brutos])

            por_rotulo[pid] = sha(texto)
            total += 1

        congelado["prompts"][condicao] = por_rotulo
        print(f"{condicao}: {len(por_rotulo)} prompts congelados (de {arquivo})")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(congelado, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"\ntotal: {total} prompts")
    print(f"gravado em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
