#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy","statsmodels","pyarrow","scipy"]
# ///
"""
02_build_baseB.py — Base B definitiva (Centro-Oeste 2015-2024) + sensibilidades
+ resolução das 2 dúvidas de auditoria. Reproduz os 18 CSVs do Clarimar.

Saídas: <repo>/outputs/centro_oeste/{tables,figures,logs}
Seed 42. Raw somente leitura (definir DATA_ROOT; ver README).
"""
import os, sys, time, warnings
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from statsmodels.genmod.families import Binomial, Poisson
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
import lib_baseB as L

warnings.filterwarnings("ignore")
np.random.seed(42)

EDU_VAR = sys.argv[1] if len(sys.argv) > 1 else "ESCMAE"
assert EDU_VAR in ("ESCMAE","ESCMAE2010"), EDU_VAR
_suffix = "" if EDU_VAR == "ESCMAE" else "_escmae2010"
PROJ = Path(__file__).resolve().parents[1]
OUT = PROJ/f"outputs/centro_oeste{_suffix}"
TAB = OUT/"tables"; FIG = OUT/"figures"; LOGD = OUT/"logs"
CACHE = PROJ/".cache"; CACHE.mkdir(parents=True, exist_ok=True)
for d in (TAB, FIG, LOGD): d.mkdir(parents=True, exist_ok=True)
STAMP = "20260627"
LOG = []
def log(m):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"; print(line, flush=True); LOG.append(line)

RACE_TERMS = ["Parda","Preta","Indigena"]
RHS = {
  "M1": "C(raca, Treatment('Branca'))",
  "M2": "C(raca, Treatment('Branca')) + C(idade_cat)",
  "M3": "C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat)",
  "M4": "C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat)",
  "M5": "C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat)",
  "M6": "C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat)",
  "M7": "C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat) + C(parid_cat)",
  "M8": "C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat) + C(parid_cat) + C(estciv_cat)",
}

def fit(d, rhs, family="binomial", cov=None, groups=None):
    f = "PTB ~ " + rhs
    fam = Binomial() if family=="binomial" else Poisson()
    model = smf.glm(f, data=d, family=fam)
    if cov=="cluster":
        return model.fit(cov_type="cluster", cov_kwds={"groups": groups})
    if cov=="robust":
        return model.fit(cov_type="HC0")
    return model.fit()

def race_rows(res, model_name, n, as_rr=False):
    """Extrai OR/RR + IC + p para Parda/Preta/Indigena. N = nobs real do fit."""
    n = int(getattr(res, "nobs", n) or n)
    out=[]
    params, ci = res.params, res.conf_int()
    pv = res.pvalues
    for g in RACE_TERMS:
        key = [k for k in params.index if f"[T.{g}]" in k and "raca" in k]
        if not key: continue
        k=key[0]; est=np.exp(params[k]); lo=np.exp(ci.loc[k,0]); hi=np.exp(ci.loc[k,1])
        row=dict(Modelo=model_name, Grupo=g,
                 OR=("" if as_rr else round(est,3)),
                 CI_95_low=round(lo,3), CI_95_high=round(hi,3),
                 p_value=round(float(pv[k]),4), AIC=round(res.aic,1), N=n)
        if as_rr: row["RR"]=round(est,3)
        out.append(row)
    return out

def write_csv(df, name, script="02_build_baseB.py", regiao="Centro-Oeste (GO MT MS DF)"):
    p = TAB/name
    with open(p,"w") as fh:
        fh.write(L.prov_line(script, regiao)+"\n")
        df.to_csv(fh, index=False)
    log(f"  -> {name} ({len(df)} linhas)")

# ════════════════════════════════════════════════════════════════════
log("="*70); log("BASE B — build + sensibilidades + auditoria"); log("="*70)
t0=time.time()

log(f"[load] Carregando Centro-Oeste... (escolaridade = {EDU_VAR})")
raw = L.load_region(log=log)
prim, sens, steps, full = L.build_cascade(raw, log=log, edu_var=EDU_VAR)
prim = L.add_derived(prim, edu_var=EDU_VAR); sens = L.add_derived(sens, edu_var=EDU_VAR)
N_PRIM, N_SENS = len(prim), len(sens)
log(f"[n] primária={N_PRIM:,} | sensibilidade={N_SENS:,}")

