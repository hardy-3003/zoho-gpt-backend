import sys
import importlib
from pathlib import Path


def test_write_event_uses_repo_root(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    # Change to another directory before importing history_store
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(repo_root))
    hs = importlib.import_module("helpers.history_store")
    file_path = hs.write_event("sample", {"foo": "bar"})
    expected_dir = repo_root / "data" / "history" / "sample"
    fp = Path(file_path)
    assert fp.is_file()
    assert fp.is_relative_to(expected_dir)
