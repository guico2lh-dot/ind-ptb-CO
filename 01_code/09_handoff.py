#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy"]
# ///
"""
09_handoff.py — Tarefa 3: consolida os números ESCMAE já calculados em 2 arquivos
de handoff para a redação da revisão RSP-2026-7625. NÃO roda modelos; só lê outputs.
Decimal pt-BR. Onde faltar, escreve FALTA:.
"""
import sys, glob, re
from pathlib import Path
from datetime import datetime
import pandas as pd, numpy as np

PROJ=Path(__file__).resolve().parents[1]
CO=PROJ/"outputs/centro_oeste"; CO10=PROJ/"outputs/centro_oeste_escmae2010"
T=CO/"tables"; T10=CO10/"tables"
OUT=PROJ/"outputs/handoff"; OUT.mkdir(parents=True, exist_ok=True)
FALTAS=[]
def falta(msg): FALTAS.append(msg); return f"FALTA: {msg}"

def rd(p):
    try: return pd.read_csv(p, comment="#")
    except Exception as e: return None

def br(x, nd=3):
    if x is None or (isinstance(x,float) and np.isnan(x)): return ""
    if isinstance(x,(int,np.integer)): return f"{x:,}".replace(",",".")
    s=f"{float(x):,.{nd}f}"
    return s.replace(",","§").replace(".",",").replace("§",".")
def ic(lo,hi,nd=3): return f"{br(lo,nd)}–{br(hi,nd)}"
def brn(n): return f"{int(round(float(n))):,}".replace(",",".")  # inteiro pt-BR

# ── carregar fontes ──────────────────────────────────────────────────
t2=rd(T/"tabela2_base_B.csv")
orrr=rd(T/"or_vs_rr_comparison.csv")
pp=rd(T/"predicted_probabilities.csv")
t1=rd(T/"tabela1_base_B.csv")
prev=rd(T/"ptb_prevalencia_raca_estado.csv")
inter=rd(T/"interaction_test_raca_estado.csv")
strat=rd(T/"stratified_MS_MT.csv")
temp=rd(T/"temporal_trends.csv")
mesp=rd(T/"mesprenat_vs_consultas.csv")
pren=rd(T/"prenat_1trim_por_grupo.csv")
incl=rd(T/"incluidos_vs_excluidos.csv")
rmu=rd(T/"raca_missing_por_ano_uf.csv")
missv=rd(T/"missing_por_variavel_grupo.csv")
aud=rd(T/"audit1_M6M7M8_design.csv")
nsum=rd(T/"n_summary.csv")
recon=(CO/"reconcile_report.md").read_text() if (CO/"reconcile_report.md").exists() else ""

def nsum_get(key):
    if nsum is None: return None
    r=nsum[nsum["Amostra"]==key]
    return float(r["n"].iloc[0]) if len(r) else None
def recon_delta(key):
    m=re.search(rf"\|\s*{re.escape(key)}\s*\|\s*([\d,]+)\s*\|\s*([\d,.]+)\s*\|\s*([+\-]?[\d,]+)\s*\|", recon)
    return m.group(3) if m else None
def recon_clarimar(key):
    m=re.search(rf"\|\s*{re.escape(key)}\s*\|\s*([\d,]+)\s*\|\s*([\d,.]+)\s*\|\s*([+\-]?[\d,]+)\s*\|", recon)
    if not m: return None
    return brn(float(m.group(2).replace(",","")))

MODS=[("M1_Crude","M1 (cru)"),("M2_+Idade","M2 (+idade)"),("M3_+Esc","M3 (+escolaridade)"),
      ("M4_+Ano","M4 (+ano)"),("M5_PRIMARY","M5 (+UF) ★primário"),("M6_+Prenat","M6 (+pré-natal)"),
      ("M7_+Paridade","M7 (+paridade)"),("M8_FULL","M8 (full +estado civil)")]
def t2get(mod,grp,col):
    r=t2[(t2["Modelo"]==mod)&(t2["Grupo"]==grp)]
    return float(r[col].iloc[0]) if len(r) else None
def prget(df,mod,grp):
    r=df[(df["Modelo"]==mod)&(df["Grupo"]==grp)]
    if not len(r): return (None,None,None)
    return (float(r["RR"].iloc[0]), float(r["CI_95_low"].iloc[0]), float(r["CI_95_high"].iloc[0]))