# guardar amostras p/ reuso/depuração
prim.to_parquet(CACHE/"baseB_primaria.parquet")
sens.to_parquet(CACHE/"baseB_sensib.parquet")

# ── Tabela 2: M1-M8 logística (SE modelo) ───────────────────────────
log("[tabela2] M1-M8 logística...")
t2=[]
fits={}
for mname in ["M1","M2","M3","M4","M5","M6","M7","M8"]:
    d = prim if mname in ("M1","M2","M3","M4","M5") else sens
    n = N_PRIM if mname in ("M1","M2","M3","M4","M5") else N_SENS
    res = fit(d, RHS[mname]); fits[mname]=res
    label={"M1":"M1_Crude","M2":"M2_+Idade","M3":"M3_+Esc","M4":"M4_+Ano",
           "M5":"M5_PRIMARY","M6":"M6_+Prenat","M7":"M7_+Paridade","M8":"M8_FULL"}[mname]
    t2 += race_rows(res, label, n)
    log(f"    {label}: AIC={res.aic:.1f} | nparам={len(res.params)} | Indig OR={np.exp(res.params[[k for k in res.params.index if 'Indigena' in k][0]]):.3f}")
write_csv(pd.DataFrame(t2), "tabela2_base_B.csv")

# ── AUDITORIA 1: M6/M7/M8 — colunas da matriz de desenho + AIC ───────
log("[AUDIT1] M6/M7/M8: colunas do design + AIC")
aud=[]
for mname in ["M6","M7","M8"]:
    res=fits[mname]; cols=list(res.params.index)
    has_par = any("parid" in c for c in cols); has_civ=any("estciv" in c for c in cols)
    log(f"    {mname}: nparam={len(cols)} AIC={res.aic:.2f} | parid_no_design={has_par} estciv_no_design={has_civ}")
    log(f"       colunas: {cols}")
    aud.append(dict(Modelo=mname, n_params=len(cols), AIC=round(res.aic,2),
                    tem_paridade=has_par, tem_estado_civil=has_civ,
                    Indig_OR=round(np.exp(res.params[[k for k in cols if 'Indigena' in k][0]]),3)))
mudou = not (abs(fits["M6"].aic-fits["M7"].aic)<0.01 and abs(fits["M7"].aic-fits["M8"].aic)<0.01)
log(f"    >>> M7/M8 MUDAM em relação a M6? {mudou}")
write_csv(pd.DataFrame(aud), "audit1_M6M7M8_design.csv")

# ── OR vs RR (M1/M5/M8): logística cluster + Poisson robusto + cluster
log("[A] or_vs_rr: cluster + Poisson...")
rr=[]
for mname in ["M1","M5","M8"]:
    d = prim if mname in ("M1","M5") else sens; n=len(d)
    g=d["CODMUNRES"]
    res_c = fit(d, RHS[mname], cov="cluster", groups=g)
    rr += race_rows(res_c, f"{mname}_Logistic_cluster", n)
for mname in ["M1","M5","M8"]:
    d = prim if mname in ("M1","M5") else sens; n=len(d)
    res_r = fit(d, RHS[mname], family="poisson", cov="robust")
    rr += race_rows(res_r, f"{mname}_Poisson_robust", n, as_rr=True)
for mname in ["M1","M5","M8"]:
    d = prim if mname in ("M1","M5") else sens; n=len(d)
    res_pc = fit(d, RHS[mname], family="poisson", cov="cluster", groups=d["CODMUNRES"])
    rr += race_rows(res_pc, f"{mname}_Poisson_cluster", n, as_rr=True)
pd.DataFrame(rr).to_csv(TAB/"or_vs_rr_comparison.csv", index=False)
log(f"  -> or_vs_rr_comparison.csv ({len(rr)} linhas)")

# ── Probabilidades ajustadas (padronização marginal) M5 ─────────────
log("[A] predicted_probabilities (M5 marginal standardization)...")
m5=fits["M5"]; pp=[]
base=None
for g in ["Branca","Parda","Preta","Indigena"]:
    d2=prim.copy(); d2["raca"]=pd.Categorical([g]*len(d2), categories=L.RACA_ORDER)
    p=float(m5.predict(d2).mean())*100
    if g=="Branca": base=p
    pp.append(dict(Grupo=g, P_PTB_ajustada_pct=round(p,3), Dif_risco_pp=round(p-base,3)))
