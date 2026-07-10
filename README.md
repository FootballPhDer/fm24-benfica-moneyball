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

## Season-end checklist

Run through this every season, in order. Steps 1-3 are data collection; 4-7 are the actual football-management decisions the data should inform.

1. **Performance review** — export the league table (your league + Champions League stage), your squad's full season stats, Real Madrid's squad stats, and your CL opponents' squad stats. Compare results against the goals-for/against targets from prior seasons.
2. **Squad audit** — export/update squad data with age, contract length, and current ability/value. Flag anyone with 1 year left on their contract now.
3. **Recruitment scouting** — export a wide player search (Primeira Liga at minimum, ideally top 5 leagues) with value, age, and output stats, timed to each transfer window rather than only season's end.
4. **Needs analysis** — from the squad audit, rank position needs by urgency (genuine hole vs. depth).
5. **Transfer business** — sell first, then buy, then loans (both incoming young loanees and outgoing fringe players). Log every fee (in or out) in `data/processed/player_info.csv`.
6. **Contract renewals** — lock in good, cheap, homegrown players before their value/wage demands spike.
7. **Pre-season** — note any tactical changes tested and fringe/youth players given a look, so next season's review has that context.
