#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy","statsmodels","pyarrow","scipy"]
# ///
"""
04_clarimar_match.py — Variante de RECONCILIAÇÃO que adota as escolhas reais do
Clarimar (educação = ESCMAE2010; completeness em ESCMAE2010 não-null) para
demonstrar que reproduzimos o OR indígena canônico (~1.322) e isolar o efeito do
BUG de desenho (M7/M8 que não adicionavam paridade/estado civil) do efeito da
escolha de variável de escolaridade. NÃO é a Base B primária (essa usa ESCMAE).
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from statsmodels.genmod.families import Binomial
sys.path.insert(0, str(Path(__file__).parent))
import lib_baseB as L

RAW = L.RAW
OUT = Path(__file__).resolve().parents[1]/"outputs/centro_oeste/tables"

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

NEED = L.NEED + ["ESCMAE2010"]
frames=[]
for y in range(2015,2025):
    df=pd.read_parquet(f"{RAW}/sinasc_{y}.parquet", columns=NEED)
    cod=df["CODMUNRES"].astype("string").str.strip().str.zfill(6)
    keep=cod.str.slice(0,2).isin(["50","51","52","53"])
    d=df[keep].copy(); d["CODMUNRES"]=cod[keep]; d["UF"]=cod[keep].str.slice(0,2).map(L.CO_PREFIXES)
    for c in ["RACACORMAE","SEMAGESTAC","ESCMAE","ESCMAE2010","IDADEMAE","CONSULTAS","QTDFILVIVO","ESTCIVMAE","GRAVIDEZ"]:
        d[c]=pd.to_numeric(d[c].astype("string").str.strip().replace({"":np.nan}),errors="coerce")
    dt=df.loc[keep,"DTNASC"].astype("string").str.strip().str.zfill(8)
    d["ANO"]=pd.to_numeric(dt.str.slice(4,8),errors="coerce"); d["ANO"]=d["ANO"].where(d["ANO"].between(2015,2024),y)
    frames.append(d)
co=pd.concat(frames,ignore_index=True)
log(f"CO bruto: {len(co):,}")

# cascata estilo Clarimar: educação = ESCMAE2010 (completo = não-null)
m = co["RACACORMAE"].isin([1,2,4,5])
m &= co["SEMAGESTAC"].between(22,44)
m &= co["ESCMAE2010"].notna()          # <<< Clarimar: ESCMAE2010 não-null
m &= co["IDADEMAE"].between(10,60)
m &= co["ANO"].between(2015,2024) & co["UF"].notna()
prim = co[m].copy()
sens = prim[prim["CONSULTAS"].notna() & prim["QTDFILVIVO"].notna() & prim["ESTCIVMAE"].notna()].copy()
log(f"primária(ESCMAE2010)={len(prim):,}  (Clarimar 2,155,295)")
log(f"sensib(ESCMAE2010)={len(sens):,}  (Clarimar 2,143,570)")
ind_n=int((prim['RACACORMAE']==5).sum())
log(f"indígena primária={ind_n:,}  (Clarimar 36,469)")

def derive(d):
    d=d.copy()
    d["raca"]=pd.Categorical(d["RACACORMAE"].map(L.RACA_LABEL),categories=L.RACA_ORDER)
    d["PTB"]=(d["SEMAGESTAC"]<37).astype(int)
    d["idade_cat"]=pd.cut(d["IDADEMAE"],bins=[9,19,34,60],labels=["<20","20-34",">=35"]).cat.reorder_categories(["20-34","<20",">=35"])
    d["esc2010_cat"]=pd.Categorical(d["ESCMAE2010"].astype("Int64").astype(str))  # inclui 0..5 e 9
    d["ano_cat"]=pd.Categorical(d["ANO"].astype(int).astype(str))
    d["uf_cat"]=pd.Categorical(d["UF"])
    d["cons_cat"]=pd.Categorical(d["CONSULTAS"].map(L.CONS_LABEL),categories=list(L.CONS_LABEL.values()))
    par=d["QTDFILVIVO"].clip(upper=3).astype("Int64").astype(str); par=par.where(d["QTDFILVIVO"]!=99,"Ign")
    d["parid_cat"]=pd.Categorical(par,categories=["0","1","2","3","Ign"])
    d["estciv_cat"]=pd.Categorical(d["ESTCIVMAE"].astype("Int64").astype(str))
    return d
prim=derive(prim); sens=derive(sens)

RH={"M1":"C(raca, Treatment('Branca'))",
    "M5":"C(raca, Treatment('Branca')) + C(idade_cat) + C(esc2010_cat) + C(ano_cat) + C(uf_cat)",
    "M6":"C(raca, Treatment('Branca')) + C(idade_cat) + C(esc2010_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat)",
    "M7":"C(raca, Treatment('Branca')) + C(idade_cat) + C(esc2010_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat) + C(parid_cat)",
    "M8":"C(raca, Treatment('Branca')) + C(idade_cat) + C(esc2010_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat) + C(parid_cat) + C(estciv_cat)"}
clar={"M1":1.781,"M5":1.588,"M6":1.322,"M7":1.322,"M8":1.322}
rows=[]
for mn in ["M1","M5","M6","M7","M8"]:
    d=prim if mn in("M1","M5") else sens
    res=smf.glm("PTB ~ "+RH[mn],data=d,family=Binomial()).fit()
    k=[c for c in res.params.index if "Indigena" in c][0]
    orr=np.exp(res.params[k])
    log(f"  {mn}: Indig OR={orr:.3f} | AIC={res.aic:.1f} | nparam={len(res.params)} | nobs={int(res.nobs):,}  (Clarimar {clar[mn]})")
    rows.append(dict(Modelo=mn,Indig_OR=round(orr,3),AIC=round(res.aic,1),
                     n_params=len(res.params),nobs=int(res.nobs),Clarimar_Indig_OR=clar[mn]))
out=pd.DataFrame(rows)
with open(OUT/"reconcile_clarimar_match_ESCMAE2010.csv","w") as fh:
    fh.write("# Variante de reconciliação: educação=ESCMAE2010 (escolha real do Clarimar). NÃO é a Base B primária (ESCMAE).\n")
    out.to_csv(fh,index=False)
log("salvo reconcile_clarimar_match_ESCMAE2010.csv")
print(out.to_string(index=False))
