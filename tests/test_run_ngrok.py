"""Tests for the phone-demo launcher without creating a public tunnel."""

import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

import run_ngrok
from pyngrok.exception import PyngrokNgrokError

from run_ngrok import close_ngrok, ensure_port_is_available, stop_process


def test_phone_launcher_rejects_an_occupied_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()

        with pytest.raises(RuntimeError, match="đang được một ứng dụng khác sử dụng"):
            ensure_port_is_available(listener.getsockname()[1])


def test_phone_launcher_stop_releases_its_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    listener_code = (
        "import socket, sys, time; "
        "server = socket.socket(); "
        "server.bind(('127.0.0.1', int(sys.argv[1]))); "
        "server.listen(); "
        "time.sleep(60)"
    )
    process = subprocess.Popen([sys.executable, "-c", listener_code, str(port)])

    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("Listener child process did not open its port")

        stop_process(process)
        process.wait(timeout=5)
        ensure_port_is_available(port)
    finally:
        stop_process(process)


def test_ngrok_cleanup_ignores_already_closed_local_api(monkeypatch):
    calls = []

    def disconnect(*args, **kwargs):
        calls.append("disconnect")
        raise PyngrokNgrokError("local API already closed")

    def kill(*args, **kwargs):
        calls.append("kill")
        raise PyngrokNgrokError("process already closed")

    monkeypatch.setattr(run_ngrok.ngrok, "disconnect", disconnect)
    monkeypatch.setattr(run_ngrok.ngrok, "kill", kill)

    close_ngrok(SimpleNamespace(public_url="https://example.ngrok.dev"), object())
    assert calls == ["disconnect", "kill"]
