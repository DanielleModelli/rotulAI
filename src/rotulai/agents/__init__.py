"""Importa os agents concretos para que o decorator @register_agent execute.

Sem estes imports o _REGISTRY fica vazio e o DecisorAgent roda sem nenhum
especialista, silenciosamente.
"""

from rotulai.agents import chocolate, laticinios, soja, trigo  # noqa: F401
