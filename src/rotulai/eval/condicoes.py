"""As três condições experimentais.

Tudo é mantido igual entre elas (modelo, prompt de sistema, schema de saída,
parâmetros, rótulos e ordem). Varia somente a forma de acesso ao conhecimento
sobre alérgenos:

  C1  LLM sem recuperação            controle
  C2  LLM com a base inteira no prompt, sem seleção   ablação
  C3  multiagente com recuperação    sistema completo

C2 é o que permite atribuir um eventual ganho de C3 à recuperação em si, e não
ao simples fato de o modelo ter recebido a informação.
"""

from __future__ import annotations

import json
from pathlib import Path

from rotulai.eval.esquema import CATEGORIAS, VereditoAvaliacao
from rotulai.schemas import LabelInput

DIR_TERMOS = Path(__file__).resolve().parents[3] / "data" / "allergen_terms"

SYSTEM_PROMPT = """\
Você é um revisor especialista em segurança alimentar e rotulagem de alérgenos
no Brasil. A partir da lista de ingredientes de um rótulo, e das evidências
levantadas por agentes especialistas quando elas forem fornecidas, decida para
cada categoria se o alérgeno está presente nos ingredientes.

Considere nomes técnicos e derivados: "caseinato de sódio" indica leite,
"lecitina de soja" indica soja, "extrato de malte" indica cevada. Descarte
termos apenas parecidos: "leite de coco" não é leite, "maltodextrina" não é
malte, "manteiga de cacau" não é manteiga de leite.

Em evidencias, copie literalmente os ingredientes da lista que sustentam as
respostas. Não invente ingredientes que não estejam na lista.
"""


def _carregar_termos(categoria: str) -> list[str]:
    arquivo = DIR_TERMOS / f"{categoria}.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    entradas = dados["termos"] if isinstance(dados, dict) else dados
    return [e["termo"] if isinstance(e, dict) else e for e in entradas]


def _cabecalho(label: LabelInput) -> str:
    return (
        f"Produto: {label.product_name}\n"
        f"Ingredientes: {label.ingredients_text}\n\n"
    )


def prompt_c1(label: LabelInput) -> str:
    return _cabecalho(label) + "Decida, para cada categoria, se o alérgeno está presente."


def prompt_c2(label: LabelInput) -> str:
    blocos = []
    for cat in CATEGORIAS:
        blocos.append(f"{cat}: " + ", ".join(_carregar_termos(cat)))
    return (
        _cabecalho(label)
        + "Termos conhecidos de cada categoria:\n"
        + "\n".join(blocos)
        + "\n\nDecida, para cada categoria, se o alérgeno está presente."
    )


def prompt_c3(label: LabelInput, findings) -> str:
    achados = [f.model_dump() for f in findings]
    return (
        _cabecalho(label)
        + "Evidências recuperadas pelos agentes especialistas:\n"
        + json.dumps(achados, ensure_ascii=False, indent=2)
        + "\n\nDecida, para cada categoria, se o alérgeno está presente."
    )


def _acima_do_limiar(finding, limiar: float):
    """Cópia do achado mantendo só as correspondências acima do limiar."""
    copia = finding.model_copy(deep=True)
    copia.matches = [m for m in finding.matches if m.similarity >= limiar]
    copia.hidden_allergen_detected = bool(copia.matches)
    return copia


class Condicoes:
    """Executa as condições. O cliente do LLM é criado uma vez e reaproveitado."""

    def __init__(self, revisor, limiar: float):
        self._revisor = revisor
        self._limiar = limiar
        self._decisor: DecisorAgent | None = None

    def _chamar(self, user_content: str) -> tuple[VereditoAvaliacao, dict]:
        return self._revisor.gerar(SYSTEM_PROMPT, user_content, VereditoAvaliacao)

    def c1(self, label: LabelInput):
        v, meta = self._chamar(prompt_c1(label))
        return v, [], meta

    def c2(self, label: LabelInput):
        v, meta = self._chamar(prompt_c2(label))
        return v, [], meta

    def c3(self, label: LabelInput):
        if self._decisor is None:
            # Limiar zero na recuperação para GRAVAR todas as similaridades: é
            # o que permite varrer limiares depois sem gastar uma única chamada
            # nova de API. O prompt recebe apenas o que passa do limiar real.
            #
            # Os imports ficam aqui, e não no topo, para que a construção dos
            # prompts seja importável sem ChromaDB. É o que permite ao teste de
            # regressão reconstruir os prompts publicados sem subir infra.
            from rotulai.agents.decisor import DecisorAgent
            from rotulai.agents.registry import get_registered_agents

            self._decisor = DecisorAgent(
                agents={cat: cls(threshold=0.0) for cat, cls in get_registered_agents().items()}
            )

        brutos = self._decisor.route(label)
        filtrados = [_acima_do_limiar(f, self._limiar) for f in brutos]
        v, meta = self._chamar(prompt_c3(label, filtrados))
        return v, brutos, meta


CONDICOES = ("c1", "c2", "c3")
