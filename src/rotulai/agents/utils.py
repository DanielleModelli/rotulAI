from __future__ import annotations
import re


def split_ingredients(ingredients_text: str) -> list[str]:
    """Quebra o texto de ingredientes em itens individuais.

    Heurística simples (vírgula/ponto-e-vírgula/parênteses); suficiente para
    o formato usual de rótulos brasileiros. Ajustar quando os dados reais
    chegarem.
    """
    normalized = re.sub(r"[()]", ",", ingredients_text)
    items = [item.strip() for item in re.split(r"[,;]", normalized)]
    return [item for item in items if item]