write_csv(pd.DataFrame(pp), "predicted_probabilities.csv")

# ── Tabela 1: descritivas por raça ──────────────────────────────────
log("[tabela1] descritivas...")
def tab1_row(d, ds, grp):
    sub = d if grp=="TOTAL" else d[d["raca"]==grp]
    subs = ds if grp=="TOTAL" else ds[ds["raca"]==grp]
    n=len(sub); sem=sub["SEMAGESTAC"]
    r=dict(Caracteristica="", Grupo=grp, N=n, PTB_n=int(sub["PTB"].sum()),
           PTB_pct=round(100*sub["PTB"].mean(),1),
           PTB_ext_pct=round(100*(sem<28).mean(),1),
           PTB_muito_pct=round(100*((sem>=28)&(sem<32)).mean(),1),
           PTB_mod_pct=round(100*((sem>=32)&(sem<37)).mean(),1),
           Idade_media=round(sub["IDADEMAE"].mean(),1), Idade_SD=round(sub["IDADEMAE"].std(),1),
           Idade_lt20_pct=round(100*(sub["idade_cat"]=="<20").mean(),1),
           Idade_2034_pct=round(100*(sub["idade_cat"]=="20-34").mean(),1),
           Idade_ge35_pct=round(100*(sub["idade_cat"]==">=35").mean(),1))
    for code,lab in L.ESC_LABEL.items():
        r[f"Esc_{lab}_pct"]=round(100*(sub["ESCMAE"]==code).mean(),1)
    for uf in ["GO","MT","MS","DF"]:
        r[f"Estado_{uf}_pct"]=round(100*(sub["UF"]==uf).mean(),1)
    r["N_sens"]=len(subs)
    for code,lab in L.CONS_LABEL.items():
        r[f"Cons_{lab}_pct"]=round(100*(subs["CONSULTAS"]==code).mean(),1)
    r["MESPRENAT_1trim_pct"]=round(100*(subs["MESPRENAT"].between(1,3)).mean(),1)
    return r
t1=[tab1_row(prim,sens,g) for g in ["Branca","Parda","Preta","Indigena","TOTAL"]]
write_csv(pd.DataFrame(t1), "tabela1_base_B.csv")

# ── B: categorical vs linear ────────────────────────────────────────
log("[B] model_comparison_categorical_linear...")
sens["esc_lin"]=sens[EDU_VAR].astype(float); sens["cons_lin"]=sens["CONSULTAS"].astype(float)
prim["esc_lin"]=prim[EDU_VAR].astype(float)
mc=[]
mc+=race_rows(fit(prim,"C(raca, Treatment('Branca')) + C(idade_cat) + esc_lin + C(ano_cat) + C(uf_cat)"),"M5_Lin_Esc_artigo",N_PRIM)
base8="C(raca, Treatment('Branca')) + C(idade_cat) + {esc} + C(ano_cat) + C(uf_cat) + {cons} + C(parid_cat) + C(estciv_cat)"
mc+=race_rows(fit(sens,base8.format(esc="esc_lin",cons="cons_lin")),"M8_Lin_Esc_Lin_Cons",N_SENS)
mc+=race_rows(fit(sens,base8.format(esc="C(esc_cat)",cons="cons_lin")),"M8_Cat_Esc_Lin_Cons",N_SENS)
mc+=race_rows(fit(sens,base8.format(esc="esc_lin",cons="C(cons_cat)")),"M8_Lin_Esc_Cat_Cons",N_SENS)
mc+=race_rows(fit(sens,base8.format(esc="C(esc_cat)",cons="C(cons_cat)")),"M8_Cat_Esc_Cat_Cons",N_SENS)
write_csv(pd.DataFrame(mc), "model_comparison_categorical_linear.csv")

