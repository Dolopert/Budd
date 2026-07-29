# -*- coding: utf-8 -*-
"""Wooldridge test for serial correlation in panel data (Drukker, 2003)
บน balanced panel 200 obs (10 บริษัท x 20 ไตรมาส ไม่มีช่องว่าง จึง first-difference ได้)
H0: ไม่มี autocorrelation  (สัมประสิทธิ์ e_lag = -0.5)"""
import os, numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats

CSV = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "metrics_all.csv"))
df = pd.read_csv(CSV, encoding="utf-8-sig")
df["q"] = df["quarter"].str[1].astype(int)
df["t"] = (df["year"]-2564)*4 + df["q"]
df["ROA"] = df["ROA"].astype(float)*100
df["ROE"] = df["ROE"].astype(float)*100
df["CCC"] = df["CCC"].astype(float)
df["SIZE"] = np.log(df["total_assets_end"].astype(float))
df["LEV"] = (df["total_assets_end"]-df["total_equity_end"])/df["total_equity_end"]
for k in (2,3,4): df[f"Q{k}"] = (df.q==k).astype(int)
df = df.sort_values(["ticker","t"]).reset_index(drop=True)

XVARS = ["SIZE","LEV","Q2","Q3","Q4"]     # time-varying (DIV ถูก first-diff ลบทิ้ง)

def wooldridge(dv):
    d = df.copy()
    g = d.groupby("ticker")
    # first difference ภายในบริษัท
    dd = pd.DataFrame({c: g[c].diff() for c in [dv]+XVARS})
    dd["ticker"] = d["ticker"]
    dd = dd.dropna()
    y = dd[dv].values
    X = dd[XVARS].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)   # ไม่มี const (first-diff)
    e = y - X @ beta
    dd = dd.assign(e=e)
    # lag e ภายในบริษัท
    dd["e_lag"] = dd.groupby("ticker")["e"].shift(1)
    reg = dd.dropna(subset=["e","e_lag"])
    m = sm.OLS(reg["e"], reg["e_lag"]).fit(
        cov_type="cluster", cov_kwds={"groups": reg["ticker"]})
    coef = m.params["e_lag"]; se = m.bse["e_lag"]
    Fstat = ((coef - (-0.5))/se)**2
    nclust = reg["ticker"].nunique()
    p = 1 - stats.f.cdf(Fstat, 1, nclust-1)
    return coef, Fstat, p

print(f"{'ตัวแปรตาม':10} {'coef e_lag':>11} {'(ควร=-0.5)':>10} {'F':>8} {'p-value':>9}  ผล")
print("-"*62)
for dv in ["CCC","ROA","ROE"]:
    coef, F, p = wooldridge(dv)
    res = "มี autocorrelation" if p < 0.05 else "ไม่พบ autocorrelation"
    print(f"{dv:10} {coef:>11.3f} {'-0.5':>10} {F:>8.2f} {p:>9.4f}  {res}")
print("\n(H0: ไม่มี serial correlation; ถ้า p<0.05 = ปฏิเสธ = มี autocorrelation)")
