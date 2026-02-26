import pandas as pd

# Paths
flood_path = "data/raw/2014_India_floods_CF_labeled_data.tsv"
earthquake_path = "data/raw/2015_Nepal_Earthquake_en_CF_labeled_data.tsv"
landslide_path = "data/raw/Landslides_Worldwide_en.csv"

# Load
flood = pd.read_csv(flood_path, sep="\t", encoding="latin-1")
earthquake = pd.read_csv(earthquake_path, sep="\t", encoding="latin-1")
landslide = pd.read_csv(landslide_path, encoding="latin-1" )

def find_text_column(df):
    for col in df.columns:
        if "text" in col.lower() or "tweet_text" in col.lower():
            return col
    return df.columns[0]

# Extract text columns
flood_text = find_text_column(flood)
earthquake_text = find_text_column(earthquake)
landslide_text = find_text_column(landslide)

flood_clean = flood[[flood_text]].copy()
print(flood_clean.columns)
flood_clean.columns = ["text"]
flood_clean["disaster_type"] = "flood"

earthquake_clean = earthquake[[earthquake_text]].copy()
earthquake_clean.columns = ["text"]
earthquake_clean["disaster_type"] = "earthquake"

landslide_clean = landslide[[landslide_text]].copy()
landslide_clean.columns = ["text"]
landslide_clean["disaster_type"] = "landslide"

# Combine
combined = pd.concat([flood_clean, earthquake_clean, landslide_clean])

combined = combined.dropna(subset=["text"])
combined = combined[combined["text"].str.len() > 20]

combined.to_csv("data/processed/social_stream.csv", index=False)

print("Unified dataset created successfully.")
