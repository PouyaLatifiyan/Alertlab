"""Plot the two capacity contracts using the archived matched comparison."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent
with (ROOT / "matched_regret.csv").open(newline="") as stream:
    rows = list(csv.DictReader(stream))

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
fig, axes = plt.subplots(1, 2, figsize=(7, 2.55), sharey=True)
for ax, (contract, title) in zip(axes, [
    ("one slot per handoff", "Unit charge"),
    ("duration-weighted handoff", "Duration-weighted charge"),
]):
    points = sorted(
        (r for r in rows if r["contract"] == contract and r["same_law_choice"] == "True"),
        key=lambda r: float(r["budget"]),
    )
    budgets = [float(r["budget"]) for r in points]
    ax.axvspan(0, budgets[0] - .025, color="#e9e9e9", label="Both abstain (grid)")
    for key, label, fmt in [
        ("separate_bound", "Separate feasibility check", "#9b490d"),
        ("same_law_bound", "Feasibility under the same law", "#1369aa"),
    ]:
        ax.plot(budgets, [float(r[key]) for r in points], color=fmt,
                marker="o" if key == "separate_bound" else "^", markersize=3.6,
                linestyle="--" if key == "separate_bound" else "-", label=label)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(-.018, .49)
    ax.set_title(title)
    ax.set_xlabel("Capacity budget")
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.grid(axis="y", alpha=.35)
axes[0].set_ylabel("Upper excess miss risk")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
fig.subplots_adjust(bottom=.31, top=.89, left=.11, right=.98, wspace=.15)
fig.savefig(ROOT / "matched_regret_comparison.pdf")
