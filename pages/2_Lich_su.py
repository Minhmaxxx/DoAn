"""
pages/2_Lich_su.py — Meal History & Analytics
Shows historical meal logs with daily calorie trends, macro charts and summaries.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import config
from utils.nutrition import calculate_goal_calories, calculate_bmr, calculate_tdee
from utils.visualization import daily_calorie_chart, macro_donut_chart

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lịch sử — NutriVision",
    page_icon="📊",
    layout="wide",
)

css_path = ROOT_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Init state ───────────────────────────────────────────────────────────────
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "age": 22, "gender": "Nam", "weight_kg": 65.0,
        "height_cm": 170.0, "activity_level": "Vừa phải (3-5 ngày/tuần)",
        "goal": "Giữ cân",
    }
if "meal_history" not in st.session_state:
    st.session_state.meal_history = []


def load_all_history() -> list[dict]:
    """Load history from both session state and disk."""
    records = list(st.session_state.meal_history)

    if config.MEAL_HISTORY_PATH.exists():
        try:
            with open(config.MEAL_HISTORY_PATH, "r", encoding="utf-8") as f:
                disk_records = json.load(f)
            # Merge, avoiding duplicates by timestamp
            existing_ts = {r["timestamp"] for r in records}
            for r in disk_records:
                if r["timestamp"] not in existing_ts:
                    records.append(r)
        except Exception:
            pass

    return sorted(records, key=lambda r: r["timestamp"], reverse=True)


def main():
    st.markdown('<h1 class="page-title">📊 Lịch sử Dinh dưỡng</h1>', unsafe_allow_html=True)
    st.markdown("Theo dõi tiến trình ăn uống và xu hướng dinh dưỡng theo thời gian.")
    st.markdown("---")

    history = load_all_history()

    if not history:
        st.info(
            "📭 Chưa có dữ liệu lịch sử. "
            "Hãy phân tích một bữa ăn và lưu lại tại trang **Phân tích ảnh**."
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
    col1.metric("📅 Hôm nay", f"{today_calories:.0f} kcal",
                f"{today_calories - target_cal:+.0f} kcal vs mục tiêu")
    col2.metric("🍽️ Số bữa hôm nay", len(today_meals))
    col3.metric("📆 Tổng bữa đã ghi", len(history))
    col4.metric("🎯 Mục tiêu/ngày", f"{target_cal:.0f} kcal")

    st.markdown("---")

    # ── 7-Day Chart ────────────────────────────────────────────────────────
    st.markdown("### 📈 Calo 7 Ngày Gần Nhất")

    dates_7 = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    calories_7 = []
    for d in dates_7:
        day_meals = [r for r in history if r.get("date") == d]
        calories_7.append(sum(r["totals"]["calories"] for r in day_meals))

    display_dates = [(datetime.now() - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    fig_hist = daily_calorie_chart(display_dates, calories_7, target_cal)
    st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")

    # ── Recent Meals Table ──────────────────────────────────────────────────
    st.markdown("### 🍽️ Danh sách Bữa ăn Gần đây")

    tab_all, tab_today = st.tabs(["Tất cả", "Hôm nay"])

    with tab_all:
        _render_history_table(history[:50])

    with tab_today:
        if today_meals:
            _render_history_table(today_meals)
        else:
            st.info("Chưa có bữa ăn nào được ghi hôm nay.")

    st.markdown("---")

    # ── Weekly Macro Breakdown ──────────────────────────────────────────────
    st.markdown("### 🥗 Phân tích Macro Tuần Này")
    week_meals = [r for r in history if r.get("date") in dates_7]
    if week_meals:
        total_carb = sum(r["totals"].get("carbohydrate_g", 0) for r in week_meals)
        total_protein = sum(r["totals"].get("protein_g", 0) for r in week_meals)
        total_fat = sum(r["totals"].get("fat_g", 0) for r in week_meals)

        col_macro, col_text = st.columns([1, 1])
        with col_macro:
            fig_macro = macro_donut_chart(total_carb, total_protein, total_fat,
                                          title="Tổng Macro Tuần Này")
            st.plotly_chart(fig_macro, use_container_width=True, config={"displayModeBar": False})
        with col_text:
            st.markdown("#### Tổng kết 7 ngày")
            avg_cal = sum(calories_7) / 7
            st.metric("Trung bình calo/ngày", f"{avg_cal:.0f} kcal")
            days_on_target = sum(1 for c in calories_7 if abs(c - target_cal) <= target_cal * 0.1)
            st.metric("Ngày đạt mục tiêu (±10%)", f"{days_on_target}/7 ngày")
            st.metric("Tổng Carb tuần", f"{total_carb:.0f}g")
            st.metric("Tổng Protein tuần", f"{total_protein:.0f}g")
            st.metric("Tổng Fat tuần", f"{total_fat:.0f}g")
    else:
        st.info("Chưa có đủ dữ liệu tuần này.")

    # ── Clear History ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚠️ Xóa lịch sử"):
        st.warning("Hành động này sẽ xóa toàn bộ lịch sử bữa ăn và không thể hoàn tác.")
        if st.button("🗑️ Xóa tất cả lịch sử", type="secondary"):
            st.session_state.meal_history = []
            if config.MEAL_HISTORY_PATH.exists():
                config.MEAL_HISTORY_PATH.unlink()
            st.success("Đã xóa lịch sử.")
            st.rerun()


def _render_history_table(records: list[dict]):
    if not records:
        st.info("Không có dữ liệu.")
        return

    rows = []
    for r in records:
        foods_str = ", ".join(
            f"{f['emoji']} {f['display_name']} ({f['portion_multiplier']}x)"
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
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_demo_history():
    """Show demo chart with placeholder data."""
    st.markdown("### 📈 Ví dụ: Biểu đồ Calo 7 Ngày")
    demo_dates = [(datetime.now() - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    demo_calories = [1850, 2100, 1780, 2050, 1920, 2200, 1750]
    fig = daily_calorie_chart(demo_dates, demo_calories, 2000, "Ví dụ: Calo 7 Ngày (Demo)")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("_Dữ liệu trên chỉ là ví dụ minh họa._")


if __name__ == "__main__":
    main()
