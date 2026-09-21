#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","pyarrow","duckdb"]
# ///
"""
10_parity_check.py — prova que DuckDB e pandas leem o SINASC igual.

A suíte em tests/ roda sobre microdados sintéticos. Este script roda sobre os
SEUS Parquet reais: é a verificação que autoriza confiar no motor DuckDB para
os números do artigo. Rode uma vez após apontar o DATA_ROOT, e de novo sempre
que trocar a versão de um arquivo anual do DATASUS.

    export DATA_ROOT=/caminho/para/sinasc
    python 01_code/10_parity_check.py                 # Centro-Oeste, 2015-2024
    python 01_code/10_parity_check.py --years 2015 2016
    python 01_code/10_parity_check.py --nacional

Saída: tempo de cada motor e o veredito. Código de saída 0 = idêntico,
1 = divergente (com a primeira diferença impressa).
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import pandas.testing as pdt

sys.path.insert(0, str(Path(__file__).parent))
import lib_baseB as L  # noqa: E402


def _cronometra(engine, prefixes, years):
    t0 = time.perf_counter()
    df = L.load_region(prefixes=prefixes, years=years, log=lambda *a: None, engine=engine)
    return df, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", nargs="+", type=int, default=None,
                    help="anos a comparar (padrão: 2015-2024)")
    ap.add_argument("--nacional", action="store_true",
                    help="comparar as 27 UFs em vez do Centro-Oeste")
    args = ap.parse_args()

    prefixes = L.NATIONAL_PREFIXES if args.nacional else L.CO_PREFIXES
    years = args.years or L.YEARS
    regiao = "Nacional (27 UFs)" if args.nacional else "Centro-Oeste (GO MT MS DF)"

    print(f"Paridade de motores — {regiao}, anos {years[0]}-{years[-1]}")
    print(f"DATA_ROOT = {L.RAW}\n")
    faltando = [y for y in years if not (L.RAW / f"sinasc_{y}.parquet").exists()]
    if faltando:
        print(f"ERRO: arquivos ausentes para {faltando}. Defina DATA_ROOT (ver README).")
        return 2

    df_pd, t_pd = _cronometra("pandas", prefixes, years)
    print(f"  pandas: {len(df_pd):,} linhas em {t_pd:6.1f}s")
    df_dk, t_dk = _cronometra("duckdb", prefixes, years)
    print(f"  duckdb: {len(df_dk):,} linhas em {t_dk:6.1f}s")
    if t_dk > 0:
        print(f"  ganho:  {t_pd / t_dk:.1f}x\n")

    try:
        pdt.assert_frame_equal(df_dk, df_pd)
    except AssertionError as exc:
        print("DIVERGENTE — NÃO use o motor duckdb para os números do artigo.")
        print("Rode com PTB_ENGINE=pandas e abra uma issue com a saída abaixo.\n")
        print(str(exc)[:4000])
        return 1

    print("IDÊNTICO — os dois motores produzem o mesmo dataframe "
          "(mesmas células, dtypes e ordem de linhas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
