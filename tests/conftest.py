"""
Fixtures de teste — microdados SINASC sintéticos.

Os microdados reais não são (e não podem ser) versionados. Para exercitar o
carregamento, a cascata e a paridade entre motores sem eles, geramos arquivos
Parquet com a mesma FORMA do SINASC: nomes de coluna originais, códigos do
dicionário DATASUS, DTNASC como DDMMAAAA, e — de propósito — a variação de
tipo que existe na série real (alguns anos com CODMUNRES textual, outros
numérico), que é justamente onde motores diferentes divergem.

Seed 42, igual ao pipeline.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

CODE_DIR = Path(__file__).resolve().parents[1] / "01_code"
sys.path.insert(0, str(CODE_DIR))

SEED = 42
YEARS = [2015, 2016]
# Municípios do Centro-Oeste (prefixos 50-53) e de fora, para testar o recorte.
MUNI_CO = ["500270", "510340", "520870", "530010"]
MUNI_FORA = ["355030", "330455", "292740"]


def _make_year(rng, year, n=400):
    """Um ano sintético de SINASC, com códigos válidos e casos-limite."""
    muni = rng.choice(MUNI_CO + MUNI_FORA, size=n)
    dia = rng.integers(1, 29, size=n)
    mes = rng.integers(1, 13, size=n)
    df = pd.DataFrame(
        {
            "CODMUNRES": muni,
            "RACACORMAE": rng.choice([1, 2, 3, 4, 5, None], size=n,
                                     p=[0.45, 0.08, 0.04, 0.37, 0.03, 0.03]),
            "SEMAGESTAC": rng.choice(
                [20, 22, 25, 30, 34, 36, 38, 40, 42, 44, None], size=n,
                p=[0.02, 0.03, 0.03, 0.05, 0.07, 0.10, 0.30, 0.28, 0.05, 0.03, 0.04]),
            "ESCMAE": rng.choice([1, 2, 3, 4, 5, 9, None], size=n,
                                 p=[0.03, 0.07, 0.15, 0.40, 0.28, 0.04, 0.03]),
            "ESCMAE2010": rng.choice([0, 1, 2, 3, 4, 5, 9, None], size=n,
                                     p=[0.03, 0.07, 0.10, 0.35, 0.15, 0.22, 0.05, 0.03]),
            "IDADEMAE": rng.choice(
                [9, 14, 18, 22, 28, 33, 38, 44, 61, None], size=n,
                p=[0.01, 0.04, 0.10, 0.18, 0.25, 0.20, 0.12, 0.06, 0.01, 0.03]),
            "DTNASC": [f"{d:02d}{m:02d}{year}" for d, m in zip(dia, mes)],
            "CONSULTAS": rng.choice([1, 2, 3, 4, 9, None], size=n,
                                    p=[0.05, 0.12, 0.25, 0.50, 0.05, 0.03]),
            "QTDFILVIVO": rng.choice([0, 1, 2, 3, 5, 99, None], size=n,
                                     p=[0.30, 0.30, 0.18, 0.08, 0.05, 0.04, 0.05]),
            "ESTCIVMAE": rng.choice([1, 2, 3, 4, 5, 9, None], size=n,
                                    p=[0.28, 0.30, 0.05, 0.05, 0.25, 0.04, 0.03]),
            "GRAVIDEZ": rng.choice([1, 2, 3, 9, None], size=n,
                                   p=[0.94, 0.03, 0.01, 0.01, 0.01]),
            "MESPRENAT": rng.choice([1, 2, 3, 4, 6, 9, 99, None], size=n,
                                    p=[0.22, 0.28, 0.20, 0.12, 0.08, 0.04, 0.03, 0.03]),
        }
    )
    # Casos-limite fixos, sempre presentes: DTNASC inválido (dispara o
    # fallback para o ano do arquivo) e CODMUNRES com zero à esquerda perdido.
    df.loc[0, "DTNASC"] = "01010001"
    df.loc[1, "CODMUNRES"] = "50027"
    return df


@pytest.fixture(scope="session")
def sinasc_root(tmp_path_factory):
    """Pasta com sinasc_YYYY.parquet sintéticos. Devolve o caminho (DATA_ROOT).

    2015 grava CODMUNRES como texto; 2016 como numérico — a heterogeneidade
    de tipos documentada no lib_baseB ("2023 é Float/Int, demais String").
    """
    root = tmp_path_factory.mktemp("sinasc")
    rng = np.random.default_rng(SEED)
    for i, year in enumerate(YEARS):
        df = _make_year(rng, year)
        if i % 2 == 1:
            # ano "numérico": CODMUNRES vira inteiro e perde o zero à esquerda
            df["CODMUNRES"] = pd.to_numeric(df["CODMUNRES"], errors="coerce").astype("Int64")
        df.to_parquet(root / f"sinasc_{year}.parquet", index=False)
    return root


@pytest.fixture()
def lib(sinasc_root, monkeypatch):
    """lib_baseB com DATA_ROOT apontando para os dados sintéticos."""
    monkeypatch.setenv("DATA_ROOT", str(sinasc_root))
    monkeypatch.setenv("PTB_VALIDATE", "1")
    for mod in ("lib_baseB", "schemas", "duck_loader"):
        sys.modules.pop(mod, None)
    import lib_baseB

    lib_baseB.RAW = Path(sinasc_root)
    lib_baseB.YEARS = list(YEARS)
    return lib_baseB
