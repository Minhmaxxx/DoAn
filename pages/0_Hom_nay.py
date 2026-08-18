"""Personal home for the current NutriVision session."""

from __future__ import annotations

from html import escape
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.nutrition import calculate_bmr, calculate_goal_calories, calculate_tdee
from utils.history import vietnam_now
from utils.pwa import render_install_button
from utils.state import initialize_session_state
from utils.ui import render_page_header, render_stat_grid


initialize_session_state()


def main() -> None:
    profile = st.session_state.user_profile
    if st.session_state.profile_completed:
        bmr = calculate_bmr(
            profile["weight_kg"],
            profile["height_cm"],
            profile["age"],
            profile["gender"],
        )
        target_calories = calculate_goal_calories(
            calculate_tdee(bmr, profile["activity_level"]), profile["goal"]
        )["target_calories"]
    else:
        target_calories = 0
    today = vietnam_now().strftime("%Y-%m-%d")
    today_meals = [
        meal for meal in st.session_state.meal_history if meal.get("date") == today
    ]
    consumed = sum(meal["totals"]["calories"] for meal in today_meals)
    remaining = max(target_calories - consumed, 0)
    progress = min(consumed / target_calories * 100, 100) if target_calories else 0
    display_name = profile.get("name", "").strip()

    render_page_header(
        "NHỊP DINH DƯỠNG HÔM NAY",
        f"Chào {display_name}." if display_name else "Hôm nay ăn gì?",
        "Một ảnh cho mỗi bữa, một bản tổng kết đủ rõ để bạn điều chỉnh.",
        meta=vietnam_now().strftime("%d.%m.%Y"),
    )

    with st.container(key="today-layout"):
        energy, action = st.columns([1.25, 0.75], gap="large")
        with energy:
            target_text = f"Mục tiêu {target_calories:.0f} kcal" if target_calories else "Chưa có mục tiêu"
            st.markdown(
                f"""
                <div class="energy-card">
                    <div class="energy-card-head"><span>NĂNG LƯỢNG ĐÃ GHI</span><b>{escape(target_text)}</b></div>
                    <div class="energy-card-total"><strong>{consumed:.0f} <small>kcal</small></strong><span>{remaining:.0f} kcal còn lại</span></div>
                    <div class="energy-meter"><i style="--progress:{progress:.1f}%"></i></div>
                    <div class="energy-card-foot"><span>0</span><span>{progress:.0f}% mục tiêu ngày</span><span>{target_calories:.0f}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with action:
            if not st.session_state.profile_completed:
                st.markdown(
                    "<div class='action-card'><span>BƯỚC TIẾP THEO</span><strong>Hoàn tất hồ sơ</strong><p>Lưu thông tin cơ thể để mở mục tiêu calo và phân tích cá nhân.</p></div>",
                    unsafe_allow_html=True,
                )
                if st.button("Điền hồ sơ", type="primary", width="stretch"):
                    st.switch_page("pages/3_Ho_so.py")
            elif not today_meals:
                st.markdown(
                    "<div class='action-card'><span>BỮA ĐẦU TIÊN</span><strong>Chụp món bạn vừa ăn</strong><p>AI gợi ý món, còn bạn xác nhận nhãn và khẩu phần trước khi lưu.</p></div>",
                    unsafe_allow_html=True,
                )
                if st.button("Phân tích bữa ăn", type="primary", width="stretch"):
                    st.switch_page("pages/1_Phan_tich_anh.py")
            else:
                latest = today_meals[-1]
                foods = ", ".join(food["display_name"] for food in latest.get("foods", []))
                st.markdown(
                    f"<div class='action-card'><span>BỮA GẦN NHẤT</span><strong>{escape(foods or 'Bữa ăn đã lưu')}</strong><p>{latest['totals']['calories']:.0f} kcal · {escape(latest.get('meal_type', 'Đã lưu'))}</p></div>",
                    unsafe_allow_html=True,
                )
                first, second = st.columns(2)
                with first:
                    if st.button("Thêm bữa", type="primary", width="stretch"):
                        st.switch_page("pages/1_Phan_tich_anh.py")
                with second:
                    if st.button("Lịch sử", width="stretch"):
                        st.switch_page("pages/2_Lich_su.py")

    render_stat_grid(
        [
            ("BỮA HÔM NAY", str(len(today_meals)), "Đã xác nhận và lưu"),
            ("CÒN LẠI", f"{remaining:.0f}", "kcal theo mục tiêu"),
            ("TRẠNG THÁI", "Sẵn sàng" if st.session_state.profile_completed else "Thiếu hồ sơ", "Dữ liệu trong phiên"),
        ]
    )

    with st.expander("Cài NutriVision lên màn hình chính"):
        render_install_button()

    with st.expander("Dữ liệu của bạn"):
        st.markdown(
            "Hồ sơ và lịch sử hiện chỉ tồn tại trong phiên trình duyệt này. "
            "Phiên bản sau sẽ dùng khóa cá nhân để khôi phục dữ liệu trên thiết bị khác."
        )


if __name__ == "__main__":
    main()
