import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Data and analysis jobs on pracuj.pl", layout="wide")

@st.cache_data
def load():
    con = sqlite3.connect("data/jobs.db")
    offers = pd.read_sql("select * from offers", con)
    skills = pd.read_sql("select * from offer_skills", con)
    con.close()
    for c in ["is_remote", "multi_location", "open_to_entry"]:
        offers[c] = offers[c].astype(bool)
    return offers, skills

offers, skills = load()

st.title("Data and analysis jobs on pracuj.pl")
st.caption(f"Snapshot of {len(offers)} offers. Pay is shown only for offers that publish it.")


levels = ["entry", "mid", "senior", "management"]
sel_levels = st.sidebar.multiselect("Lowest level", levels, default=levels)
workplace = st.sidebar.radio("Workplace", ["All", "On-site (single city)", "Remote", "Multi-location"])
top_cities = offers.loc[~offers["is_remote"] & ~offers["multi_location"], "city"].value_counts().head(10).index.tolist()
sel_cities = st.sidebar.multiselect("City (on-site offers only)", top_cities)

d = offers[offers["level_min"].isin(sel_levels)]
if workplace == "On-site (single city)":
    d = d[~d["is_remote"] & ~d["multi_location"]]
elif workplace == "Remote":
    d = d[d["is_remote"]]
elif workplace == "Multi-location":
    d = d[d["multi_location"]]
if sel_cities:
    d = d[d["city"].isin(sel_cities) & ~d["is_remote"] & ~d["multi_location"]]

if d.empty:
    st.warning("No offers match these filters.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Offers", len(d))
c2.metric("With pay", f"{d['pay_min'].notna().sum()} ({d['pay_min'].notna().mean()*100:.0f}%)")
c3.metric("Open to entry level", int(d["open_to_entry"].sum()))


left, right = st.columns(2)

cc = (d[~d["is_remote"] & ~d["multi_location"]]["city"]
      .value_counts().head(10).rename("offers").reset_index())
if not cc.empty:
    left.plotly_chart(px.bar(cc.sort_values("offers"), x="offers", y="city", orientation="h",
                             title="Offers by city (on-site, single city)"))

ids = d.loc[d["skills"].notna(), "offer_id"]
if len(ids):
    top = skills[skills["offer_id"].isin(ids)]["skill"].value_counts().head(15)
    sk = (top / len(ids) * 100).round(1).rename("share").reset_index()
    right.plotly_chart(px.bar(sk.sort_values("share"), x="share", y="skill", orientation="h",
                              title=f"Top skills (% of {len(ids)} offers with skills listed)"))


st.subheader("Pay")
basis_names = {"net_plus_vat": "Net + VAT (B2B-style)",
               "gross": "Gross (employment contract)",
               "depends_on_contract": "Depends on contract"}
basis = st.selectbox("Pay type (not comparable with each other)", list(basis_names),
                     format_func=basis_names.get)
p = d[(d["pay_basis"] == basis) & (d["pay_mid_month"] >= 3000)]
st.write(f"{len(p)} offers. Midpoint of the range, monthly equivalent (hourly x 168).")
if len(p) < 10:
    st.warning("Fewer than 10 offers: do not draw conclusions from this.")
if len(p):
    cnt = p["level_min"].value_counts()
    p = p.assign(group=p["level_min"].map(lambda l: f"{l} (n={cnt[l]})"))
    st.plotly_chart(px.box(p, x="group", y="pay_mid_month", points="all",
                           labels={"pay_mid_month": "PLN per month", "group": "lowest level"}))


st.subheader("Offers")
st.dataframe(d[["title", "company", "city", "level", "pay", "link"]],
             column_config={"link": st.column_config.LinkColumn("link", display_text="open")},
             hide_index=True)