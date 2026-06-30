#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas","numpy","pyarrow"]
# ///
"""06_fix_audit2.py — recompute limpo de incluidos_vs_excluidos (Auditoria 2)."""
import sys
from pathlib import Path
import pandas as pd, numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import lib_baseB as L

TAB=Path(__file__).resolve().parents[1]/"outputs/centro_oeste/tables"

raw=L.load_region(log=lambda *a:None)
prim,sens,steps,full=L.build_cascade(raw,log=lambda *a:None)

# máscaras limpas (numpy bool, sem nullable)
inc = full["_incluido_primaria"].fillna(False).to_numpy(dtype=bool)
rv  = full["_raca_valida"].fillna(False).to_numpy(dtype=bool)
d = full.copy()
d["raca_any"]=d["RACACORMAE"].map(L.RACA_LABEL)
d["is_ptb"]=np.where(d["SEMAGESTAC"].notna(), (d["SEMAGESTAC"]<37), np.nan)
d["amar_miss"]=(d["RACACORMAE"].isna()|(d["RACACORMAE"]==3))

NTOT=len(d)
print(f"CO total={NTOT:,} | incluídos(primária)={inc.sum():,} | "
      f"excl FULL={(~inc).sum():,} | excl Clarimar(raça-válida)={(rv&~inc).sum():,}")
assert inc.sum()==len(prim)==2156674, inc.sum()

def stats(mask, nome):
    s=d.loc[mask]; n=len(s)
    vc=s["raca_any"].value_counts(normalize=True)*100
    ptb=s["is_ptb"].mean()*100  # média ignora NaN (IG-missing)
    return dict(Grupo=nome, N=n, PTB_pct=round(ptb,2),
                PTB_definido_em=f"{int(s['is_ptb'].notna().sum()):,} c/ IG válida",
                Idade_media=round(s["IDADEMAE"].mean(),1),
                Raca_Branca_pct=round(vc.get("Branca",0),1),
                Raca_Parda_pct=round(vc.get("Parda",0),1),
                Raca_Preta_pct=round(vc.get("Preta",0),1),
                Raca_Indigena_pct=round(vc.get("Indigena",0),1),
                Raca_Amarela_Missing_pct=round(100*s["amar_miss"].mean(),1))

rows=[stats(inc,"Incluidos"),
      stats(rv&~inc,"Excluidos_clarimar(so raca-valida)"),
      stats(~inc,"Excluidos_FULL(cascata completa)")]
out=pd.DataFrame(rows)
with open(TAB/"incluidos_vs_excluidos.csv","w") as fh:
    fh.write(L.prov_line("06_fix_audit2.py")+"\n")
    out.to_csv(fh,index=False)
print(out.to_string(index=False))
