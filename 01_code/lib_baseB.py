#!/usr/bin/env python3
"""
lib_baseB.py — carregamento, casting, recorte regional e cascata de exclusão
para o estudo de desigualdades raciais em prematuridade (SINASC).

Região é parametrizável (Centro-Oeste agora; nacional/indígena depois).
Raw é SOMENTE LEITURA. Seed 42.

Motor de leitura
----------------
`PTB_ENGINE=duckdb` (padrão) filtra a região durante a varredura do Parquet.
`PTB_ENGINE=pandas` lê o ano inteiro em memória e filtra depois — o caminho
original, mantido como referência de paridade.

Os dois motores compartilham `_prepare_year()`, que concentra todo o casting;
a escolha do motor muda apenas COMO as linhas chegam, nunca o que sai.
Para provar isso sobre os microdados reais: `python 01_code/10_parity_check.py`.
"""
import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

try:
    import schemas
except ImportError:  # importado de fora de 01_code/
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import schemas

SEED = 42
# Motor de leitura dos Parquet: "duckdb" (padrão) ou "pandas".
ENGINE = os.environ.get("PTB_ENGINE", "duckdb").strip().lower()
# Raiz dos microdados SINASC (somente leitura), fora do repositório.
# Defina a variável de ambiente DATA_ROOT apontando para a pasta com
# sinasc_2015.parquet … sinasc_2024.parquet (ver README). Fallback: ./data/sinasc
RAW = Path(os.environ.get("DATA_ROOT", "data/sinasc"))
YEARS = list(range(2015, 2025))

# Região Centro-Oeste: CODMUNRES começa em 50 MS, 51 MT, 52 GO, 53 DF
CO_PREFIXES = {"50": "MS", "51": "MT", "52": "GO", "53": "DF"}

# Nacional: 27 UFs (prefixo de 2 dígitos do CODMUNRES -> sigla)
NATIONAL_PREFIXES = {
    "11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
    "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL","28":"SE","29":"BA",
    "31":"MG","32":"ES","33":"RJ","35":"SP",
    "41":"PR","42":"SC","43":"RS",
    "50":"MS","51":"MT","52":"GO","53":"DF",
}
REGIAO5 = {  # UF -> grande região (para relatórios)
    **{u:"Norte" for u in ["RO","AC","AM","RR","PA","AP","TO"]},
    **{u:"Nordeste" for u in ["MA","PI","CE","RN","PB","PE","AL","SE","BA"]},
    **{u:"Sudeste" for u in ["MG","ES","RJ","SP"]},
    **{u:"Sul" for u in ["PR","SC","RS"]},
    **{u:"Centro-Oeste" for u in ["MS","MT","GO","DF"]},
}

RACA_LABEL = {1: "Branca", 2: "Preta", 4: "Parda", 5: "Indigena"}  # 3 Amarela e null excluídos
RACA_ORDER = ["Branca", "Parda", "Preta", "Indigena"]              # ref = Branca
ESC_LABEL = {1: "Nenhuma", 2: "1-3anos", 3: "4-7anos", 4: "8-11anos", 5: "12mais"}
CONS_LABEL = {1: "None", 2: "1-3", 3: "4-6", 4: "7plus", 9: "Ignorado"}

# colunas necessárias (subset, leitura leve)
NEED = ["CODMUNRES","RACACORMAE","SEMAGESTAC","ESCMAE","ESCMAE2010","IDADEMAE","DTNASC",
        "CONSULTAS","QTDFILVIVO","ESTCIVMAE","GRAVIDEZ","MESPRENAT"]

# config de escolaridade por variável: (faixa válida, rótulos das categorias)
EDU_CONFIG = {
    "ESCMAE":     {"valid": (1, 5), "labels": ESC_LABEL},
    # ESCMAE2010: 0 Sem escol., 1 Fund.I, 2 Fund.II, 3 Médio, 4 Sup.incompleto, 5 Sup.completo; 9 ignorado/null excluídos
    "ESCMAE2010": {"valid": (0, 5), "labels": {0:"0_Sem",1:"1_FundI",2:"2_FundII",3:"3_Medio",4:"4_SupInc",5:"5_SupComp"}},
}

def _to_num(series):
    return pd.to_numeric(series.astype("string").str.strip().replace({"": pd.NA}), errors="coerce")

