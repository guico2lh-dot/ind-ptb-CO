"""
Paridade entre os motores de leitura.

Este é o teste que sustenta a troca do motor padrão para DuckDB: se a leitura
via DuckDB divergir da leitura via pandas em QUALQUER célula, dtype ou ordem
de linha, a suíte falha. Cobre a série sintética inteira e também cada ano
isolado, para que uma divergência de tipo (ano textual vs. ano numérico)
apareça apontando o arquivo culpado.

Equivalente sobre os microdados reais: `python 01_code/10_parity_check.py`.
"""
import pandas as pd
import pandas.testing as pdt
import pytest


def test_load_region_identico_entre_motores(lib):
    """Os dois motores devolvem o mesmo dataframe, célula a célula."""
    via_pandas = lib.load_region(log=lambda *a: None, engine="pandas")
    via_duckdb = lib.load_region(log=lambda *a: None, engine="duckdb")

    assert len(via_duckdb) > 0, "recorte sintético vazio: fixture quebrada"
    pdt.assert_frame_equal(via_duckdb, via_pandas)


@pytest.mark.parametrize("year", [2015, 2016])
def test_paridade_por_ano(lib, year):
    """Isola o ano para flagrar divergência de tipo do CODMUNRES."""
    via_pandas = lib.load_region(years=[year], log=lambda *a: None, engine="pandas")
    via_duckdb = lib.load_region(years=[year], log=lambda *a: None, engine="duckdb")
    pdt.assert_frame_equal(via_duckdb, via_pandas)


def test_duckdb_preserva_ordem_das_linhas(lib):
    """Sem ORDER BY file_row_number a leitura paralela embaralharia as linhas."""
    via_pandas = lib.load_region(log=lambda *a: None, engine="pandas")
    via_duckdb = lib.load_region(log=lambda *a: None, engine="duckdb")
    pdt.assert_series_equal(via_duckdb["DTNASC"], via_pandas["DTNASC"])


def test_engine_invalido_falha_claro(lib):
    with pytest.raises(ValueError, match="PTB_ENGINE inválido"):
        lib.load_region(log=lambda *a: None, engine="polars")


def test_recorte_regional_so_traz_centro_oeste(lib):
    """O filtro é o mesmo nos dois motores: só prefixos 50-53."""
    for engine in ("pandas", "duckdb"):
        df = lib.load_region(log=lambda *a: None, engine=engine)
        prefixos = set(df["CODMUNRES"].str.slice(0, 2))
        assert prefixos <= set(lib.CO_PREFIXES), f"{engine}: vazou {prefixos}"
        assert set(df["UF"]) <= {"MS", "MT", "GO", "DF"}


def test_codmunres_zero_a_esquerda_recuperado(lib):
    """'50027' (5 dígitos) precisa virar '050027'... ou seja, cair FORA do CO.

    O caso-limite existe justamente para travar o comportamento: zfill/lpad
    não inventam o zero perdido no fim, e um município truncado não pode ser
    classificado como Centro-Oeste por acidente.
    """
    for engine in ("pandas", "duckdb"):
        df = lib.load_region(log=lambda *a: None, engine=engine)
        assert (df["CODMUNRES"].str.len() == 6).all()
        assert "050027" not in set(df["CODMUNRES"])


def test_ano_invalido_cai_no_fallback_do_arquivo(lib):
    """DTNASC '01010001' tem ano 0001: vale o ano do arquivo."""
    for engine in ("pandas", "duckdb"):
        df = lib.load_region(log=lambda *a: None, engine=engine)
        assert df["ANO"].between(2015, 2024).all()
        ruins = df[df["DTNASC"].astype("string").str.slice(4, 8) == "0001"]
        if len(ruins):
            pdt.assert_series_equal(
                ruins["ANO"].astype(int),
                ruins["_ano_arquivo"].astype(int),
                check_names=False,
            )
