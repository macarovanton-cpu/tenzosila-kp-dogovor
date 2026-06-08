"""Тесты CLI и batch-режима pdf_to_fundament_docx."""
import subprocess
import sys
from pathlib import Path

from scripts import pdf_to_fundament_docx as converter


def test_iter_batch_maps_source_and_control_sheet_pdfs(tmp_path, monkeypatch):
    src_dir = tmp_path / "pdf_source"
    out_dir = tmp_path / "build_task"
    cs_src = src_dir / "control_sheet"
    cs_out = tmp_path / "control_sheet"
    src_dir.mkdir()
    cs_src.mkdir()
    (src_dir / "first.pdf").write_bytes(b"")
    (src_dir / "second.PDF").write_bytes(b"")
    (src_dir / "skip.txt").write_text("skip", encoding="utf-8")
    (cs_src / "check.PDF").write_bytes(b"")

    monkeypatch.setattr(converter, "SRC_DIR", src_dir)
    monkeypatch.setattr(converter, "OUT_DIR", out_dir)
    monkeypatch.setattr(converter, "CS_SRC", cs_src)
    monkeypatch.setattr(converter, "CS_OUT", cs_out)

    jobs = converter._iter_batch()

    assert set(jobs) == {
        (src_dir / "first.pdf", out_dir / "first.docx"),
        (src_dir / "second.PDF", out_dir / "second.docx"),
        (cs_src / "check.PDF", cs_out / "check.docx"),
    }


def test_convert_many_continues_after_single_file_error(tmp_path, monkeypatch, capsys):
    out_dir = tmp_path / "out"
    jobs = [
        (tmp_path / "bad.pdf", out_dir / "bad.docx"),
        (tmp_path / "good.pdf", out_dir / "good.docx"),
        (tmp_path / "also_good.pdf", out_dir / "also_good.docx"),
    ]

    def fake_convert(pdf_path: Path, out_path: Path) -> None:
        if pdf_path.name == "bad.pdf":
            raise RuntimeError("boom")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("ok", encoding="utf-8")

    monkeypatch.setattr(converter, "convert", fake_convert)
    errors = converter._convert_many(jobs)

    captured = capsys.readouterr().out
    assert errors == 1
    assert "[1/3] bad.pdf ... ERROR: boom" in captured
    assert "[2/3] good.pdf ... OK" in captured
    assert "[3/3] also_good.pdf ... OK" in captured
    assert (out_dir / "good.docx").exists()
    assert (out_dir / "also_good.docx").exists()


def test_main_converts_single_pdf_to_build_task(tmp_path, monkeypatch):
    pdf_path = tmp_path / "one.pdf"
    out_dir = tmp_path / "out"
    pdf_path.write_bytes(b"")
    calls = []

    def fake_convert_many(jobs: list[tuple[Path, Path]]) -> int:
        calls.extend(jobs)
        return 0

    monkeypatch.setattr(converter, "OUT_DIR", out_dir)
    monkeypatch.setattr(converter, "_convert_many", fake_convert_many)

    exit_code = converter.main([str(pdf_path)])

    assert exit_code == 0
    assert calls == [(pdf_path, out_dir / "one.docx")]


def test_main_all_uses_batch_jobs(tmp_path, monkeypatch):
    jobs = [(tmp_path / "one.pdf", tmp_path / "one.docx")]
    calls = []

    def fake_iter_batch() -> list[tuple[Path, Path]]:
        return jobs

    def fake_convert_many(batch_jobs: list[tuple[Path, Path]]) -> int:
        calls.extend(batch_jobs)
        return 0

    monkeypatch.setattr(converter, "_iter_batch", fake_iter_batch)
    monkeypatch.setattr(converter, "_convert_many", fake_convert_many)

    exit_code = converter.main(["--all"])

    assert exit_code == 0
    assert calls == jobs


def test_direct_script_help_runs_from_repo_root():
    result = subprocess.run(
        [sys.executable, "scripts/pdf_to_fundament_docx.py", "--help"],
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert b"usage:" in result.stdout