# % atenuação do OR (derivado dos OR de tabela2): (OR_M1 - OR_Mk)/(OR_M1 - 1)*100
def atten(grp,mod):
    o1=t2get("M1_Crude",grp,"OR"); ok=t2get(mod,grp,"OR")
    if o1 is None or ok is None or o1==1: return None
    return (o1-ok)/(o1-1)*100

# ════════════════════ ARQUIVO 2: tabela2_revisada_ESCMAE.csv ════════════════════
rows=[]
for mod,_ in MODS:
    n=t2get(mod,"Indigena","N")
    row={"Modelo":mod.replace("_"," "),"n":brn(n) if n else ""}
    for grp in ["Parda","Preta","Indigena"]:
        orv=t2get(mod,grp,"OR"); lo=t2get(mod,grp,"CI_95_low"); hi=t2get(mod,grp,"CI_95_high")
        row[f"{grp}_OR"]=br(orv); row[f"{grp}_IC"]=ic(lo,hi)
        pr=prget(orrr,mod.split("_")[0]+"_Poisson_robust",grp)  # só M1/M5/M8 existem
        row[f"{grp}_PR"]=br(pr[0]) if pr[0] is not None else ""
        row[f"{grp}_PR_IC"]=ic(pr[1],pr[2]) if pr[1] is not None else ""
    a=atten("Indigena",mod)
    row["Indigena_pct_atenuacao_OR"]=br(a,1) if a is not None else ""
    rows.append(row)
cols=["Modelo","n","Parda_OR","Parda_IC","Parda_PR","Parda_PR_IC",
      "Preta_OR","Preta_IC","Preta_PR","Preta_PR_IC",
      "Indigena_OR","Indigena_IC","Indigena_PR","Indigena_PR_IC","Indigena_pct_atenuacao_OR"]
tab2rev=pd.DataFrame(rows)[cols]
with open(OUT/"tabela2_revisada_ESCMAE.csv","w") as fh:
    fh.write(f"# Tabela 2 revisada (ESCMAE) | RSP-2026-7625 | gerado {datetime.now():%Y-%m-%d %H:%M} | "
             f"fonte tabela2_base_B.csv + or_vs_rr_comparison.csv | OR=logística SE-modelo, PR=Poisson robusto (cluster municipio) | "
             f"% atenuacao do OR = (OR_M1-OR_Mk)/(OR_M1-1)*100 [derivado dos OR reportados] | decimal pt-BR\n")
    tab2rev.to_csv(fh,index=False)

# ════════════════════ ARQUIVO 1: handoff md ════════════════════
L=[]; w=L.append
w("# Handoff — números da revisão RSP-2026-7625 (variante **ESCMAE**, primária)\n")
w(f"Gerado: {datetime.now():%Y-%m-%d %H:%M} · Fonte: `outputs/centro_oeste/` (ESCMAE) e "
  "`outputs/centro_oeste_escmae2010/` (sensibilidade). Decimal pt-BR. **Nenhum modelo re-rodado.**\n")

# 1. Amostras
w("\n## 1. Amostras (Base B, ESCMAE)\n")
w("| Amostra | n (Forja ESCMAE) | Clarimar | Δ | fonte |")
w("|---|--:|--:|--:|---|")
for key,lab in [("primaria_M1-5","Primária (M1–M5)"),("sensibilidade_M6-8","Sensibilidade (M6–M8)"),
                ("singletons_primaria","Singletons primária"),("singletons_sensib","Singletons sensibilidade"),
                ("mesprenat_subsample","Subamostra MESPRENAT")]:
    n=nsum_get(key); d=recon_delta(key); cl=recon_clarimar(key)
    w(f"| {lab} | {brn(n) if n else falta(key)} | {cl or '—'} | {d or ''} | [n_summary.csv; reconcile_report.md] |")

# 2. Cascata
w("\n## 2. Cascata de exclusão (Figura 1) [fonte: build_baseB log, ESCMAE]\n")
logs=sorted(glob.glob(str(CO/"logs/build_baseB_*.log")))
casc=[]
if logs:
    txt=Path(logs[-1]).read_text()
    for m in re.finditer(r"cascata (\d_[^\:]+): ([\d,]+)", txt):
        casc.append((m.group(1), int(m.group(2).replace(",",""))))
    casc=casc[:6]
