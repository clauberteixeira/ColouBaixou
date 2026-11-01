from ytdl.windowing import app_size


class FakeWindow:
    def __init__(self, width, height, scale):
        self.width, self.height, self.scale = width, height, scale

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def _get_window_scaling(self):
        return self.scale


def test_app_size_removes_the_windows_scale():
    assert app_size(FakeWindow(1500, 1125, 1.5)) == (1000, 750)


def test_app_size_without_scale_is_the_same_size():
    assert app_size(FakeWindow(950, 700, 1.0)) == (950, 700)


def test_playlist_columns_fill_the_list_exactly():
    from ytdl.playlist_window import playlist_widths
    for total in (548, 708, 1048):
        title, channel = playlist_widths(total, 300)
        assert title + channel + 300 == total


def test_playlist_title_gets_most_of_the_room():
    from ytdl.playlist_window import playlist_widths
    title, channel = playlist_widths(1048, 300)
    assert title > channel >= 100
