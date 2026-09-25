"""Classifica cada par (rótulo, categoria) em estratos.

Estratos, para um par cujo gabarito externo diz "contem":
  explicito          -> o nome comum do alérgeno aparece na lista de ingredientes
  oculto_na_base     -> só aparece nome técnico, e esse nome ESTÁ na base curada
  oculto_fora_base   -> só aparece nome técnico, e esse nome NÃO está na base

O terceiro é o estrato anticircularidade: mede quanto do desempenho vem da
cobertura da curadoria e quanto vem de generalização semântica.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# Nomes comuns, isto é, o jeito óbvio de o alérgeno aparecer.
NOMES_COMUNS = {
    "laticinios": [r"\bleite\b", r"\bleites\b"],
    "soja": [r"\bsoja\b"],
    "trigo": [r"\btrigo\b", r"\bgl[uú]ten\b", r"\bcenteio\b", r"\bcevada\b", r"\baveia\b"],
}


def sem_acento(s: str) -> str:
    s = s.replace("_", " ").replace("*", " ").lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def carregar_base() -> dict[str, list[str]]:
    base = {}
    for f in (REPO / "data" / "allergen_terms").glob("*.json"):
        dados = json.loads(f.read_text(encoding="utf-8"))
        termos = dados["termos"] if isinstance(dados, dict) else dados
        base[f.stem] = [
            sem_acento(t["termo"] if isinstance(t, dict) else t) for t in termos
        ]
    return base


def classificar(insumo: str, categoria: str, base: dict[str, list[str]]) -> tuple[str, list[str]]:
    """Devolve (estrato, termos_da_base_encontrados)."""
    texto = sem_acento(insumo)

    for padrao in NOMES_COMUNS.get(categoria, []):
        if re.search(sem_acento(padrao).replace("\\b", r"\b"), texto):
            return "explicito", []

    # não tem nome comum: é oculto. A base cobre?
    achados = [
        t for t in base.get(categoria, [])
        if len(t) > 3 and re.search(rf"\b{re.escape(t)}", texto)
    ]
    return ("oculto_na_base" if achados else "oculto_fora_base"), achados
