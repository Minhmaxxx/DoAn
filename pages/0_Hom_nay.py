"""Personal home for the current NutriVision session."""

from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.nutrition import calculate_bmr, calculate_goal_calories, calculate_tdee
from utils.state import initialize_session_state


initialize_session_state()


def main() -> None:
    profile = st.session_state.user_profile
    bmr = calculate_bmr(
        profile["weight_kg"], profile["height_cm"], profile["age"], profile["gender"]
    )
    target_calories = calculate_goal_calories(
        calculate_tdee(bmr, profile["activity_level"]), profile["goal"]
    )["target_calories"]
    today = datetime.now().strftime("%Y-%m-%d")
    today_meals = [
        meal for meal in st.session_state.meal_history if meal.get("date") == today
    ]
    consumed = sum(meal["totals"]["calories"] for meal in today_meals)

    st.markdown('<h1 class="page-title">Hôm nay</h1>', unsafe_allow_html=True)
    st.caption("Tổng quan bữa ăn trong phiên hiện tại.")

    metrics = st.columns(3)
    metrics[0].metric("Đã ăn", f"{consumed:.0f} kcal")
    metrics[1].metric("Còn lại", f"{max(target_calories - consumed, 0):.0f} kcal")
    metrics[2].metric("Bữa đã lưu", len(today_meals))

    st.markdown("---")
    if not profile.get("name"):
        st.markdown(
            "<div class='today-panel'><strong>Hoàn tất hồ sơ trước</strong>"
            "<span>Chỉ mất một phút để tính mục tiêu phù hợp với bạn.</span></div>",
            unsafe_allow_html=True,
        )
        if st.button("Điền hồ sơ", type="primary", width="stretch"):
            st.switch_page("pages/3_Ho_so.py")
    elif not today_meals:
        st.markdown(
            "<div class='today-panel'><strong>Chưa có bữa ăn hôm nay</strong>"
            "<span>Thêm ảnh bữa ăn đầu tiên để bắt đầu theo dõi.</span></div>",
            unsafe_allow_html=True,
        )
        if st.button("Phân tích bữa ăn", type="primary", width="stretch"):
            st.switch_page("pages/1_Phan_tich_anh.py")
    else:
        latest = today_meals[-1]
        foods = ", ".join(food["display_name"] for food in latest.get("foods", []))
        st.markdown(
            "<div class='today-panel'><strong>Bữa gần nhất</strong>"
            f"<span>{foods or 'Bữa ăn đã lưu'} · {latest['totals']['calories']:.0f} kcal</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        first, second = st.columns(2)
        with first:
            if st.button("Thêm bữa ăn", type="primary", width="stretch"):
                st.switch_page("pages/1_Phan_tich_anh.py")
        with second:
            if st.button("Xem lịch sử", width="stretch"):
                st.switch_page("pages/2_Lich_su.py")

    with st.expander("Dữ liệu của bạn"):
        st.markdown(
            "Hồ sơ và lịch sử hiện chỉ tồn tại trong phiên trình duyệt này. "
            "Phiên bản sau sẽ dùng khóa cá nhân để khôi phục dữ liệu trên thiết bị khác."
        )


if __name__ == "__main__":
    main()
