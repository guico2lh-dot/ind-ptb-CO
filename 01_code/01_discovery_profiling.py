#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["polars>=1.0"]
# ///
"""
Tarefa 1 — Descoberta e perfilamento do SINASC (2015-2024).
Projeto: desigualdades raciais em prematuridade (PTB <37 sem), SINASC/DATASUS.

Somente leitura sobre os dados brutos. Leitura lazy (polars scan_parquet),
ano a ano, para não estourar memória. Gera:
  outputs/discovery/data_inventory.csv
  outputs/discovery/data_dictionary.md
  outputs/discovery/profiling_report.md
  outputs/discovery/discovery_log.txt
"""
import polars as pl
from pathlib import Path
from datetime import datetime
import os

SEED = 42
RAW = Path(os.environ.get("DATA_ROOT", "data/sinasc"))   # microdados SINASC (fora do repo)
PROJ = Path(__file__).resolve().parents[1]               # raiz do repositório
OUT = PROJ / "outputs" / "discovery"
OUT.mkdir(parents=True, exist_ok=True)
YEARS = list(range(2015, 2025))  # janela analítica 2015-2024

LOG_LINES = []
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)

# Variáveis-chave e códigos "ignorado" conhecidos do SINASC
KEY_VARS = ["SEMAGESTAC","GESTACAO","RACACORMAE","IDADEMAE","ESCMAE","ESCMAE2010",
            "DTNASC","CODMUNRES","CONSULTAS","CONSPRENAT","MESPRENAT","QTDFILVIVO",
            "ESTCIVMAE","GRAVIDEZ"]
# código de "ignorado" por variável categórica (None = não se aplica / numérica)
IGNORED_CODE = {
    "RACACORMAE": "9", "ESCMAE": "9", "ESCMAE2010": "9", "ESTCIVMAE": "9",
    "CONSULTAS": "9", "GRAVIDEZ": "9", "GESTACAO": "9", "MESPRENAT": "99",
    "QTDFILVIVO": "99", "CONSPRENAT": "99",
}
RACA_LABELS = {"1":"Branca","2":"Preta","3":"Amarela","4":"Parda","5":"Indígena","9":"Ignorado"}
GRAV_LABELS = {"1":"Única","2":"Dupla","3":"Tripla+","9":"Ignorado"}
UF_CO = {"50":"MS","51":"MT","52":"GO","53":"DF"}

log("="*64)
log("TAREFA 1 — Descoberta e perfilamento SINASC 2015-2024")
log(f"Seed fixa = {SEED} | Raiz dados = {RAW}")
log("="*64)

def s(col):
    """cast string limpo (trim); '' -> null."""
    e = pl.col(col).cast(pl.Utf8).str.strip_chars()
    return pl.when(e == "").then(None).otherwise(e)

def num(col):
    """string -> Float64 (não-numérico vira null)."""
    return s(col).cast(pl.Float64, strict=False)

# ─────────────────────────────────────────────────────────────────────
# 1) INVENTÁRIO + 2) SCHEMA
# ─────────────────────────────────────────────────────────────────────
log("[1/4] Inventário de arquivos e schema por ano...")
inv_rows = []
schemas = {}   # ano -> {col: dtype}
for y in YEARS:
    f = RAW / f"sinasc_{y}.parquet"
    if not f.exists():
        log(f"  !! AUSENTE: {f.name}")
        inv_rows.append(dict(ano=y, arquivo=f.name, formato="parquet",
                             existe=False, n_linhas=None, n_colunas=None,
                             tamanho_mb=None, escopo="ausente"))
        continue
    lf = pl.scan_parquet(f)
    sch = lf.collect_schema()
    nrows = lf.select(pl.len()).collect().item()
    size_mb = round(os.path.getsize(f)/1e6, 1)
    schemas[y] = {c: str(t) for c, t in zip(sch.names(), sch.dtypes())}
    inv_rows.append(dict(ano=y, arquivo=f.name, formato="parquet", existe=True,
                         n_linhas=nrows, n_colunas=len(sch.names()),
                         tamanho_mb=size_mb, escopo="nacional (DNBR/residência)"))
    log(f"  {y}: {nrows:,} linhas | {len(sch.names())} colunas | {size_mb} MB")

inv = pl.DataFrame(inv_rows)
inv.write_csv(OUT / "data_inventory.csv")
log(f"  -> salvo data_inventory.csv ({len(inv_rows)} anos)")