def _prepare_year(df, y, prefixes):
    """Casting, recorte regional e derivação de ANO para um arquivo anual.

    Compartilhado pelos motores duckdb e pandas — é aqui que mora TODA a
    lógica de tipos. No caminho duckdb o filtro regional já foi aplicado na
    varredura, então `keep` é integralmente verdadeiro e a operação é um
    no-op; recalculá-lo custa pouco e mantém um único ponto de verdade.
    """
    pref = tuple(prefixes.keys())
    # casting explícito homogêneo (2023 é Float/Int, demais String)
    cod = df["CODMUNRES"].astype("string").str.strip()
    muni6 = cod.str.zfill(6)
    uf2 = muni6.str.slice(0, 2)
    keep = uf2.isin(pref)
    d = df.loc[keep].copy()
    d["CODMUNRES"] = muni6[keep]
    d["UF"] = uf2[keep].map(prefixes)
    for c in ["RACACORMAE","SEMAGESTAC","ESCMAE","ESCMAE2010","IDADEMAE","CONSULTAS",
              "QTDFILVIVO","ESTCIVMAE","GRAVIDEZ","MESPRENAT"]:
        d[c] = _to_num(d[c])
    # ano de DTNASC (DDMMAAAA) -> últimos 4 dígitos
    dt = df.loc[keep, "DTNASC"].astype("string").str.strip().str.zfill(8)
    d["ANO"] = pd.to_numeric(dt.str.slice(4, 8), errors="coerce")
    # fallback: usar ano do arquivo se DTNASC inválido
    d["ANO"] = d["ANO"].where(d["ANO"].between(2015, 2024), y)
    d["_ano_arquivo"] = y
    return d


def _read_year(f, prefixes, engine, con):
    """Lê um arquivo anual pelo motor escolhido, já projetado em NEED."""
    if engine == "pandas":
        return pd.read_parquet(f, columns=NEED)
    import duck_loader
    return duck_loader.scan_year(f, NEED, tuple(prefixes.keys()), con=con)


def load_region(prefixes=CO_PREFIXES, years=None, log=print, engine=None):
    """Carrega SINASC anual, casta tudo p/ numérico, filtra região por CODMUNRES.

    engine: "duckdb" (padrão, filtro na varredura do Parquet) ou "pandas"
    (lê o ano inteiro e filtra na memória). Ambos devolvem o mesmo dataframe.
    """
    # resolvidos na chamada (e não no def) para que YEARS/RAW possam ser
    # ajustados em tempo de execução — testes e recortes ad hoc.
    years = list(YEARS if years is None else years)
    engine = (engine or ENGINE).strip().lower()
    if engine not in ("duckdb", "pandas"):
        raise ValueError(f"PTB_ENGINE inválido: {engine!r} (use 'duckdb' ou 'pandas')")

    con = None
    if engine == "duckdb":
        try:
            import duck_loader
        except ImportError as exc:
            raise ImportError(
                "motor duckdb pedido mas o pacote duckdb não está instalado. "
                "Instale com `pip install duckdb` (ou `uv sync --extra fast`), "
                "ou rode com PTB_ENGINE=pandas."
            ) from exc
        con = duck_loader.connect()

    log(f"  [engine] leitura via {engine}")
    frames = []
    try:
        for y in years:
            f = RAW / f"sinasc_{y}.parquet"
            d = _prepare_year(_read_year(f, prefixes, engine, con), y, prefixes)
            frames.append(d)
            log(f"  [{y}] CO bruto: {len(d):,} linhas")
    finally:
        if con is not None:
            con.close()

    out = pd.concat(frames, ignore_index=True)
    log(f"  Total região (bruto, todas as raças): {len(out):,}")
    schemas.validate_region(out, set(prefixes.values()), log=log)
    return out

