from __future__ import annotations
import operator
import re

_OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
}


def compare(observed: float, op: str, expected: float) -> bool:
    """Avalia `observed <op> expected` (ex.: compare(35, ">=", 30) -> True)."""
    try:
        return _OPERATORS[op](observed, expected)
    except KeyError:
        raise ValueError(f"operador de regra desconhecido: {op!r}")


def split_ingredients(ingredients_text: str) -> list[str]:
    """Quebra o texto de ingredientes em itens individuais.

    Heurística simples (vírgula/ponto-e-vírgula/parênteses); suficiente para
    o formato usual de rótulos brasileiros. Ajustar quando os dados reais
    chegarem.
    """
    normalized = re.sub(r"[()]", ",", ingredients_text)
    items = [item.strip() for item in re.split(r"[,;]", normalized)]
    return [item for item in items if item]


def find_ingredient_position(ingredients: list[str], keywords: list[str]) -> tuple[str, int] | None:
    """Posição (1-indexado) do primeiro ingrediente que contém uma das
    `keywords` (case-insensitive) — ex.: achar em que posição da lista
    aparece "cacau"/"cocoa". Retorna (keyword encontrada, posição) ou None
    se nenhuma keyword aparecer.
    """
    for index, ingredient in enumerate(ingredients, start=1):
        lowered = ingredient.lower()
        for keyword in keywords:
            if keyword.lower() in lowered:
                return keyword, index
    return None
