# -*- coding: utf-8 -*-
"""ถ้า DIV มีบริษัทมากกว่านี้ ผลจะต่างไหม — power analysis + simulation
บนค่าเฉลี่ยระดับบริษัท (เพราะ DIV เป็น time-invariant การทดสอบจริงคือ 3 บริษัท vs 7 บริษัท)"""
import os, numpy as np, pandas as pd
from scipy import stats

HERE = os.path.dirname(__file__)
CSV = os.path.normpath(os.path.join(HERE, "..", "output", "metrics_all.csv"))
INTL = {"MINT", "SHR", "DUSIT"}

df = pd.read_csv(CSV, encoding="utf-8-sig")
df = df[df["rev_low"] != "Y"].copy()                 # ตัดโควิด
df["DIV"] = df["ticker"].isin(INTL).astype(int)
df["ROA"] = df["ROA"].astype(float) * 100
df["ROE"] = df["ROE"].astype(float) * 100
df["CCC"] = df["CCC"].astype(float)

# ค่าเฉลี่ยต่อบริษัท (1 บริษัท = 1 จุด)
firm = df.groupby(["ticker", "DIV"])[["CCC", "ROA", "ROE"]].mean().reset_index()

print("จำนวนบริษัท: ต่างประเทศ =", (firm.DIV==1).sum(), " ในไทย =", (firm.DIV==0).sum())
print("="*76)
print(f"{'ตัวแปร':5} {'ต่างปท.เฉลี่ย':>12} {'ในไทยเฉลี่ย':>12} {'ผลต่าง':>8} {'Cohen d':>8} "
      f"{'p ตอนนี้':>9} {'n/กลุ่มที่ต้องใช้*':>16}")

from statsmodels.stats.power import TTestIndPower
analysis = TTestIndPower()

for v in ["CCC", "ROA", "ROE"]:
    a = firm[firm.DIV==1][v]; b = firm[firm.DIV==0][v]
    diff = a.mean() - b.mean()
    # pooled SD
    sp = np.sqrt(((a.std(ddof=1)**2)*(len(a)-1) + (b.std(ddof=1)**2)*(len(b)-1)) / (len(a)+len(b)-2))
    d = diff / sp
    t, p = stats.ttest_ind(a, b, equal_var=False)
    # n ต่อกลุ่มที่ต้องใช้เพื่อให้ power=0.8 ที่ effect size เท่านี้
    try:
        n_need = analysis.solve_power(effect_size=abs(d), alpha=0.05, power=0.8, ratio=1.0)
    except Exception:
        n_need = float('nan')
    print(f"{v:5} {a.mean():>12.2f} {b.mean():>12.2f} {diff:>8.2f} {d:>8.2f} {p:>9.3f} {n_need:>16.0f}")

print("* = จำนวนบริษัทต่อกลุ่มที่ต้องมี เพื่อให้ผลต่างขนาดนี้มีนัยสำคัญที่ power 0.8")
print("="*76)

# simulation: ถ้า scale จำนวนบริษัทขึ้น (คงค่าเฉลี่ย+SD เดิม) p จะเป็นเท่าไร
print("\nถ้าสมมติผลต่าง/ความแปรปรวนเท่าเดิม แต่มีบริษัทมากขึ้น (n ต่อกลุ่ม):")
print(f"{'ตัวแปร':5} " + "".join(f"{f'x{k}':>9}" for k in [1,2,3,5,10]))
for v in ["CCC", "ROA", "ROE"]:
    a = firm[firm.DIV==1][v]; b = firm[firm.DIV==0][v]
    diff = a.mean() - b.mean()
    sp = np.sqrt(((a.std(ddof=1)**2)*(len(a)-1) + (b.std(ddof=1)**2)*(len(b)-1)) / (len(a)+len(b)-2))
    d = diff / sp
    row = f"{v:5} "
    for k in [1,2,3,5,10]:
        n1, n2 = 3*k, 7*k
        # t ที่คาดจาก effect size d และ n (สูตร t = d * sqrt(n1*n2/(n1+n2)))
        tval = d * np.sqrt(n1*n2/(n1+n2))
        dfree = n1+n2-2
        pval = 2*(1-stats.t.cdf(abs(tval), dfree))
        star = "*" if pval<0.05 else " "
        row += f"{pval:>8.3f}{star}"
    print(row)
print("(x1 = ปัจจุบัน 3 vs 7 บริษัท; * = p<0.05)")
