"""
Convert FM24 "Export view" HTML files into clean CSVs.

Usage:
    python parse_export.py <input.html or input folder> <output_folder>

FM's exported views are HTML tables with messy formatting: currency symbols,
thousands separators, "K"/"M" suffixes, "p/a" wage suffixes, and value
columns shown as ranges (e.g. "$180K - $2.2M") when a player isn't fully
scouted. This script reads the table, cleans that formatting, splits range
columns into low/high, converts numeric-looking columns, and writes a clean
CSV per input file. Columns that are genuinely text (names, positions,
nationality codes, dates, personality, etc.) are left untouched, since they
fail the numeric conversion and fall through unchanged.
"""
import re
import sys
from pathlib import Path

import pandas as pd

NUMERIC_CLEAN_RE = re.compile(r"[£$€,%]|\s*p/[aw]\b", re.IGNORECASE)
APPS_RE = re.compile(r"^(\d+)\s*\((\d+)\)$")

# FM's attribute columns are abbreviated, and "Nat" collides between Nationality and
# Natural Fitness (pandas auto-suffixes the second one "Nat.1"). Expand everything to
# full names so the CSV is usable without a legend.
ATTRIBUTE_COLUMN_NAMES = {
    "Acc": "Acceleration", "Aer": "Aerial Reach", "Agg": "Aggression", "Agi": "Agility",
    "Ant": "Anticipation", "Bal": "Balance", "Bra": "Bravery", "Cmd": "Command of Area",
    "Com": "Communication", "Cmp": "Composure", "Cnt": "Concentration", "Cor": "Corners",
    "Cro": "Crossing", "Dec": "Decisions", "Dri": "Dribbling", "Ecc": "Eccentricity",
    "Fin": "Finishing", "Fir": "First Touch", "Fla": "Flair", "Fre": "Free Kick Taking",
    "Han": "Handling", "Hea": "Heading", "Jum": "Jumping Reach", "Kic": "Kicking",
    "Ldr": "Leadership", "Lon": "Long Shots", "L Th": "Long Throws", "Mar": "Marking",
    "Nat.1": "Natural Fitness", "OtB": "Off The Ball", "1v1": "One on Ones", "Pac": "Pace",
    "Pas": "Passing", "Pen": "Penalty Taking", "Pos": "Positioning", "Pun": "Punching (Tendency)",
    "Ref": "Reflexes", "TRO": "Rushing Out (Tendency)", "Sta": "Stamina", "Str": "Strength",
    "Tck": "Tackling", "Tea": "Teamwork", "Tec": "Technique", "Thr": "Throwing",
    "Vis": "Vision", "Wor": "Work Rate",
}


def clean_numeric(val):
    if not isinstance(val, str):
        return val
    stripped = val.strip()
    if stripped in ("", "-", "N/A"):
        return None

    cleaned = NUMERIC_CLEAN_RE.sub("", stripped).strip()

    # FM shows large currency values as e.g. "15M" / "800K"
    multiplier = 1
    if cleaned.endswith("M"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = 1_000
        cleaned = cleaned[:-1]

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return val  # leave non-numeric text (names, positions, dates, etc.) untouched


def split_range(val):
    """Handle columns like Transfer Value shown as '$180K - $2.2M' for unscouted players."""
    if not isinstance(val, str):
        return val, val
    stripped = val.strip()
    if stripped in ("", "-", "N/A"):
        return None, None
    if " - " in stripped:
        low, high = stripped.split(" - ", 1)
        return clean_numeric(low), clean_numeric(high)
    single = clean_numeric(stripped)
    return single, single


def split_apps(val):
    """Handle FM's 'starts (sub apps)' format, e.g. '41 (2)' = 41 starts + 2 sub apps."""
    if not isinstance(val, str):
        return val, 0
    match = APPS_RE.match(val.strip())
    if match:
        starts, subs = float(match.group(1)), float(match.group(2))
        return starts + subs, subs
    total = clean_numeric(val)
    return total, (0.0 if total is not None else None)


def parse_file(html_path: Path, output_folder: Path):
    tables = pd.read_html(html_path, encoding="utf-8")
    if not tables:
        print(f"  no tables found in {html_path.name}, skipping")
        return

    df = max(tables, key=len)  # FM export files sometimes wrap the table in extra markup
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns=ATTRIBUTE_COLUMN_NAMES)

    for col in list(df.columns):
        if "value" in col.lower():
            lows, highs = zip(*df[col].map(split_range))
            col_index = df.columns.get_loc(col)
            df = df.drop(columns=[col])
            df.insert(col_index, f"{col} (Low)", lows)
            df.insert(col_index + 1, f"{col} (High)", highs)
        elif df[col].astype(str).str.match(APPS_RE).any():
            totals, subs = zip(*df[col].map(split_apps))
            col_index = df.columns.get_loc(col)
            df = df.drop(columns=[col])
            df.insert(col_index, f"{col} (Total)", totals)
            df.insert(col_index + 1, f"{col} (Sub Apps)", subs)
        else:
            df[col] = df[col].map(clean_numeric)

    output_folder.mkdir(parents=True, exist_ok=True)
    out_path = output_folder / f"{html_path.stem}.csv"
    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path} ({len(df)} rows, {len(df.columns)} cols)")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_folder = Path(sys.argv[2])

    html_files = [input_path] if input_path.is_file() else sorted(input_path.glob("*.html"))
    if not html_files:
        print(f"No .html files found at {input_path}")
        sys.exit(1)

    for html_file in html_files:
        print(f"Parsing {html_file.name}...")
        parse_file(html_file, output_folder)


if __name__ == "__main__":
    main()
