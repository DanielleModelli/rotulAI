"""Protege a reprodutibilidade dos números publicados no relatório.

SE ESTE TESTE FALHAR, NÃO ATUALIZE O FIXTURE. A falha significa que os prompts
enviados ao modelo mudaram, e portanto que os resultados das Tabelas 1 a 9 do
relatório não são mais reproduzíveis pelo código atual.

Por que isso é frágil o bastante para merecer um teste. A condição C3 monta o
prompt serializando o AgentFinding inteiro:

    json.dumps([f.model_dump() for f in findings])

Acrescentar um campo ao schema, ainda que opcional e vazio, muda o texto que o
modelo recebeu. Como a linha que serializa não precisa ser tocada para isso
acontecer, o git não marca conflito e a regressão passa silenciosa. Foi
exatamente esse o risco identificado ao integrar a branch principal, que
acrescenta dois campos ao AgentFinding.

O teste roda sem rede, sem Postgres e sem ChromaDB: os achados brutos estão
gravados em results/runs/*_c3.jsonl com limiar zero, e o filtro do limiar é
reaplicado aqui.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rotulai.eval.condicoes import (
    SYSTEM_PROMPT,
    _acima_do_limiar,
    prompt_c1,
    prompt_c2,
    prompt_c3,
)
from rotulai.schemas import AgentFinding, LabelInput

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "prompts_congelados.json"
GOLD = RAIZ / "data" / "eval" / "gold_v1.jsonl"
RUNS = RAIZ / "results" / "runs"

EXECUCOES = {
    "c1": "20260922-1946_c1.jsonl",
    "c2": "20260922-1949_c2.jsonl",
    "c3": "20260922-1953_c3.jsonl",
}

SOCORRO = (
    "\n\nO prompt publicado mudou. NÃO regenere o fixture para silenciar isto. "
    "Ou reverta a alteração que mexeu no schema/na montagem do prompt, ou "
    "reexecute o experimento e atualize os números do relatório."
)


def sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def congelado() -> dict:
    if not FIXTURE.exists():
        pytest.skip("fixture de prompts congelados ausente")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rotulos() -> dict[str, LabelInput]:
    saida = {}
    for linha in GOLD.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        d = json.loads(linha)
        saida[d["product_id"]] = LabelInput(
            product_id=d["product_id"],
            product_name=d["product_name"] or "(sem nome)",
            ingredients_text=d["ingredients_text"],
        )
    return saida


def test_campos_do_agent_finding_nao_mudaram(congelado):
    """Canário barato: é a mudança de schema que contamina o prompt da C3."""
    atual = sorted(AgentFinding.model_fields)
    assert atual == congelado["campos_agent_finding"], (
        f"AgentFinding mudou de {congelado['campos_agent_finding']} para {atual}. "
        "Campos novos são serializados dentro do prompt da C3." + SOCORRO
    )


def test_system_prompt_nao_mudou(congelado):
    assert sha(SYSTEM_PROMPT) == congelado["system_prompt_sha256"], (
        "O prompt de sistema mudou, e ele é idêntico nas três condições." + SOCORRO
    )


@pytest.mark.parametrize("condicao", sorted(EXECUCOES))
def test_prompts_reproduzem_os_publicados(condicao, congelado, rotulos):
    caminho = RUNS / EXECUCOES[condicao]
    if not caminho.exists():
        pytest.skip(f"execução {caminho.name} ausente")

    esperado = congelado["prompts"][condicao]
    divergentes = []

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        reg = json.loads(linha)
        pid = reg["product_id"]
        label = rotulos[pid]

        if condicao == "c1":
            texto = prompt_c1(label)
        elif condicao == "c2":
            texto = prompt_c2(label)
        else:
            brutos = [AgentFinding.model_validate(a) for a in reg["achados"]]
            filtrados = [_acima_do_limiar(f, reg["limiar_usado"]) for f in brutos]
            texto = prompt_c3(label, filtrados)

        if sha(texto) != esperado.get(pid):
            divergentes.append(pid)

    assert not divergentes, (
        f"{len(divergentes)} de {len(esperado)} prompts da condição {condicao.upper()} "
        f"mudaram. Primeiros: {divergentes[:5]}" + SOCORRO
    )