if casc:
    w("| Passo | n | n excluído no passo |")
    w("|---|--:|--:|")
    prevn=None
    labels={"0":"(0) CO bruto","1":"(1) raça válida (excl. Amarela/null)","2":"(2) IG 22–44",
            "3":"(3) ESCMAE presente","4":"(4) idade 10–60","5":"(5) ano/UF/município"}
    for code,n in casc:
        k=code.split("_")[0]; exc="" if prevn is None else brn(prevn-n)
        w(f"| {labels.get(k,code)} | {brn(n)} | {exc} |"); prevn=n
else:
    w(falta("cascata não encontrada no log do build ESCMAE"))

# 3. Tabela 2 completa
w("\n## 3. Tabela 2 (M1→M8), ESCMAE — OR (IC95%), % atenuação, n [tabela2_base_B.csv]\n")
w("Paridade/estado civil **de fato incluídos** confirmados pelo AIC (audit1): "
  "M6→M7→M8 com AIC distintos (M7 soma +paridade, M8 soma +estado civil).\n")
w("`% atenuação OR` só é interpretável para Indígena (Parda/Preta têm OR cru ≈ 1 → métrica indefinida).\n")
w("| Modelo | n | Grupo | OR | IC95% | % atenuação OR (só Indígena) |")
w("|---|--:|---|--:|--:|--:|")
for mod,lab in MODS:
    for grp in ["Parda","Preta","Indigena"]:
        orv=t2get(mod,grp,"OR"); lo=t2get(mod,grp,"CI_95_low"); hi=t2get(mod,grp,"CI_95_high")
        n=t2get(mod,grp,"N"); a=atten(grp,mod) if grp=="Indigena" else None
        w(f"| {lab} | {brn(n)} | {grp} | {br(orv)} | {ic(lo,hi)} | {br(a,1) if a is not None else ''} |")
if aud is not None:
    w("\n**Confirmação design (audit1_M6M7M8_design.csv):**")
    w("| Modelo | nº params | AIC | tem paridade | tem est.civil |")
    w("|---|--:|--:|:--:|:--:|")
    for _,r in aud.iterrows():
        w(f"| {r['Modelo']} | {int(r['n_params'])} | {br(r['AIC'],1)} | {r['tem_paridade']} | {r['tem_estado_civil']} |")

# 4. PR
w("\n## 4. Prevalence ratios (Poisson robusto; **cluster por CODMUNRES = município de residência**) [or_vs_rr_comparison.csv]\n")
w("| Modelo | Grupo | PR | IC95% |")
w("|---|---|--:|--:|")
for mod in ["M1","M5","M8"]:
    for grp in ["Indigena","Parda","Preta"]:
        pr=prget(orrr,f"{mod}_Poisson_robust",grp)
        w(f"| {mod} | {grp} | {br(pr[0])} | {ic(pr[1],pr[2]) if pr[1] is not None else falta(f'PR {mod} {grp}')} |")

# 5. Probabilidades ajustadas
w("\n## 5. Probabilidades ajustadas de PTB (M5, padronização marginal) [predicted_probabilities.csv]\n")
if pp is not None:
    w("| Grupo | P(PTB) ajustada % | Δ pp vs Branca |")
    w("|---|--:|--:|")
    for _,r in pp.iterrows():
        w(f"| {r['Grupo']} | {br(r['P_PTB_ajustada_pct'],3)} | {br(r['Dif_risco_pp'],3)} |")
else: w(falta("predicted_probabilities.csv"))

# 6. Prevalência bruta
w("\n## 6. Prevalência bruta de PTB por grupo (Base B ESCMAE) [tabela1_base_B.csv]\n")
if t1 is not None:
    w("| Grupo | N | PTB n | PTB % |")
    w("|---|--:|--:|--:|")
    bran=None
    for _,r in t1.iterrows():
        w(f"| {r['Grupo']} | {brn(r['N'])} | {brn(r['PTB_n'])} | {br(r['PTB_pct'],1)} |")
        if r['Grupo']=='Branca': bran=float(r['PTB_pct'])
        if r['Grupo']=='Indigena': ind=float(r['PTB_pct'])
    if bran is not None:
        w(f"\n**Diferença absoluta Indígena − Branca = {br(ind-bran,1)} pontos percentuais.**")
else: w(falta("tabela1_base_B.csv"))

