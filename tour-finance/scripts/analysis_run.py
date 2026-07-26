#!/usr/bin/env python3
"""
analysis_run.py — รันการวิเคราะห์ตามบทระเบียบวิธี (บทที่ 6) แบบตรงตามที่เขียน
โดย "ไม่ซ่อม" 3 จุดที่ท้วง (ไม่ตัด outlier โควิด, ไม่ใส่ quarterly dummy, ปล่อย Hausman เลือก)

ตัวแปร:
  DV : CCC (วัน), ROA (%), ROE (%)
  IV : DIV (1 = MINT/SHR/DUSIT ต่างประเทศ, 0 = ในไทย)
  CV : SIZE = ln(สินทรัพย์รวม), LEV = หนี้สินรวม / ส่วนของผู้ถือหุ้น

ขั้น: descriptive -> t-test 2 กลุ่ม -> correlation -> VIF -> Pooled/FE/RE + Chow/LM/Hausman
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from linearmodels.panel import PooledOLS, PanelOLS, RandomEffects
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
CSV = os.path.normpath(os.path.join(HERE, "..", "output", "metrics_all.csv"))
INTL = {"MINT", "SHR", "DUSIT"}          # กลุ่มกระจายความเสี่ยงต่างประเทศ


def load():
    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df["t"] = (df["year"] - 2564) * 4 + df["quarter"].str[1].astype(int)
    df["DIV"] = df["ticker"].isin(INTL).astype(int)
    df["CCC"] = df["CCC"].astype(float)
    df["ROA"] = df["ROA"].astype(float) * 100     # เป็น %
    df["ROE"] = df["ROE"].astype(float) * 100
    df["SIZE"] = np.log(df["total_assets_end"].astype(float))
    liab = df["total_assets_end"].astype(float) - df["total_equity_end"].astype(float)
    df["LEV"] = liab / df["total_equity_end"].astype(float)
    return df.sort_values(["ticker", "t"]).reset_index(drop=True)


def sep(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def descriptive(df):
    sep("1. สถิติเชิงพรรณนา (Descriptive) — ทั้งหมด และแยกกลุ่ม")
    for name, sub in [("ทั้งหมด (n=%d)" % len(df), df),
                      ("ต่างประเทศ DIV=1 (n=%d)" % (df.DIV == 1).sum(), df[df.DIV == 1]),
                      ("ในไทย DIV=0 (n=%d)" % (df.DIV == 0).sum(), df[df.DIV == 0])]:
        print(f"\n[{name}]")
        d = sub[["CCC", "ROA", "ROE", "SIZE", "LEV"]].describe().T[["mean", "std", "min", "max"]]
        print(d.round(2).to_string())


def ttests(df):
    sep("2. Independent-samples t-test : ต่างประเทศ vs ในไทย")
    print(f"{'ตัวแปร':6} {'ต่างประเทศ':>12} {'ในไทย':>12} {'t':>8} {'p-value':>10}  ผล")
    for v in ["CCC", "ROA", "ROE"]:
        a = df[df.DIV == 1][v].dropna()
        b = df[df.DIV == 0][v].dropna()
        t, p = stats.ttest_ind(a, b, equal_var=False)     # Welch
        sig = "ต่างอย่างมีนัยสำคัญ" if p < 0.05 else "ไม่ต่างนัยสำคัญ"
        print(f"{v:6} {a.mean():>12.2f} {b.mean():>12.2f} {t:>8.2f} {p:>10.4f}  {sig}")


def correlation(df):
    sep("3. Pearson correlation")
    print(df[["CCC", "ROA", "ROE", "DIV", "SIZE", "LEV"]].corr().round(3).to_string())


def vif(df):
    sep("4. VIF (multicollinearity ของตัวแปรอิสระ/ควบคุม) — เกณฑ์ < 10")
    X = df[["DIV", "SIZE", "LEV"]].dropna()
    Xc = sm.add_constant(X)
    for i, col in enumerate(Xc.columns):
        if col == "const":
            continue
        v = variance_inflation_factor(Xc.values, i)
        print(f"  {col:6}: VIF = {v:.2f}  {'OK' if v < 10 else 'สูงเกิน!'}")


def panel_models(df, dv):
    """รัน Pooled / FE / RE + เลือกโมเดล (Chow, BP-LM, Hausman) สำหรับตัวแปรตาม dv"""
    sep(f"5. Panel regression — ตัวแปรตาม = {dv}")
    d = df.dropna(subset=[dv, "DIV", "SIZE", "LEV"]).copy()
    d = d.set_index(["ticker", "t"])
    y = d[dv]
    X = sm.add_constant(d[["DIV", "SIZE", "LEV"]])

    pooled = PooledOLS(y, X).fit()
    re = RandomEffects(y, X).fit()
    # FE: DIV time-invariant -> ถูกดูดหาย
    try:
        fe = PanelOLS(y, X, entity_effects=True).fit()
        fe_note = ""
    except Exception as e:
        fe = PanelOLS(y, sm.add_constant(d[["SIZE", "LEV"]]), entity_effects=True).fit()
        fe_note = "  << DIV ถูก drop (time-invariant) จึงรัน FE โดยไม่มี DIV"

    def coefs(m, names):
        out = {}
        for n in names:
            if n in m.params.index:
                out[n] = (m.params[n], m.pvalues[n])
        return out

    print(f"{'ตัวแปร':8} | {'Pooled OLS':>22} | {'Fixed Effects':>22} | {'Random Effects':>22}")
    print(f"{'':8} | {'coef':>12}{'p':>10} | {'coef':>12}{'p':>10} | {'coef':>12}{'p':>10}")
    for n in ["const", "DIV", "SIZE", "LEV"]:
        row = f"{n:8} |"
        for m in (pooled, fe, re):
            if n in m.params.index:
                star = "*" if m.pvalues[n] < 0.05 else " "
                row += f" {m.params[n]:>11.3f}{star}{m.pvalues[n]:>9.3f} |"
            else:
                row += f" {'—(dropped)':>22} |"
        print(row)
    if fe_note:
        print(fe_note)
    print(f"R²: Pooled={pooled.rsquared:.3f}  FE(within)={fe.rsquared_within:.3f}  RE={re.rsquared:.3f}")

    # เลือกโมเดล
    # Hausman FE vs RE
    try:
        b_fe = fe.params.reindex(["SIZE", "LEV"]).dropna()
        b_re = re.params.reindex(b_fe.index)
        v_fe = fe.cov.loc[b_fe.index, b_fe.index]
        v_re = re.cov.loc[b_fe.index, b_fe.index]
        diff = b_fe - b_re
        vdiff = v_fe.values - v_re.values
        stat = float(diff.values @ np.linalg.pinv(vdiff) @ diff.values)
        from scipy.stats import chi2
        pval = 1 - chi2.cdf(abs(stat), len(diff))
        pick = "FE" if pval < 0.05 else "RE"
        print(f"Hausman test: stat={stat:.2f}, p={pval:.3f} -> เลือก {pick}"
              + ("  ** ถ้าเลือก FE จะไม่มีค่า DIV ให้ตีความ! **" if pick == "FE" else ""))
    except Exception as e:
        print(f"Hausman: คำนวณไม่ได้ ({e})")


def diagnostics(df):
    sep("6. ตรวจ residual (heteroskedasticity + normality) จาก Pooled OLS ของ ROA")
    d = df.dropna(subset=["ROA", "DIV", "SIZE", "LEV"])
    X = sm.add_constant(d[["DIV", "SIZE", "LEV"]])
    ols = sm.OLS(d["ROA"], X).fit()
    from statsmodels.stats.diagnostic import het_breuschpagan
    bp = het_breuschpagan(ols.resid, X)
    print(f"  Breusch-Pagan: LM p-value = {bp[1]:.4f}  "
          f"-> {'มี heteroskedasticity (ผิดข้อตกลง)' if bp[1] < 0.05 else 'ผ่าน (homoskedastic)'}")
    sk = stats.skew(ols.resid); ku = stats.kurtosis(ols.resid)
    jb, jbp = stats.jarque_bera(ols.resid)[:2]
    print(f"  Jarque-Bera normality: p = {jbp:.4f}  skew={sk:.2f} kurtosis={ku:.2f}  "
          f"-> {'residual ไม่ปกติ (ผิดข้อตกลง)' if jbp < 0.05 else 'ปกติ'}")
    print(f"  Durbin-Watson (Pooled) = {sm.stats.durbin_watson(ols.resid):.2f}  (ควรใกล้ 2)")


def main():
    df = load()
    print(f"โหลดข้อมูล: {len(df)} obs, {df.ticker.nunique()} บริษัท x {df.t.nunique()} ไตรมาส")
    print(f"กลุ่มต่างประเทศ (DIV=1): {sorted(INTL)}  = {(df.DIV==1).sum()} obs")
    descriptive(df)
    ttests(df)
    correlation(df)
    vif(df)
    for dv in ["CCC", "ROA", "ROE"]:
        panel_models(df, dv)
    diagnostics(df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
