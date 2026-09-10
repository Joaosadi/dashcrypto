## [unreleased]

### Performance

- Speed up stablecoin historical data fetch
- Cache CoinGecko snapshot fetches for 5 minutes

### Styling

- Restyle stablecoin supply chart to match market share chart
- Match macro metrics charts to BTC tab styling
- Move macro chart legends to the right to avoid overlap
- Make app layout responsive on mobile phones
- Use container-width charts for responsive sizing

### Miscellaneous Tasks

- Stop tracking pyc and jupyter checkpoint artifacts
- Track devcontainer config (remove it from gitignore)
- Exclude automated data-sync commits from changelog
- Remove icons from changelog headings
- Add Streamlit dark theme config and require streamlit 1.49+

## [0.1.0] - 2026-09-10

### Features

- New macrodata charts available in jl notebooks, soon to be in the app.
- Added macro data tab to compare btc price to american dollar metrics

### Refactor

- Reorganized plots into their own directory
