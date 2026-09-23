from scripts.enrich_cocoa_pct import extract_cocoa_pct


def test_extrai_percentual_em_portugues_no_nome():
    assert extract_cocoa_pct("Talento Dark 50% Cacau Café") == 50.0


def test_extrai_percentual_em_ingles_no_texto():
    assert extract_cocoa_pct("Cocoa solids 31% minimum, milk solids 18% minimum.") == 31.0


def test_sem_percentual_declarado_retorna_none():
    assert extract_cocoa_pct("açúcar, leite em pó, manteiga de cacau, massa de cacau") is None
