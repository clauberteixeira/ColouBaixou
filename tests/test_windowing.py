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
