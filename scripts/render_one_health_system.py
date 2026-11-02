"""Render the authored One Health system map with standard plotting tools."""
from pathlib import Path
import argparse
import os

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".tools/matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/figures")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(14, 8.3), facecolor="white")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8.3)
    ax.axis("off")
    palette = {"data": ("#eaf2f8", "#285b83"), "simulation": ("#fff0df", "#b36b17"),
               "context": ("#f1eef7", "#76618d")}

    def box(x, y, w, h, title, lines, kind):
        fill, edge = palette[kind]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12,rounding_size=.08",
                                   linewidth=1.3, edgecolor=edge, facecolor=fill, zorder=2))
        ax.text(x + .13, y + h - .2, title, va="top", ha="left", fontsize=11.5,
                fontweight="bold", color=edge, zorder=3)
        ax.text(x + .13, y + h - .57, lines, va="top", ha="left", fontsize=10,
                linespacing=1.4, color="#21313f", zorder=3)

    def arrow(start, end, style="-", color="#285b83", rad=0):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
            linewidth=1.5, color=color, linestyle=style, connectionstyle=f"arc3,rad={rad}", zorder=1))

    ax.text(.1, 8.02, "AEGIS One Health decision system", fontsize=21, fontweight="bold", color="#17374f")
    ax.text(.1, 7.65, "Missouri refrigerated-poultry dispatch review | observed evidence, exploratory alignment and simulation remain distinct",
            fontsize=10.5, color="#52636f")
    box(.2, 5.75, 3.3, 1.3, "HUMAN HEALTH", "PulseNet-derived BEAM aggregates\nNORS historical outbreak records\nSeparate isolate / outbreak denominators", "data")
    box(.2, 3.93, 3.3, 1.3, "FOOD / ANIMAL", "FSIS selected poultry primary samples\nSalmonella Positive / Negative\nNo consumer-illness label", "data")
    box(.2, 2.1, 3.3, 1.3, "ENVIRONMENT", "NOAA: five Missouri airport stations\nDaily ambient TMAX / TMIN / PRCP\nNo cargo / establishment exposure", "data")
    box(4.5, 4.9, 4.0, 2.15, "RETROSPECTIVE ALIGNMENT", "Missouri selected sample; 7-day lead\nExplicit origins and assumed lags\nEcological state-level covariates\nNo genomic or causal attribution\nNo validated prospective forecast", "data")
    box(4.5, 2.1, 4.0, 1.73, "DECISION SUPPORT", "Inspect / verify; compare plans; substitute\nPropose precautionary hold for review\nModel output cannot impose a hold\nConcrete plan requires human approval", "simulation")
    box(9.45, 5.6, 4.0, 1.45, "SIMULATED SUPPLY CHAIN", "Suppliers → DCs → fictional recipients\nLots, trucks, stock and cargo telemetry\nNo verified real contracts / traceability", "simulation")
    box(9.45, 3.25, 4.0, 1.43, "HUMAN APPROVAL", "Dispatcher and receiving review\nInventory / time / eligibility constraints\nHeld or recalled lots cannot dispatch", "simulation")
    box(9.45, 1.05, 4.0, 1.33, "SIMULATED OUTCOMES", "Delivered kg; unmet demand; cost / delay\nQuality-window parameter sensitivity\nNo measured illnesses prevented", "simulation")
    box(.2, .15, 8.3, 1.15, "FOOD SECURITY / ACCESS — HISTORICAL CONTEXT", "USDA ERS county indicators (2019 / 2020 / 2023); actual recipient need is unverified.\nNo county is assigned to a fictional destination; service trade-offs are simulated.", "context")
    arrow((3.62, 6.38), (4.38, 6.38))
    arrow((3.62, 4.58), (4.38, 5.62))
    arrow((3.62, 2.75), (4.38, 5.08))
    arrow((6.5, 4.78), (6.5, 3.95), ":")
    ax.text(6.65, 4.33, "attention evidence only", fontsize=9, color="#285b83")
    arrow((10.7, 5.48), (8.63, 3.6), "--", "#b36b17")
    arrow((8.63, 2.97), (9.33, 3.95), "--", "#b36b17")
    arrow((11.45, 3.13), (11.45, 2.5), "--", "#b36b17")
    arrow((8.62, .72), (9.34, 3.3), ":", "#76618d")
    fig.text(.035, .015, "Blue solid: observed-data alignment    ··· Dotted: context / evidence only    — — Orange dashed: simulated decision pathway",
             fontsize=9.5, color="#43525d")
    fig.subplots_adjust(left=.025, right=.99, top=.99, bottom=.04)
    for extension in ("svg", "png", "pdf"):
        fig.savefig(args.output_dir / f"one_health_system.{extension}", dpi=220, facecolor="white")
    plt.close(fig)
    print(str(args.output_dir / "one_health_system.svg"))


if __name__ == "__main__":
    main()
