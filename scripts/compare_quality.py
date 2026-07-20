"""
Compare squad quality (attributes) rather than market value, since value is a
market proxy influenced by reputation/age/hype, not a pure ability measure.

Usage:
    python compare_quality.py
"""
import pandas as pd

BENFICA_PATH = "../data/processed/2026-2027/End of Season Stats.csv"
BARCA_PATH = "../data/processed/2026-2027/Champions League Winners Squads.csv"

CORE_ATTRS = [
    "Acceleration", "Agility", "Balance", "Jumping Reach", "Natural Fitness", "Pace",
    "Stamina", "Strength", "Aggression", "Anticipation", "Bravery", "Composure",
    "Concentration", "Decisions", "Det", "Flair", "Leadership", "Off The Ball",
    "Positioning", "Teamwork", "Vision", "Work Rate", "Corners", "Crossing", "Dribbling",
    "Finishing", "First Touch", "Free Kick Taking", "Heading", "Long Shots", "Marking",
    "Passing", "Tackling", "Technique",
]

POSITION_GROUPS = {
    "Center Backs": (r"D \([^)]*C", ["Marking", "Tackling", "Positioning", "Heading", "Strength", "Composure"]),
    "DM/CM": (r"DM|M \(C", ["Passing", "Vision", "Tackling", "Decisions", "Work Rate", "Stamina"]),
    "Wide Attackers/AM": (r"AM \(|M \(R|M \(L", ["Dribbling", "Technique", "Vision", "Off The Ball", "Flair", "Pace"]),
    "Strikers": (r"ST \(C", ["Finishing", "Off The Ball", "Composure", "Heading", "Anticipation"]),
}


def load(path):
    df = pd.read_csv(path)
    for col in CORE_ATTRS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    return df


def main():
    benfica = load(BENFICA_PATH)
    benfica = benfica[benfica["Club"] == "Benfica"]
    barca = load(BARCA_PATH)

    # Focus on senior, first-team-relevant players (excludes raw youth/reserves)
    benfica_senior = benfica[benfica["Age"] >= 20]
    barca_senior = barca[barca["Age"] >= 20]

    print(f"Benfica senior squad: {len(benfica_senior)} players")
    print(f"Barcelona senior squad: {len(barca_senior)} players\n")

    print("=== Overall attribute average (all core attributes, senior players) ===")
    b_avg = benfica_senior[CORE_ATTRS].mean().mean()
    bc_avg = barca_senior[CORE_ATTRS].mean().mean()
    print(f"Benfica:   {b_avg:.2f}")
    print(f"Barcelona: {bc_avg:.2f}")
    print(f"Gap: {bc_avg - b_avg:.2f} attribute points\n")

    for label, (pattern, attrs) in POSITION_GROUPS.items():
        b_group = benfica_senior[benfica_senior["Position"].str.contains(pattern, na=False, regex=True)]
        bc_group = barca_senior[barca_senior["Position"].str.contains(pattern, na=False, regex=True)]
        if len(b_group) == 0 or len(bc_group) == 0:
            continue
        print(f"=== {label} (Benfica n={len(b_group)}, Barcelona n={len(bc_group)}) ===")
        for attr in attrs:
            b_val = b_group[attr].mean()
            bc_val = bc_group[attr].mean()
            print(f"  {attr:15s}  Benfica {b_val:5.1f}  vs  Barcelona {bc_val:5.1f}  (gap {bc_val - b_val:+.1f})")
        print()


if __name__ == "__main__":
    main()
