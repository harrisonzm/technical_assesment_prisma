from app.core.config.logging import emit_log


def test_emit_log_writes_to_file_without_permission_error(tmp_path, monkeypatch):
    log_path = tmp_path / "service.log"
    monkeypatch.setenv("LOG_FILE_PATH", str(log_path))

    emit_log(service="backend", level="info", message="hello")

    assert log_path.exists()
    assert log_path.read_text(encoding="utf-8").strip()


def test_emit_log_does_not_raise_when_log_path_is_unwritable(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("LOG_FILE_PATH", str(log_dir))

    emit_log(service="backend", level="info", message="hello")
