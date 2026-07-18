"""
Convert FM24 "Export view" files (HTML, or a markdown-style pipe table saved
as .rtf/.txt) into clean CSVs.

Usage:
    python parse_export.py <input file or input folder> <output_folder>

FM's exported views have messy formatting: currency symbols, thousands
separators, "K"/"M" suffixes, "p/a" wage suffixes, and value columns shown as
ranges (e.g. "$180K - $2.2M") when a player isn't fully scouted. This script
reads the table (from either format), cleans that formatting, splits range
columns into low/high, converts numeric-looking columns, and writes a clean
CSV per input file. Columns that are genuinely text (names, positions,
nationality codes, dates, personality, etc.) are left untouched, since they
fail the numeric conversion and fall through unchanged.
"""
import re
import sys
from pathlib import Path

import pandas as pd

NUMERIC_CLEAN_RE = re.compile(r"[£$€,%]|\s*p/[aw]\b|mi\b", re.IGNORECASE)
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


def load_html_table(path: Path) -> pd.DataFrame | None:
    tables = pd.read_html(path, encoding="utf-8")
    if not tables:
        return None
    df = max(tables, key=len)  # FM export files sometimes wrap the table in extra markup
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_pipe_table(path: Path) -> pd.DataFrame | None:
    """Read a markdown-style pipe table (FM sometimes exports these as .rtf/.txt
    instead of HTML - same data, just '| col | col |' rows with a '|---|---|'
    separator line, rather than an HTML <table>)."""
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    def split_row(line):
        parts = line.strip().split("|")
        # leading/trailing "|" produce empty first/last elements - drop them
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]
        return [p.strip() for p in parts]

    is_separator = lambda line: bool(re.fullmatch(r"[\s|:-]+", line))

    headers = dedupe_columns(split_row(lines[0]))
    data_lines = [line for line in lines[1:] if not is_separator(line)]
    data_rows = [split_row(line) for line in data_lines]
    data_rows = [row for row in data_rows if len(row) == len(headers)]
    if not data_rows:
        return None
    return pd.DataFrame(data_rows, columns=headers)


def dedupe_columns(headers: list[str]) -> list[str]:
    """FM's exports reuse a header (e.g. "Nat" for both Nationality and Natural
    Fitness). pandas.read_html auto-suffixes repeats as "Nat.1", "Nat.2" - mimic
    that here since building a DataFrame straight from a header list doesn't."""
    seen = {}
    deduped = []
    for header in headers:
        count = seen.get(header, 0)
        deduped.append(header if count == 0 else f"{header}.{count}")
        seen[header] = count + 1
    return deduped


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Only expand attribute abbreviations on genuine squad/attribute exports - a handful of
    # these abbreviations (e.g. "Pos") collide with unrelated columns on other screens
    # (like the League Table's position/rank column), so require several matches as a
    # signal this is actually a full-attribute squad view before renaming.
    attribute_signal_count = sum(1 for col in ATTRIBUTE_COLUMN_NAMES if col in df.columns)
    if attribute_signal_count >= 5:
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

    return df


def parse_file(in_path: Path, output_folder: Path):
    if in_path.suffix.lower() == ".html":
        df = load_html_table(in_path)
    else:
        df = load_pipe_table(in_path)

    if df is None:
        print(f"  no table found in {in_path.name}, skipping")
        return

    df = clean_dataframe(df)

    # Tag every row with the season (taken from the output folder name, e.g.
    # "data/processed/2024-25" -> "2024-25") so multi-season files can later be
    # concatenated safely without relying on folder structure alone.
    df.insert(0, "Season", output_folder.name)

    output_folder.mkdir(parents=True, exist_ok=True)
    out_path = output_folder / f"{in_path.stem}.csv"
    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path} ({len(df)} rows, {len(df.columns)} cols)")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_folder = Path(sys.argv[2])

    supported_exts = (".html", ".rtf", ".txt")
    if input_path.is_file():
        input_files = [input_path]
    else:
        input_files = sorted(p for p in input_path.iterdir() if p.suffix.lower() in supported_exts)

    if not input_files:
        print(f"No supported export files ({', '.join(supported_exts)}) found at {input_path}")
        sys.exit(1)

    for in_file in input_files:
        print(f"Parsing {in_file.name}...")
        parse_file(in_file, output_folder)


if __name__ == "__main__":
    main()
