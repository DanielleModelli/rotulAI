"""Separa o texto de ingredientes da declaração obrigatória de alérgenos.

A declaração do fabricante é o critério EXTERNO do gabarito. O texto que entra
no sistema é apenas a parte de ingredientes, sem a declaração, para não vazar
a resposta.

Regras de leitura, nesta ordem de precedência por cláusula:
  "NÃO CONTÉM X"  -> negativo explícito
  "PODE CONTER X" -> traços (contaminação cruzada), NÃO conta como presente
  "CONTÉM X"      -> presente
"""

from __future__ import annotations

import re
import unicodedata

# Onde a declaração começa. Qualquer uma destas marca o fim do insumo.
INICIO_DECL = re.compile(
    r"(al[ée]rgicos?\s*[:\-]|(?<![a-zà-ÿ])(?:n[ãa]o\s+)?cont[ée]m\s|pode\s+conter\s)",
    re.I,
)

VERBOS = r"n[ãa]o\s+cont[ée]m|pode\s+conter|cont[ée]m"

# O alvo da cláusula vai até o próximo verbo, ponto ou ponto e vírgula. Parar
# só no ponto estava errado: muitos rótulos separam cláusulas por vírgula
# ("CONTÉM DERIVADOS DE SOJA E PODE CONTER TRAÇOS DE LEITE"), e o leite acabava
# engolido pela cláusula do "contém", virando presença onde havia só traço.
CLAUSULA = re.compile(
    rf"({VERBOS})\s*:?\s*((?:(?!{VERBOS})[^.;])*)",
    re.I,
)

# nome comum declarado -> categoria do sistema
MAPA = {
    "leite": "laticinios",
    "lactose": "laticinios",
    "soja": "soja",
    "trigo": "trigo",
    "centeio": "trigo",
    "cevada": "trigo",
    "aveia": "trigo",
    "gluten": "trigo",
    "malte": "trigo",
}

CATEGORIAS_REGULADAS = ("laticinios", "soja", "trigo")


def sem_acento(s: str) -> str:
    # O Open Food Facts marca alérgenos com sublinhado (_LEITE_). Como "_" é
    # caractere de palavra, \b não casa entre ele e a letra: trocar por espaço.
    s = s.replace("_", " ").replace("*", " ")
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def separar(texto: str) -> tuple[str, str]:
    """Devolve (insumo, declaracao). Insumo é o que entra no sistema."""
    m = INICIO_DECL.search(texto)
    if not m:
        return texto.strip(), ""
    return texto[: m.start()].strip(), texto[m.start():].strip()


def ler_declaracao(declaracao: str) -> dict[str, str]:
    """Categoria -> "contem" | "tracos" | "nao_contem". Ausente = não declarado."""
    resultado: dict[str, str] = {}
    for verbo, alvo in CLAUSULA.findall(declaracao):
        v = sem_acento(verbo)
        if v.startswith("nao"):
            rotulo = "nao_contem"
        elif v.startswith("pode"):
            rotulo = "tracos"
        else:
            rotulo = "contem"

        alvo_norm = sem_acento(alvo)
        for nome, categoria in MAPA.items():
            if re.search(rf"\b{nome}", alvo_norm):
                # "contem" tem precedência sobre traços; negativo explícito vence empate
                atual = resultado.get(categoria)
                if atual == "contem" and rotulo != "nao_contem":
                    continue
                if atual == "nao_contem" and rotulo == "tracos":
                    continue
                resultado[categoria] = rotulo
    return resultado