# divergências de schema
all_cols = {}
for y, sc in schemas.items():
    for c in sc:
        all_cols.setdefault(c, set()).add(y)
present_years = sorted(schemas.keys())
core_cols = [c for c, ys in all_cols.items() if len(ys) == len(present_years)]
var_cols = {c: sorted(ys) for c, ys in all_cols.items() if len(ys) != len(present_years)}
# divergências de dtype
dtype_div = {}
for c in core_cols:
    dts = {schemas[y][c] for y in present_years}
    if len(dts) > 1:
        dtype_div[c] = {y: schemas[y][c] for y in present_years}

# ─────────────────────────────────────────────────────────────────────
# DATA DICTIONARY
# ─────────────────────────────────────────────────────────────────────
log("[dic] Montando data_dictionary.md...")
dd = []
dd.append("# Dicionário de dados — SINASC 2015–2024 (nacional, bruto)\n")
dd.append(f"Gerado: {datetime.now():%Y-%m-%d %H:%M} · Raiz: `{RAW}`\n")
dd.append(f"Anos com schema lido: {', '.join(map(str,present_years))}\n")
dd.append("\n## Mapeamento das variáveis-chave do estudo\n")
dd.append("| Papel | Var. alvo | Presente? | Variantes/alternativas presentes | Obs |")
dd.append("|---|---|---|---|---|")
def pres(col): return "✅" if col in all_cols and len(all_cols[col])==len(present_years) else ("⚠️ parcial" if col in all_cols else "❌")
def years_of(col): return "todos" if col in all_cols and len(all_cols[col])==len(present_years) else (",".join(map(str,sorted(all_cols[col]))) if col in all_cols else "—")
rows_map = [
 ("Desfecho (IG semanas)","SEMAGESTAC","GESTACAO (categórica)","weeks; flag <22 e >44"),
 ("Exposição (raça/cor mãe)","RACACORMAE","RACACOR (do RN, NÃO usar)","1B 2P 3Am 4Pa 5Ind 9ign"),
 ("Covariável: idade","IDADEMAE","—","numérica"),
 ("Covariável: escolaridade","ESCMAE","ESCMAE2010, ESCMAEAGR1, SERIESCMAE","5 níveis (ESCMAE) vs 2010"),
 ("Tempo: ano nasc.","(derivar de DTNASC)","ANONASC ausente","DTNASC=DDMMAAAA"),
 ("Cluster: município resid.","CODMUNRES","—","UF=2 primeiros dígitos"),
 ("Sens.: nº consultas pré-natal","CONSULTAS","CONSPRENAT (contagem)","1 nenhuma..4 7+"),
 ("Sens.: início pré-natal","MESPRENAT","—","mês 1-9, 99 ign"),
 ("Sens.: paridade","QTDFILVIVO","QTDGESTANT,QTDPARTNOR,QTDPARTCES,PARIDADE","nasc. vivos anteriores"),
 ("Sens.: estado civil","ESTCIVMAE","—","categórica"),
 ("Sens.: tipo gravidez","GRAVIDEZ","—","1 única 2 dupla 3 tripla+"),
]
for papel, tgt, alt, obs in rows_map:
    base = tgt.split(" ")[0].strip("()") if tgt.startswith("(") else tgt
    dd.append(f"| {papel} | `{tgt}` | {pres(base)} ({years_of(base)}) | {alt} | {obs} |")

dd.append("\n## Divergências de schema entre anos\n")
if var_cols:
    dd.append("Colunas **não presentes em todos os anos**:\n")
    dd.append("| Coluna | Anos presentes |")
    dd.append("|---|---|")
    for c, ys in sorted(var_cols.items()):
        dd.append(f"| `{c}` | {','.join(map(str,ys))} |")
else:
    dd.append("_Nenhuma — todas as colunas presentes em todos os anos._\n")
dd.append("")
if dtype_div:
    dd.append("Colunas com **dtype divergente** entre anos:\n")
    dd.append("| Coluna | " + " | ".join(map(str,present_years)) + " |")
    dd.append("|---|" + "---|"*len(present_years))
    for c, mp in sorted(dtype_div.items()):
        dd.append(f"| `{c}` | " + " | ".join(mp[y] for y in present_years) + " |")
else:
    dd.append("_Nenhuma divergência de dtype nas colunas comuns._")

dd.append("\n## Schema completo por ano (todas as colunas)\n")
for y in present_years:
    dd.append(f"### {y} — {len(schemas[y])} colunas")
    cols = ", ".join(f"`{c}`" for c in schemas[y])
    dd.append(cols + "\n")
