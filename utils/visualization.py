"""
utils/visualization.py — Plotly charts for nutrition data
Renders macro pie charts, daily calorie progress bars, and history trend lines.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px


# ─── Color Theme ─────────────────────────────────────────────────────────────

MACRO_COLORS = {
    "Carbohydrate": "#4ECDC4",
    "Protein": "#FF6B6B",
    "Fat": "#FFD93D",
    "Chất xơ": "#96CEB4",
}

CALORIE_GRADIENT = ["#2ECC71", "#F39C12", "#E74C3C"]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#e0e0e0"),
    margin=dict(l=10, r=10, t=40, b=10),
)


# ─── Macro Donut Chart ────────────────────────────────────────────────────────

def macro_donut_chart(
    carb_g: float,
    protein_g: float,
    fat_g: float,
    title: str = "Tỷ lệ Macronutrients",
) -> go.Figure:
    """
    Create a donut chart showing macro breakdown.

    Parameters
    ----------
    carb_g, protein_g, fat_g : float
        Macro amounts in grams.
    title : str
        Chart title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    labels = ["Carbohydrate", "Protein", "Fat"]
    values = [
        carb_g * 4,      # Convert to kcal: 4 kcal/g
        protein_g * 4,
        fat_g * 9,       # 9 kcal/g
    ]
    colors = [MACRO_COLORS[l] for l in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker_colors=colors,
        textinfo="label+percent",
        textfont=dict(size=13, color="white"),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "%{value:.0f} kcal<br>"
            + "<extra></extra>"
        ),
    )])

    total_kcal = sum(values)
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#e0e0e0"), x=0.5),
        annotations=[dict(
            text=f"<b>{total_kcal:.0f}</b><br>kcal",
            x=0.5, y=0.5,
            font_size=18,
            font_color="#e0e0e0",
            showarrow=False,
        )],
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(color="#e0e0e0"),
        ),
       **CHART_LAYOUT,
    )
    return fig


# ─── Calorie Progress Bar ─────────────────────────────────────────────────────

def calorie_gauge(
    current_cal: float,
    target_cal: float,
    title: str = "Calo Bữa Ăn",
) -> go.Figure:
    """
    Create a gauge chart showing calorie progress vs target.
    """
    ratio = min(current_cal / max(target_cal, 1), 1.5)  # cap at 150%
    pct = ratio * 100

    # Color based on progress
    if pct < 80:
        bar_color = "#4ECDC4"
    elif pct < 105:
        bar_color = "#2ECC71"
    elif pct < 120:
        bar_color = "#F39C12"
    else:
        bar_color = "#E74C3C"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_cal,
        number=dict(suffix=" kcal", font=dict(size=28, color="#e0e0e0")),
        delta=dict(
            reference=target_cal,
            valueformat=".0f",
            prefix="Δ",
            font=dict(size=16),
        ),
        gauge=dict(
            axis=dict(
                range=[0, target_cal * 1.5],
                tickfont=dict(color="#aaa"),
            ),
            bar=dict(color=bar_color, thickness=0.25),
            bgcolor="rgba(255,255,255,0.05)",
            borderwidth=0,
            steps=[
                dict(range=[0, target_cal * 0.8], color="rgba(255,255,255,0.03)"),
                dict(range=[target_cal * 0.8, target_cal], color="rgba(46,204,113,0.08)"),
                dict(range=[target_cal, target_cal * 1.5], color="rgba(231,76,60,0.08)"),
            ],
            threshold=dict(
                line=dict(color="#fff", width=2),
                thickness=0.75,
                value=target_cal,
            ),
        ),
        title=dict(text=f"<b>{title}</b><br>Mục tiêu: {target_cal:.0f} kcal", font=dict(size=14, color="#aaa")),
    ))
    fig.update_layout(height=280, **CHART_LAYOUT)
    return fig


# ─── Daily History Bar Chart ──────────────────────────────────────────────────

def daily_calorie_chart(
    dates: list[str],
    calories: list[float],
    target_cal: float,
    title: str = "Lịch sử Calo 7 Ngày",
) -> go.Figure:
    """
    Bar chart showing daily calorie intake vs target over time.
    """
    bar_colors = [
        "#2ECC71" if c <= target_cal * 1.05 else "#E74C3C"
        for c in calories
    ]

    fig = go.Figure()

    # Bars
    fig.add_trace(go.Bar(
        x=dates,
        y=calories,
        name="Calo tiêu thụ",
        marker_color=bar_colors,
        opacity=0.85,
        text=[f"{c:.0f}" for c in calories],
        textposition="outside",
        textfont=dict(color="#e0e0e0", size=12),
    ))

    # Target line
    fig.add_trace(go.Scatter(
        x=dates,
        y=[target_cal] * len(dates),
        name=f"Mục tiêu ({target_cal:.0f} kcal)",
        mode="lines",
        line=dict(color="#FFD93D", dash="dash", width=2),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#e0e0e0"), x=0.5),
        xaxis=dict(tickfont=dict(color="#aaa")),
        yaxis=dict(
            title="kcal",
            tickfont=dict(color="#aaa"),
            gridcolor="rgba(255,255,255,0.07)",
        ),
        legend=dict(font=dict(color="#e0e0e0")),
        bargap=0.25,
       **CHART_LAYOUT,
    )
    return fig


# ─── Macro Progress Bars ─────────────────────────────────────────────────────

def macro_progress_bars(
    meal_totals: dict,
    macro_targets: dict,
    title: str = "Tiến độ Macro (%)",
) -> go.Figure:
    """
    Horizontal bar chart comparing eaten macros vs daily targets.
    """
    macros = ["Carbohydrate", "Protein", "Fat"]
    keys = ["carbohydrate_g", "protein_g", "fat_g"]
    colors = [MACRO_COLORS[m] for m in macros]

    eaten = [meal_totals.get(k, 0) for k in keys]
    targets = [macro_targets.get(k, 1) for k in keys]
    pcts = [min(e / max(t, 1) * 100, 120) for e, t in zip(eaten, targets)]

    fig = go.Figure()

    # Background (target) bars
    fig.add_trace(go.Bar(
        name="Mục tiêu",
        y=macros,
        x=[100, 100, 100],
        orientation="h",
        marker_color="rgba(255,255,255,0.08)",
        showlegend=False,
    ))

    # Progress bars
    for i, (macro, pct, eaten_g, target_g, color) in enumerate(
        zip(macros, pcts, eaten, targets, colors)
    ):
        fig.add_trace(go.Bar(
            name=macro,
            y=[macro],
            x=[pct],
            orientation="h",
            marker_color=color,
            opacity=0.85,
            text=f"{eaten_g:.0f}g / {target_g:.0f}g",
            textposition="inside",
            textfont=dict(size=12, color="white"),
            showlegend=True,
        ))

    fig.update_layout(
        barmode="overlay",
        title=dict(text=title, font=dict(size=15, color="#e0e0e0"), x=0.5),
        xaxis=dict(
            range=[0, 120],
            title="%",
            tickfont=dict(color="#aaa"),
            gridcolor="rgba(255,255,255,0.07)",
        ),
        yaxis=dict(tickfont=dict(color="#e0e0e0", size=13)),
        height=220,
        legend=dict(font=dict(color="#e0e0e0")),
       **CHART_LAYOUT,
    )
    return fig
