"""Cost-breakdown charts: stacked bar + donut, rendered to PNG.

Same chart forms and the same render-to-PNG approach as the original
streamlit_map_eva11.py (a deliberate choice there to avoid chart flicker on
Streamlit rerun -- kept unchanged here per instructions). Styling comes
entirely from co2pipe.ui.theme constants (light surface, text tokens, the
validated 8-slot categorical palette) in fixed order, with a 2px
surface-color gap between stacked/wedge segments instead of a border stroke
(see the dataviz skill's marks-and-anatomy spec). Because every color here is
a theme.* reference rather than a hardcoded hex, a future theme swap (as just
happened, dark -> light) requires no changes in this file.
"""
from io import BytesIO
from typing import List, Sequence

import matplotlib.pyplot as plt
import numpy as np

from co2pipe.ui import theme

plt.rcParams["font.family"] = "sans-serif"

# Rendered pixel width for both charts. Passed explicitly to st.image(width=...)
# rather than relying on use_container_width, which isn't present on st.image
# in every Streamlit version (added later there than on other widgets) --
# requirements.txt pins no version, so avoid depending on it.
CHART_WIDTH_PX = 520


def _fig_to_png(fig, width_px: int = 540) -> BytesIO:
    """Render a Matplotlib fig to PNG bytes at a fixed width to keep layout stable
    across Streamlit reruns (unchanged from the original _fig_to_png)."""
    buf = BytesIO()
    target_dpi = 110
    fig.set_dpi(target_dpi)
    w_in = width_px / target_dpi
    if fig.get_figheight() < 1.0:
        fig.set_size_inches(w_in, w_in * 0.75, forward=True)
    else:
        fig.set_size_inches(w_in, fig.get_figheight(), forward=True)
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf


def _style_axes(ax) -> None:
    ax.set_facecolor(theme.SURFACE)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(theme.CHART_BASELINE)
    ax.tick_params(colors=theme.TEXT_MUTED)
    ax.yaxis.label.set_color(theme.TEXT_SECONDARY)
    ax.xaxis.label.set_color(theme.TEXT_SECONDARY)
    ax.title.set_color(theme.TEXT_PRIMARY)


def render_stacked_bar_png(cost_labels: Sequence[str], cost_values: Sequence[float], width_px: int = CHART_WIDTH_PX) -> BytesIO:
    """Stacked single-bar cost breakdown, in MMUSD."""
    colors = theme.CATEGORICAL[: len(cost_labels)]

    fig, ax = plt.subplots(figsize=(6, 7), dpi=110)
    fig.patch.set_facecolor(theme.SURFACE)
    _style_axes(ax)

    bottoms = [0.0]
    for i in range(1, len(cost_values)):
        bottoms.append(bottoms[-1] + cost_values[i - 1])

    vals_mm = [v / 1e6 for v in cost_values]
    bottoms_mm = [b / 1e6 for b in bottoms]

    ax.grid(axis="y", color=theme.CHART_GRIDLINE, linewidth=1, zorder=0)
    ax.set_axisbelow(True)

    for val, bottom, color, label in zip(vals_mm, bottoms_mm, colors, cost_labels):
        ax.bar(
            "Total", val, bottom=bottom, color=color, label=label, width=0.65,
            edgecolor=theme.SURFACE, linewidth=2, zorder=3,
        )

    ax.set_ylabel("Cost (MMUSD)")
    ax.set_xticks([])
    ax.set_title("CO₂ Offshore Pipeline Stacked Cost Breakdown", pad=36)

    handles, labels = ax.get_legend_handles_labels()
    legend = fig.legend(
        handles, labels,
        loc="lower center", bbox_to_anchor=(0.5, 0.995), ncol=3,
        fontsize=9, frameon=False, title="Categories", title_fontsize=10,
    )
    legend.get_title().set_color(theme.TEXT_SECONDARY)
    for text in legend.get_texts():
        text.set_color(theme.TEXT_SECONDARY)

    fig.subplots_adjust(top=0.78)

    png = _fig_to_png(fig, width_px=width_px)
    plt.close(fig)
    return png


def render_donut_png(cost_labels: Sequence[str], cost_values: Sequence[float], width_px: int = CHART_WIDTH_PX) -> BytesIO:
    """Donut chart share-of-total cost breakdown, with direct % labels."""
    colors = theme.CATEGORICAL[: len(cost_labels)]

    fig, ax = plt.subplots(figsize=(6, 6), dpi=110)
    fig.patch.set_facecolor(theme.SURFACE)
    ax.set_facecolor(theme.SURFACE)
    ax.title.set_color(theme.TEXT_PRIMARY)

    wedges, _texts = ax.pie(
        cost_values,
        labels=None,
        autopct=None,
        startangle=140,
        colors=colors,
        wedgeprops=dict(width=0.38, edgecolor=theme.SURFACE, linewidth=2),
    )

    total = float(sum(cost_values))
    for i, w in enumerate(wedges):
        angle = (w.theta2 + w.theta1) / 2.0
        pct = 100.0 * cost_values[i] / total
        x = 0.95 * np.cos(np.deg2rad(angle))
        y = 0.95 * np.sin(np.deg2rad(angle))
        ax.annotate(
            f"{pct:.1f}%",
            xy=(x, y),
            xytext=(1.12 * x, 1.12 * y),
            textcoords="data",
            ha="center", va="center", fontsize=10,
            arrowprops=dict(arrowstyle="-", lw=0.8, color=theme.TEXT_MUTED),
            color=theme.TEXT_SECONDARY,
        )

    ax.axis("equal")
    ax.set_title("Cost Share by Category", pad=36)

    legend = fig.legend(
        wedges, cost_labels,
        loc="lower center", bbox_to_anchor=(0.5, 0.995), ncol=3,
        fontsize=9, frameon=False, title="Categories", title_fontsize=10,
    )
    legend.get_title().set_color(theme.TEXT_SECONDARY)
    for text in legend.get_texts():
        text.set_color(theme.TEXT_SECONDARY)

    fig.subplots_adjust(top=0.78)

    png = _fig_to_png(fig, width_px=width_px)
    plt.close(fig)
    return png
