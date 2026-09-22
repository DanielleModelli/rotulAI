"""Seleciona os 40 rótulos do conjunto de avaliação e grava gold_v1.jsonl.

Seleção por COTAS, e não gulosa: cada estrato tem um teto, para que nenhum
domine. O estrato "oculto_fora_base" é deliberadamente limitado, porque é o
que mais depende de adjudicação humana (a declaração pode ser defensiva).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from rotulai.eval.estratos import carregar_base, classificar, sem_acento

REGULADAS = ("laticinios", "soja", "trigo")
ALVO_ROTULOS = 40

DISTRATORES = {
    "trigo": ["maltodextrina", "amido de milho", "farinha de arroz", "fecula de mandioca",
              "polvilho", "amido de mandioca", "farinha de milho", "amido modificado"],
    "laticinios": ["leite de coco", "manteiga de cacau", "acido latico", "lactato de calcio",
                   "creme vegetal", "gordura vegetal", "leite de castanha", "bebida vegetal"],
    "soja": ["oleo vegetal", "lecitina", "proteina vegetal", "oleo de girassol", "oleo de palma"],
}

# tetos em DECISÕES (par rótulo x categoria)
COTAS = {
    "explicito": 32,
    "oculto_na_base": 14,
    "oculto_fora_base": 14,
    "distrator": 26,
    "ausente": 999,
}


def analisar(item, base) -> dict:
    insumo, gold_bruto = item["insumo"], item["gold"]
    texto = sem_acento(insumo)
    gold, estratos, adjudicar, dist = {}, {}, [], {}

    for cat in REGULADAS:
        estado = gold_bruto.get(cat, "nao_declarado")
        presente = estado == "contem"
        entrada = {"presente": presente, "declaracao": estado}

        if presente:
            est, achados = classificar(insumo, cat, base)
            entrada["evidencia_base"] = achados[:4]
            if est == "oculto_fora_base":
                adjudicar.append(cat)
        else:
            achados = [d for d in DISTRATORES.get(cat, []) if d in texto]
            if achados:
                est = "distrator"
                dist[cat] = achados[:3]
            else:
                est = "ausente"

        gold[cat] = entrada
        estratos[cat] = est

    return {"produto": item["p"], "insumo": insumo, "declaracao": item["decl"],
            "gold": gold, "estratos": estratos, "adjudicar": adjudicar, "distratores": dist}


def main() -> None:
    random.seed(20260922)
    base = carregar_base()
    pool = [json.loads(json.dumps(x)) for x in json.load(open("pool.json", encoding="utf-8"))]
    cands = [analisar(it, base) for it in pool if len(it["insumo"]) >= 40]
    random.shuffle(cands)

    usados = {k: 0 for k in COTAS}
    escolhidos = []

    def ganho(c):
        """Decisões que este rótulo acrescenta sem estourar cota."""
        g = 0
        for est in c["estratos"].values():
            if usados[est] < COTAS[est]:
                g += {"oculto_fora_base": 5, "oculto_na_base": 5, "distrator": 4,
                      "explicito": 2, "ausente": 1}[est]
        return g

    while len(escolhidos) < ALVO_ROTULOS and cands:
        cands.sort(key=ganho, reverse=True)
        melhor = cands.pop(0)
        if ganho(melhor) == 0:
            melhor = cands.pop(0) if cands else melhor
        escolhidos.append(melhor)
        for est in melhor["estratos"].values():
            usados[est] += 1

    with Path("gold_v1.jsonl").open("w", encoding="utf-8") as f:
        for c in escolhidos:
            p = c["produto"]
            f.write(json.dumps({
                "product_id": f"off-{p.get('code')}",
                "product_name": p.get("product_name"),
                "brand": p.get("brands"),
                "ingredients_text": c["insumo"],
                "declared_allergens_text": c["declaracao"],
                "gold": c["gold"],
                "estratos": c["estratos"],
                "distratores_presentes": c["distratores"],
                "precisa_adjudicacao": c["adjudicar"],
                "source": {"type": "open_food_facts",
                           "url": f"https://br.openfoodfacts.org/produto/{p.get('code')}",
                           "collected_at": "2026-09-22"},
                "annotator": None, "reviewed_by": None, "notes": "",
            }, ensure_ascii=False) + "\n")

    print(f"rótulos selecionados: {len(escolhidos)}")
    print("\ndecisões por estrato (40 rótulos x 3 categorias = 120):")
    for k in ("explicito", "oculto_na_base", "oculto_fora_base", "distrator", "ausente"):
        print(f"  {k:18} {usados[k]:3}")
    pos = usados["explicito"] + usados["oculto_na_base"] + usados["oculto_fora_base"]
    print(f"\n  positivos {pos} | negativos {usados['distrator'] + usados['ausente']}")
    print(f"  rótulos com adjudicação pendente: {sum(1 for c in escolhidos if c['adjudicar'])}")


if __name__ == "__main__":
    main()
