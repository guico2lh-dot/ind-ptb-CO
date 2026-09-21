#!/usr/bin/env python3
"""
schemas.py — validação de esquema do SINASC com pandera.

Por que isso existe: o layout dos arquivos anuais do DATASUS muda entre
versões (colunas que trocam de tipo, códigos novos, a virada do ESCMAE para o
ESCMAE2010). Uma mudança silenciosa não quebra o pipeline — ela produz
categorias vazias, `NaN` onde havia dado e estimativas viesadas que passam
despercebidas. As duas checagens abaixo transformam isso em erro imediato.

Dois pontos de controle:

1. `validate_region()` — logo após a leitura dos Parquet. Confere que os
   códigos do SINASC estão dentro dos domínios documentados.
2. `validate_baseB()` — após a cascata de exclusão. Confere as
   pós-condições que a cascata promete (IG 22-44, idade 10-60, raça válida,
   sem faltantes nas variáveis do modelo). É uma prova executável da cascata,
   não uma checagem cosmética.

As validações NÃO alteram nenhum dado: ou passam em silêncio, ou levantam
erro. Para desligar (ex.: rodar sobre um recorte propositalmente fora do
padrão), exporte `PTB_VALIDATE=0`.
"""
import os
import warnings

# Domínios dos códigos do SINASC (dicionário de variáveis do DATASUS).
# 9 = ignorado; nulo = ausente. Ambos são tratados na cascata, não aqui.
DOM_RACACORMAE = [1, 2, 3, 4, 5]
DOM_ESCMAE = [1, 2, 3, 4, 5, 9]
DOM_ESCMAE2010 = [0, 1, 2, 3, 4, 5, 9]
DOM_CONSULTAS = [1, 2, 3, 4, 9]
DOM_ESTCIVMAE = [1, 2, 3, 4, 5, 9]
DOM_GRAVIDEZ = [1, 2, 3, 9]

_WARNED = False


def enabled():
    """Validação ligada? Desligue com PTB_VALIDATE=0 (ou false/no)."""
    return os.environ.get("PTB_VALIDATE", "1").strip().lower() not in ("0", "false", "no")


def _pandera():
    """Importa pandera sob demanda; devolve None se ausente (avisando uma vez)."""
    global _WARNED
    try:
        import pandera.pandas as pa  # noqa: WPS433
        return pa
    except ImportError:
        if not _WARNED:
            warnings.warn(
                "pandera não instalado: validação de esquema PULADA. "
                "Instale com `pip install 'pandera[pandas]'` "
                "(ou `uv sync --extra validate`).",
                RuntimeWarning,
                stacklevel=2,
            )
            _WARNED = True
        return None


def _region_schema(pa, ufs):
    C, K = pa.Column, pa.Check
    nullable_code = dict(nullable=True, coerce=False, required=True)
    return pa.DataFrameSchema(
        {
            # Após o filtro regional, o município é sempre presente e com 6 dígitos.
            "CODMUNRES": C(None, K.str_matches(r"^\d{6}$"), nullable=False),
            "UF": C(None, K.isin(sorted(ufs)), nullable=False),
            "ANO": C(None, K.in_range(2015, 2024), nullable=False),
            "RACACORMAE": C(None, K.isin(DOM_RACACORMAE), **nullable_code),
            "ESCMAE": C(None, K.isin(DOM_ESCMAE), **nullable_code),
            "ESCMAE2010": C(None, K.isin(DOM_ESCMAE2010), **nullable_code),
            "CONSULTAS": C(None, K.isin(DOM_CONSULTAS), **nullable_code),
            "ESTCIVMAE": C(None, K.isin(DOM_ESTCIVMAE), **nullable_code),
            "GRAVIDEZ": C(None, K.isin(DOM_GRAVIDEZ), **nullable_code),
            # Faixas largas: aqui só se procura absurdo de layout, não outlier
            # clínico — o recorte analítico é feito pela cascata.
            "SEMAGESTAC": C(None, K.in_range(0, 99), **nullable_code),
            "IDADEMAE": C(None, K.in_range(0, 99), **nullable_code),
            "MESPRENAT": C(None, K.in_range(0, 99), **nullable_code),
            "QTDFILVIVO": C(None, K.in_range(0, 99), **nullable_code),
        },
        strict=False,
        name="SINASC recorte regional (pós-leitura)",
    )


def _baseB_schema(pa, racas, ufs):
    C, K = pa.Column, pa.Check
    return pa.DataFrameSchema(
        {
            # Pós-condições da cascata de exclusão — todas sem faltante.
            "PTB": C(None, K.isin([0, 1]), nullable=False),
            "SEMAGESTAC": C(None, K.in_range(22, 44), nullable=False),
            "IDADEMAE": C(None, K.in_range(10, 60), nullable=False),
            "raca": C(None, K.isin(list(racas)), nullable=False),
            "ANO": C(None, K.in_range(2015, 2024), nullable=False),
            "UF": C(None, K.isin(sorted(ufs)), nullable=False),
            "CODMUNRES": C(None, K.str_matches(r"^\d{6}$"), nullable=False),
            "idade_cat": C(None, nullable=False),
            "esc_cat": C(None, nullable=False),
        },
        strict=False,
        name="Base B (pós-cascata)",
    )


def _run(schema, df, rotulo, log):
    pa = _pandera()
    if pa is None:
        return df
    try:
        schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as exc:
        cases = exc.failure_cases
        resumo = (
            cases.groupby(["column", "check"], dropna=False)
            .size()
            .sort_values(ascending=False)
            .head(15)
        )
        raise ValueError(
            f"Validação de esquema FALHOU em {rotulo} "
            f"({len(cases):,} casos). Provável mudança de layout do DATASUS "
            f"ou recorte inesperado.\n{resumo.to_string()}"
        ) from exc
    log(f"  [schema] {rotulo}: OK ({len(df):,} linhas)")
    return df


def validate_region(df, ufs, log=print):
    """Valida o recorte regional recém-lido. Devolve `df` inalterado."""
    if not enabled():
        log("  [schema] validação desligada (PTB_VALIDATE=0)")
        return df
    pa = _pandera()
    if pa is None:
        return df
    return _run(_region_schema(pa, ufs), df, "recorte regional", log)


def validate_baseB(df, racas, ufs, rotulo="Base B primária", log=print):
    """Valida as pós-condições da cascata. Devolve `df` inalterado."""
    if not enabled():
        return df
    pa = _pandera()
    if pa is None:
        return df
    return _run(_baseB_schema(pa, racas, ufs), df, rotulo, log)
