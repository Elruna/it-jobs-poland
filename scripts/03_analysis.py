import sqlite3
import pandas as pd

pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 70)

con = sqlite3.connect("data/jobs.db")
offers = pd.read_sql("select * from offers", con)
sk = pd.read_sql("select * from offer_skills", con)
con.close()
for c in ["is_remote", "multi_location", "open_to_entry"]:
    offers[c] = offers[c].astype(bool)
total = len(offers)

# ---------- 1. levels ----------
print("1. OFFERS BY LOWEST LEVEL")
lv = offers["level_min"].value_counts()
print(pd.DataFrame({"n": lv, "share_%": (lv / total * 100).round(1)}))
print("Open to entry level:", offers["open_to_entry"].sum(),
      f"({offers['open_to_entry'].mean()*100:.1f}%)")

# ---------- 2. places ----------
print("\n2. WHERE")
print("Remote share %:", round(offers["is_remote"].mean() * 100, 1))
onsite = offers[~offers["is_remote"] & ~offers["multi_location"]]
print("On-site, single city:", len(onsite),
      "| multi-location offers:", offers["multi_location"].sum())
c = onsite["city"].value_counts().head(8)
print(pd.DataFrame({"n": c, "share_of_onsite_%": (c / len(onsite) * 100).round(1)}))
print("\nEntry-level on-site offers by city:\n",
      onsite[onsite["open_to_entry"]]["city"].value_counts().head(5))

# ---------- 3. skills ----------
print("\n3. SKILLS")
has_sk = offers[offers["skills"].notna()]

def top_skills(ids, label):
    n = len(ids)
    t = sk[sk["offer_id"].isin(ids)]["skill"].value_counts().head(12)
    print(f"\nTop skills, {label} (offers with skills listed: {n})")
    print(pd.DataFrame({"offers": t, "share_%": (t / n * 100).round(1)}))

top_skills(has_sk["offer_id"], "all offers")
top_skills(has_sk[has_sk["open_to_entry"]]["offer_id"], "entry-level offers")
top_skills(has_sk[has_sk["level_min"] == "senior"]["offer_id"], "senior offers")

# ---------- 4. pay ----------
print("\n4. PAY")
has_pay = offers["pay_min"].notna()
print("Offers with pay:", has_pay.sum(), "of", total, f"({has_pay.mean()*100:.1f}%)")
print("\nShare with pay, by lowest level:")
print(offers.groupby("level_min")["pay_min"]
      .agg(offers="size", with_pay="count")
      .assign(share_pct=lambda d: (d.with_pay / d.offers * 100).round(1)))

paid = offers[has_pay].copy()
paid["pay_mid"] = (paid["pay_min"] + paid["pay_max"]) / 2
bad = paid[paid["pay_mid_month"] < 3000]
print("\nEXCLUDED as implausible (monthly equivalent < 3 000 zl):", len(bad))
print(bad[["title", "pay", "pay_period"]].to_string())
paid = paid[paid["pay_mid_month"] >= 3000]

def table(d, by, col):
    t = d.groupby(by)[col].agg(n="count", median="median",
                               q1=lambda s: s.quantile(.25),
                               q3=lambda s: s.quantile(.75)).round(0)
    t["small_sample"] = t["n"] < 10
    return t

print("\nPay by basis and period (native units: zl/month or zl/hour):")
print(table(paid, ["pay_basis", "pay_period"], "pay_mid"))
print("\nMonthly-equivalent pay by basis (hourly x 168):")
print(table(paid, "pay_basis", "pay_mid_month"))
print("\nNet + VAT, monthly-equivalent, by lowest level:")
print(table(paid[paid["pay_basis"] == "net_plus_vat"], "level_min", "pay_mid_month"))
print("\nGross, monthly-equivalent, by lowest level:")
print(table(paid[paid["pay_basis"] == "gross"], "level_min", "pay_mid_month"))
city_pay = paid[(paid["pay_basis"] == "net_plus_vat") & ~paid["is_remote"]
                & ~paid["multi_location"]
                & paid["city"].isin(["Warszawa", "Kraków", "Wrocław"])]
print("\nNet + VAT, monthly-equivalent, by city:")
print(table(city_pay, "city", "pay_mid_month"))