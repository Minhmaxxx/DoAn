"""Start NutriVision and expose it through a temporary ngrok HTTPS URL."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from pyngrok import ngrok
from pyngrok.conf import PyngrokConfig


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")
PORT = int(os.getenv("STREAMLIT_PORT", "8501"))


def wait_for_port(process: subprocess.Popen, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Streamlit đã dừng với mã lỗi {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit không mở cổng {PORT} sau {timeout:.0f} giây")


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    if not token and sys.stdin.isatty():
        print("Chưa có NGROK_AUTHTOKEN trong .env.")
        token = getpass("Dán ngrok authtoken (sẽ không hiển thị hoặc lưu lại): ").strip()
    if not token:
        raise SystemExit(
            "Thiếu NGROK_AUTHTOKEN. Thêm token từ https://dashboard.ngrok.com/get-started/your-authtoken "
            "vào file .env rồi chạy lại."
        )

    streamlit_command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(PORT),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    print(f"Đang khởi động NutriVision tại http://127.0.0.1:{PORT} ...")
    streamlit_process = subprocess.Popen(streamlit_command, cwd=ROOT_DIR)
    tunnel = None
    pyngrok_config = PyngrokConfig(auth_token=token)

    try:
        wait_for_port(streamlit_process)
        print("Đang tạo ngrok HTTPS tunnel ...")
        tunnel = ngrok.connect(
            addr=PORT,
            proto="http",
            bind_tls=True,
            pyngrok_config=pyngrok_config,
        )
        print("\n" + "=" * 72)
        print(f"LINK ĐIỆN THOẠI: {tunnel.public_url}")
        print("Link này công khai trong thời gian chương trình đang chạy.")
        print("Không tải ảnh hoặc nhập API key nhạy cảm nếu bạn đã chia sẻ link.")
        print("Nhấn Ctrl+C để đóng tunnel và Streamlit.")
        print("=" * 72 + "\n")
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("\nĐang đóng NutriVision và ngrok ...")
    finally:
        if tunnel is not None:
            ngrok.disconnect(tunnel.public_url, pyngrok_config=pyngrok_config)
        ngrok.kill(pyngrok_config=pyngrok_config)
        stop_process(streamlit_process)


if __name__ == "__main__":
    main()
