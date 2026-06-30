#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy","matplotlib"]
# ///
"""05_figures.py — figuras 600 dpi (nome versionado) a partir das tabelas da Base B."""
import sys
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_suf = "" if (len(sys.argv)<2 or sys.argv[1]=="ESCMAE") else "_escmae2010"
_PROJ=Path(__file__).resolve().parents[1]
TAB=_PROJ/f"outputs/centro_oeste{_suf}/tables"
FIG=_PROJ/f"outputs/centro_oeste{_suf}/figures"
FIG.mkdir(parents=True,exist_ok=True)
STAMP="20260627"
def rd(p): return pd.read_csv(p,comment="#")

# ── Fig 1: OR (logística cluster) vs PR (Poisson robusto) — por grupo, M1/M5/M8
o=rd(TAB/"or_vs_rr_comparison.csv")
groups=["Parda","Preta","Indigena"]; models=["M1","M5","M8"]
fig,axes=plt.subplots(1,3,figsize=(11,4),sharex=True)
for ax,m in zip(axes,models):
    log=o[(o["Modelo"]==f"{m}_Logistic_cluster")].set_index("Grupo")
    poi=o[(o["Modelo"]==f"{m}_Poisson_robust")].set_index("Grupo")
    y=np.arange(len(groups))
    for i,g in enumerate(groups):
        if g in log.index:
            ax.plot([log.loc[g,"CI_95_low"],log.loc[g,"CI_95_high"]],[i+0.12]*2,"-",color="#1f77b4",lw=2)
            ax.plot(log.loc[g,"OR"],i+0.12,"o",color="#1f77b4",ms=6,label="OR (logística, cluster)" if i==0 else "")
        if g in poi.index:
            ax.plot([poi.loc[g,"CI_95_low"],poi.loc[g,"CI_95_high"]],[i-0.12]*2,"-",color="#d62728",lw=2)
            ax.plot(poi.loc[g,"RR"],i-0.12,"s",color="#d62728",ms=6,label="PR (Poisson, robusto)" if i==0 else "")
    ax.axvline(1.0,color="grey",ls=":",lw=1)
    ax.set_yticks(y); ax.set_yticklabels(groups); ax.set_title(m); ax.set_xlabel("OR / PR (vs Branca)")
    ax.invert_yaxis()
axes[0].legend(fontsize=7,loc="lower right")
fig.suptitle("PTB (<37 sem) — OR vs PR por grupo racial, Centro-Oeste 2015–2024 (Base B, ESCMAE)")
fig.tight_layout()
p1=FIG/f"fig01_OR_vs_RR_v1_{STAMP}.png"; fig.savefig(p1,dpi=600,bbox_inches="tight"); plt.close(fig)
print("salvo",p1)

# ── Fig 2: tendência temporal do OR indígena (por ano) ──────────────
t=rd(TAB/"temporal_trends.csv")
ti=t[(t["Grupo"]=="Indigena")&(t["Modelo"].str.startswith("Ano_"))].copy()
ti["ano"]=ti["Ano"].astype(float).astype(int); ti=ti.sort_values("ano")
fig,ax=plt.subplots(figsize=(8,4.5))
ax.plot(ti["ano"],ti["OR"],"-o",color="#2ca02c",lw=2)
ax.fill_between(ti["ano"],ti["CI_95_low"],ti["CI_95_high"],color="#2ca02c",alpha=0.18)
ax.axhline(1.0,color="grey",ls=":",lw=1)
ax.set_xticks(ti["ano"]); ax.set_xlabel("Ano de nascimento"); ax.set_ylabel("OR indígena vs Branca (ajustado idade+esc+UF)")
ax.set_title("Tendência temporal do OR de PTB em indígenas — Centro-Oeste (Base B, ESCMAE)")
fig.tight_layout()
p2=FIG/f"fig02_temporal_indigena_v1_{STAMP}.png"; fig.savefig(p2,dpi=600,bbox_inches="tight"); plt.close(fig)
print("salvo",p2)
