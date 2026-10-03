import pandas as pd

pd.set_option("display.max_colwidth", 120)
df = pd.read_csv("data/raw/jobs_pracujpl.csv")

print(df.shape)
print("duplicate links:", df.duplicated("link").sum())
print("\nMissing values:\n", df.isna().sum())

print("\nPay samples:\n", df["pay"].dropna().sample(25, random_state=1).to_string())
print("\nLevel values:\n", df["level"].value_counts().head(15))
print("\nType values:\n", df["type"].value_counts().head(10))
print("\nLocation samples:\n", df["location"].sample(15, random_state=1).to_string())