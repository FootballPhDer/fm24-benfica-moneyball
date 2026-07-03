# FM24 Benfica Moneyball

A data-driven Football Manager 2024 save: build Benfica into a club that wins more Champions Leagues than Real Madrid over the long term.

## Approach

1. **Targets model** — figure out the goals-scored / goals-conceded thresholds historically needed to win the league and progress deep in the Champions League, so each season has a concrete target to hit.
2. **Squad tracking** — track squad stats season over season (attributes, output, market value) to see what's working.
3. **Undervalued player scouting** — flag players whose output/attributes are underpriced relative to their transfer value, using stats exports and scouting screens.

## Data pipeline

FM24 doesn't give a clean bulk export, but almost every screen with a data grid (squad view, player search, league table, stats) has an **Export view** button that dumps the table to HTML.

Workflow:
1. In-game, export the relevant views (squad, league table, stats screens) to `data/raw/<season>/`.
2. Run `scripts/parse_export.py` to convert the raw HTML exports into clean CSVs in `data/processed/`.
3. Analyze in `notebooks/`.

## Folder structure

- `data/raw/` — raw FM HTML exports, one subfolder per season (gitignored, stays local)
- `data/processed/` — cleaned CSVs, safe to commit
- `scripts/` — parsing and cleaning scripts
- `notebooks/` — analysis notebooks
