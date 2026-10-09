# Notebooks

[AI_Chip_Market_Intelligence.ipynb](AI_Chip_Market_Intelligence.ipynb) is the
main scientific notebook. Run All uses FAST: verified published tables/figures,
archived loss curves and arithmetic checks of frozen forecasts. No local market
data, model training, network or R is needed.

From the repository root with `.venv` and development dependencies installed:

```powershell
python python/09a_execute_notebook.py --clean-copy
```

Executed notebooks are ignored under `.cache/phase9a/`. FULL reproduction is
a separate manual procedure in [the guide](../docs/reproduction_guide.md).
See [Windows/RStudio setup](../docs/team_setup_windows.md).
