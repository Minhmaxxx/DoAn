"""Model benchmark dashboard for Baseline A0, A, and B."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT_DIR = Path(__file__).parent.parent
RESULTS_DIR = ROOT_DIR / "test_model" / "benchmark_results_common_v1"
BENCHMARK_DIR = ROOT_DIR / "test_model" / "benchmark_common_v1"


@st.cache_data
def load_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    overall = pd.read_csv(RESULTS_DIR / "overall_metrics.csv")
    per_class = pd.read_csv(RESULTS_DIR / "per_class_metrics.csv")
    return overall, per_class


def metric_chart(overall: pd.DataFrame) -> go.Figure:
    colors = {"Baseline_A0": "#94A3B8", "Baseline_A": "#4ECDC4", "Baseline_B": "#FF6B6B"}
    fig = go.Figure()
    for model_name in overall["model"]:
        row = overall[overall["model"] == model_name].iloc[0]
        fig.add_trace(
            go.Bar(
                name=model_name.replace("_", " "),
                x=["Precision", "Recall", "mAP50", "mAP50-95"],
                y=[row["precision"], row["recall"], row["mAP50"], row["mAP50_95"]],
                marker_color=colors[model_name],
                text=[f"{value:.3f}" for value in [row["precision"], row["recall"], row["mAP50"], row["mAP50_95"]]],
                textposition="outside",
            )
        )
    fig.update_layout(
        barmode="group",
        height=430,
        yaxis=dict(range=[0, 1.05], title="Điểm", gridcolor="rgba(255,255,255,0.08)"),
        xaxis_title=None,
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0"),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def main() -> None:
    st.markdown('<h1 class="page-title">Đánh giá Mô hình</h1>', unsafe_allow_html=True)
    st.markdown(
        "So sánh công bằng ba checkpoint trên benchmark chung đã loại rò rỉ dữ liệu. "
        "Các ảnh challenge chỉ dùng minh họa, không tham gia tính metric."
    )

    if not (RESULTS_DIR / "overall_metrics.csv").exists():
        st.error("Chưa có benchmark results. Chạy `python test_model/evaluate_common_benchmark.py`.")
        return

    overall, per_class = load_results()
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Benchmark sạch", "404 ảnh", "447 boxes")
    c2.metric("Ảnh bị loại", "28", "rò rỉ / trùng lặp")
    c3.metric("mAP50 cao nhất", f"{overall['mAP50'].max():.3f}", "Baseline B")
    c4.metric("mAP50-95 cao nhất", f"{overall['mAP50_95'].max():.3f}", "Baseline A")

    st.markdown(
        "<div class='model-verdict'><strong>Model triển khai: Baseline B</strong>"
        "<span>Được chọn bằng tie-break đã công bố: precision/mAP50 cao hơn và 0 false positive "
        "trên 10 ảnh negative. Baseline A vẫn dẫn recall và mAP50-95.</span></div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(metric_chart(overall), width="stretch", config={"displayModeBar": False})

    display = overall[
        [
            "model",
            "precision",
            "recall",
            "mAP50",
            "mAP50_95",
            "false_positives_on_negatives",
            "inference_ms_per_image",
        ]
    ].copy()
    display.columns = ["Model", "Precision", "Recall", "mAP50", "mAP50-95", "FP negative", "ms/ảnh CPU"]
    for column in ["Precision", "Recall", "mAP50", "mAP50-95"]:
        display[column] = display[column].map(lambda value: f"{value:.4f}")
    display["ms/ảnh CPU"] = display["ms/ảnh CPU"].map(lambda value: f"{value:.2f}")
    st.dataframe(display, width="stretch", hide_index=True)

    st.markdown("### Phân tích theo lớp")
    class_name = st.selectbox("Chọn lớp món ăn", per_class["class_name"].drop_duplicates().tolist())
    class_rows = per_class[per_class["class_name"] == class_name].copy()
    class_rows = class_rows[["model", "precision", "recall", "mAP50", "mAP50_95"]]
    class_rows.columns = ["Model", "Precision", "Recall", "mAP50", "mAP50-95"]
    st.dataframe(class_rows.style.format(precision=4), width="stretch", hide_index=True)

    with st.expander("Phương pháp và giới hạn"):
        st.markdown(
            """
            - Cùng Ultralytics 8.4.86, CPU, ảnh 640 px, IoU 0.7 và confidence 0.001 cho mAP.
            - 28/432 ảnh test gốc bị loại do duplicate, crop, cùng scene hoặc rò rỉ train/validation.
            - Tie-break vận hành dùng confidence 0.45 và IoU 0.45, đúng cấu hình app.
            - Negative set mới có 10 ảnh; chưa đủ để tuyên bố B vượt trội tuyệt đối về false positives.
            - Một số lớp còn dưới 30 mẫu, đặc biệt Bún thịt nướng và Phở.
            """
        )
        st.caption(f"Manifest: `{BENCHMARK_DIR / 'manifest.csv'}`")


if __name__ == "__main__":
    main()
