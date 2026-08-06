"""
app.py — NutriVision: Personalized Nutrition Advisory System
Main Streamlit entry point.

Run:
    streamlit run app.py
"""

import hashlib
import json
from pathlib import Path

import streamlit as st

import config
from utils.state import initialize_session_state

# ─── Page configuration (MUST be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title=config.APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/Minhmaxxx/DoAn",
        "About": "## NutriVision\nYOLOv8n Baseline B · 12 lớp · HITL · LLM"
    }
)

# ─── Load custom CSS ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

initialize_session_state()

# ─── Landing Page ─────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div class="hero-header">
        <div class="hero-kicker">PERSONALIZED NUTRITION VISION</div>
        <h1 class="hero-title">NutriVision</h1>
        <p class="hero-subtitle">
            Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa<br>
            <span class="hero-tagline">YOLOv8n Baseline B · 12 lớp món ăn · Human-in-the-Loop</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Feature cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-index">01</div>
            <h3>Nhận diện Món ăn</h3>
            <p>Chụp ảnh bữa ăn và hệ thống tự động nhận diện tên món, 
            vị trí bằng YOLOv8n được huấn luyện trên 12 lớp món ăn Việt Nam.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-index">02</div>
            <h3>Tinh chỉnh Khẩu phần</h3>
            <p>Cơ chế Human-in-the-Loop giúp bạn điều chỉnh kích cỡ phần ăn 
            bằng thanh trượt để tính toán calo chính xác hơn.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-index">03</div>
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
                <span class="stat-number">12</span>
                <span class="stat-label">Lớp món ăn VN</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">0.901</span>
                <span class="stat-label">mAP50 benchmark sạch</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">B</span>
                <span class="stat-label">Model triển khai</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # System status
    st.markdown("---")
    st.markdown("### Trạng thái Hệ thống")
    _show_system_status()


def _show_system_status():
    """Show current system configuration status."""
    col1, col2, col3 = st.columns(3)

    with col1:
        if config.MODEL_PATH.exists():
            digest = hashlib.sha256(config.MODEL_PATH.read_bytes()).hexdigest()
            if digest == config.MODEL_SHA256:
                st.success("Baseline B · 12 lớp · checksum hợp lệ")
            else:
                st.error("Checkpoint tồn tại nhưng checksum không hợp lệ")
        else:
            st.error(f"Thiếu checkpoint: {config.MODEL_PATH.name}")

    with col2:
        runtime_config = st.session_state.get("llm_runtime_config", {})
        provider = runtime_config.get("provider", config.LLM_PROVIDER)
        runtime_key = runtime_config.get(f"{provider}_api_key", "").strip()
        environment_key = config.GEMINI_API_KEY if provider == "gemini" else config.OPENAI_API_KEY
        has_key = bool(runtime_key or environment_key)
        if has_key:
            st.success(f"LLM {provider.capitalize()} đã cấu hình")
        else:
            st.info("Chưa có API key · dùng tư vấn mẫu")

    with col3:
        try:
            with config.NUTRITION_DB_PATH.open(encoding="utf-8") as file:
                food_count = len(json.load(file)["foods"])
            if food_count == len(config.FOOD_CLASSES):
                st.success(f"Dinh dưỡng {food_count}/{len(config.FOOD_CLASSES)} món")
            else:
                st.error(f"Dinh dưỡng mới có {food_count}/{len(config.FOOD_CLASSES)} món")
        except (OSError, KeyError, json.JSONDecodeError) as error:
            st.error(f"Lỗi nutrition DB: {error}")


if __name__ == "__main__":
    main()
