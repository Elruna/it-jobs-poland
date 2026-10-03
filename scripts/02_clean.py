import re, sqlite3
import numpy as np
import pandas as pd

RAW = "data/raw/jobs_pracujpl.csv"
HOURS_PER_MONTH = 168  

df = pd.read_csv(RAW)  
df.insert(0, "offer_id", range(1, len(df) + 1))

# ---------- pay ----------
def parse_pay(text):
    empty = pd.Series({"pay_min": np.nan, "pay_max": np.nan,
                       "pay_period": None, "pay_basis": None})
    if pd.isna(text):
        return empty
    t = re.sub(r"\s+", " ", str(text)).strip()   # also fixes non-breaking spaces
    try:
        amount = t.split("zł")[0]
        vals = [float(p.replace(" ", "").replace(",", "."))
                for p in re.split(r"[–-]", amount) if p.strip()]
        lo, hi = vals[0], vals[-1]
    except (ValueError, IndexError):
        return empty                               # counted as a failure below
    period = "hour" if "godz" in t else "month" if "mies" in t else None
    if "brutto" in t:
        basis = "gross"
    elif "netto" in t:
        basis = "net_plus_vat"
    elif "zal. od umowy" in t:
        basis = "depends_on_contract"
    else:
        basis = "unspecified"
    return pd.Series({"pay_min": lo, "pay_max": hi,
                      "pay_period": period, "pay_basis": basis})

df = pd.concat([df, df["pay"].apply(parse_pay)], axis=1)

factor = df["pay_period"].map({"month": 1, "hour": HOURS_PER_MONTH})
df["pay_min_month"] = df["pay_min"] * factor
df["pay_max_month"] = df["pay_max"] * factor
df["pay_mid_month"] = (df["pay_min_month"] + df["pay_max_month"]) / 2


def level_groups(text):
    t = str(text)
    g = []
    if any(k in t for k in ["Praktykant", "Asystent", "Junior"]): g.append("entry")
    if "Mid" in t: g.append("mid")
    if any(k in t for k in ["Senior", "Ekspert"]): g.append("senior")
    if any(k in t for k in ["Kierownik", "Menedżer", "Dyrektor"]): g.append("management")
    return g

groups = df["level"].apply(level_groups)
df["level_min"] = groups.apply(lambda g: g[0] if g else "unknown")
df["open_to_entry"] = groups.apply(lambda g: "entry" in g)


def parse_location(text):
    t = str(text)
    remote = "praca zdalna" in t
    multi = bool(re.match(r"^\d+\s+lokaliz", t))   
    if "Siedziba firmy:" in t:
        place = t.split("Siedziba firmy:")[1]
    elif t.startswith("Miejsce pracy:") or multi:
        place = ""
    else:
        place = t
    city = place.split(",")[0].strip() or None
    return pd.Series({"city": city, "is_remote": remote, "multi_location": multi})

df = pd.concat([df, df["location"].apply(parse_location)], axis=1)


skills = (df[["offer_id", "skills"]].dropna()
          .assign(skill=lambda d: d["skills"].str.split(","))
          .explode("skill"))
skills["skill"] = skills["skill"].str.strip()
ALIASES = {"Microsoft Power BI": "Power BI", "Microsoft Azure": "Azure",
           "Microsoft Excel": "Excel"}
skills["skill"] = skills["skill"].replace(ALIASES)
skills = skills[skills["skill"] != ""][["offer_id", "skill"]].drop_duplicates()


cols = ["offer_id", "title", "company", "link", "location", "city", "is_remote", "multi_location",
        "level", "level_min", "open_to_entry", "type", "pay", "pay_min", "pay_max",
        "pay_period", "pay_basis", "pay_min_month", "pay_max_month",
        "pay_mid_month", "skills"]
offers = df[cols]
con = sqlite3.connect("data/jobs.db")
offers.to_sql("offers", con, if_exists="replace", index=False)
skills.to_sql("offer_skills", con, if_exists="replace", index=False)
con.close()
offers.to_csv("data/offers_clean.csv", index=False)

print("Offers:", len(offers), "| with pay text:", offers["pay"].notna().sum())
print("Pay parse failures:", (offers["pay"].notna() & offers["pay_min"].isna()).sum())
print("min > max rows:", (offers["pay_min"] > offers["pay_max"]).sum())
print("\nPay basis x period:\n", offers.groupby(["pay_basis", "pay_period"], dropna=False).size())
print("\nLowest level:\n", offers["level_min"].value_counts())
print("Open to entry level:", offers["open_to_entry"].sum())
print("\nRemote:\n", offers["is_remote"].value_counts())
print("\nTop on-site cities:\n", offers.loc[~offers["is_remote"], "city"].value_counts().head(10))
odd = offers[offers["location"].str.contains("Miejsce pracy") & ~offers["is_remote"]]
print("\nUnusual 'Miejsce pracy' rows (not remote):", len(odd))
print(odd["location"].head().to_string())
print("\nMonthly-equivalent pay, summary:\n", offers["pay_mid_month"].describe().round(0))
print("\nTop skills:\n", skills["skill"].value_counts().head(25))