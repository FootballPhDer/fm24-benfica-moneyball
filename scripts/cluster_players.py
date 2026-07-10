"""
Discover natural player-style clusters from performance stats, independent of
FM's own role/duty star ratings, and see how they compare.

Combines the Benfica squad export and the scouted-players export using only
the stat columns present in both (performance/data-hub stats - the scouted
export doesn't include individual attributes, only output stats), so the
comparison is apples-to-apples.

Usage:
    python cluster_players.py
"""
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

SQUAD_PATH = "../data/processed/2024-25/Full Team Stats.csv"
SCOUTED_PATH = "../data/processed/2024-25/High-Rated Scouted Players.csv"
OUTPUT_PATH = "../data/processed/2024-25/player_clusters.csv"

FEATURES = [
    "xG", "xA", "Tck/90", "Int/90", "Pas %", "Pr passes/90", "Poss Won/90",
    "Poss Lost/90", "K Ps/90", "Drb/90", "Cr C/90", "Ch C/90", "Dist/90",
    "Sprints/90", "Clr/90", "Blk/90", "Aer A/90", "Hdrs W/90",
]
MIN_APPS = 10


def load(path, source):
    df = pd.read_csv(path)
    df["Source"] = source
    df["Apps (Total)"] = pd.to_numeric(df["Apps (Total)"], errors="coerce")
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def main():
    squad = load(SQUAD_PATH, "Benfica Squad")
    scouted = load(SCOUTED_PATH, "Scouted")

    combined = pd.concat([squad[["Name", "Position", "Apps (Total)", "Source"] + FEATURES],
                           scouted[["Name", "Position", "Apps (Total)", "Source"] + FEATURES]],
                          ignore_index=True)

    combined = combined[combined["Apps (Total)"] >= MIN_APPS].dropna(subset=FEATURES)
    print(f"Players with >= {MIN_APPS} apps and complete stats: {len(combined)}")

    X = StandardScaler().fit_transform(combined[FEATURES])

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X)
    combined["pc1"] = coords[:, 0]
    combined["pc2"] = coords[:, 1]
    print(f"PCA explained variance: {pca.explained_variance_ratio_[:2].sum():.1%}")

    k = 6
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    combined["cluster"] = kmeans.fit_predict(X)

    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {OUTPUT_PATH} ({len(combined)} players, {k} clusters)")

    print("\nCluster sizes:")
    print(combined["cluster"].value_counts().sort_index())

    for name in ["João Neves", "Javi Guerra - Spanish", "Rafael Luís", "Tiago Gouveia", "Arthur Cabral"]:
        row = combined[combined["Name"] == name]
        if not row.empty:
            r = row.iloc[0]
            print(f"{name}: cluster {r['cluster']}, pc1={r['pc1']:.2f}, pc2={r['pc2']:.2f}")


if __name__ == "__main__":
    main()