# ── C: prevalência raça×estado, interação (LRT), estratificado, temporal
log("[C] prevalência raça×estado + interação + estratificado + temporal...")
prev=[]
for uf in ["DF","GO","MS","MT"]:
    for g in ["Branca","Parda","Preta","Indigena"]:
        sub=prim[(prim["UF"]==uf)&(prim["raca"]==g)]
        prev.append(dict(ESTADO=uf,RACA=g,N=len(sub),PTB_n=int(sub["PTB"].sum()),
                         PTB_pct=round(100*sub["PTB"].mean(),2)))
prevdf=pd.DataFrame(prev); write_csv(prevdf,"ptb_prevalencia_raca_estado.csv")
piv=prevdf.pivot(index="ESTADO",columns="RACA",values="PTB_pct")[["Branca","Parda","Preta","Indigena"]].reset_index()
write_csv(piv,"ptb_prevalencia_raca_estado_pivot.csv")
# LRT interação raça×UF sobre M5
m5_noint=fit(prim,RHS["M5"])
m5_int=fit(prim,RHS["M5"]+" + C(raca, Treatment('Branca')):C(uf_cat)")
lrt=2*(m5_int.llf-m5_noint.llf); ddf=len(m5_int.params)-len(m5_noint.params)
pval=stats.chi2.sf(lrt,ddf)
write_csv(pd.DataFrame([dict(LRT_chi2=round(lrt,2),df=ddf,p_value=round(pval,4),
          AIC_sem_int=round(m5_noint.aic,1),AIC_com_int=round(m5_int.aic,1))]),
          "interaction_test_raca_estado.csv")
# estratificado MS e MT (M5 e M8). Em estrato, remover C(uf_cat)
strat=[]
for uf in ["MS","MT"]:
    dp=prim[prim["UF"]==uf]; dsv=sens[sens["UF"]==uf]
    rhs5="C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat)"
    rhs8=rhs5+" + C(cons_cat) + C(parid_cat) + C(estciv_cat)"
    strat+=race_rows(fit(dp,rhs5),f"M5_{uf}",len(dp))
    strat+=race_rows(fit(dsv,rhs8),f"M8_{uf}",len(dsv))
write_csv(pd.DataFrame(strat),"stratified_MS_MT.csv")
# temporal: por ano (M5 dentro do ano, sem C(ano)) + blocos
temp=[]
rhs_year="C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(uf_cat)"
for y in range(2015,2025):
    dy=prim[prim["ANO"]==y]
    rows=race_rows(fit(dy,rhs_year),f"Ano_{y}",len(dy))
    for r in rows: r["Ano"]=float(y)
    temp+=rows
for label,yrs in [("Pre-pandemia(2015-2019)",range(2015,2020)),
                  ("Pandemia(2020-2022)",range(2020,2023)),
                  ("Pos-pandemia(2023-2024)",range(2023,2025))]:
    db=prim[prim["ANO"].isin(list(yrs))]
    rows=race_rows(fit(db,RHS["M5"]),label,len(db))
    for r in rows: r["Ano"]=""
    temp+=rows
pd.DataFrame(temp).to_csv(TAB/"temporal_trends.csv",index=False)
log("  -> temporal_trends.csv")

# ── D: sensibilidade sem-2024 + singletons 8 modelos ────────────────
log("[D] sem-2024 + singletons...")
s24=[]
for tag,dd,base in [("sem2024",None,None)]:
    pass
prim_no24=prim[prim["ANO"]!=2024]; sens_no24=sens[sens["ANO"]!=2024]
for mname,d,lab in [("M5",prim_no24,"M5_sem2024"),("M8",sens_no24,"M8_sem2024")]:
    s24+=race_rows(fit(d,RHS[mname]),lab,len(d))
for mname,d,lab in [("M5",prim,"M5_com2024"),("M8",sens,"M8_com2024")]:
    s24+=race_rows(fit(d,RHS[mname]),lab,len(d))
