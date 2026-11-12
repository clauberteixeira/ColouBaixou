from pathlib import Path

from ytdl.preview import FRAME, MAX_PLAY_S, due_frame, frame_args, frames_args, play_length, sound_args

FF, SRC = Path("ffmpeg.exe"), Path("p.mkv")


def pair(args, flag):
    return args[args.index(flag) + 1]


def test_single_frame_is_raw_rgb_of_fixed_size():
    a = frame_args(FF, SRC, 7.5)
    assert pair(a, "-ss") == "7.50" and a.index("-ss") < a.index("-i")
    assert pair(a, "-frames:v") == "1" and pair(a, "-pix_fmt") == "rgb24"
    assert f"scale={FRAME[0]}:{FRAME[1]}" in pair(a, "-vf")
    assert a[-1] == "pipe:1"


def test_playing_frames_and_sound_cover_the_same_stretch():
    v = frames_args(FF, SRC, 5, 7)
    s = sound_args(FF, SRC, 5, 7, Path("a.wav"))
    for a in (v, s):
        assert pair(a, "-ss") == "5.00" and pair(a, "-t") == "7.00"
    assert "-an" in v and pair(v, "-vf").startswith("fps=")
    assert "-vn" in s and s[-1] == "a.wav"


def test_play_length_stops_at_the_end_of_the_selection():
    assert play_length(5, 12) == 7
    assert play_length(0, 3600) == MAX_PLAY_S
    assert play_length(20, 12) == 0


def test_due_frame():
    assert due_frame(0) == 0
    assert due_frame(1.0) == 15
