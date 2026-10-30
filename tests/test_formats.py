import dataclasses
import json
from pathlib import Path

from ytdl.formats import available_heights, best_audio, format_duration, parse_info, plan_video, quality_label

DATA = json.loads((Path(__file__).parent / "fixtures" / "info_sample.json").read_text("utf-8"))


def info(**changes):
    return dataclasses.replace(parse_info(DATA), **changes)


def vids(i, keep):
    return tuple(f for f in i.video_formats if f.format_id in keep)


def test_parse_basic_fields():
    i = parse_info(DATA)
    assert (i.title, i.channel, i.duration) == ("Vídeo de Teste", "Canal Teste", 754)
    assert "sb0" not in {f.format_id for f in i.video_formats}
    assert {f.format_id for f in i.audio_formats} == {"140", "251"}


def test_channel_falls_back_to_uploader_then_unknown():
    assert parse_info(dict(DATA, channel=None)).channel == "Canal Teste"
    assert parse_info(dict(DATA, channel=None, uploader=None)).channel == "Desconhecido"


def test_heights_capped_at_4k():
    assert available_heights(parse_info(DATA)) == [2160, 1080, 720]


def test_best_is_4k60_sdr_not_8k_not_hdr():
    p = plan_video(parse_info(DATA))
    assert p.video.format_id == "315"
    assert (p.transcode_video, p.hdr, p.scale_to) == (True, False, None)
    assert p.audio.format_id == "140" and p.transcode_audio is False
    assert p.est_bytes == 2000000000 + 12000000


def test_only_hdr_at_4k_marks_hdr():
    i = info(video_formats=vids(parse_info(DATA), {"337", "137"}))
    p = plan_video(i)
    assert p.video.format_id == "337" and p.hdr and p.transcode_video


def test_1080_prefers_avc1_no_transcode():
    p = plan_video(parse_info(DATA), 1080)
    assert p.video.format_id == "137" and p.transcode_video is False


def test_higher_fps_beats_avc1():
    i = parse_info(DATA)
    vp9_60 = dataclasses.replace(next(f for f in i.video_formats if f.format_id == "248"), fps=60)
    i = info(video_formats=(vp9_60,) + vids(i, {"137"}))
    assert plan_video(i, 1080).video.format_id == "248"


def test_only_8k_is_scaled_to_4k():
    i = info(video_formats=vids(parse_info(DATA), {"571"}))
    assert available_heights(i) == [2160]
    p = plan_video(i)
    assert p.video.format_id == "571" and p.scale_to == 2160 and p.transcode_video


def test_no_m4a_means_audio_transcode():
    i = info(audio_formats=tuple(f for f in parse_info(DATA).audio_formats if f.format_id == "251"))
    p = plan_video(i, 1080)
    assert p.audio.format_id == "251" and p.transcode_audio is True


def test_vertical_short_uses_smaller_dimension():
    d = dict(DATA, formats=[
        {"format_id": "v", "vcodec": "avc1.64", "acodec": "none", "width": 1080, "height": 1920, "fps": 30,
         "dynamic_range": "SDR", "tbr": 3000, "ext": "mp4", "protocol": "https"},
        {"format_id": "a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128, "ext": "m4a", "protocol": "https"},
    ])
    assert available_heights(parse_info(d)) == [1080]


def test_missing_size_estimated_from_tbr():
    d = json.loads(json.dumps(DATA))
    for f in d["formats"]:
        f["filesize"] = None
    p = plan_video(parse_info(d), 720)
    assert p.est_bytes == int((1500 + 129) * 125 * 754)


def test_drc_audio_is_avoided():
    i = parse_info(DATA)
    m4a = next(f for f in i.audio_formats if f.format_id == "140")
    opus = next(f for f in i.audio_formats if f.format_id == "251")
    drc = (dataclasses.replace(m4a, format_id="140-drc", abr=200), dataclasses.replace(opus, format_id="251-drc", abr=300))
    i = info(audio_formats=drc + i.audio_formats)
    assert plan_video(i, 1080).audio.format_id == "140"
    assert best_audio(i).format_id == "251"


def test_original_language_beats_dubbed_tracks():
    # Caso real (vídeo com dublagens): a faixa italiana dublada tem abr maior que a original.
    audio = [
        {"format_id": "140-7", "acodec": "mp4a.40.2", "abr": 129.473, "language_preference": -1},
        {"format_id": "140-20", "acodec": "mp4a.40.2", "abr": 129.474, "language_preference": 10},
        {"format_id": "251-19", "acodec": "opus", "abr": 137.652, "language_preference": -1},
        {"format_id": "251-20", "acodec": "opus", "abr": 127.968, "language_preference": 10},
    ]
    formats = [f for f in DATA["formats"] if f["vcodec"] != "none"]
    formats += [dict(a, vcodec="none", ext="m4a", protocol="https") for a in audio]
    i = parse_info(dict(DATA, formats=formats))
    assert plan_video(i, 1080).audio.format_id == "140-20"
    assert best_audio(i).format_id == "140-20"  # maior abr entre as originais; antes vinha 251-19 (italiano)


def test_best_audio_for_mp3_is_highest_abr():
    assert best_audio(parse_info(DATA)).format_id == "251"


def test_labels():
    assert [quality_label(h) for h in (2160, 1440, 1080)] == ["4K", "1440p (2K)", "1080p"]
    assert [format_duration(s) for s in (754, 3723, 0)] == ["12:34", "1:02:03", "0:00"]
