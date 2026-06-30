#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy","statsmodels","pyarrow","scipy"]
# ///
"""
07_build_national.py — Estudo NACIONAL indígena de prematuridade (PTB <37).
Contraste focal: Indígena vs Branca (modelo RACACORMAE completo, Branca ref).
Escolaridade = ESCMAE (5 níveis). UF (27) como covariável/estrato.
Reusa lib_baseB (mesma cascata travada, parametrizada por região).

Uso:
  python 07_build_national.py data     # cascata + descritivas + prevalência UF (rápido)
  python 07_build_national.py models   # + M1-M8, OR/PR indígena, temporal (pesado)
"""
import sys, time
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import lib_baseB as L

STAGE = sys.argv[1] if len(sys.argv) > 1 else "data"
EDU_VAR = "ESCMAE"
PROJ = Path(__file__).resolve().parents[1]
OUT = PROJ/"outputs/nacional_indigena"
TAB = OUT/"tables"; FIG = OUT/"figures"; LOGD = OUT/"logs"
for d in (TAB, FIG, LOGD): d.mkdir(parents=True, exist_ok=True)
CACHE = str(PROJ/".cache"); Path(CACHE).mkdir(parents=True, exist_ok=True)
LOG=[]
def log(m):
    line=f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"; print(line,flush=True); LOG.append(line)
def prov(): return L.prov_line(f"07_build_national.py [{EDU_VAR}]", regiao="Nacional (27 UFs)")
def wcsv(df,name):
    with open(TAB/name,"w") as fh: fh.write(prov()+"\n"); df.to_csv(fh,index=False)
    log(f"  -> {name} ({len(df)} linhas)")

log("="*68); log(f"NACIONAL indígena | stage={STAGE} | escolaridade={EDU_VAR}"); log("="*68)
t0=time.time()

prim_cache = f"{CACHE}/nac_primaria.parquet"; sens_cache=f"{CACHE}/nac_sensib.parquet"
if STAGE=="data" or not Path(prim_cache).exists():
    log("[load] Carregando Brasil inteiro (27 UFs)...")
    raw = L.load_region(prefixes=L.NATIONAL_PREFIXES, log=log)
    prim, sens, steps, full = L.build_cascade(raw, log=log, edu_var=EDU_VAR)
    prim = L.add_derived(prim, edu_var=EDU_VAR); sens = L.add_derived(sens, edu_var=EDU_VAR)
    prim["regiao"]=prim["UF"].map(L.REGIAO5); sens["regiao"]=sens["UF"].map(L.REGIAO5)
    prim.to_parquet(prim_cache); sens.to_parquet(sens_cache)
    # n_summary + fluxograma
    wcsv(pd.DataFrame(steps,columns=["Passo","n"]), "cascata_fluxograma.csv")
    log(f"[n] primária={len(prim):,} | sensibilidade={len(sens):,}")
    # tabela1 por raça (descritivas nacionais)
    rows=[]
    for g in ["Branca","Parda","Preta","Indigena","TOTAL"]:
        s = prim if g=="TOTAL" else prim[prim["raca"]==g]
        rows.append(dict(Grupo=g, N=len(s), PTB_n=int(s["PTB"].sum()),
                         PTB_pct=round(100*s["PTB"].mean(),2),
                         Idade_media=round(s["IDADEMAE"].mean(),1),
                         Idade_lt20_pct=round(100*(s["idade_cat"]=="<20").mean(),1),
                         Idade_ge35_pct=round(100*(s["idade_cat"]==">=35").mean(),1)))
    wcsv(pd.DataFrame(rows), "tabela1_nacional.csv")
    # prevalência indígena vs branca por UF e por região
    prev=[]
    for uf in sorted(prim["UF"].dropna().unique()):
        sub=prim[prim["UF"]==uf]
        for g in ["Branca","Indigena"]:
            sg=sub[sub["raca"]==g]
            if len(sg): prev.append(dict(UF=uf, Regiao=L.REGIAO5.get(uf), Grupo=g, N=len(sg),
                                          PTB_n=int(sg["PTB"].sum()), PTB_pct=round(100*sg["PTB"].mean(),2)))
    wcsv(pd.DataFrame(prev), "prevalencia_indigena_branca_por_uf.csv")
    # indígenas por região (volume — onde está a população)
    ind=prim[prim["raca"]=="Indigena"]
    reg=(ind.groupby("regiao").size().rename("n_indigena").reset_index()
           .sort_values("n_indigena",ascending=False))
    reg["pct_dos_indigenas"]=round(100*reg["n_indigena"]/len(ind),1)
    wcsv(reg, "indigenas_por_regiao.csv")
    log(f"[data] indígenas na primária = {len(ind):,}")
    log(f"CONCLUÍDO stage=data em {(time.time()-t0)/60:.1f} min")
    (LOGD/"build_national_data.log").write_text("\n".join(LOG))
    print("OK_DATA_DONE")