# 7. Heterogeneidade
w("\n## 7. Heterogeneidade (ponto 5 do revisor)\n")
w("\n**7a. Prevalência PTB por raça × UF** [ptb_prevalencia_raca_estado.csv]\n")
if prev is not None:
    w("| UF | Branca % | Parda % | Preta % | Indígena % |")
    w("|---|--:|--:|--:|--:|")
    for uf in ["GO","MT","MS","DF"]:
        g={r["RACA"]:r["PTB_pct"] for _,r in prev[prev["ESTADO"]==uf].iterrows()}
        w(f"| {uf} | {br(g.get('Branca'),2)} | {br(g.get('Parda'),2)} | {br(g.get('Preta'),2)} | {br(g.get('Indigena'),2)} |")
w("\n**7b. LRT interação raça×UF** [interaction_test_raca_estado.csv]\n")
if inter is not None:
    r=inter.iloc[0]
    w(f"- χ² = {br(r['LRT_chi2'],2)}; df = {int(r['df'])}; p = {br(r['p_value'],4)} "
      f"(AIC sem interação {br(r['AIC_sem_int'],1)} → com {br(r['AIC_com_int'],1)}).")
w("\n**7c. OR/PR indígena estratificado MS e MT (M5 e M8)** [stratified_MS_MT.csv]\n")
if strat is not None:
    w("| Estrato | Grupo | OR | IC95% |")
    w("|---|---|--:|--:|")
    for mod in ["M5_MS","M8_MS","M5_MT","M8_MT"]:
        r=strat[(strat["Modelo"]==mod)&(strat["Grupo"]=="Indigena")]
        if len(r):
            r=r.iloc[0]; w(f"| {mod} | Indígena | {br(r['OR'])} | {ic(r['CI_95_low'],r['CI_95_high'])} |")
    w("\n  PR estratificado por UF: " + falta("PR (Poisson) estratificado MS/MT não consta em stratified_MS_MT.csv (só OR logístico)"))
w("\n**7d. Tendência temporal (OR indígena)** [temporal_trends.csv]\n")
if temp is not None:
    ti=temp[(temp["Grupo"]=="Indigena")&(temp["Modelo"].str.startswith("Ano_"))]
    yrs=" · ".join(f"{int(float(r['Ano']))}: {br(r['OR'])}" for _,r in ti.iterrows())
    w(f"- Por ano — {yrs}")
    tb=temp[(temp["Grupo"]=="Indigena")&(temp["Modelo"].str.contains("pandemia",case=False))]
    for _,r in tb.iterrows():
        w(f"- {r['Modelo']}: OR {br(r['OR'])} ({ic(r['CI_95_low'],r['CI_95_high'])})")

# 8. Pré-natal
w("\n## 8. Pré-natal — MESPRENAT vs consultas (ponto 3) [mesprenat_vs_consultas.csv; prenat_1trim_por_grupo.csv]\n")
if mesp is not None:
    w("| Modelo | Grupo | OR | IC95% | AIC |")
    w("|---|---|--:|--:|--:|")
    for mod in ["M_CONSULTAS_categorica","M_MESPRENAT_1trim"]:
        r=mesp[(mesp["Modelo"]==mod)&(mesp["Grupo"]=="Indigena")]
        if len(r): r=r.iloc[0]; w(f"| {mod} | Indígena | {br(r['OR'])} | {ic(r['CI_95_low'],r['CI_95_high'])} | {br(r['AIC'],1)} |")
if pren is not None:
    w("\n% início no 1º trimestre (MESPRENAT≤3) por grupo:")
    w(" · ".join(f"{r['Grupo']}: {br(r['Inicio_1trim_pct'],1)}%" for _,r in pren.iterrows()))

# 9. Exclusão / missing
w("\n## 9. Exclusão / missing (pontos 1 e 7)\n")
w("\n**9a. Incluídos × excluídos (cascata completa)** [incluidos_vs_excluidos.csv]\n")
if incl is not None:
    w("| Grupo | N | PTB % | Indígena % | Amarela/Missing % |")
    w("|---|--:|--:|--:|--:|")
    for _,r in incl.iterrows():
        w(f"| {r['Grupo']} | {brn(r['N'])} | {br(r['PTB_pct'],2)} | {br(r['Raca_Indigena_pct'],1)} | {br(r.get('Raca_Amarela_Missing_pct'),1)} |")