write_csv(pd.DataFrame(s24),"sensitivity_excl2024.csv")
# singletons (GRAVIDEZ==1)
ps=prim[prim["GRAVIDEZ"]==1]; ss=sens[sens["GRAVIDEZ"]==1]
log(f"    singletons primária={len(ps):,} sensib={len(ss):,}")
sg=[]
for mname in ["M1","M2","M3","M4","M5","M6","M7","M8"]:
    d=ps if mname in("M1","M2","M3","M4","M5") else ss
    label={"M1":"M1_Crude","M2":"M2_+Idade","M3":"M3_+Esc","M4":"M4_+Ano",
           "M5":"M5_PRIMARY","M6":"M6_+Prenat","M7":"M7_+Paridade","M8":"M8_FULL"}[mname]
    sg+=race_rows(fit(d,RHS[mname]),label,len(d))
write_csv(pd.DataFrame(sg),"suplementar_singletons_8modelos.csv")

# ── E: missing por variável×grupo + incluídos×excluídos (AUDIT2) ────
log("[E] missing + incluídos×excluídos (AUDIT2)...")
pool=full[full["_raca_valida"]].copy()
pool["raca"]=pool["RACACORMAE"].map(L.RACA_LABEL)
varmap=[("Idade gestacional","SEMAGESTAC",lambda s:s.isna()|~s.between(22,44)),
        ("Raca/cor materna","RACACORMAE",lambda s:s.isna()),
        ("Idade materna","IDADEMAE",lambda s:s.isna()|~s.between(10,60)),
        ("Escolaridade","ESCMAE",lambda s:s.isna()|~s.between(1,5)),
        ("No consultas pre-natal","CONSULTAS",lambda s:s.isna()),
        ("Mes inicio pre-natal","MESPRENAT",lambda s:s.isna()|(s==99)),
        ("Paridade","QTDFILVIVO",lambda s:s.isna()),
        ("Estado civil","ESTCIVMAE",lambda s:s.isna()),
        ("Municipio residencia","CODMUNRES",lambda s:s.isna())]
miss=[]
for vlabel,col,fn in varmap:
    for g in ["Branca","Parda","Preta","Indigena","TOTAL"]:
        sub=pool if g=="TOTAL" else pool[pool["raca"]==g]
        mn=int(fn(sub[col]).sum())
        miss.append(dict(Variavel=vlabel,Grupo=g,N=len(sub),Missing_n=mn,
                         Missing_pct=round(100*mn/len(sub),2)))
write_csv(pd.DataFrame(miss),"missing_por_variavel_grupo.csv")

# incluídos×excluídos — máscaras numpy limpas (sem nullable-boolean)
full_d=full.copy()
full_d["raca_any"]=full_d["RACACORMAE"].map(L.RACA_LABEL)
full_d["is_ptb"]=np.where(full_d["SEMAGESTAC"].notna(), (full_d["SEMAGESTAC"]<37), np.nan)
inc = full_d["_incluido_primaria"].fillna(False).to_numpy(dtype=bool)
rv  = full_d["_raca_valida"].fillna(False).to_numpy(dtype=bool)
def grp_stats(mask):
    s=full_d.loc[mask]; rd=s["raca_any"].value_counts(normalize=True)*100
    return dict(N=len(s),PTB_pct=round(100*np.nanmean(s["is_ptb"]),2),
                PTB_definido_em=f"{int(s['is_ptb'].notna().sum()):,} c/ IG válida",
                Idade_media=round(s["IDADEMAE"].mean(),1),
                Raca_Branca_pct=round(rd.get("Branca",0),1),Raca_Parda_pct=round(rd.get("Parda",0),1),
                Raca_Preta_pct=round(rd.get("Preta",0),1),Raca_Indigena_pct=round(rd.get("Indigena",0),1),
                Raca_Amarela_Missing_pct=round(100*(full_d.loc[mask,"RACACORMAE"].isna()|(full_d.loc[mask,"RACACORMAE"]==3)).mean(),1))
rows_io=[{"Grupo":"Incluidos", **grp_stats(inc)},
         {"Grupo":"Excluidos_clarimar(so raca-valida)", **grp_stats(rv & ~inc)},
         {"Grupo":"Excluidos_FULL(cascata completa)", **grp_stats(~inc)}]
write_csv(pd.DataFrame(rows_io),"incluidos_vs_excluidos.csv")
log(f"    AUDIT2: incluídos={inc.sum():,} | excl Clarimar n={int((rv&~inc).sum()):,} | excl FULL n={int((~inc).sum()):,}")