if STAGE=="models":
    # MÉTODO AGREGADO: todos os preditores são categóricos -> colapsa 25,8M linhas
    # em células e ajusta GLM binomial/Poisson ponderado. ORs/RRs e CIs model-based
    # são IDÊNTICOS ao ajuste individual, com memória mínima.
    import patsy, statsmodels.api as sm
    from statsmodels.genmod.families import Binomial, Poisson
    from scipy import stats
    log("[models] carregando amostras cacheadas (método agregado por células)...")
    prim=pd.read_parquet(prim_cache); sens=pd.read_parquet(sens_cache)
    log(f"[n] primária={len(prim):,} | sensibilidade={len(sens):,}")
    RHS={"M1":("C(raca, Treatment('Branca'))",["raca"]),
         "M5":("C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat)",
               ["raca","idade_cat","esc_cat","ano_cat","uf_cat"]),
         "M8":("C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(ano_cat) + C(uf_cat) + C(cons_cat) + C(parid_cat) + C(estciv_cat)",
               ["raca","idade_cat","esc_cat","ano_cat","uf_cat","cons_cat","parid_cat","estciv_cat"])}
    def cells(d, cols):
        g=d.groupby(cols, observed=True)["PTB"].agg(succ="sum", n="size").reset_index()
        g["fail"]=g["n"]-g["succ"]; return g
    def rowstats(res, name, n, as_rr=False):
        out=[]; ci=res.conf_int()
        for grp in ["Parda","Preta","Indigena"]:
            k=[c for c in res.params.index if f"[T.{grp}]" in c and "raca" in c]
            if not k: continue
            k=k[0]; est=np.exp(res.params[k])
            out.append(dict(Modelo=name,Grupo=grp,
                OR=("" if as_rr else round(est,3)), RR=(round(est,3) if as_rr else ""),
                CI_low=round(np.exp(ci.loc[k,0]),3),CI_high=round(np.exp(ci.loc[k,1]),3),
                p_value=round(float(res.pvalues[k]),4),N=int(n)))
        return out
    res=[]
    for mn in ["M1","M5","M8"]:
        d=prim if mn in("M1","M5") else sens; rhs,cols=RHS[mn]; n=len(d)
        t=time.time(); cell=cells(d,cols)
        X=patsy.dmatrix(rhs, cell, return_type="dataframe")
        rb=sm.GLM(cell[["succ","fail"]], X, family=Binomial()).fit()
        res+=rowstats(rb,f"{mn}_logit",n)
        # PR via Poisson com offset log(n) (RR ponto = Poisson modificada)
        rp=sm.GLM(cell["succ"], X, family=Poisson(), offset=np.log(cell["n"].astype(float))).fit()
        res+=rowstats(rp,f"{mn}_poisson_RR",n,as_rr=True)
        oi=np.exp(rb.params[[c for c in rb.params.index if 'Indigena' in c][0]])
        ri=np.exp(rp.params[[c for c in rp.params.index if 'Indigena' in c][0]])
        log(f"  {mn}: Indig OR={oi:.3f} | RR={ri:.3f} | {len(cell):,} células ({time.time()-t:.0f}s)")
    wcsv(pd.DataFrame(res),"modelos_indigena_nacional.csv")
    # cluster SE (município) p/ o cru M1 — barato via células raça×município
    cellc=cells(prim,["raca","CODMUNRES"])
    Xc=patsy.dmatrix("C(raca, Treatment('Branca'))",cellc,return_type="dataframe")
    rbc=sm.GLM(cellc[["succ","fail"]],Xc,family=Binomial()).fit(cov_type="cluster",cov_kwds={"groups":cellc["CODMUNRES"]})
    wcsv(pd.DataFrame(rowstats(rbc,"M1_logit_cluster_muni",len(prim))),"m1_cluster_se.csv")
    # temporal por ano (indígena, ajustado idade+esc+uf)
    temp=[]
    for y in range(2015,2025):
        dy=prim[prim["ANO"]==y]; cell=cells(dy,["raca","idade_cat","esc_cat","uf_cat"])
        X=patsy.dmatrix("C(raca, Treatment('Branca')) + C(idade_cat) + C(esc_cat) + C(uf_cat)",cell,return_type="dataframe")
        rb=sm.GLM(cell[["succ","fail"]],X,family=Binomial()).fit()
        rows=rowstats(rb,f"Ano_{y}",len(dy)); [row.update(Ano=y) for row in rows]; temp+=rows
    wcsv(pd.DataFrame(temp),"temporal_indigena_nacional.csv")
    log(f"CONCLUÍDO stage=models em {(time.time()-t0)/60:.1f} min")
    (LOGD/"build_national_models.log").write_text("\n".join(LOG))
    print("OK_MODELS_DONE")