w("\n**9b. Raça missing/ignorada por ano×UF** [raca_missing_por_ano_uf.csv]\n")
if rmu is not None:
    mn,mx=rmu["RACACOR_missing_pct"].min(), rmu["RACACOR_missing_pct"].max()
    hi=rmu.loc[rmu["RACACOR_missing_pct"].idxmax()]
    lo=rmu.loc[rmu["RACACOR_missing_pct"].idxmin()]
    w(f"- Faixa de % raça missing: {br(mn,3)}% a {br(mx,3)}% — máximo em {hi['UF']} {int(hi['Ano'])}, "
      f"mínimo em {lo['UF']} {int(lo['Ano'])}.")
    dfm=rmu.groupby("UF")["RACACOR_missing_pct"].mean().round(2).sort_values(ascending=False)
    w("- Média por UF: " + " · ".join(f"{uf} {br(v,2)}%" for uf,v in dfm.items()) + " (concentra no DF e GO, anos iniciais).")
w("\n**9c. Missing por variável × grupo racial** [missing_por_variavel_grupo.csv]\n")
if missv is not None:
    w("| Variável | Branca % | Parda % | Preta % | Indígena % |")
    w("|---|--:|--:|--:|--:|")
    for v in missv["Variavel"].unique():
        g={r["Grupo"]:r["Missing_pct"] for _,r in missv[missv["Variavel"]==v].iterrows()}
        w(f"| {v} | {br(g.get('Branca'),2)} | {br(g.get('Parda'),2)} | {br(g.get('Preta'),2)} | {br(g.get('Indigena'),2)} |")

# 10. Sensibilidade ESCMAE2010
w("\n## 10. Sensibilidade ESCMAE2010 (robustez p/ a carta) [centro_oeste_escmae2010/]\n")
t2b=rd(T10/"tabela2_base_B.csv"); orb=rd(T10/"or_vs_rr_comparison.csv")
def g2(df,mod,grp,col):
    if df is None: return None
    r=df[(df["Modelo"]==mod)&(df["Grupo"]==grp)]; return float(r[col].iloc[0]) if len(r) else None
w("| Métrica (Indígena) | ESCMAE (primária) | ESCMAE2010 (sensib.) |")
w("|---|--:|--:|")
for mod,lab in [("M5_PRIMARY","M5 OR"),("M8_FULL","M8 OR")]:
    a=t2get(mod,"Indigena","OR"); b=g2(t2b,mod,"Indigena","OR")
    al=t2get(mod,"Indigena","CI_95_low"); ah=t2get(mod,"Indigena","CI_95_high")
    bl=g2(t2b,mod,"Indigena","CI_95_low"); bh=g2(t2b,mod,"Indigena","CI_95_high")
    w(f"| {lab} | {br(a)} ({ic(al,ah)}) | {br(b)} ({ic(bl,bh)}) |")
for mod,lab in [("M5_Poisson_robust","M5 PR"),("M8_Poisson_robust","M8 PR")]:
    pa=prget(orrr,mod,"Indigena"); pb=prget(orb,mod,"Indigena") if orb is not None else (None,None,None)
    w(f"| {lab} | {br(pa[0])} ({ic(pa[1],pa[2])}) | {br(pb[0])} ({ic(pb[1],pb[2]) if pb[1] is not None else ''}) |")

# 11. Metadados
w("\n## 11. Metadados travados\n")
prov=""
for f in [T/"tabela2_base_B.csv"]:
    if f.exists(): prov=f.read_text().splitlines()[0]
w(f"- **Extração DATASUS:** 2024 = DNBR **final** publicado **2025-12-23**, baixado **2026-06-27**; "
  "demais anos (2015–2023) = parquet nacional pré-existente na Forja. (Clarimar extraiu 2026-02-03.)")
w(f"- **Status 2024:** DNBR final (não preliminar) — confirmado pela reconciliação ano a ano (Δ=0 no ESCMAE2010).")
w(f"- **Seed:** 42.")
w(f"- **Versões:** Python {sys.version.split()[0]}; pandas {pd.__version__}; NumPy {np.__version__}; "
  f"statsmodels 0.14.6 (build via `uv run`).")
w(f"- **Repositório:** `{PROJ}` (local). " + falta("URL do GitHub do projeto"))
w(f"- **Linha de proveniência dos CSVs:** `{prov}`")

# FALTAS
w("\n## Pendências (FALTA)\n")
if FALTAS:
    for f in dict.fromkeys(FALTAS): w(f"- FALTA: {f}")
else: w("Nenhuma — todos os números solicitados foram localizados nos outputs.")

(OUT/"handoff_numeros_revisao_ESCMAE.md").write_text("\n".join(L), encoding="utf-8")
print("OK_HANDOFF")
print("FALTAS:", len(set(FALTAS)))
for f in dict.fromkeys(FALTAS): print("  -", f)
