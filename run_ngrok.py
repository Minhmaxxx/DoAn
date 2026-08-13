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
from pyngrok.exception import PyngrokNgrokError


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


def ensure_port_is_available(port: int) -> None:
    """Fail before spawning Streamlit instead of tunneling a stale app."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(
                f"Cổng {port} đang được một ứng dụng khác sử dụng. "
                "Đóng app cũ bằng Ctrl+C, hoặc đặt STREAMLIT_PORT=8502 trong .env rồi chạy lại."
            ) from error


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        # Streamlit may create child processes; close the owned process tree too.
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def close_ngrok(tunnel, pyngrok_config: PyngrokConfig) -> None:
    """Best-effort tunnel cleanup; the local ngrok API may already be gone."""
    if tunnel is not None:
        try:
            ngrok.disconnect(tunnel.public_url, pyngrok_config=pyngrok_config)
        except PyngrokNgrokError:
            pass
    try:
        ngrok.kill(pyngrok_config=pyngrok_config)
    except PyngrokNgrokError:
        pass


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

    try:
        ensure_port_is_available(PORT)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error

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
    popen_options = {"cwd": ROOT_DIR}
    if os.name == "nt":
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    streamlit_process = subprocess.Popen(streamlit_command, **popen_options)
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
        while streamlit_process.poll() is None:
            try:
                active_tunnels = ngrok.get_tunnels(pyngrok_config=pyngrok_config)
            except PyngrokNgrokError:
                active_tunnels = []
            if not any(item.public_url == tunnel.public_url for item in active_tunnels):
                print("Tunnel đã đóng. Đang dừng Streamlit để giải phóng cổng ...")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐang đóng NutriVision và ngrok ...")
    finally:
        try:
            close_ngrok(tunnel, pyngrok_config)
        finally:
            # Always release the local port, even when ngrok teardown fails.
            stop_process(streamlit_process)


if __name__ == "__main__":
    main()
