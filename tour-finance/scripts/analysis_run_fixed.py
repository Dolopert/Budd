#!/usr/bin/env python3
"""
analysis_run_fixed.py — รันเวอร์ชัน "ซ่อม 3 จุด" เทียบกับเวอร์ชัน as-is

การซ่อม:
  1. ใช้ Random Effects (RE) เป็นหลัก — เพราะ DIV เป็น time-invariant (FE จะ drop ทิ้ง)
     + ใช้ standard error แบบ clustered ต่อบริษัท (กัน hetero/autocorrelation)
  2. ตัดค่าโควิดที่รายได้ต่ำผิดปกติ (rev_low='Y', 20 จุด) -> เหลือ 180 obs
  3. ใส่ quarterly dummy (Q2,Q3,Q4; Q1 = ฐาน) คุมฤดูกาล

ตัวแปรตาม: CCC, ROA(%), ROE(%)   อิสระ: DIV   ควบคุม: SIZE, LEV + ฤดูกาล
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from linearmodels.panel import RandomEffects
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
CSV = os.path.normpath(os.path.join(HERE, "..", "output", "metrics_all.csv"))
INTL = {"MINT", "SHR", "DUSIT"}


def load(drop_covid=True):
    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df["q"] = df["quarter"].str[1].astype(int)
    df["t"] = (df["year"] - 2564) * 4 + df["q"]
    df["DIV"] = df["ticker"].isin(INTL).astype(int)
    df["CCC"] = df["CCC"].astype(float)
    df["ROA"] = df["ROA"].astype(float) * 100
    df["ROE"] = df["ROE"].astype(float) * 100
    df["SIZE"] = np.log(df["total_assets_end"].astype(float))
    liab = df["total_assets_end"].astype(float) - df["total_equity_end"].astype(float)
    df["LEV"] = liab / df["total_equity_end"].astype(float)
    # ฤดูกาล: dummy Q2,Q3,Q4 (Q1 = ฐาน)
    for qq in (2, 3, 4):
        df[f"Q{qq}"] = (df["q"] == qq).astype(int)
    n0 = len(df)
    if drop_covid:
        df = df[df["rev_low"] != "Y"].copy()      # ตัดค่าโควิดรายได้ต่ำผิดปกติ
    print(f"ข้อมูล: {n0} -> {len(df)} obs (ตัดโควิด rev_low {n0-len(df)} จุด)")
    return df.sort_values(["ticker", "t"]).reset_index(drop=True)


def re_model(df, dv, seasonal=True):
    d = df.dropna(subset=[dv, "DIV", "SIZE", "LEV"]).set_index(["ticker", "t"])
    cols = ["DIV", "SIZE", "LEV"] + (["Q2", "Q3", "Q4"] if seasonal else [])
    X = sm.add_constant(d[cols])
    m = RandomEffects(d[dv], X).fit(cov_type="clustered", cluster_entity=True)
    return m


def main():
    print("=" * 74)
    print("เวอร์ชันซ่อมแล้ว: RE + ตัดค่าโควิด + ตัวแปรฤดูกาล + clustered SE")
    print("=" * 74)
    df = load(drop_covid=True)
    print(f"กลุ่มต่างประเทศ (DIV=1): {sorted(INTL)} = {(df.DIV==1).sum()} obs | "
          f"ในไทย = {(df.DIV==0).sum()} obs\n")

    # t-test ระดับบริษัท (เฉลี่ยต่อบริษัทก่อน กัน obs ไม่ independent)
    print("--- t-test ระดับบริษัท (เฉลี่ยต่อบริษัท n=3 vs 7) ---")
    firm = df.groupby("ticker").agg(DIV=("DIV", "first"),
                                    CCC=("CCC", "mean"), ROA=("ROA", "mean"), ROE=("ROE", "mean"))
    for v in ["CCC", "ROA", "ROE"]:
        a = firm[firm.DIV == 1][v]; b = firm[firm.DIV == 0][v]
        t, p = stats.ttest_ind(a, b, equal_var=False)
        print(f"  {v:4}: ต่างประเทศ={a.mean():8.2f}  ในไทย={b.mean():8.2f}  t={t:6.2f}  p={p:.3f}  "
              f"{'ต่างนัยสำคัญ' if p<0.05 else 'ไม่ต่างนัยสำคัญ'}")

    print("\n--- Random Effects regression (มี DIV, clustered SE, คุมฤดูกาล) ---")
    for dv in ["CCC", "ROA", "ROE"]:
        m = re_model(df, dv, seasonal=True)
        print(f"\n[ ตัวแปรตาม = {dv} ]   (R²={m.rsquared:.3f}, n={m.nobs})")
        print(f"  {'ตัวแปร':7} {'coef':>10} {'p-value':>9}   ผล")
        for name in ["DIV", "SIZE", "LEV", "Q2", "Q3", "Q4", "const"]:
            if name in m.params.index:
                c, p = m.params[name], m.pvalues[name]
                sig = "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.10 else ""))
                tag = ""
                if name == "DIV":
                    tag = ("  <== ต่างประเทศต่างจากในไทยอย่างมีนัยสำคัญ" if p < 0.05
                           else "  <== DIV ยังไม่มีนัยสำคัญ")
                print(f"  {name:7} {c:>10.3f} {p:>9.3f} {sig:3}{tag}")

    # เทียบ diagnostics ก่อน/หลังตัดโควิด (ROA, pooled OLS)
    print("\n--- ผลตัดโควิดต่อ residual ของ ROA (Breusch-Pagan / normality) ---")
    from statsmodels.stats.diagnostic import het_breuschpagan
    full = load(drop_covid=False)
    for label, dd in [("as-is (200 obs)", full), ("ตัดโควิดแล้ว (180 obs)", df)]:
        d = dd.dropna(subset=["ROA", "DIV", "SIZE", "LEV"])
        X = sm.add_constant(d[["DIV", "SIZE", "LEV"]])
        ols = sm.OLS(d["ROA"], X).fit()
        bp = het_breuschpagan(ols.resid, X)[1]
        jb = stats.jarque_bera(ols.resid)[1]
        print(f"  {label:20}: Breusch-Pagan p={bp:.3f} ({'ผ่าน' if bp>0.05 else 'ไม่ผ่าน'})  "
              f"Jarque-Bera p={jb:.3f} ({'ปกติ' if jb>0.05 else 'ไม่ปกติ'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