(OUT / "data_dictionary.md").write_text("\n".join(dd), encoding="utf-8")
log("  -> salvo data_dictionary.md")

# ─────────────────────────────────────────────────────────────────────
# 3+4) PERFILAMENTO por ano (lazy, ano a ano)
# ─────────────────────────────────────────────────────────────────────
log("[perfil] Perfilamento por variável-chave, ano a ano...")
miss_tbl = []      # ano,var,n,n_null,pct_null,n_ign,pct_ign
raca_tbl = []      # ano,codigo,label,n,pct
grav_tbl = []      # ano,codigo,label,n,pct
sem_tbl = []       # ano,min,max,pct_lt22,pct_gt44,pct_null,p1,p50,p99
uf_tbl = []        # ano,uf,n  (Centro-Oeste)
uf_all_tbl = []    # ano,total_nacional,total_centro_oeste

for y in present_years:
    lf = pl.scan_parquet(RAW / f"sinasc_{y}.parquet")
    n = lf.select(pl.len()).collect().item()

    # missingness por variável-chave
    null_exprs = []
    for v in KEY_VARS:
        if v in schemas[y]:
            null_exprs.append(s(v).is_null().sum().alias(f"null__{v}"))
            ic = IGNORED_CODE.get(v)
            if ic is not None:
                null_exprs.append((s(v) == ic).sum().alias(f"ign__{v}"))
    miss = lf.select(null_exprs).collect().to_dicts()[0]
    for v in KEY_VARS:
        if v not in schemas[y]:
            miss_tbl.append(dict(ano=y, variavel=v, n=n, n_null=None, pct_null=None,
                                 cod_ign=None, n_ign=None, pct_ign=None, status="AUSENTE"))
            continue
        nn = miss.get(f"null__{v}")
        ic = IGNORED_CODE.get(v)
        ni = miss.get(f"ign__{v}") if ic is not None else None
        miss_tbl.append(dict(ano=y, variavel=v, n=n,
                             n_null=nn, pct_null=round(100*nn/n,2),
                             cod_ign=ic, n_ign=ni,
                             pct_ign=(round(100*ni/n,2) if ni is not None else None),
                             status="ok"))

    # distribuição RACACORMAE
    if "RACACORMAE" in schemas[y]:
        d = (lf.select(s("RACACORMAE").alias("c")).group_by("c").len()
               .collect().sort("c"))
        for r in d.to_dicts():
            code = r["c"]
            raca_tbl.append(dict(ano=y, codigo=(code if code is not None else "(null)"),
                                 label=RACA_LABELS.get(code, "—" if code else "(null/missing)"),
                                 n=r["len"], pct=round(100*r["len"]/n,2)))
    # distribuição GRAVIDEZ
    if "GRAVIDEZ" in schemas[y]:
        d = (lf.select(s("GRAVIDEZ").alias("c")).group_by("c").len().collect().sort("c"))
        for r in d.to_dicts():
            code = r["c"]
            grav_tbl.append(dict(ano=y, codigo=(code if code is not None else "(null)"),
                                 label=GRAV_LABELS.get(code, "—" if code else "(null/missing)"),
                                 n=r["len"], pct=round(100*r["len"]/n,2)))
    # faixa SEMAGESTAC (numérico)
    if "SEMAGESTAC" in schemas[y]:
        st = lf.select([
            num("SEMAGESTAC").min().alias("min"),
            num("SEMAGESTAC").max().alias("max"),
            num("SEMAGESTAC").quantile(0.01).alias("p1"),
            num("SEMAGESTAC").quantile(0.50).alias("p50"),
            num("SEMAGESTAC").quantile(0.99).alias("p99"),
            (num("SEMAGESTAC") < 22).sum().alias("lt22"),
            (num("SEMAGESTAC") > 44).sum().alias("gt44"),
            s("SEMAGESTAC").is_null().sum().alias("nnull"),
        ]).collect().to_dicts()[0]
        sem_tbl.append(dict(ano=y, min=st["min"], max=st["max"],
                            p1=st["p1"], p50=st["p50"], p99=st["p99"],
                            n_lt22=st["lt22"], pct_lt22=round(100*st["lt22"]/n,3),
                            n_gt44=st["gt44"], pct_gt44=round(100*st["gt44"]/n,3),
                            pct_null=round(100*st["nnull"]/n,2)))
    # UF x ano (Centro-Oeste via CODMUNRES 50/51/52/53)
    if "CODMUNRES" in schemas[y]:
        uf = lf.select(s("CODMUNRES").str.slice(0,2).alias("uf")).group_by("uf").len().collect()
        ufm = {r["uf"]: r["len"] for r in uf.to_dicts()}
        co_total = 0
        for code, sigla in UF_CO.items():
            cnt = ufm.get(code, 0)
            uf_tbl.append(dict(ano=y, uf_cod=code, uf=sigla, n=cnt))
            co_total += cnt
        uf_all_tbl.append(dict(ano=y, total_nacional=n, total_centro_oeste=co_total,
                               pct_co=round(100*co_total/n,2)))
    log(f"  {y}: perfilado (n={n:,})")

