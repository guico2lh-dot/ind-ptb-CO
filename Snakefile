# Snakefile — orquestração do pipeline RSP-2026-7625.
#
# Substitui a sequência de comandos manuais do README por um grafo com
# dependências explícitas: o Snakemake só reexecuta o que ficou desatualizado,
# e `--dag` exporta a figura do pipeline para o material suplementar.
#
#     export DATA_ROOT=/caminho/para/sinasc
#     snakemake -c4                      # tudo que estiver desatualizado
#     snakemake -c4 baseB                # só a Base B primária
#     snakemake -c1 parity               # paridade duckdb vs pandas
#     snakemake -c1 profiling            # discovery/profiling (exploratório,
#                                        # fora do `all` de propósito)
#     snakemake --dag | dot -Tpng > outputs/pipeline_dag.png
#
# Os scripts continuam executáveis à mão, exatamente como antes — o Snakefile
# é uma camada por cima, não um requisito.

import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data/sinasc"))
YEARS = list(range(2015, 2025))
SINASC = [str(DATA_ROOT / f"sinasc_{y}.parquet") for y in YEARS]

# Carimbo de versão das figuras — precisa casar com o STAMP de 05_figures.py.
STAMP = "20260627"

OUT_CO = "outputs/centro_oeste"
OUT_CO_SENS = "outputs/centro_oeste_escmae2010"
OUT_NAT = "outputs/nacional_indigena"

LIB = ["01_code/lib_baseB.py", "01_code/schemas.py", "01_code/duck_loader.py"]


rule all:
    input:
        f"{OUT_CO}/tables/tabela2_base_B.csv",
        f"{OUT_CO_SENS}/tables/tabela2_base_B.csv",
        f"{OUT_CO}/figures/fig01_OR_vs_RR_v1_{STAMP}.png",
        f"{OUT_NAT}/tables/.national_models_done",
        "outputs/handoff/handoff_numeros_revisao_ESCMAE.md",


rule profiling:
    """01 — discovery / profiling dos arquivos anuais (exploratório)."""
    input:
        SINASC,
    output:
        touch(f"{OUT_CO}/logs/.profiling_done"),
    shell:
        "python 01_code/01_discovery_profiling.py"


rule baseB:
    """02 — Base B primária (escolaridade = ESCMAE, especificação travada)."""
    input:
        SINASC,
        lib=LIB,
    output:
        f"{OUT_CO}/tables/tabela2_base_B.csv",
        f"{OUT_CO}/tables/tabela1_base_B.csv",
        f"{OUT_CO}/tables/n_summary.csv",
    shell:
        "python 01_code/02_build_baseB.py ESCMAE"


rule baseB_escmae2010:
    """02 — sensibilidade com ESCMAE2010."""
    input:
        SINASC,
        lib=LIB,
    output:
        f"{OUT_CO_SENS}/tables/tabela2_base_B.csv",
    shell:
        "python 01_code/02_build_baseB.py ESCMAE2010"


rule figures:
    """05 — figuras do artigo (600 dpi)."""
    input:
        f"{OUT_CO}/tables/tabela2_base_B.csv",
    output:
        f"{OUT_CO}/figures/fig01_OR_vs_RR_v1_{STAMP}.png",
        f"{OUT_CO}/figures/fig02_temporal_indigena_v1_{STAMP}.png",
    shell:
        "python 01_code/05_figures.py ESCMAE"


rule national_data:
    """07 — estudo nacional irmão: cascata."""
    input:
        SINASC,
        lib=LIB,
    output:
        touch(f"{OUT_NAT}/.national_data_done"),
    shell:
        "python 01_code/07_build_national.py data"


rule national_models:
    """07 — estudo nacional irmão: modelos (agregados por célula)."""
    input:
        f"{OUT_NAT}/.national_data_done",
    output:
        touch(f"{OUT_NAT}/tables/.national_models_done"),
    shell:
        "python 01_code/07_build_national.py models"


rule handoff:
    """09 — consolida os números que vão para o manuscrito."""
    input:
        f"{OUT_CO}/tables/tabela2_base_B.csv",
        f"{OUT_CO_SENS}/tables/tabela2_base_B.csv",
        f"{OUT_NAT}/tables/.national_models_done",
    output:
        "outputs/handoff/handoff_numeros_revisao_ESCMAE.md",
    shell:
        "python 01_code/09_handoff.py"


rule parity:
    """Verifica que duckdb e pandas leem os microdados de forma idêntica."""
    input:
        SINASC,
    shell:
        "python 01_code/10_parity_check.py"


rule test:
    """Suíte sobre microdados sintéticos — não precisa de DATA_ROOT."""
    shell:
        "python -m pytest tests/ -q"