# raca_missing_por_ano_uf (sobre TODO o CO bruto)
log("[E] raca_missing_por_ano_uf...")
rmu=[]
for y in range(2015,2025):
    for uf in ["GO","MT","MS","DF"]:
        sub=raw[(raw["ANO"]==y)&(raw["UF"]==uf)]
        nt=len(sub); miss_n=int(sub["RACACORMAE"].isna().sum())
        amar=int((sub["RACACORMAE"]==3).sum())
        rmu.append(dict(Ano=y,UF=uf,N_total=nt,RACACOR_missing_n=miss_n,
                        RACACOR_missing_pct=round(100*miss_n/nt,3),
                        Amarela_n=amar,Amarela_pct=round(100*amar/nt,3),Invalido_n=0))
write_csv(pd.DataFrame(rmu),"raca_missing_por_ano_uf.csv")

# ── F: MESPRENAT ────────────────────────────────────────────────────
log("[F] MESPRENAT...")
mesp=sens[sens["MESPRENAT"].between(1,9)].copy()  # exclui 99 e null
log(f"    mesprenat subsample={len(mesp):,}")
mesp["mesp1trim"]=(mesp["MESPRENAT"]<=3).astype(int)
p1=[]
for g in ["Branca","Parda","Preta","Indigena"]:
    sub=sens[sens["raca"]==g]
    valid=sub[sub["MESPRENAT"].between(1,9)]
    p1.append(dict(Grupo=g,N=len(valid),Inicio_1trim_pct=round(100*(valid["MESPRENAT"]<=3).mean(),1)))
write_csv(pd.DataFrame(p1),"prenat_1trim_por_grupo.csv")
mvc=[]
rhs_mesp="C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat) + C(mesp1trim) + C(parid_cat) + C(estciv_cat)"
rhs_cons="C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat) + C(parid_cat) + C(estciv_cat)"
mvc+=race_rows(fit(mesp,rhs_mesp),"M_MESPRENAT_1trim",len(mesp))
mvc+=race_rows(fit(mesp,rhs_cons),"M_CONSULTAS_categorica",len(mesp))
write_csv(pd.DataFrame(mvc),"mesprenat_vs_consultas.csv")

# ── n_summary ───────────────────────────────────────────────────────
log("[n_summary]...")
ns=[("primaria_M1-5",N_PRIM,"Complete cases race,IG,age,edu,year,state,muni"),
    ("sensibilidade_M6-8",N_SENS,"+ prenatal,parity,marital (null-complete)"),
    ("singletons_primaria",len(ps),"Primary, GRAVIDEZ==1"),
    ("singletons_sensib",len(ss),"Sensitivity, GRAVIDEZ==1"),
    ("mesprenat_subsample",len(mesp),"Sensitivity, MESPRENAT 1-9"),
    ("sem2024_primaria",len(prim_no24),"Primary excl 2024"),
    ("sem2024_sensib",len(sens_no24),"Sensitivity excl 2024"),
    ("2024_contribuicao",int((prim["ANO"]==2024).sum()),"2024 records in primary"),
    ("MS_M5_n",len(prim[prim["UF"]=="MS"]),"MS primary"),
    ("MS_M8_n",len(sens[sens["UF"]=="MS"]),"MS sensitivity"),
    ("MT_M5_n",len(prim[prim["UF"]=="MT"]),"MT primary"),
    ("MT_M8_n",len(sens[sens["UF"]=="MT"]),"MT sensitivity")]
m8_ind=round(np.exp(fits["M8"].params[[k for k in fits["M8"].params.index if 'Indigena' in k][0]]),3)
ns.append(("OR_M8_canonico_Indig",m8_ind,"OR M8 Indigenous vs White (ESC cat + CONS cat + ANO cat)"))
nsdf=pd.DataFrame(ns,columns=["Amostra","n","Descricao"])
write_csv(nsdf,"n_summary.csv")
log(f"    >>> OR M8 indígena canônico = {m8_ind}  (Clarimar 1.322)")

log("="*70); log(f"CONCLUÍDO em {(time.time()-t0)/60:.1f} min"); log("="*70)
(LOGD/f"build_baseB_{STAMP}.log").write_text("\n".join(LOG))
print("OK_BUILD_DONE")
