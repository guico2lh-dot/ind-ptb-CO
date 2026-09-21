# Racial inequalities in preterm birth in Centro-Oeste Brazil, 2015–2024

Analytical code for **RSP-2026-7625**. This repository reproduces the "Base B"
analysis of racial inequalities in preterm birth (PTB, <37 weeks) among White,
*Parda*/Brown, Black/*Preta*, and Indigenous mothers in Brazil's Centro-Oeste
region (GO, MT, MS, DF), 2015–2024, using linked SINASC/DATASUS live-birth records.
Progressive logistic models (M1 crude → M8 fully adjusted), modified-Poisson
prevalence ratios with municipality-clustered SE, marginal-standardized adjusted
probabilities, and heterogeneity / sensitivity analyses.

> **No individual-level data are included in this repository.** Only code is
> distributed here; all microdata are public and obtained from DATASUS (see below).

---

## Radar semanal de editais (Claude Code Routines)

Além do código analítico do artigo, este repositório serve de **base para uma
routine semanal de varredura de editais de pesquisa**, executada via
[Claude Code Routines](https://code.claude.com/docs/en/claude-code-on-the-web).

**Propósito.** A cada semana, o Claude Code varre um conjunto de fontes de
fomento (FAPESP, CNPq, CAPES, Finep, Google.org e outras), compara as chamadas
abertas com o perfil do pesquisador e produz um relatório classificando os
editais por **aderência** (Alta / Média / Baixa), com prazo, valor,
elegibilidade e link. O objetivo é não perder oportunidades de financiamento
alinhadas às linhas de pesquisa (clima e saúde materno-perinatal, disparidades
em saúde, saúde digital) e às vias de elegibilidade (doutorando UNICAMP e
2SLH Tech LTDA).

**Estrutura do radar:**

```
perfil.md            perfil do pesquisador — critérios de matching e elegibilidade
fontes.md            fontes monitoradas (URL + seção relevante) e expansão futura
resultados/          relatórios semanais gerados pela routine
  README.md          padrão de nomenclatura e estrutura dos relatórios
  editais_YYYY-MM-DD.md   um relatório por varredura (data ISO 8601)
```

**Como funciona (visão geral):**

1. A routine lê `perfil.md` (o que procurar / elegibilidade) e `fontes.md`
   (onde procurar).
2. Varre cada fonte, extrai as chamadas abertas e avalia a aderência ao perfil.
3. Grava o resultado em `resultados/editais_YYYY-MM-DD.md`, ordenado por
   aderência.

Para ajustar o alvo da varredura, edite `perfil.md`; para incluir novas fontes,
edite `fontes.md` (seção "Outras fontes").

---

## Análise (RSP-2026-7625)

O restante deste README descreve o pipeline analítico do artigo sobre
desigualdades raciais em prematuridade no Centro-Oeste (2015–2024).

## Data source

- **SINASC** (Sistema de Informações sobre Nascidos Vivos), DATASUS — public
  microdata: https://datasus.saude.gov.br (live births, DNRES, by residence).
- Annual national series **2015–2024**. The **2024** file is the **final DNBR
  release published on 2025-12-23** (not the preliminary version).
- Microdata are **not** redistributed here. Download the annual files yourself
  and point `DATA_ROOT` to the folder containing
  `sinasc_2015.parquet … sinasc_2024.parquet` (or convert the DATASUS `.dbc`
  files to Parquet keeping the raw SINASC column names).

## Reproduce

```bash
# 1. Environment (Python 3.13)
pip install -r requirements.txt            # or: uv sync --extra dev

# 2. Point to the SINASC microdata (outside this repo)
export DATA_ROOT=/path/to/sinasc           # folder with sinasc_YYYY.parquet

# 3. Verify the two read engines agree on YOUR files (see below)
python 01_code/10_parity_check.py

# 4. Run the pipeline (outputs land in ./outputs, regenerated; git-ignored)
python 01_code/01_discovery_profiling.py          # data discovery / profiling
python 01_code/02_build_baseB.py ESCMAE           # Base B (primary, education = ESCMAE)
python 01_code/02_build_baseB.py ESCMAE2010       # sensitivity (education = ESCMAE2010)
python 01_code/05_figures.py ESCMAE               # figures (600 dpi)
python 01_code/07_build_national.py data          # national sibling study (cascade)
python 01_code/07_build_national.py models        # national models (cell-aggregated)
python 01_code/09_handoff.py                      # consolidate numbers for the manuscript
```

Steps 3–4 are also wired as a `Snakefile`, which only re-runs what is stale:

```bash
snakemake -c4                                     # whole pipeline
snakemake -c1 parity                              # engine parity check only
snakemake --dag | dot -Tpng > outputs/pipeline_dag.png
```

- **Reproducibility:** fixed `seed = 42` throughout.
- All file paths are relative to the repository root; only `DATA_ROOT` (the raw
  microdata location) must be set. With `DATA_ROOT` unset the scripts fall back
  to `./data/sinasc`.
- `03_reconcile_baseB.py` compares results against a collaborator reference
  bundle (`ref_clarimar/`) that is **not** included here.

## Read engine and schema validation

Reading the annual Parquet files is the pipeline's bottleneck: the regional
subset discards most of every national file. Two environment variables control
how that is handled.

| Variable | Default | Effect |
|---|---|---|
| `PTB_ENGINE` | `duckdb` | `duckdb` filters the region during the Parquet scan (predicate pushdown). `pandas` reads each full year into memory and filters afterwards — the original path, kept as the parity reference. |
| `PTB_VALIDATE` | `1` | Validates the SINASC code domains after loading, and the exclusion cascade's post-conditions after `add_derived`. Set to `0` to skip. |

Both engines share `lib_baseB._prepare_year()`, which holds **all** the type
casting, so the engine changes only how rows arrive — never what comes out.
That claim is tested two ways:

```bash
python -m pytest tests/ -q          # synthetic microdata, no DATA_ROOT needed
python 01_code/10_parity_check.py   # your real Parquet files
```

`10_parity_check.py` exits 0 only if both engines produce an identical
dataframe (same cells, dtypes and row order) and prints the speedup. **Run it
once after pointing `DATA_ROOT`, and again whenever a DATASUS annual file is
replaced** — a layout change is exactly the kind of thing that makes two
readers diverge. If it ever reports a divergence, fall back to
`PTB_ENGINE=pandas` for the manuscript numbers.

Schema validation never alters data: it either passes silently or raises,
naming the offending column. It exists because a silent DATASUS layout change
does not crash the pipeline — it produces empty categories and biased
estimates that nobody notices.

## Manuscript tooling

Overleaf and Zotero can be wired to Claude Code for the writing stage; setup,
credentials and the AE/BE rules per target journal are in
[`docs/frente-b-literatura-escrita.md`](docs/frente-b-literatura-escrita.md).
Copy `.mcp.json.example` to `.mcp.json` (git-ignored) and export the tokens —
never commit them.

## Education variable

- **Primary:** `ESCMAE` (5 categories) — locked specification.
- **Sensitivity:** `ESCMAE2010` (codes 0–5). Both are reported; conclusions are
  robust to the choice.

## Repository layout

```
01_code/        analysis pipeline (lib_baseB.py + numbered scripts 01–10)
  duck_loader.py    DuckDB Parquet scan (projection + filter only)
  schemas.py        pandera schemas: SINASC code domains + cascade post-conditions
  10_parity_check.py  proves duckdb == pandas on the real microdata
tests/          parity and schema tests over synthetic microdata (seed 42)
docs/           manuscript tooling (Overleaf/Zotero, AE vs BE per journal)
Snakefile       pipeline orchestration (only re-runs what is stale)
pyproject.toml  uv-compatible mirror of requirements.txt
requirements.txt
LICENSE         MIT
outputs/        regenerated by the scripts (git-ignored; not distributed)
```

## Ethics

Study of secondary, anonymized, publicly available SINASC/DATASUS data. Approved
under **Of. CEP nº 036/2026 (UNICAMP)**; ethics framework per **Resolução CNS
nº 510/2016**.

## Citation

> [Authors]. *Racial inequalities in preterm birth in Centro-Oeste Brazil,
> 2015–2024.* Revista de Saúde Pública (RSP-2026-7625). DOI: `TBD`.

## License

MIT — see [LICENSE](LICENSE).
