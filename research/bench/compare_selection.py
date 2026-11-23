"""Compare fixed candidate configurations and decision rules on frozen validation."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

ROOT = Path(__file__).resolve().parent
METHODS = ("Shewhart", "CUSUM", "GLR16", "RankRestart")
SCENARIOS = ("moderate persistent", "brief pulse", "shifted healthy law")
COLORS = ("#1369aa", "#ab450f", "#168262", "#6d4c85")
MARKERS = ("o", "s", "^", "D")
CAPS = {"fa": .02, "miss": .30, "risk": .60}

with (ROOT / "coordinate_intervals.csv").open(newline="") as stream:
    rows = {(row["scenario"], row["method"]): row for row in csv.DictReader(stream)
            if float(row["false_alarm_cap"]) == CAPS["fa"]}


def feasible(row, limits, end):
    return int(row["slots"]) <= 250 and all(
        float(row[f"{endpoint}_{end}"]) <= cap for endpoint, cap in limits.items()
    )


def compare():
    results = []
    reliability_and_hazard = {"fa": CAPS["fa"], "risk": CAPS["risk"]}
    for scenario in sorted({scenario for scenario, _ in rows}):
        ordered = [rows[scenario, method] for method in METHODS]
        baseline = min(ordered, key=lambda row: int(row["risk_k"]))
        row = {"scenario": scenario, "hazard_only_choice": baseline["method"],
               "hazard_only_alert_lower": baseline["fa_lo"]}
        for label, limits in (("original", reliability_and_hazard), ("with_timeliness", CAPS)):
            inner = [r for r in ordered if feasible(r, limits, "up")]
            outer = [r for r in ordered if feasible(r, limits, "lo")]
            row[f"{label}_choice"] = (
                min(inner, key=lambda r: float(r["risk_up"]))["method"] if inner else ""
            )
            row[f"{label}_possibly_feasible"] = " / ".join(r["method"] for r in outer)
        results.append(row)

    with (ROOT / "decision_baseline.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    for label, limits in (("original", reliability_and_hazard), ("with_timeliness", CAPS)):
        common = [method for method in METHODS
                  if all(feasible(rows[scenario, method], limits, "lo")
                         for scenario in SCENARIOS[:2])]
        print(f"{label}, two-regime possible menu: {common}")
    print(next(row for row in results if row["scenario"] == SCENARIOS[-1]))


def plot():
    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.02))
    for ax, (key, title) in zip(axes, (
        ("fa", "Healthy false alerts"), ("miss", "Missed actionable window"),
        ("risk", "Closed-loop hazard"),
    )):
        for index, (method, color, marker) in enumerate(zip(METHODS, COLORS, MARKERS)):
            lower, upper = ([float(rows[s, method][f"{key}_{end}"]) for s in SCENARIOS]
                            for end in ("lo", "up"))
            x = np.arange(len(SCENARIOS)) + (index - 1.5) * .17
            center = (np.array(lower) + upper) / 2
            ax.errorbar(x, center, yerr=np.array(upper) - center, fmt=marker,
                        color=color, markersize=3.3, capsize=2.5, linewidth=1.05,
                        label=method, zorder=3)
        ax.axhline(CAPS[key], color="#555555", linewidth=.8, linestyle="--")
        ax.set_xticks(range(len(SCENARIOS)), ["Persistent", "Pulse", "Shifted\nhealthy"])
        ax.set_title(title, fontsize=8.5)
        ax.set_ylim(-.025, 1.035)
        ax.set_yticks([0, .25, .5, .75, 1])
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.grid(axis="y", linewidth=.45, color="#dddddd")
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(.5, -.022))
    fig.subplots_adjust(left=.058, right=.99, bottom=.29, top=.89, wspace=.28)
    fig.savefig(ROOT / "risk_comparison.pdf")
    plt.close(fig)


if __name__ == "__main__":
    compare()
    plot()
