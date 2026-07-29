# -*- coding: utf-8 -*-
"""รัน regression รายไตรมาส vs รวมเป็นรายปี — ดูว่า DIV เปลี่ยนไหม
ประเด็น: DIV เป็น between-firm (time-invariant) จำนวนบริษัทคงที่ 10 ไม่ว่ารายไตรมาสหรือรายปี"""
import os, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
from linearmodels.panel import RandomEffects
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
CSV = os.path.normpath(os.path.join(HERE, "..", "output", "metrics_all.csv"))
INTL = {"MINT", "SHR", "DUSIT"}

df = pd.read_csv(CSV, encoding="utf-8-sig")
df = df[df["rev_low"] != "Y"].copy()                    # ตัดโควิด
df["q"] = df["quarter"].str[1].astype(int)
df["DIV"] = df["ticker"].isin(INTL).astype(int)
for c in ["revenue","cogs","net_profit","total_assets_end","total_equity_end","CCC","ROA","ROE"]:
    df[c] = df[c].astype(float)

# ---------- รวมเป็นรายปี ----------
rows = []
for (tk, yr), g in df.groupby(["ticker","year"]):
    if len(g) < 4:      # ต้องครบ 4 ไตรมาสถึงรวมเป็นปีได้
        continue
    ye = g[g.q == 4].iloc[0]      # ยอดปลายปี (Q4)
    np_y = g["net_profit"].sum()
    rows.append(dict(ticker=tk, year=yr,
        DIV=int(tk in INTL),
        ROA=np_y / ye["total_assets_end"] * 100,
        ROE=np_y / ye["total_equity_end"] * 100,
        CCC=g["CCC"].mean(),
        SIZE=np.log(ye["total_assets_end"]),
        LEV=(ye["total_assets_end"] - ye["total_equity_end"]) / ye["total_equity_end"]))
ann = pd.DataFrame(rows)
print(f"รายปี: {len(ann)} obs, {ann.ticker.nunique()} บริษัท x {ann.year.nunique()} ปี "
      f"(ต่างประเทศ {ann.DIV.sum()//ann.year.nunique()} บริษัท)")

def run_re(d, dv, tvar):
    dd = d.dropna(subset=[dv,"DIV","SIZE","LEV"]).set_index(["ticker", tvar])
    X = sm.add_constant(dd[["DIV","SIZE","LEV"]])
    return RandomEffects(dd[dv], X).fit(cov_type="clustered", cluster_entity=True)

# quarterly panel (180 obs) เทียบ
dq = df.copy(); dq["t"] = (dq["year"]-2564)*4 + dq["q"]

print("\n" + "="*70)
print(f"{'':22}| {'รายไตรมาส (180 obs)':>22} | {'รายปี (50 obs)':>20}")
print(f"{'ตัวแปรตาม / DIV':22}| {'coef':>12}{'p':>10} | {'coef':>10}{'p':>10}")
print("-"*70)
for dv in ["CCC","ROA","ROE"]:
    mq = run_re(dq, dv, "t")
    ma = run_re(ann, dv, "year")
    cq, pq = mq.params["DIV"], mq.pvalues["DIV"]
    ca, pa = ma.params["DIV"], ma.pvalues["DIV"]
    sq = "*" if pq<0.05 else " "; sa = "*" if pa<0.05 else " "
    print(f"{dv+' : DIV':22}| {cq:>11.3f}{sq}{pq:>10.3f} | {ca:>9.3f}{sa}{pa:>10.3f}")
print("="*70)
print("(ทั้งคู่ใช้ RE + clustered SE; รายปีไม่ต้องมี dummy ฤดูกาล)")
