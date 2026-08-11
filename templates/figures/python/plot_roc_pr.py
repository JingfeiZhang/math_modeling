from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, configure_style, export_triplet, load_verified_csv, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot cross-validation ROC and precision-recall curves with explicit baselines.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="roc-pr")
    args = parser.parse_args()

    configure_style()
    required = ["fold", "fpr", "tpr", "recall", "precision", "prevalence"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["fpr", "tpr", "recall", "precision", "prevalence"])
    for column in ["fpr", "tpr", "recall", "precision", "prevalence"]:
        if ((frame[column] < 0) | (frame[column] > 1)).any():
            raise ValueError(f"Column must be within [0, 1]: {column}")
    prevalence_values = frame["prevalence"].drop_duplicates()
    if len(prevalence_values) != 1:
        raise ValueError("A single evidence-grounded prevalence is required for the PR baseline")
    prevalence = float(prevalence_values.iloc[0])
    grid = np.linspace(0, 1, 201)
    tprs = []
    precisions = []

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.05), constrained_layout=True)
    for _, fold in frame.groupby("fold", sort=True):
        roc = fold.sort_values("fpr")
        pr = fold.sort_values("recall")
        axes[0].plot(roc["fpr"], roc["tpr"], color=COLORS["primary"], alpha=0.25, linewidth=0.8)
        axes[1].plot(pr["recall"], pr["precision"], color=COLORS["positive"], alpha=0.25, linewidth=0.8)
        tprs.append(np.interp(grid, roc["fpr"], roc["tpr"]))
        precisions.append(np.interp(grid, pr["recall"], pr["precision"]))
    mean_tpr = np.mean(tprs, axis=0)
    mean_precision = np.mean(precisions, axis=0)
    auc_roc = float(np.trapezoid(mean_tpr, grid))
    auc_pr = float(np.trapezoid(mean_precision, grid))

    axes[0].plot([0, 1], [0, 1], color=COLORS["neutral"], linestyle=":", label="Random baseline")
    axes[0].plot(grid, mean_tpr, color=COLORS["primary"], label=f"Mean ROC (AUC={auc_roc:.3f})")
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="(a) ROC")
    axes[1].axhline(prevalence, color=COLORS["neutral"], linestyle=":", label=f"Prevalence={prevalence:.3f}")
    axes[1].plot(grid, mean_precision, color=COLORS["positive"], label=f"Mean PR (AUC={auc_pr:.3f})")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="(b) Precision-recall")
    for ax in axes:
        ax.set(xlim=(0, 1), ylim=(0, 1))
        style_axis(ax)
        ax.legend(loc="lower right")
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
