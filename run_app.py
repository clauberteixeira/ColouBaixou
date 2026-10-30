import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ytdl.app import main  # noqa: E402

main()
