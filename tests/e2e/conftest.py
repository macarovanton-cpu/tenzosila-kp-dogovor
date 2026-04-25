"""Фикстуры и хуки pytest для e2e-слоя.

Поднимает Streamlit отдельным subprocess'ом на свободном порту, открывает
chromium через Playwright, проставляет всем тестам в подкаталоге маркер
`e2e`. Унит-стек на корне это не задевает.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
OUTPUT_DIR = TESTS_DIR / "output"
BASELINE_DIR = TESTS_DIR / "baseline"

FAKE_DATE = "2026-04-25"


def pytest_collection_modifyitems(config, items) -> None:
    e2e_root = str(TESTS_DIR / "e2e").replace("\\", "/")
    for item in items:
        if e2e_root in str(item.fspath).replace("\\", "/"):
            item.add_marker("e2e")


@pytest.fixture(scope="session")
def update_baseline(request) -> bool:
    return bool(request.config.getoption("--update-baseline"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_port(port: int, deadline_s: float = 30.0) -> None:
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"Streamlit не открыл порт {port} за {deadline_s} c")


@pytest.fixture(scope="session")
def streamlit_server() -> str:
    port = _free_port()
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "TENZOSILA_E2E": "1",
        "TENZOSILA_FAKE_DATE": FAKE_DATE,
    }
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(ROOT / "src" / "app.py"),
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_port(port)
        # Streamlit принимает TCP, но первый rerun ещё догружается. Небольшой буфер.
        time.sleep(1.5)
    except Exception:
        proc.kill()
        proc.wait(timeout=5)
        raise
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.fixture(scope="session")
def playwright_instance():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def page(browser, streamlit_server):
    context = browser.new_context(
        accept_downloads=True,
        viewport={"width": 1600, "height": 1000},
        locale="ru-RU",
    )
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(streamlit_server)
    page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=20_000)
    # Streamlit держит постоянный websocket — networkidle тут не годится.
    # Ждём появления первого input'а как сигнал, что начальный рендер завершён.
    page.wait_for_selector('input[aria-label="Номер КП"]', timeout=20_000)
    page.wait_for_timeout(800)
    yield page
    context.close()


@pytest.fixture
def kp_page(page):
    from tests.e2e.pages.kp_page import KpPage
    return KpPage(page)


@pytest.fixture(autouse=True)
def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASELINE_DIR / "png").mkdir(parents=True, exist_ok=True)
    (BASELINE_DIR / "docx").mkdir(parents=True, exist_ok=True)
