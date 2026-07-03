"""
Convert FM24 "Export view" HTML files into clean CSVs.

Usage:
    python parse_export.py <input.html or input folder> <output_folder>

FM's exported views are HTML tables with messy formatting (currency symbols,
percent signs, thousands separators, unicode arrows in headers). This script
reads the table, strips that formatting, converts numeric-looking columns,
and writes a clean CSV per input file.
"""
import re
import sys
from pathlib import Path

import pandas as pd

NUMERIC_CLEAN_RE = re.compile(r"[£$€,%]")


def clean_value(val):
    if not isinstance(val, str):
        return val
    stripped = val.strip()
    if stripped in ("", "-", "N/A"):
        return None

    cleaned = NUMERIC_CLEAN_RE.sub("", stripped)

    # FM shows transfer values as e.g. "15M" / "800K"
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
        return val  # leave non-numeric text (names, positions, etc.) untouched


def parse_file(html_path: Path, output_folder: Path):
    tables = pd.read_html(html_path)
    if not tables:
        print(f"  no tables found in {html_path.name}, skipping")
        return

    df = max(tables, key=len)  # FM export files sometimes wrap the table in extra markup
    df.columns = [str(c).strip() for c in df.columns]
    df = df.map(clean_value)

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
