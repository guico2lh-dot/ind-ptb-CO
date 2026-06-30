#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy","matplotlib"]
# ///
"""08_national_figure.py — figura 600dpi: prevalência de PTB indígena vs branca por UF."""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys; sys.path.insert(0,str(Path(__file__).parent)); import lib_baseB as L

_PROJ=Path(__file__).resolve().parents[1]
TAB=_PROJ/"outputs/nacional_indigena/tables"
FIG=_PROJ/"outputs/nacional_indigena/figures"; FIG.mkdir(parents=True,exist_ok=True)
d=pd.read_csv(TAB/"prevalencia_indigena_branca_por_uf.csv",comment="#")
piv=d.pivot(index="UF",columns="Grupo",values="PTB_pct")
nind=d[d["Grupo"]=="Indigena"].set_index("UF")["N"]
piv=piv.loc[nind.sort_values(ascending=False).index]      # ordenar por volume indígena
piv=piv.head(20)[::-1]
fig,ax=plt.subplots(figsize=(8,7))
y=np.arange(len(piv))
ax.hlines(y,piv["Branca"],piv["Indigena"],color="#bbb",lw=2,zorder=1)
ax.scatter(piv["Branca"],y,color="#1f77b4",s=40,label="Branca",zorder=2)
ax.scatter(piv["Indigena"],y,color="#d62728",s=40,label="Indígena",zorder=2)
ax.set_yticks(y); ax.set_yticklabels([f"{uf} ({L.REGIAO5.get(uf,'')[:2]})" for uf in piv.index])
ax.axvline(11.3,color="#1f77b4",ls=":",lw=1,alpha=.6)
ax.set_xlabel("Prevalência de PTB <37 sem (%)"); ax.legend(loc="lower right")
ax.set_title("PTB indígena vs branca por UF (20 maiores populações indígenas), Brasil 2015–2024")
fig.tight_layout()
p=FIG/"fig01_prevalencia_indigena_uf_v1_20260627.png"; fig.savefig(p,dpi=600,bbox_inches="tight")
print("salvo",p)
