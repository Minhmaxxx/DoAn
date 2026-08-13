"""
pages/2_Lich_su.py — Meal History & Analytics
Shows historical meal logs with daily calorie trends, macro charts and summaries.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.nutrition import calculate_goal_calories, calculate_bmr, calculate_tdee
from utils.history import sort_meal_history
from utils.visualization import daily_calorie_chart, macro_donut_chart
from utils.state import initialize_session_state

# ─── Init state ───────────────────────────────────────────────────────────────
initialize_session_state()


def load_all_history() -> list[dict]:
    """Return meal history belonging only to the active browser session."""
    return sort_meal_history(st.session_state.meal_history)


def main():
    st.markdown('<h1 class="page-title">Lịch sử</h1>', unsafe_allow_html=True)
    st.caption("Các bữa ăn đã lưu trong phiên hiện tại.")
    st.markdown("---")

    history = load_all_history()

    if not history:
        st.info(
            "Chưa có bữa ăn nào. Phân tích ảnh rồi chọn Lưu bữa ăn để bắt đầu."
        )
        _render_demo_history()
        return

    # ── Summary Stats ──────────────────────────────────────────────────────
    profile = st.session_state.user_profile
    bmr = calculate_bmr(profile["weight_kg"], profile["height_cm"],
                        profile["age"], profile["gender"])
    tdee = calculate_tdee(bmr, profile["activity_level"])
    goal_info = calculate_goal_calories(tdee, profile["goal"])
    target_cal = goal_info["target_calories"]

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_meals = [r for r in history if r.get("date") == today_str]
    today_calories = sum(r["totals"]["calories"] for r in today_meals)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Hôm nay", f"{today_calories:.0f} kcal",
                f"{today_calories - target_cal:+.0f} kcal vs mục tiêu")
    col2.metric("Bữa hôm nay", len(today_meals))
    col3.metric("Đã lưu", len(history))
    col4.metric("Mục tiêu", f"{target_cal:.0f} kcal")

    st.markdown("---")

    # ── 7-Day Chart ────────────────────────────────────────────────────────
    st.markdown("### Calo 7 ngày")

    dates_7 = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    calories_7 = []
    for d in dates_7:
        day_meals = [r for r in history if r.get("date") == d]
        calories_7.append(sum(r["totals"]["calories"] for r in day_meals))

    display_dates = [(datetime.now() - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    fig_hist = daily_calorie_chart(display_dates, calories_7, target_cal)
    st.plotly_chart(fig_hist, width="stretch", config={"displayModeBar": False})

    st.markdown("---")

    # ── Recent Meals Table ──────────────────────────────────────────────────
    st.markdown("### Bữa ăn")

    tab_all, tab_today = st.tabs(["Tất cả", "Hôm nay"])

    with tab_all:
        _render_history_table(history[:50])

    with tab_today:
        if today_meals:
            _render_history_table(today_meals)
        else:
            st.info("Chưa có bữa ăn hôm nay.")

    st.markdown("---")

    # ── Weekly Macro Breakdown ──────────────────────────────────────────────
    st.markdown("### Macro tuần này")
    week_meals = [r for r in history if r.get("date") in dates_7]
    if week_meals:
        total_carb = sum(r["totals"].get("carbohydrate_g", 0) for r in week_meals)
        total_protein = sum(r["totals"].get("protein_g", 0) for r in week_meals)
        total_fat = sum(r["totals"].get("fat_g", 0) for r in week_meals)

        col_macro, col_text = st.columns([1, 1])
        with col_macro:
            fig_macro = macro_donut_chart(total_carb, total_protein, total_fat,
                                          title="Tổng Macro Tuần Này")
            st.plotly_chart(fig_macro, width="stretch", config={"displayModeBar": False})
        with col_text:
            st.markdown("Tổng kết")
            avg_cal = sum(calories_7) / 7
            st.metric("Trung bình/ngày", f"{avg_cal:.0f} kcal")
            days_on_target = sum(1 for c in calories_7 if abs(c - target_cal) <= target_cal * 0.1)
            st.metric("Đạt mục tiêu", f"{days_on_target}/7 ngày")
            st.metric("Carb", f"{total_carb:.0f}g")
            st.metric("Protein", f"{total_protein:.0f}g")
            st.metric("Fat", f"{total_fat:.0f}g")
    else:
        st.info("Chưa có bữa ăn trong 7 ngày qua.")

    # ── Clear History ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("Xóa lịch sử"):
        st.warning("Không thể hoàn tác.")
        if st.button("Xóa tất cả", type="secondary"):
            st.session_state.meal_history = []
            st.success("Đã xóa.")
            st.rerun()


def _render_history_table(records: list[dict]):
    if not records:
        st.info("Không có dữ liệu.")
        return

    rows = []
    for r in records:
        foods_str = ", ".join(
            f"{f['display_name']} ({f['portion_multiplier']}x)"
            for f in r.get("foods", [])
        )
        rows.append({
            "Thời gian": f"{r.get('date', '?')} {r.get('time', '')}",
            "Bữa ăn": r.get("meal_type", ""),
            "Món ăn": foods_str,
            "Calo": f"{r['totals']['calories']:.0f} kcal",
            "Carb": f"{r['totals'].get('carbohydrate_g', 0):.0f}g",
            "Protein": f"{r['totals'].get('protein_g', 0):.0f}g",
            "Fat": f"{r['totals'].get('fat_g', 0):.0f}g",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)


def _render_demo_history():
    """Show demo chart with placeholder data."""
    st.markdown("### Ví dụ: Calo 7 ngày")
    demo_dates = [(datetime.now() - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    demo_calories = [1850, 2100, 1780, 2050, 1920, 2200, 1750]
    fig = daily_calorie_chart(demo_dates, demo_calories, 2000, "Ví dụ: Calo 7 Ngày (Demo)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("_Dữ liệu trên chỉ là ví dụ minh họa._")


if __name__ == "__main__":
    main()
