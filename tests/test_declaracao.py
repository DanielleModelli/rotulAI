"""A leitura da declaração de alérgenos é o gabarito do experimento.

Um erro aqui não quebra nada: ele produz números plausíveis e errados. Por
isso os casos abaixo vêm de rótulos reais do conjunto de avaliação.
"""

import pytest

from rotulai.eval.declaracao import ler_declaracao, separar


def test_contem_e_nao_contem_na_mesma_declaracao():
    d = "ALÉRGICOS: CONTÉM LEITE. CONTÉM LACTOSE. NÃO CONTÉM GLÚTEN."
    assert ler_declaracao(d) == {"laticinios": "contem", "trigo": "nao_contem"}


@pytest.mark.parametrize(
    "declaracao",
    [
        # Cláusulas separadas por VÍRGULA, não por ponto: o "leite" do "pode
        # conter" era engolido pela cláusula do "contém" e virava presença.
        "ALÉRGICOS: CONTÉM DERIVADOS DE CEVADA SOJA, PODE CONTER AMÊNDOA, LEITE, TRIGO",
        "NÃO CONTÉM GLÚTEN. ALÉRGICOS: CONTÉM DERIVADOS DE SOJA E PODE CONTER TRAÇOS DE DERIVADOS DE LEITE.",
        "CONTÉM GLÚTEN. Alérgicos: CONTÉM TRIGO, PODE CONTER DERIVADO DE SOJA E LEITE.",
    ],
)
def test_traco_nunca_vira_presenca(declaracao):
    assert ler_declaracao(declaracao).get("laticinios") == "tracos"


def test_sublinhado_do_open_food_facts_nao_esconde_o_alergeno():
    # O Open Food Facts marca alérgenos com "_". Como "_" é caractere de
    # palavra, \b não casa entre ele e a letra, e o gabarito saía vazio.
    d = "ALÉRGICOS: CONTÉM _LEITE_ E DERIVADOS DE _SOJA_."
    assert ler_declaracao(d) == {"laticinios": "contem", "soja": "contem"}


def test_separar_tira_a_declaracao_do_insumo():
    texto = "Leite integral, açúcar. ALÉRGICOS: CONTÉM LEITE."
    insumo, declaracao = separar(texto)

    assert "ALÉRGICOS" not in insumo
    assert insumo == "Leite integral, açúcar."
    assert declaracao.startswith("ALÉRGICOS")


def test_texto_sem_declaracao_devolve_insumo_inteiro():
    insumo, declaracao = separar("Água, açúcar, sal.")
    assert insumo == "Água, açúcar, sal."
    assert declaracao == ""
