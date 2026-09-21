"""
Validação de esquema: a cascata cumpre o que promete, e o pipeline reclama
quando o layout do DATASUS muda.

O ponto destes testes não é a biblioteca pandera — é garantir que uma
alteração silenciosa nos microdados (código novo em RACACORMAE, faltante que
escapa da cascata) vire ERRO, e não uma categoria vazia no modelo.
"""
import pandas as pd
import pytest


def test_cascata_produz_base_valida(lib):
    """O caminho feliz passa nas duas validações sem tocar nos dados."""
    raw = lib.load_region(log=lambda *a: None)
    prim, sens, steps, full = lib.build_cascade(raw, log=lambda *a: None)
    d = lib.add_derived(prim, log=lambda *a: None)

    assert len(d) > 0, "cascata sintética zerou: fixture quebrada"
    assert d["SEMAGESTAC"].between(22, 44).all()
    assert d["IDADEMAE"].between(10, 60).all()
    assert d["PTB"].isin([0, 1]).all()
    assert d["raca"].isin(lib.RACA_ORDER).all()
    assert d["esc_cat"].notna().all()
    assert d["idade_cat"].notna().all()


def test_cascata_e_monotonica(lib):
    """Cada passo da cascata só pode tirar linhas, nunca acrescentar."""
    raw = lib.load_region(log=lambda *a: None)
    _, _, steps, _ = lib.build_cascade(raw, log=lambda *a: None)
    ns = [n for _, n in steps]
    assert ns == sorted(ns, reverse=True), f"cascata não-monotônica: {steps}"


def test_codigo_de_raca_desconhecido_falha(lib):
    """Um código fora do dicionário DATASUS precisa estourar na leitura."""
    raw = lib.load_region(log=lambda *a: None)
    raw.loc[raw.index[0], "RACACORMAE"] = 7  # não existe no SINASC
    with pytest.raises(ValueError, match="Validação de esquema FALHOU"):
        lib.schemas.validate_region(raw, set(lib.CO_PREFIXES.values()), log=lambda *a: None)


def test_uf_fora_da_regiao_falha(lib):
    raw = lib.load_region(log=lambda *a: None)
    raw.loc[raw.index[0], "UF"] = "SP"
    with pytest.raises(ValueError, match="Validação de esquema FALHOU"):
        lib.schemas.validate_region(raw, set(lib.CO_PREFIXES.values()), log=lambda *a: None)


def test_faltante_que_escapa_da_cascata_falha(lib):
    """Se um NaN chegar à Base B, a validação precisa apontar a coluna."""
    raw = lib.load_region(log=lambda *a: None)
    prim, _, _, _ = lib.build_cascade(raw, log=lambda *a: None)
    d = lib.add_derived(prim, log=lambda *a: None)
    d.loc[d.index[0], "SEMAGESTAC"] = None
    with pytest.raises(ValueError, match="Validação de esquema FALHOU"):
        lib.schemas.validate_baseB(
            d, lib.RACA_ORDER, set(lib.CO_PREFIXES.values()), log=lambda *a: None
        )


def test_validacao_desligavel_por_env(lib, monkeypatch):
    """PTB_VALIDATE=0 é a saída de emergência para recortes ad hoc."""
    monkeypatch.setenv("PTB_VALIDATE", "0")
    raw = lib.load_region(log=lambda *a: None)
    raw.loc[raw.index[0], "RACACORMAE"] = 7
    # não levanta
    lib.schemas.validate_region(raw, set(lib.CO_PREFIXES.values()), log=lambda *a: None)


def test_validacao_nao_altera_os_dados(lib):
    raw = lib.load_region(log=lambda *a: None)
    antes = raw.copy()
    depois = lib.schemas.validate_region(
        raw, set(lib.CO_PREFIXES.values()), log=lambda *a: None
    )
    pd.testing.assert_frame_equal(depois, antes)
