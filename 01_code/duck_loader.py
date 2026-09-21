#!/usr/bin/env python3
"""
duck_loader.py — leitura dos Parquet do SINASC via DuckDB.

Motivo: os arquivos anuais do SINASC somados passam de 30 milhões de linhas, e
o recorte regional descarta a maior parte delas. Ler o ano inteiro em memória
com pandas para depois filtrar por CODMUNRES é o gargalo do pipeline. O DuckDB
faz o filtro durante a varredura do Parquet (predicate pushdown), devolvendo só
as linhas da região.

Contrato de paridade — este módulo faz APENAS projeção + filtro + ordenação.
Nenhum casting, nenhuma derivação. Todo o tratamento de tipos continua em
lib_baseB._prepare_year(), compartilhado pelos dois motores, para que
`PTB_ENGINE=duckdb` e `PTB_ENGINE=pandas` produzam o mesmo dataframe.

O predicado SQL espelha o pandas linha a linha:

    pandas   CODMUNRES.astype("string").str.strip().str.zfill(6).str[:2]
    duckdb   substr(lpad(trim(CAST(CODMUNRES AS VARCHAR)), 6, '0'), 1, 2)

Divergência conhecida e inofensiva: para um CODMUNRES com mais de 6 caracteres,
`zfill` devolve a string intacta e `lpad` trunca à direita. Os dois primeiros
caracteres — os únicos usados — são idênticos nos dois casos.
"""
from pathlib import Path

import duckdb


def _quote_ident(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


def scan_year(path, columns, prefixes, con=None):
    """Lê um Parquet anual do SINASC devolvendo só as linhas da região.

    Parameters
    ----------
    path : str | Path
        Arquivo `sinasc_YYYY.parquet`.
    columns : sequence of str
        Colunas a projetar (lib_baseB.NEED).
    prefixes : iterable of str
        Prefixos de 2 dígitos do CODMUNRES que definem a região (ex.: "50").
    con : duckdb.DuckDBPyConnection, optional
        Conexão reaproveitável. Se omitida, abre uma conexão em memória.

    Returns
    -------
    pandas.DataFrame
        Mesmas colunas e mesma ordem de linhas que
        `pd.read_parquet(path, columns=columns)` seguido do filtro regional.
    """
    path = Path(path)
    prefixes = list(prefixes)
    if not prefixes:
        raise ValueError("prefixes vazio: nenhuma região a filtrar")

    owns_con = con is None
    con = con or duckdb.connect()
    try:
        col_sql = ", ".join(_quote_ident(c) for c in columns)
        placeholders = ", ".join("?" for _ in prefixes)
        # file_row_number preserva a ordem física do Parquet, que é a ordem que
        # o pandas devolve. Sem o ORDER BY a leitura paralela do DuckDB pode
        # embaralhar as linhas e quebrar a paridade.
        query = f"""
            SELECT {col_sql}
            FROM read_parquet(?, file_row_number = true)
            WHERE substr(lpad(trim(CAST("CODMUNRES" AS VARCHAR)), 6, '0'), 1, 2)
                  IN ({placeholders})
            ORDER BY file_row_number
        """
        result = con.execute(query, [str(path), *prefixes])
        # `.arrow()` devolve um reader no duckdb >= 1.5; `to_arrow_table` é o
        # nome novo e `fetch_arrow_table` o antigo (ainda válido, deprecado).
        to_table = getattr(result, "to_arrow_table", None) or result.fetch_arrow_table
        table = to_table()
        # Mesmo caminho de conversão que pandas.read_parquet(engine="pyarrow"),
        # para que os dtypes cheguem iguais ao _prepare_year.
        return table.to_pandas()
    finally:
        if owns_con:
            con.close()


def connect():
    """Conexão DuckDB em memória para reuso ao longo dos 10 anos da série."""
    return duckdb.connect()
