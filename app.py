"""
app.py — NutriVision: Personalized Nutrition Advisory System
Main Streamlit entry point.

Run:
    streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st

# ─── Page configuration (MUST be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="NutriVision — Trợ lý Dinh dưỡng AI",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/yourusername/nutrivision",
        "About": "## NutriVision\nHệ thống Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa\nYOLOv8 + HITL + LLM"
    }
)

# ─── Load custom CSS ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Initialize session state ─────────────────────────────────────────────────
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "",
        "age": 22,
        "gender": "Nam",
        "weight_kg": 65.0,
        "height_cm": 170.0,
        "activity_level": "Vừa phải (3-5 ngày/tuần)",
        "goal": "Giữ cân",
    }

if "meal_history" not in st.session_state:
    st.session_state.meal_history = []

if "current_meal" not in st.session_state:
    st.session_state.current_meal = None

# ─── Landing Page ─────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div class="hero-header">
        <div class="hero-icon"></div>
        <h1 class="hero-title">NutriVision</h1>
        <p class="hero-subtitle">
            Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa<br>
            <span class="hero-tagline">YOLOv8 Computer Vision · Human-in-the-Loop · AI Language Model</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Feature cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon"></div>
            <h3>Nhận diện Món ăn</h3>
            <p>Chụp ảnh bữa ăn và hệ thống tự động nhận diện tên món, 
            số lượng bằng YOLOv8 được huấn luyện trên 10 món ăn Việt Nam.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon"></div>
            <h3>Tinh chỉnh Khẩu phần</h3>
            <p>Cơ chế Human-in-the-Loop giúp bạn điều chỉnh kích cỡ phần ăn 
            bằng thanh trượt để tính toán calo chính xác hơn.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon"></div>
            <h3>Tư vấn Cá nhân hóa</h3>
            <p>Trí tuệ nhân tạo Gemini/GPT phân tích dữ liệu sinh trắc học 
            và thực đơn của bạn, đưa ra lời khuyên bằng tiếng Việt.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Quick stats
    st.markdown("### Bắt đầu ngay")
    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.info("""
       **Hướng dẫn sử dụng:**
        1.  Điền **Hồ sơ cá nhân** → Trang *Hồ sơ*
        2.  Tải ảnh bữa ăn → Trang *Phân tích ảnh*
        3.  Tinh chỉnh khẩu phần bằng slider
        4.  Nhận lời khuyên dinh dưỡng từ AI
        5.  Xem lịch sử dinh dưỡng → Trang *Lịch sử*
        """)

    with col_b:
        st.markdown("""
        <div class="stats-card">
            <div class="stat-item">
                <span class="stat-number">10</span>
                <span class="stat-label">Món ăn VN</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">YOLOv8</span>
                <span class="stat-label">Object Detection</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">HITL</span>
                <span class="stat-label">Human-in-the-Loop</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # System status
    st.markdown("---")
    st.markdown("### Trạng thái Hệ thống")
    _show_system_status()


def _show_system_status():
    """Show current system configuration status."""
    import config
    from pathlib import Path

    col1, col2, col3 = st.columns(3)

    with col1:
        model_exists = Path(config.MODEL_PATH).exists()
        if model_exists:
            st.success(" Mô hình YOLOv8 đã sẵn sàng")
        else:
            st.warning(" Mô hình YOLOv8 chưa huấn luyện — đang dùng Demo Mode")

    with col2:
        has_key = bool(config.GEMINI_API_KEY or config.OPENAI_API_KEY)
        if has_key:
            provider = config.LLM_PROVIDER.capitalize()
            st.success(f" LLM API ({provider}) đã cấu hình")
        else:
            st.warning(" Chưa có API key LLM — tư vấn sẽ dùng nội dung mẫu")

    with col3:
        db_exists = Path(config.NUTRITION_DB_PATH).exists()
        if db_exists:
            st.success(" Cơ sở dữ liệu dinh dưỡng đã tải")
        else:
            st.error(" Không tìm thấy nutrition_db.json")


if __name__ == "__main__":
    main()
