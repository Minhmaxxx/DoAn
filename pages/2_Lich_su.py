"""
pages/2_Lich_su.py — Meal History & Analytics
Shows historical meal logs with daily calorie trends, macro charts and summaries.
"""

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.nutrition import calculate_goal_calories, calculate_bmr, calculate_tdee
from utils.history import sort_meal_history, vietnam_now
from utils.auth import sync_status
from utils.repository import get_repository
from utils.visualization import daily_calorie_chart, macro_donut_chart
from utils.state import initialize_session_state
from utils.ui import (
    render_empty_state,
    render_page_header,
    render_section_header,
    render_stat_grid,
)

# ─── Init state ───────────────────────────────────────────────────────────────
initialize_session_state()


def load_all_history() -> list[dict]:
    """Return this account's meal history, newest first.

    Reads the session copy rather than re-querying on every rerun: app.py
    hydrates it once after restoring a session, and the analysis page refreshes
    it after each successful save. For guests this is the only copy there is.
    """
    return sort_meal_history(st.session_state.meal_history)


def main():
    status = sync_status()
    render_page_header(
        {
            "guest": "NHẬT KÝ THEO PHIÊN",
            "anonymous": "NHẬT KÝ TRÊN MÁY CHỦ",
            "linked": "NHẬT KÝ ĐÃ ĐỒNG BỘ",
        }[status],
        "Lịch sử bữa ăn.",
        "Nhìn lại năng lượng, macro và nhịp ăn trong bảy ngày gần nhất.",
        meta="GIỜ VIỆT NAM",
    )

    history = load_all_history()

    if not history:
        render_empty_state(
            "Chưa có bữa ăn được lưu",
            "Phân tích một ảnh và xác nhận khẩu phần để bắt đầu nhật ký.",
            "00",
        )
        if st.button("Phân tích bữa ăn đầu tiên", type="primary"):
            st.switch_page("pages/1_Phan_tich_anh.py")
        with st.expander("Xem biểu đồ minh họa"):
            _render_demo_history()
        return

    # ── Summary Stats ──────────────────────────────────────────────────────
    profile = st.session_state.user_profile
    bmr = calculate_bmr(profile["weight_kg"], profile["height_cm"],
                        profile["age"], profile["gender"])
    tdee = calculate_tdee(bmr, profile["activity_level"])
    goal_info = calculate_goal_calories(tdee, profile["goal"])
    target_cal = goal_info["target_calories"]

    now = vietnam_now()
    today_str = now.strftime("%Y-%m-%d")
    today_meals = [r for r in history if r.get("date") == today_str]
    today_calories = sum(r["totals"]["calories"] for r in today_meals)

    render_stat_grid(
        [
            ("HÔM NAY", f"{today_calories:.0f}", "kcal đã ghi"),
            ("BỮA HÔM NAY", str(len(today_meals)), "bữa đã xác nhận"),
            (
                "TỔNG ĐÃ LƯU",
                str(len(history)),
                "trong phiên này" if status == "guest" else "trong tài khoản",
            ),
        ]
    )

    render_section_header("01", "Nhịp calo 7 ngày", "Đường mục tiêu dựa trên hồ sơ đã lưu.")

    dates_7 = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    calories_7 = []
    for d in dates_7:
        day_meals = [r for r in history if r.get("date") == d]
        calories_7.append(sum(r["totals"]["calories"] for r in day_meals))

    display_dates = [(now - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    with st.container(key="history-chart"):
        fig_hist = daily_calorie_chart(display_dates, calories_7, target_cal)
        st.plotly_chart(fig_hist, width="stretch", config={"displayModeBar": False})

    render_section_header(
        "02",
        "Các bữa đã xác nhận",
        "Tối đa 50 bản ghi gần nhất trong phiên."
        if status == "guest"
        else "Tối đa 50 bản ghi gần nhất trong tài khoản.",
    )

    with st.container(key="history-meals"):
        tab_all, tab_today = st.tabs(["Tất cả", "Hôm nay"])

        with tab_all:
            _render_history_table(history[:50])

        with tab_today:
            if today_meals:
                _render_history_table(today_meals)
            else:
                st.info("Chưa có bữa ăn hôm nay.")

    render_section_header("03", "Macro tuần này", "Tổng hợp carb, protein và chất béo của bảy ngày.")
    week_meals = [r for r in history if r.get("date") in dates_7]
    if week_meals:
        total_carb = sum(r["totals"].get("carbohydrate_g", 0) for r in week_meals)
        total_protein = sum(r["totals"].get("protein_g", 0) for r in week_meals)
        total_fat = sum(r["totals"].get("fat_g", 0) for r in week_meals)

        with st.container(key="history-week"):
            col_macro, col_text = st.columns([1.15, 0.85], gap="large")
            with col_macro:
                fig_macro = macro_donut_chart(total_carb, total_protein, total_fat,
                                              title="Tổng Macro Tuần Này")
                st.plotly_chart(fig_macro, width="stretch", config={"displayModeBar": False})
            with col_text:
                avg_cal = sum(calories_7) / 7
                days_on_target = sum(1 for c in calories_7 if abs(c - target_cal) <= target_cal * 0.1)
                st.metric("Trung bình/ngày", f"{avg_cal:.0f} kcal")
                st.metric("Đạt mục tiêu", f"{days_on_target}/7 ngày")
                st.metric("Carb / Protein / Fat", f"{total_carb:.0f} / {total_protein:.0f} / {total_fat:.0f}g")
    else:
        st.info("Chưa có bữa ăn trong 7 ngày qua.")

    # ── Clear History ────────────────────────────────────────────────────────
    with st.expander("Xóa lịch sử"):
        st.warning("Không thể hoàn tác.")
        if st.button("Xóa tất cả", type="secondary"):
            try:
                get_repository().delete_all_meals()
            except Exception as error:
                st.error(f"Không xóa được trên máy chủ: {error}")
            else:
                # SessionRepository clears session state itself; a cloud delete
                # only touches the database, so clear the session copy here too.
                st.session_state.meal_history = []
                st.session_state.saved_meal_signatures = set()
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
    now = vietnam_now()
    demo_dates = [(now - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    demo_calories = [1850, 2100, 1780, 2050, 1920, 2200, 1750]
    fig = daily_calorie_chart(demo_dates, demo_calories, 2000, "Ví dụ: Calo 7 Ngày (Demo)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("_Dữ liệu trên chỉ là ví dụ minh họa._")


if __name__ == "__main__":
    main()