def build_cascade(df, log=print, edu_var="ESCMAE"):
    """Aplica a cascata de exclusão travada, registrando n após cada passo.
    edu_var: 'ESCMAE' (spec travada, 1-5) ou 'ESCMAE2010' (Clarimar, 0-5).
    Retorna (primaria, sensibilidade, cascade_steps, excluded_mask_info)."""
    lo, hi = EDU_CONFIG[edu_var]["valid"]
    steps = []
    n0 = len(df)
    steps.append(("0_CO_bruto", n0))

    # marcação de cada critério (sobre o conjunto bruto, p/ auditoria de excluídos)
    df = df.copy()
    df["_raca_valida"] = df["RACACORMAE"].isin([1, 2, 4, 5])
    df["_ig_valida"]   = df["SEMAGESTAC"].between(22, 44)   # pré-truncada 19-45; exclui <22/>44 e missing
    df["_esc_valida"]  = df[edu_var].between(lo, hi)        # exclui null e código ignorado (9)
    df["_idade_valida"] = df["IDADEMAE"].between(10, 60)
    df["_geo_valida"]  = df["ANO"].between(2015, 2024) & df["UF"].notna() & df["CODMUNRES"].notna()

    # cascata sequencial (ordem travada)
    m = df["_raca_valida"]
    steps.append(("1_raca_valida(excl Amarela/null)", int(m.sum())))
    m = m & df["_ig_valida"]
    steps.append(("2_SEMAGESTAC 22-44 nao-missing", int(m.sum())))
    m = m & df["_esc_valida"]
    steps.append((f"3_{edu_var} presente", int(m.sum())))
    m = m & df["_idade_valida"]
    steps.append(("4_IDADEMAE 10-60", int(m.sum())))
    m = m & df["_geo_valida"]
    steps.append(("5_ano/UF/municipio presente", int(m.sum())))

    primaria = df.loc[m].copy()
    df["_incluido_primaria"] = m

    # sensibilidade: primária + completos em CONSULTAS, paridade, ESTCIVMAE.
    # Regras (casam com o Clarimar): QTDFILVIVO nulo = paridade 0 (primípara) -> NÃO exclui;
    # CONSULTAS mantém código 9 (ignorado) como categoria; ESTCIVMAE exclui null E 9 (ignorado).
    s = m & df["CONSULTAS"].notna() & df["ESTCIVMAE"].notna() & (df["ESTCIVMAE"] != 9)
    sensib = df.loc[s].copy()
    df["_incluido_sensib"] = s
    steps.append(("6_sensib(+cons,parid,estciv)", int(s.sum())))

    for nm, n in steps:
        log(f"    cascata {nm}: {n:,}")
    return primaria, sensib, steps, df

def add_derived(d, edu_var="ESCMAE", log=print):
    """Adiciona rótulos e variáveis derivadas usadas nos modelos."""
    d = d.copy()
    labels = EDU_CONFIG[edu_var]["labels"]
    d["raca"] = pd.Categorical(d["RACACORMAE"].map(RACA_LABEL), categories=RACA_ORDER, ordered=False)
    d["PTB"] = (d["SEMAGESTAC"] < 37).astype(int)
    # faixa etária: <20, 20-34 (ref), >=35
    d["idade_cat"] = pd.cut(d["IDADEMAE"], bins=[9, 19, 34, 60],
                            labels=["<20", "20-34", ">=35"])
    d["idade_cat"] = d["idade_cat"].cat.reorder_categories(["20-34", "<20", ">=35"])
    d["esc_cat"] = pd.Categorical(d[edu_var].map(labels),
                                  categories=list(labels.values()))
    d["ano_cat"] = pd.Categorical(d["ANO"].astype(int).astype(str))
    d["uf_cat"] = pd.Categorical(d["UF"])
    if "CONSULTAS" in d:
        d["cons_cat"] = pd.Categorical(d["CONSULTAS"].map(CONS_LABEL),
                                       categories=list(CONS_LABEL.values()))
    if "QTDFILVIVO" in d:
        q = d["QTDFILVIVO"]
        par = q.clip(upper=3).astype("Int64").astype(str)
        par = par.where(q != 99, "Ign")     # 99 ignorado vira categoria própria
        par = par.where(q.notna(), "0")     # null = primípara (0 nascidos vivos anteriores)
        d["parid_cat"] = pd.Categorical(par, categories=["0","1","2","3","Ign"])
    if "ESTCIVMAE" in d:
        d["estciv_cat"] = pd.Categorical(d["ESTCIVMAE"].astype("Int64").astype(str))
    # Prova executável da cascata: se algum critério deixou passar faltante ou
    # valor fora de faixa, a falha aparece aqui e não nas estimativas.
    schemas.validate_baseB(d, RACA_ORDER, set(NATIONAL_PREFIXES.values()), log=log)
    return d

PROV_TEMPLATE = ("# BASE B (reproducao Forja) | gerado {ts} | script {script} | seed 42 "
                 "| dados {raw} | anos 2015-2024 | regiao {regiao} "
                 "| 2024 = DNBR final publicado 2025-12-23, baixado 2026-06-27")

def prov_line(script, regiao="Centro-Oeste (GO MT MS DF)"):
    return PROV_TEMPLATE.format(ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
                                script=script, raw=str(RAW), regiao=regiao)
