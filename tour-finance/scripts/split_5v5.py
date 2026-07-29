# -*- coding: utf-8 -*-
"""ถ้าแบ่ง 5v5 แทน 3v7 ผลจะต่างไหม — ทดสอบความไวต่อการจัดกลุ่ม (classification sensitivity)"""
import os, warnings, numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm
from linearmodels.panel import RandomEffects
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
CSV = os.path.normpath(os.path.join(HERE, "..", "output", "metrics_all.csv"))

df = pd.read_csv(CSV, encoding="utf-8-sig")
df = df[df["rev_low"] != "Y"].copy()
df["q"] = df["quarter"].str[1].astype(int)
df["t"] = (df["year"]-2564)*4 + df["q"]
df["ROA"] = df["ROA"].astype(float)*100
df["ROE"] = df["ROE"].astype(float)*100
df["CCC"] = df["CCC"].astype(float)
df["SIZE"] = np.log(df["total_assets_end"].astype(float))
df["LEV"] = (df["total_assets_end"]-df["total_equity_end"])/df["total_equity_end"]
for k in (2,3,4): df[f"Q{k}"] = (df.q==k).astype(int)

SCEN = {
    "ปัจจุบัน 3v7": {"MINT","SHR","DUSIT"},
    "5v5 (+CENTEL,ERW)": {"MINT","SHR","DUSIT","CENTEL","ERW"},
}

def firm_ttest(d, dv):
    a = d[d.DIV==1].groupby("ticker")[dv].mean()
    b = d[d.DIV==0].groupby("ticker")[dv].mean()
    t,p = stats.ttest_ind(a,b,equal_var=False)
    return a.mean(), b.mean(), p

def re_div(d, dv):
    dd = d.dropna(subset=[dv,"DIV","SIZE","LEV"]).set_index(["ticker","t"])
    X = sm.add_constant(dd[["DIV","SIZE","LEV","Q2","Q3","Q4"]])
    m = RandomEffects(dd[dv], X).fit(cov_type="clustered", cluster_entity=True)
    return m.params["DIV"], m.pvalues["DIV"]

for name, intl in SCEN.items():
    d = df.copy(); d["DIV"] = d.ticker.isin(intl).astype(int)
    nintl = d[d.DIV==1].ticker.nunique(); ndom = d[d.DIV==0].ticker.nunique()
    print("\n" + "="*72)
    print(f"[{name}]  ต่างประเทศ {nintl} บริษัท : ในไทย {ndom} บริษัท")
    print(f"  กลุ่มต่างประเทศ = {sorted(intl)}")
    print(f"  {'ตัวแปร':5} {'ต่างปท.เฉลี่ย':>12} {'ในไทยเฉลี่ย':>12} {'t-test p':>10} | {'DIV coef(RE)':>12} {'p':>8}")
    for dv in ["CCC","ROA","ROE"]:
        ma, mb, pt = firm_ttest(d, dv)
        c, p = re_div(d, dv)
        st = "*" if pt<0.05 else " "; sr="*" if p<0.05 else " "
        print(f"  {dv:5} {ma:>12.2f} {mb:>12.2f} {pt:>9.3f}{st} | {c:>12.3f} {p:>7.3f}{sr}")
print("="*72)
print("(* = p<0.05; RE = Random Effects + clustered SE + คุมฤดูกาล/SIZE/LEV)")
