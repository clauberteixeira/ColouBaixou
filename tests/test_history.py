from ytdl.history import DownloadHistory, already_downloaded


def test_record_and_find(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    h = DownloadHistory(tmp_path / "history.json")
    h.record("abcdefghijk", "video", f)
    again = DownloadHistory(tmp_path / "history.json")  # gravado em disco
    assert again.find("abcdefghijk", "video") == f
    assert again.find("abcdefghijk", "audio") is None


def test_deleted_file_is_forgotten(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    h = DownloadHistory(tmp_path / "history.json")
    h.record("abcdefghijk", "video", f)
    f.unlink()
    assert h.find("abcdefghijk", "video") is None


def test_corrupt_history_starts_empty(tmp_path):
    (tmp_path / "history.json").write_text("{quebrado", encoding="utf-8")
    assert DownloadHistory(tmp_path / "history.json").find("abcdefghijk", "video") is None


def test_already_downloaded_by_history_or_existing_file(tmp_path):
    h = DownloadHistory(tmp_path / "history.json")
    base = tmp_path / "base"
    # arquivo que já estava na pasta (baixado antes do histórico existir)
    old = base / "Vídeos" / "Canal" / "Título.mp4"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"x")
    assert already_downloaded(h, base, "aaaaaaaaaaa", "video", "Canal", "Título") == old
    assert already_downloaded(h, base, "aaaaaaaaaaa", "audio", "Canal", "Título") is None
    # sem título/canal ainda (link colado): só o histórico vale
    assert already_downloaded(h, base, "aaaaaaaaaaa", "video", None, None) is None
