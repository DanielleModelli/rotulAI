"""Regras de identidade/composição (PIQ) — ex.: Lei do Chocolate, RIISPOA."""

from rotulai.agents.base import IdentityRuleChecker, IngredientPositionChecker
from rotulai.schemas import LabelInput, Rule

CHOCOLATE_35 = Rule(
    id="chocolate-cacau-total",
    category="chocolate",
    applies_to="chocolate",
    field="solidos_totais_cacau_pct",
    operator=">=",
    value=35,
    unit="%",
    on_fail_denomination="achocolatado",
    norma_referencia="Lei 15.404/2026, Art. 2º, VIII",
)


def test_produto_abaixo_do_piso_de_cacau_falha_a_regra():
    checker = IdentityRuleChecker("chocolate", rules=[CHOCOLATE_35])
    label = LabelInput(
        product_id="choquito",
        product_name="Choquito",
        ingredients_text="açúcar, gordura vegetal, cacau em pó, soro de leite",
        declared_category="chocolate",
        declared_composition={"solidos_totais_cacau_pct": 12},
    )

    results = checker.check(label)

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].on_fail_denomination == "achocolatado"


def test_produto_acima_do_piso_de_cacau_passa_na_regra():
    checker = IdentityRuleChecker("chocolate", rules=[CHOCOLATE_35])
    label = LabelInput(
        product_id="chocolate-de-verdade",
        product_name="Chocolate 70%",
        ingredients_text="cacau, manteiga de cacau, açúcar",
        declared_category="chocolate",
        declared_composition={"solidos_totais_cacau_pct": 70},
    )

    results = checker.check(label)

    assert results[0].passed is True


def test_campo_nao_declarado_fica_sem_avaliar_nao_falha():
    checker = IdentityRuleChecker("chocolate", rules=[CHOCOLATE_35])
    label = LabelInput(
        product_id="sem-composicao",
        product_name="Chocolate qualquer",
        ingredients_text="açúcar, cacau, manteiga de cacau",
        declared_category="chocolate",
    )

    results = checker.check(label)

    assert results[0].passed is None
    assert results[0].observed_value is None


def test_sem_declared_category_nao_roda_checagem_de_identidade():
    checker = IdentityRuleChecker("chocolate", rules=[CHOCOLATE_35])
    label = LabelInput(
        product_id="sem-categoria",
        product_name="Produto qualquer",
        ingredients_text="água, sal",
    )

    assert checker.check(label) == []


def test_regra_de_outra_denominacao_nao_se_aplica():
    checker = IdentityRuleChecker("chocolate", rules=[CHOCOLATE_35])
    label = LabelInput(
        product_id="achocolatado-comum",
        product_name="Achocolatado em Pó",
        ingredients_text="açúcar, cacau em pó, maltodextrina",
        declared_category="achocolatado",
        declared_composition={"solidos_totais_cacau_pct": 15},
    )

    assert checker.check(label) == []


def test_posicao_do_cacau_e_indicio_nao_regra_formal():
    checker = IngredientPositionChecker("chocolate")
    label = LabelInput(
        product_id="baton",
        product_name="Baton",
        ingredients_text="açúcar, leite em pó, manteiga de cacau, massa de cacau",
        declared_category="chocolate",
    )

    signal = checker.check(label)

    assert signal.keyword_matched == "cacau"
    assert signal.position == 3
    assert signal.total_ingredients == 4


def test_posicao_sem_categoria_declarada_nao_calcula_sinal():
    checker = IngredientPositionChecker("chocolate")
    label = LabelInput(
        product_id="sem-categoria",
        product_name="Produto qualquer",
        ingredients_text="açúcar, cacau em pó",
    )

    assert checker.check(label) is None


def test_posicao_categoria_sem_keyword_mapeada_nao_calcula_sinal():
    checker = IngredientPositionChecker("laticinios")
    label = LabelInput(
        product_id="queijo",
        product_name="Queijo",
        ingredients_text="leite, sal, fermento lático",
        declared_category="queijo",
    )

    assert checker.check(label) is None
