"""Teste real sem interface: python scripts/smoke.py <url> mp4 [altura] | mp3"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ytdl.config import load_config  # noqa: E402
from ytdl.downloader import Job, fetch_info  # noqa: E402
from ytdl.formats import plan_video  # noqa: E402
from ytdl.paths import app_data_dir  # noqa: E402
from ytdl.tools import load_tools  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    url, mode = sys.argv[1], sys.argv[2]
    tools = load_tools()
    info = fetch_info(tools, url)
    print(f"{info.title} | {info.channel}")
    last = {}

    def show(p):
        key = (p.stage, int(p.percent // 10) if p.percent is not None else None)
        if key != last.get("k"):
            last["k"] = key
            print(f"  {p.stage}: {p.percent and round(p.percent)}% {p.downloaded}/{p.total} eta={p.eta}", flush=True)

    job = Job(tools, app_data_dir() / "tmp", show)
    base = load_config().base_dir
    if mode == "mp3":
        result = job.run_audio(url, info, base)
    else:
        plan = plan_video(info, int(sys.argv[3]) if len(sys.argv) > 3 else None)
        print(f"  plano: {plan.video.format_id} {plan.video.vcodec} {plan.video.res}p "
              f"transcode={plan.transcode_video} hdr={plan.hdr} scale={plan.scale_to}")
        result = job.run_video(url, info, plan, base)
    print("OK ->", result)


if __name__ == "__main__":
    main()
