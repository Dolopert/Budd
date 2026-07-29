# -*- coding: utf-8 -*-
"""เทียบ RE: ฉบับแก้ (ฤดูกาล+clustered SE) vs ตัดฤดูกาล + SE ธรรมดา
บนกลุ่มตัวอย่างเดียวกัน 180 obs (ตัดโควิด rev_low) เพื่อแยกผลของ 2 อย่างนี้"""
import os, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
from linearmodels.panel import RandomEffects
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
CSV = os.path.normpath(os.path.join(HERE, "..", "output", "metrics_all.csv"))
INTL = {"MINT", "SHR", "DUSIT"}

df = pd.read_csv(CSV, encoding="utf-8-sig")
df["t"] = (df["year"] - 2564) * 4 + df["quarter"].str[1].astype(int)
df["DIV"] = df["ticker"].isin(INTL).astype(int)
df["ROA"] = df["ROA"].astype(float) * 100
df["ROE"] = df["ROE"].astype(float) * 100
df["CCC"] = df["CCC"].astype(float)
df["SIZE"] = np.log(df["total_assets_end"].astype(float))
df["LEV"] = (df["total_assets_end"] - df["total_equity_end"]) / df["total_equity_end"]
q = df["quarter"].str[1].astype(int)
for k in (2, 3, 4):
    df[f"Q{k}"] = (q == k).astype(int)
df = df[df["rev_low"] != "Y"].copy()                 # ตัดโควิด -> 180 obs
df = df.sort_values(["ticker", "t"]).set_index(["ticker", "t"])
print(f"n = {len(df)} obs, {df.index.get_level_values(0).nunique()} บริษัท")

def run(dv, seasonal, clustered):
    cols = ["DIV", "SIZE", "LEV"] + (["Q2", "Q3", "Q4"] if seasonal else [])
    d = df.dropna(subset=[dv] + cols)
    X = sm.add_constant(d[cols]); y = d[dv]
    if clustered:
        m = RandomEffects(y, X).fit(cov_type="clustered", cluster_entity=True)
    else:
        m = RandomEffects(y, X).fit()                # unadjusted (ธรรมดา)
    return m

def show(dv):
    print("\n" + "="*70 + f"\nตัวแปรตาม = {dv}\n" + "="*70)
    fix = run(dv, True, True)      # ฉบับแก้
    plain = run(dv, False, False)  # ตัดฤดูกาล + SE ธรรมดา
    print(f"{'ตัวแปร':7}| {'ฉบับแก้ (ฤดูกาล+clustered)':>32} | {'ตัดฤดูกาล + SE ธรรมดา':>28}")
    print(f"{'':7}| {'coef':>16}{'p':>12} | {'coef':>14}{'p':>12}")
    for n in ["DIV", "SIZE", "LEV", "const"]:
        row = f"{n:7}|"
        for m in (fix, plain):
            if n in m.params.index:
                s = "***" if m.pvalues[n]<0.01 else "**" if m.pvalues[n]<0.05 else "*" if m.pvalues[n]<0.10 else " "
                row += f" {m.params[n]:>13.3f}{s:>3}{m.pvalues[n]:>10.3f} |"
            else:
                row += f" {'-':>26} |"
        print(row)
    print(f"R²: ฉบับแก้={fix.rsquared:.3f}  ตัดฤดูกาล/ธรรมดา={plain.rsquared:.3f}")

for dv in ["CCC", "ROA", "ROE"]:
    show(dv)