# ─────────────────────────────────────────────────────────────────────
# RELATÓRIO DE PERFILAMENTO
# ─────────────────────────────────────────────────────────────────────
log("[rel] Escrevendo profiling_report.md...")
def md_table(rows, cols, headers=None):
    headers = headers or cols
    out = ["| " + " | ".join(headers) + " |", "|" + "---|"*len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |")
    return "\n".join(out)

rep = []
rep.append("# Relatório de perfilamento — SINASC 2015–2024 (nacional)\n")
rep.append(f"Gerado: {datetime.now():%Y-%m-%d %H:%M} · Seed={SEED} · Leitura lazy (polars)\n")

rep.append("\n## 1. Linhas por ano\n")
rep.append(md_table([r for r in inv_rows if r['existe']],
                    ["ano","n_linhas","n_colunas","tamanho_mb"]))

rep.append("\n\n## 2. Missingness por variável × ano (% null e % código-ignorado)\n")
rep.append("`pct_null` = vazio/ausente; `pct_ign` = código de ignorado (9, 99) quando aplicável.\n")
rep.append(md_table(miss_tbl, ["ano","variavel","n","pct_null","cod_ign","pct_ign","status"]))

rep.append("\n\n## 3. Distribuição de RACACORMAE (exposição) por código × ano\n")
rep.append("Códigos: 1 Branca · 2 Preta · 3 Amarela · 4 Parda · 5 Indígena · 9 Ignorado · (null)=vazio.\n")
rep.append(md_table(raca_tbl, ["ano","codigo","label","n","pct"]))

rep.append("\n\n## 4. Distribuição de GRAVIDEZ por código × ano\n")
rep.append(md_table(grav_tbl, ["ano","codigo","label","n","pct"]))

rep.append("\n\n## 5. SEMAGESTAC — faixa e caudas implausíveis (<22 e >44 semanas)\n")
rep.append(md_table(sem_tbl, ["ano","min","max","p1","p50","p99","pct_null","pct_lt22","pct_gt44"]))

rep.append("\n\n## 6. Recorte Centro-Oeste — contagens UF × ano (CODMUNRES 50/51/52/53)\n")
rep.append("Filtro CO: `CODMUNRES` iniciando em 50 (MS), 51 (MT), 52 (GO), 53 (DF).\n")
# pivot UF x ano
years_p = present_years
piv = {sigla: {y:0 for y in years_p} for sigla in UF_CO.values()}
for r in uf_tbl: piv[r["uf"]][r["ano"]] = r["n"]
rep.append("| UF | " + " | ".join(map(str,years_p)) + " |")
rep.append("|---|" + "---|"*len(years_p))
for sigla in ["MS","MT","GO","DF"]:
    rep.append(f"| {sigla} | " + " | ".join(f"{piv[sigla][y]:,}" for y in years_p) + " |")
rep.append("\n**Totais nacional vs Centro-Oeste por ano:**\n")
rep.append(md_table(uf_all_tbl, ["ano","total_nacional","total_centro_oeste","pct_co"]))

(OUT / "profiling_report.md").write_text("\n".join(rep), encoding="utf-8")
log("  -> salvo profiling_report.md")

# também salvar tabelas longas em CSV para reuso
pl.DataFrame(miss_tbl).write_csv(OUT/"missingness_var_ano.csv")
pl.DataFrame(raca_tbl).write_csv(OUT/"racacormae_dist.csv")
pl.DataFrame(uf_tbl).write_csv(OUT/"uf_ano_centrooeste.csv")
log("  -> salvos CSVs auxiliares (missingness, raca, uf)")

log("="*64)
log("CONCLUÍDO. Entregáveis em outputs/discovery/")
log("="*64)
(OUT / "discovery_log.txt").write_text("\n".join(LOG_LINES), encoding="utf-8")
print("\nOK")
