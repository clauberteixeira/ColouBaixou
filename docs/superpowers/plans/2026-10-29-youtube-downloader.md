# YouTube Downloader (Etapa 1): plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Programa de Windows com uma janela: o usuário cola um link do YouTube, vê a prévia e baixa MP4 (até 4K, compatível com qualquer player) ou MP3 320 kbps, que vão para pastas organizadas por canal.

**Architecture:** Aplicativo Python com interface CustomTkinter. O download é feito chamando o `yt-dlp.exe` standalone como subprocesso (ele se atualiza com `-U`). A conversão para H.264/AAC é feita pelo `ffmpeg.exe` com NVENC e fallback para x264. Toda a lógica de decisão (escolha de formato, montagem de comandos, nomes de arquivo, leitura de progresso e tradução de erros) fica em módulos puros e testados. A janela só orquestra, usando uma thread de trabalho e uma fila.

**Tech Stack:** Python 3.12, CustomTkinter, Pillow, pytest, PyInstaller (onedir), yt-dlp.exe (standalone), FFmpeg 8.1 (Gyan full build, com libzimg), Node.js como runtime JS do yt-dlp.

**Spec:** `docs/superpowers/specs/2026-10-29-youtube-downloader-design.md`

## Global Constraints

- Windows 11 apenas. Interface e mensagens 100% em português do Brasil, sem termos técnicos nas mensagens de erro.
- MP4: resolução máxima **2160p (4K)**. Vídeo final sempre **H.264 (yuv420p, 8 bits, SDR)** + áudio **AAC** dentro de `.mp4` com `+faststart`.
- MP3: **320 kbps**, com miniatura embutida como capa e metadados (título, canal como artista, data).
- Destinos: `<base>\Vídeos\<Canal>\<título>.mp4` e `<base>\Áudios\<Canal>\<título>.mp3`. Base padrão: `%USERPROFILE%\Downloads\YouTube`.
- Dados graváveis em `%LOCALAPPDATA%\YoutubeForDownload\` (`bin\yt-dlp.exe`, `config.json`, `logs\`, `tmp\`).
- Nunca sobrescrever: colisão vira ` (2)`, ` (3)`…
- Um download por vez, sempre com `--no-playlist`.
- Todo subprocesso usa `creationflags=subprocess.CREATE_NO_WINDOW` (nenhuma janela de console pode piscar no `.exe`) e decodifica a saída como UTF-8 com `errors="replace"`.
- Os arquivos parciais nunca ficam na pasta de destino: tudo é baixado e convertido em `tmp\<uuid>\` e só é movido no fim.
- Código em `src/ytdl/`, testes em `tests/`, e o pytest roda com `pythonpath = ["src"]`.

## Review Focus

1. **Títulos e canais com emoji, acentos, `CON`/`NUL`, pontos finais ou mais de 200 caracteres** precisam virar nomes válidos e o arquivo precisa ser criado. Teste em `tests/test_paths.py` (Task 1).
2. **Auto-colar da área de transferência:** não pode recarregar a prévia quando o link é o mesmo que já está no campo, nem durante um download. Teste `should_autofill` em `tests/test_urls.py` (Task 2).
3. **Queda de rede ou erro do yt-dlp no meio do download:** precisa mostrar uma mensagem amigável, apagar a pasta temporária e não deixar nada na pasta de destino. Teste com `FakeRunner` em `tests/test_downloader.py` (Task 7).
4. **Fechar a janela ou Cancelar durante o download:** precisa encerrar o processo filho e apagar a pasta temporária. Teste de cancelamento em `tests/test_downloader.py` (Task 7).
5. **Tamanho total desconhecido (`NA`) na linha de progresso:** não pode quebrar, e a tela mostra os MB baixados sem %. Teste em `tests/test_progress.py` (Task 4).

---

## Estrutura de arquivos

```
C:\YoutubeForDownload\
  pyproject.toml            # metadados + config do pytest
  requirements.txt          # customtkinter, pillow
  requirements-dev.txt      # pytest, pyinstaller
  .gitignore
  run_app.py                # entrada do PyInstaller: from ytdl.app import main; main()
  src/ytdl/
    __init__.py
    paths.py      # pastas do app, limpeza de nomes, destino único
    urls.py       # validação/normalização de links, should_autofill
    config.py     # config.json (base_dir)
    formats.py    # parse do `yt-dlp -J`, resoluções, escolha do plano de download
    progress.py   # leitura das linhas de progresso do yt-dlp e do ffmpeg
    errors.py     # saída do yt-dlp -> mensagem amigável
    tools.py      # localizar/baixar/atualizar yt-dlp, ffmpeg, node
    commands.py   # montagem das linhas de comando (puro)
    downloader.py # execução: fetch_info, Job (vídeo/áudio), cancelamento
    app.py        # janela principal CustomTkinter
    settings.py   # janela de Configurações
  tests/
    fixtures/info_sample.json
    test_*.py
  scripts/
    build.ps1               # PyInstaller + cópia do ffmpeg
    create_shortcut.ps1     # atalho na área de trabalho
```

---

### Task 1: Esqueleto do projeto + `paths.py`

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `src/ytdl/__init__.py`, `src/ytdl/paths.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- Produces:
  - `app_data_dir() -> Path`: `%LOCALAPPDATA%\YoutubeForDownload`, criado se não existir.
  - `resource_dir() -> Path`: `Path(sys._MEIPASS)` quando estiver empacotado e a raiz do projeto em desenvolvimento.
  - `sanitize_component(name: str, max_len: int = 80) -> str`
  - `destination_path(base: Path, kind: Literal["video", "audio"], channel: str, title: str) -> Path`: devolve o caminho final já único (com `(n)` se preciso). Cria as pastas. Extensão `.mp4` para `video` e `.mp3` para `audio`. Subpasta `Vídeos` ou `Áudios`.
  - `unique_path(path: Path) -> Path`

- [ ] **Step 1: Preparar o repositório e o ambiente**

```powershell
cd C:\YoutubeForDownload
git init
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install customtkinter pillow pytest pyinstaller
```
`.gitignore`: `.venv/`, `build/`, `dist/`, `.superpowers/`, `__pycache__/`, `*.spec`. `pyproject.toml` com `[tool.pytest.ini_options] pythonpath = ["src"]` e `testpaths = ["tests"]`. Fixe as versões instaladas em `requirements*.txt` (`pip freeze` filtrado).

- [ ] **Step 2: Escrever os testes que falham**

```python
from pathlib import Path
from ytdl.paths import sanitize_component, destination_path, unique_path

def test_removes_forbidden_chars():
    assert sanitize_component('a\\b/c:d*e?f"g<h>i|j') == "abcdefghij"

def test_strips_trailing_dots_and_spaces():
    assert sanitize_component("Título final. . ") == "Título final"

def test_keeps_accents_and_emoji():
    assert sanitize_component("Canção 🎵 ação") == "Canção 🎵 ação"

def test_reserved_windows_names_get_suffix():
    assert sanitize_component("CON") == "CON_"
    assert sanitize_component("nul") == "nul_"

def test_truncates_long_names():
    assert len(sanitize_component("x" * 300)) == 80

def test_empty_name_becomes_placeholder():
    assert sanitize_component("???") == "sem nome"

def test_destination_layout(tmp_path):
    p = destination_path(tmp_path, "video", "Canal: X", "Meu vídeo?")
    assert p == tmp_path / "Vídeos" / "Canal X" / "Meu vídeo.mp4"
    assert p.parent.is_dir()
    a = destination_path(tmp_path, "audio", "Canal X", "Música")
    assert a == tmp_path / "Áudios" / "Canal X" / "Música.mp3"

def test_unique_path_adds_counter(tmp_path):
    f = tmp_path / "a.mp4"; f.write_text("x")
    assert unique_path(f) == tmp_path / "a (2).mp4"
    (tmp_path / "a (2).mp4").write_text("x")
    assert unique_path(f) == tmp_path / "a (3).mp4"

def test_destination_with_emoji_title_is_creatable(tmp_path):
    p = destination_path(tmp_path, "audio", "🎸 Rock", "🔥" * 100)
    p.write_bytes(b"ok")
    assert p.exists()
```

- [ ] **Step 3: Rodar e confirmar a falha**

Run: `.\.venv\Scripts\python -m pytest tests/test_paths.py -v`
Expected: FAIL (`ModuleNotFoundError: ytdl.paths`)

- [ ] **Step 4: Implementar `src/ytdl/paths.py`**

Nomes reservados: `CON PRN AUX NUL COM1..COM9 LPT1..LPT9`, comparação case-insensitive, sem extensão. Remove também caracteres de controle (`ord < 32`). O corte por `max_len` é feito em caracteres (antes de remover pontos e espaços finais), para que o resultado nunca termine em ponto ou espaço.

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.\.venv\Scripts\python -m pytest tests/test_paths.py -v`
Expected: PASS (9 testes)

- [ ] **Step 6: Commit**

```powershell
git add .
git commit -m "feat: project skeleton and filename/destination helpers"
```

---

### Task 2: `urls.py` + `config.py`

**Files:**
- Create: `src/ytdl/urls.py`, `src/ytdl/config.py`
- Test: `tests/test_urls.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `app_data_dir()` (Task 1)
- Produces:
  - `extract_video_id(text: str) -> str | None`
  - `canonical_url(video_id: str) -> str`: `https://www.youtube.com/watch?v=<id>`
  - `should_autofill(clipboard: str, current_text: str, busy: bool) -> bool`
  - `@dataclass Config(base_dir: Path)`, `load_config(path: Path | None = None) -> Config`, `save_config(cfg: Config, path: Path | None = None) -> None`. O caminho padrão é `app_data_dir() / "config.json"`.

- [ ] **Step 1: Escrever os testes que falham**

```python
import pytest
from ytdl.urls import extract_video_id, should_autofill

ID = "dQw4w9WgXcQ"

@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={ID}",
    f"https://youtube.com/watch?v={ID}&list=PL123&index=4",
    f"https://m.youtube.com/watch?v={ID}",
    f"https://music.youtube.com/watch?v={ID}&feature=share",
    f"https://youtu.be/{ID}?si=abc",
    f"https://www.youtube.com/shorts/{ID}",
    f"https://www.youtube.com/embed/{ID}",
    f"  youtube.com/watch?v={ID}  ",
])
def test_accepts_youtube_links(url):
    assert extract_video_id(url) == ID

@pytest.mark.parametrize("url", [
    "https://vimeo.com/123", "https://www.youtube.com/@canal",
    "https://www.youtube.com/playlist?list=PL123", "texto qualquer", "",
    "https://evil.com/watch?v=dQw4w9WgXcQ",
])
def test_rejects_other_links(url):
    assert extract_video_id(url) is None

def test_autofill_new_link_when_idle():
    assert should_autofill(f"https://youtu.be/{ID}", "", busy=False)

def test_no_autofill_same_video_already_in_field():
    assert not should_autofill(f"https://youtu.be/{ID}", f"https://www.youtube.com/watch?v={ID}", busy=False)

def test_no_autofill_while_busy():
    assert not should_autofill(f"https://youtu.be/{ID}", "", busy=True)

def test_no_autofill_non_youtube():
    assert not should_autofill("olá", "", busy=False)
```

```python
from pathlib import Path
from ytdl.config import Config, load_config, save_config

def test_default_base_dir_when_missing(tmp_path):
    cfg = load_config(tmp_path / "config.json")
    assert cfg.base_dir == Path.home() / "Downloads" / "YouTube"

def test_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    save_config(Config(base_dir=tmp_path / "Meus Vídeos"), p)
    assert load_config(p).base_dir == tmp_path / "Meus Vídeos"

def test_corrupt_file_falls_back_to_default(tmp_path):
    p = tmp_path / "config.json"; p.write_text("{não é json")
    assert load_config(p).base_dir == Path.home() / "Downloads" / "YouTube"
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `.\.venv\Scripts\python -m pytest tests/test_urls.py tests/test_config.py -v`
Expected: FAIL (módulos inexistentes)

- [ ] **Step 3: Implementar**

`urls.py`: aceita só os hosts `youtube.com`, `www.youtube.com`, `m.youtube.com`, `music.youtube.com` e `youtu.be`, e adiciona `https://` se faltar. O ID segue `[A-Za-z0-9_-]{11}`, vindo de `v=`, de `/shorts/<id>`, de `/embed/<id>`, de `/live/<id>` ou do caminho do `youtu.be`. Use `urllib.parse`. `config.py`: JSON `{"base_dir": "..."}` em UTF-8.

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.\.venv\Scripts\python -m pytest tests/test_urls.py tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/ytdl/urls.py src/ytdl/config.py tests/test_urls.py tests/test_config.py
git commit -m "feat: YouTube link parsing, clipboard autofill rule and config file"
```

---

### Task 3: `formats.py`: prévia e escolha do formato

**Files:**
- Create: `src/ytdl/formats.py`, `tests/fixtures/info_sample.json`
- Test: `tests/test_formats.py`

**Interfaces:**
- Produces:
  ```python
  CAP = 2160

  @dataclass(frozen=True)
  class Fmt:
      format_id: str; vcodec: str; acodec: str; ext: str
      width: int | None; height: int | None
      res: int | None        # min(width, height); None em áudio
      fps: float; dynamic_range: str  # "SDR", "HDR10", "HLG"...
      tbr: float; abr: float; protocol: str; size: int | None  # filesize or filesize_approx

  @dataclass(frozen=True)
  class VideoInfo:
      id: str; title: str; channel: str; duration: int
      thumbnail_url: str | None; live_status: str | None
      video_formats: tuple[Fmt, ...]; audio_formats: tuple[Fmt, ...]

  @dataclass(frozen=True)
  class VideoPlan:
      video: Fmt; audio: Fmt
      transcode_video: bool; transcode_audio: bool
      hdr: bool; scale_to: int | None; est_bytes: int

  def parse_info(data: dict) -> VideoInfo
  def available_heights(info: VideoInfo) -> list[int]          # desc, únicas, <= CAP
  def plan_video(info: VideoInfo, res: int | None = None) -> VideoPlan   # None = melhor
  def best_audio(info: VideoInfo) -> Fmt                       # maior abr (para MP3)
  def quality_label(res: int) -> str
  def format_duration(seconds: int) -> str
  ```

**Regras (da spec):**
- Vídeo = `vcodec != "none"` e `acodec == "none"`. Áudio = `vcodec == "none"` e `acodec != "none"`. Descartar `has_drm`, `ext == "mhtml"` (storyboards) e formatos de vídeo sem `width`/`height`.
- `channel` = `channel` ou `uploader` ou `"Desconhecido"`. Se `duration` vier ausente, vale 0.
- `available_heights`: valores únicos de `res` ≤ CAP, em ordem decrescente. Se nenhum for ≤ CAP mas existir algum acima, a lista é `[CAP]`.
- `plan_video`: o alvo é `res` ou `available_heights[0]`. Os candidatos são os formatos com `res == alvo`. Se não houver nenhum (só existe acima de CAP), use o grupo de menor `res` acima de CAP e `scale_to = CAP`. A escolha é pelo `max` com a chave `(fps, dynamic_range == "SDR", vcodec.startswith("avc1"), protocol == "https", tbr)`.
- `hdr = dynamic_range != "SDR"`. `transcode_video = not avc1 or hdr or scale_to is not None`.
- Áudio do MP4: o maior `abr` entre os que têm `acodec.startswith("mp4a")`, com `transcode_audio=False`. Se não houver nenhum, o maior `abr` geral, com `transcode_audio=True`.
- `est_bytes` = `int(` soma, para vídeo e áudio, de `size` ou, quando `size` for None, de `(tbr or abr) * 125 * duration` `)`.
- `quality_label`: `2160 → "4K"`, `1440 → "1440p (2K)"` e os demais `"<n>p"`.
- `format_duration`: `754 → "12:34"`, `3723 → "1:02:03"`, `0 → "0:00"`.

- [ ] **Step 1: Criar a fixture `tests/fixtures/info_sample.json`**

Um JSON no formato do `yt-dlp -J` com `id`, `title: "Vídeo de Teste"`, `channel: "Canal Teste"`, `duration: 754`, `thumbnail`, `live_status: "not_live"` e estes `formats` (os campos que faltarem são `null`):

| format_id | vcodec | acodec | w×h | fps | dynamic_range | tbr/abr | filesize |
|---|---|---|---|---|---|---|---|
| sb0 | none | none | 160×90 | — | — | — | — (ext mhtml) |
| 140 | none | mp4a.40.2 | — | — | — | abr 129 | 12000000 |
| 251 | none | opus | — | — | — | abr 140 | 13000000 |
| 137 | avc1.640028 | none | 1920×1080 | 30 | SDR | 4000 | 300000000 |
| 248 | vp09.00.40.08 | none | 1920×1080 | 30 | SDR | 2500 | 200000000 |
| 313 | vp09.00.51.08 | none | 3840×2160 | 30 | SDR | 18000 | 1500000000 |
| 315 | vp09.00.51.08 | none | 3840×2160 | 60 | SDR | 26000 | 2000000000 |
| 337 | vp09.02.51.10 | none | 3840×2160 | 60 | HDR10 | 30000 | 2200000000 |
| 571 | av01.0.16M.08 | none | 7680×4320 | 60 | SDR | 60000 | 5000000000 |
| 136 | avc1.4d401f | none | 1280×720 | 30 | SDR | 1500 | 100000000 |

- [ ] **Step 2: Escrever os testes que falham**

```python
import json, dataclasses
from pathlib import Path
from ytdl.formats import parse_info, available_heights, plan_video, best_audio, quality_label, format_duration

DATA = json.loads((Path(__file__).parent / "fixtures/info_sample.json").read_text("utf-8"))

def info(**changes):
    i = parse_info(DATA)
    return dataclasses.replace(i, **changes)

def vids(i, keep):
    return tuple(f for f in i.video_formats if f.format_id in keep)

def test_parse_basic_fields():
    i = parse_info(DATA)
    assert (i.title, i.channel, i.duration) == ("Vídeo de Teste", "Canal Teste", 754)
    assert "sb0" not in {f.format_id for f in i.video_formats}
    assert {f.format_id for f in i.audio_formats} == {"140", "251"}

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
    d = dict(DATA, formats=[{"format_id": "v", "vcodec": "avc1.64", "acodec": "none", "width": 1080, "height": 1920, "fps": 30, "dynamic_range": "SDR", "tbr": 3000, "ext": "mp4", "protocol": "https"},
                             {"format_id": "a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128, "ext": "m4a", "protocol": "https"}])
    assert available_heights(parse_info(d)) == [1080]

def test_missing_size_estimated_from_tbr():
    d = json.loads(json.dumps(DATA))
    for f in d["formats"]:
        f["filesize"] = None
    p = plan_video(parse_info(d), 720)
    assert p.est_bytes == int((1500 + 129) * 125 * 754)

def test_best_audio_for_mp3_is_highest_abr():
    assert best_audio(parse_info(DATA)).format_id == "251"

def test_labels():
    assert [quality_label(h) for h in (2160, 1440, 1080)] == ["4K", "1440p (2K)", "1080p"]
    assert [format_duration(s) for s in (754, 3723, 0)] == ["12:34", "1:02:03", "0:00"]
```

- [ ] **Step 3: Rodar e confirmar a falha**

Run: `.\.venv\Scripts\python -m pytest tests/test_formats.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 4: Implementar `src/ytdl/formats.py`** seguindo as regras acima.

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.\.venv\Scripts\python -m pytest tests/test_formats.py -v`
Expected: PASS (12 testes)

- [ ] **Step 6: Commit**

```powershell
git add src/ytdl/formats.py tests/test_formats.py tests/fixtures/info_sample.json
git commit -m "feat: parse yt-dlp info and choose 4K-capped compatible download plan"
```

---

### Task 4: `progress.py`

**Files:**
- Create: `src/ytdl/progress.py`
- Test: `tests/test_progress.py`

**Interfaces:**
- Produces:
  ```python
  PROGRESS_TEMPLATE = "download:[dl]%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.eta)s|%(info.format_id)s"

  @dataclass(frozen=True)
  class DlLine: downloaded: int; total: int | None; eta: int | None; format_id: str

  @dataclass(frozen=True)
  class Progress:
      stage: Literal["download", "convert", "mp3"]
      percent: float | None      # 0–100
      downloaded: int | None; total: int | None; eta: int | None

  def parse_dl_line(line: str) -> DlLine | None      # linhas que não começam com "[dl]" → None
  class DownloadTracker:
      def __init__(self, expected: dict[str, int | None]): ...   # format_id -> tamanho esperado
      def update(self, line: DlLine) -> Progress                 # stage="download", agrega todas as partes
  def parse_ffmpeg_line(line: str, duration_s: int) -> float | None   # "out_time_us=..." → percent
  ```
- `total` = `total_bytes` ou `total_bytes_estimate`, e `"NA"` vira None.
- `DownloadTracker`: o total é a soma dos tamanhos de todas as partes. Para cada parte, usa o tamanho da linha se houver e, senão, o `expected`. Se algum for desconhecido, `total=None` e `percent=None`. `downloaded` = partes já concluídas + parte atual. Uma parte é concluída quando chega uma linha de outro `format_id`. `eta` vem da linha atual.

- [ ] **Step 1: Escrever os testes que falham**

```python
import pytest
from ytdl.progress import parse_dl_line, DownloadTracker, parse_ffmpeg_line, DlLine

def test_parse_full_line():
    assert parse_dl_line("[dl]500|1000|NA|12|315") == DlLine(500, 1000, 12, "315")

def test_parse_uses_estimate_when_total_missing():
    assert parse_dl_line("[dl]500|NA|2000.5|NA|140") == DlLine(500, 2000, None, "140")

def test_unknown_total_does_not_crash():
    assert parse_dl_line("[dl]500|NA|NA|NA|140").total is None

def test_ignores_other_lines():
    assert parse_dl_line("[Merger] Merging formats into ...") is None

def test_tracker_aggregates_two_parts():
    t = DownloadTracker({"315": 1000, "140": 100})
    assert t.update(DlLine(500, 1000, 5, "315")).percent == pytest.approx(500 / 1100 * 100)
    p = t.update(DlLine(50, 100, 1, "140"))
    assert (p.downloaded, p.total) == (1050, 1100)

def test_tracker_unknown_size_gives_no_percent():
    p = DownloadTracker({"315": None}).update(DlLine(500, None, None, "315"))
    assert p.percent is None and p.downloaded == 500

def test_ffmpeg_progress():
    assert parse_ffmpeg_line("out_time_us=30000000", 60) == 50.0
    assert parse_ffmpeg_line("out_time_us=N/A", 60) is None
    assert parse_ffmpeg_line("progress=continue", 60) is None
    assert parse_ffmpeg_line("out_time_us=99000000", 60) == 100.0
    assert parse_ffmpeg_line("out_time_us=5000000", 0) is None
```

- [ ] **Step 2: Rodar e confirmar a falha.** Run: `.\.venv\Scripts\python -m pytest tests/test_progress.py -v`. Expected: FAIL.
- [ ] **Step 3: Implementar `src/ytdl/progress.py`.** O percentual do ffmpeg é limitado a 100.
- [ ] **Step 4: Rodar e confirmar que passa.** Expected: PASS (7 testes).
- [ ] **Step 5: Commit**

```powershell
git add src/ytdl/progress.py tests/test_progress.py
git commit -m "feat: parse yt-dlp and ffmpeg progress"
```

---

### Task 5: `errors.py`

**Files:**
- Create: `src/ytdl/errors.py`
- Test: `tests/test_errors.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class FriendlyError: message: str; suggest_update: bool = False

  class DownloadError(Exception):
      def __init__(self, friendly: FriendlyError): ...   # .friendly
  class Cancelled(Exception): ...

  def friendly_error(output: str) -> FriendlyError
  def error_for_live(live_status: str | None) -> FriendlyError | None
  INVALID_LINK: FriendlyError; NO_SPACE: FriendlyError; NO_NODE_WARNING: str
  ```

Texto exato (a busca não diferencia maiúsculas e minúsculas, e a primeira regra que bater vence):

| Detectar em `output` | `message` | `suggest_update` |
|---|---|---|
| `getaddrinfo failed`, `Failed to resolve`, `Unable to download webpage`, `timed out`, `No connection` | "Sem conexão com a internet. Verifique sua rede e tente de novo." | False |
| `Private video` | "Este vídeo é privado e não pode ser baixado." | False |
| `Sign in to confirm your age`, `age-restricted` | "Este vídeo tem restrição de idade e precisa de login. Isso não é suportado." | False |
| `members-only`, `Join this channel` | "Este vídeo é exclusivo para membros do canal e não pode ser baixado." | False |
| `Video unavailable`, `has been removed`, `This video is not available` | "Este vídeo está indisponível ou foi removido." | False |
| `No space left`, `Errno 28`, `WinError 112` | NO_SPACE = "Não há espaço suficiente no disco." | False |
| `not a bot` | "O YouTube bloqueou temporariamente o download. Tente mais tarde ou atualize o programa." | True |
| (qualquer outra coisa) | "Não foi possível baixar este vídeo. Tente atualizar o programa." | True |

- `error_for_live`: `"is_live"` → "Transmissões ao vivo em andamento não podem ser baixadas."; `"is_upcoming"` → "Esta transmissão ainda não começou."; caso contrário None.
- `INVALID_LINK` = "Este não parece ser um link de vídeo do YouTube."
- `NO_NODE_WARNING` = "Node.js não encontrado: vídeos acima de 1080p podem não aparecer. Instale o Node.js para liberar todas as qualidades."

- [ ] **Step 1: Escrever os testes que falham.** Um teste parametrizado por linha da tabela, com uma saída realista do yt-dlp. Exemplo: `"ERROR: [youtube] abc: Private video. Sign in if you've been granted access"` → mensagem de privado, `suggest_update False`. Inclua também o caso padrão (`"ERROR: something weird"` → `suggest_update True`) e os três casos de `error_for_live`.
- [ ] **Step 2: Rodar e confirmar a falha.** Run: `.\.venv\Scripts\python -m pytest tests/test_errors.py -v`
- [ ] **Step 3: Implementar `src/ytdl/errors.py`.**
- [ ] **Step 4: Rodar e confirmar que passa.**
- [ ] **Step 5: Commit** — `git commit -m "feat: friendly pt-BR error messages"`

---

### Task 6: `tools.py` + `commands.py`

**Files:**
- Create: `src/ytdl/tools.py`, `src/ytdl/commands.py`
- Test: `tests/test_tools.py`, `tests/test_commands.py`

**Interfaces:**
- Consumes: `app_data_dir`, `resource_dir` (Task 1), `VideoPlan` (Task 3), `PROGRESS_TEMPLATE` (Task 4)
- Produces (`tools.py`):
  ```python
  YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
  NO_WINDOW = subprocess.CREATE_NO_WINDOW

  @dataclass(frozen=True)
  class Tools: ytdlp: Path; ffmpeg_dir: Path; node: Path | None

  def find_ffmpeg_dir() -> Path | None      # resource_dir()/"ffmpeg"/ffmpeg.exe, senão shutil.which("ffmpeg")
  def find_node() -> Path | None            # shutil.which("node")
  def ensure_ytdlp(bin_dir: Path, download: Callable[[str, Path], None] = _urlretrieve) -> Path
      # já existe → devolve; senão baixa para bin_dir/"yt-dlp.exe.part" e renomeia
  def ytdlp_version(ytdlp: Path) -> str     # `yt-dlp.exe --version`, strip
  def update_ytdlp(ytdlp: Path) -> str      # `yt-dlp.exe -U`, devolve versão depois
  def load_tools() -> Tools                 # ensure_ytdlp(app_data_dir()/"bin"); levanta RuntimeError se faltar ffmpeg
  ```
- Produces (`commands.py`), todas funções puras que devolvem `list[str]`:
  ```python
  def base_args(t: Tools) -> list[str]
      # [ytdlp, "--no-playlist", "--encoding", "utf-8", "--ffmpeg-location", ffmpeg_dir,
      #  "--newline", "--progress-template", PROGRESS_TEMPLATE] + (["--js-runtimes", f"node:{node}"] se node)
  def info_args(t: Tools, url: str) -> list[str]                     # base + ["-J", url]
  def video_args(t: Tools, url: str, plan: VideoPlan, tmp: Path) -> list[str]
      # base + ["-f", f"{v.format_id}+{a.format_id}", "--merge-output-format", "mp4" se não houver transcode, senão "mkv",
      #         "-o", str(tmp / "media.%(ext)s"), url]
  def audio_args(t: Tools, url: str, audio_format_id: str, tmp: Path) -> list[str]
      # base + ["-f", audio_format_id, "-x", "--audio-format", "mp3", "--audio-quality", "320K",
      #         "--embed-thumbnail", "--embed-metadata", "--parse-metadata", "%(channel)s:%(artist)s",
      #         "-o", str(tmp / "media.%(ext)s"), url]
  def ffmpeg_args(ffmpeg: Path, src: Path, dst: Path, plan: VideoPlan, encoder: Literal["nvenc", "x264"]) -> list[str]
  ```
- `ffmpeg_args`, nesta ordem: `[ffmpeg, "-y", "-hide_banner", "-nostats", "-progress", "pipe:1", "-i", src, "-map", "0:v:0", "-map", "0:a:0"]`.
  - Vídeo: se `transcode_video` for False, usa `-c:v copy`. Senão, monta o `-vf` com:
    - se `hdr`: `zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv`;
    - se `scale_to`: `scale=-2:{scale_to}` quando `plan.video.width >= plan.video.height` e `scale={scale_to}:-2` quando for vertical;
    - sempre `format=yuv420p`, com as partes unidas por vírgula.
  - Encoder: `nvenc` → `-c:v h264_nvenc -preset p5 -rc vbr -cq 19 -b:v 0 -profile:v high`; `x264` → `-c:v libx264 -preset medium -crf 18 -profile:v high`.
  - Áudio: `-c:a copy` se `transcode_audio` for False, senão `-c:a aac -b:a 192k`.
  - Final: `-movflags +faststart` e `dst`.

- [ ] **Step 1: Escrever os testes que falham**

`test_commands.py`, com `Tools(Path("y.exe"), Path("ff"), Path("node.exe"))` e um `VideoPlan` montado à mão:
```python
def test_base_has_no_playlist_and_node(): ...      # "--no-playlist" in args; ["--js-runtimes", "node:node.exe"] presente
def test_base_without_node_omits_js_runtimes(): ...
def test_video_args_no_transcode_merges_mp4(): ...  # "-f","137+140" e "--merge-output-format","mp4"
def test_video_args_transcode_merges_mkv(): ...
def test_audio_args_mp3_320(): ...                 # contém "--audio-quality","320K","--embed-thumbnail","--embed-metadata"
def test_ffmpeg_copy_when_no_transcode(): ...      # "-c:v","copy" e "-c:a","copy"; sem "-vf"
def test_ffmpeg_nvenc_sdr(): ...                   # "h264_nvenc"; vf == "format=yuv420p"
def test_ffmpeg_x264_fallback(): ...               # "libx264", "-crf","18"
def test_ffmpeg_hdr_tonemaps(): ...                # "tonemap=tonemap=hable" in vf; vf termina com "format=yuv420p"
def test_ffmpeg_scale_8k_to_4k(): ...              # "scale=-2:2160" in vf
def test_ffmpeg_aac_when_audio_transcode(): ...    # "-c:a","aac","-b:a","192k"
def test_ffmpeg_ends_with_faststart_and_dst(): ... # args[-3:] == ["-movflags", "+faststart", str(dst)]
```
`test_tools.py`:
```python
def test_ensure_ytdlp_downloads_when_missing(tmp_path):
    calls = []
    def fake(url, dest): calls.append(url); dest.write_bytes(b"exe")
    p = ensure_ytdlp(tmp_path, download=fake)
    assert p == tmp_path / "yt-dlp.exe" and p.read_bytes() == b"exe" and calls == [YTDLP_URL]

def test_ensure_ytdlp_skips_when_present(tmp_path):
    (tmp_path / "yt-dlp.exe").write_bytes(b"x")
    ensure_ytdlp(tmp_path, download=lambda *a: pytest.fail("não deveria baixar"))

def test_failed_download_leaves_no_exe(tmp_path):
    def boom(url, dest): dest.write_bytes(b"meio"); raise OSError("rede")
    with pytest.raises(OSError): ensure_ytdlp(tmp_path, download=boom)
    assert not (tmp_path / "yt-dlp.exe").exists() and not (tmp_path / "yt-dlp.exe.part").exists()
```

- [ ] **Step 2: Rodar e confirmar a falha.** Run: `.\.venv\Scripts\python -m pytest tests/test_commands.py tests/test_tools.py -v`
- [ ] **Step 3: Implementar `tools.py` e `commands.py`.** Todo `subprocess.run` usa `creationflags=NO_WINDOW, capture_output=True, encoding="utf-8", errors="replace"`.
- [ ] **Step 4: Rodar e confirmar que passa.**
- [ ] **Step 5: Verificação real (rede)**

```powershell
.\.venv\Scripts\python -c "from ytdl.tools import load_tools, ytdlp_version; t=load_tools(); print(t, ytdlp_version(t.ytdlp))"
```
Expected: imprime `Tools(...)` com `node` preenchido e uma versão `2026.xx.xx`. Depois rode `info_args` num vídeo 4K real (por exemplo, um vídeo de demonstração 4K) e confira se o JSON tem formatos com `height` 2160. Se a saída avisar sobre componente EJS ausente, acrescente `["--remote-components", "ejs:github"]` em `base_args`, atualize o teste correspondente e registre isso no commit.

- [ ] **Step 6: Commit** — `git commit -m "feat: locate/bootstrap tools and build yt-dlp/ffmpeg command lines"`

---

### Task 7: `downloader.py`: execução, cancelamento e limpeza

**Files:**
- Create: `src/ytdl/downloader.py`
- Test: `tests/test_downloader.py`

**Interfaces:**
- Consumes: tudo o que foi produzido nas Tasks 1, 3, 4, 5 e 6.
- Produces:
  ```python
  class ProcessRunner:
      def run(self, args: list[str], on_line: Callable[[str], None]) -> int
          # Popen(stdout=PIPE, stderr=STDOUT, creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
          # chama on_line para cada linha (sem \n); devolve o returncode
      def cancel(self) -> None   # `taskkill /T /F /PID <pid>` (mata yt-dlp e o ffmpeg filho)

  def fetch_info(t: Tools, url: str, run=subprocess.run) -> VideoInfo
      # rc != 0 → DownloadError(friendly_error(stderr)); live → DownloadError(error_for_live(...))

  def cleanup_stale_temp(tmp_root: Path) -> None   # apaga subpastas de tmp_root

  class Job:
      def __init__(self, tools: Tools, tmp_root: Path, on_progress: Callable[[Progress], None],
                   runner_factory: Callable[[], ProcessRunner] = ProcessRunner,
                   free_space: Callable[[Path], int] = lambda p: shutil.disk_usage(p).free): ...
      def run_video(self, url: str, info: VideoInfo, plan: VideoPlan, base_dir: Path) -> Path
      def run_audio(self, url: str, info: VideoInfo, base_dir: Path) -> Path
      def cancel(self) -> None
  ```

**Comportamento:**
1. Cria `tmp = tmp_root / uuid4().hex`. Tudo acontece dentro de `try/finally: shutil.rmtree(tmp, ignore_errors=True)`.
2. Antes de começar, verifica o espaço: precisa de `est_bytes * (3 if transcode else 2)` no vídeo e de `best_audio.size or 0` vezes 3 no áudio. Usa `free_space(base_dir)` (criando `base_dir` antes). Se faltar, levanta `DownloadError(NO_SPACE)`.
3. Roda `video_args` ou `audio_args` com um runner novo e alimenta `DownloadTracker(expected={id: size})` → `on_progress`. No áudio, ao ver uma linha começando com `[ExtractAudio]`, emite `Progress("mp3", None, ...)`.
4. Se `rc != 0`: se `cancel()` tiver sido chamado, levanta `Cancelled`. Senão, levanta `DownloadError(friendly_error(últimas 50 linhas))`.
5. Vídeo com transcode: `ffmpeg_args(..., "nvenc")` com `parse_ffmpeg_line` → `Progress("convert", pct, ...)`. Se rc for diferente de 0 e não houver cancelamento, refaz com `"x264"`. Se o x264 também falhar, levanta `DownloadError(friendly_error(saída))`. A saída vai para `tmp / "final.mp4"`.
6. Move o arquivo final (`media.mp4`, `final.mp4` ou `media.mp3`) para `destination_path(base_dir, kind, info.channel, info.title)` com `shutil.move`, e devolve esse caminho.
7. `cancel()` marca a flag e chama `runner.cancel()` no runner ativo. Depois do cancelamento, nenhum passo novo começa.
8. Registra em log (`logging.getLogger("ytdl")`) os comandos executados e as últimas linhas de saída quando houver erro.

- [ ] **Step 1: Escrever os testes que falham**

Use um `FakeRunner` configurável. Ele recebe uma lista de "roteiros" `(linhas, rc, arquivo_a_criar)`, um por chamada de `run`. Ao rodar, ele cria o arquivo no `tmp` (que descobre pelo `-o` ou pelo último argumento do ffmpeg), emite as linhas e devolve `rc`. Registre também os `args` recebidos.

```python
def test_video_no_transcode_moves_to_destination(tmp_path): ...
    # plano 1080 avc1; roteiro: ["[dl]50|100|NA|1|137", "[dl]100|100|NA|0|137"], rc 0, cria media.mp4
    # resultado == base/"Vídeos"/"Canal Teste"/"Vídeo de Teste.mp4", existe; tmp_root vazio; progresso recebido

def test_video_transcode_uses_nvenc(tmp_path): ...
    # 2 chamadas; a 2ª contém "h264_nvenc"; progresso stage "convert" emitido

def test_nvenc_failure_falls_back_to_x264(tmp_path): ...
    # roteiros: download ok, nvenc rc 1, x264 ok → 3 chamadas, a 3ª contém "libx264"; arquivo final existe

def test_download_error_is_friendly_and_cleans_up(tmp_path): ...
    # roteiro: ["ERROR: Unable to download webpage: timed out"], rc 1, cria media.mp4.part
    # pytest.raises(DownloadError) com mensagem de internet; tmp_root vazio; base/"Vídeos" sem arquivos

def test_cancel_raises_cancelled_and_cleans_up(tmp_path): ...
    # FakeRunner que, em on_line, chama job.cancel() e devolve rc 1 → Cancelled; runner.cancel foi chamado; tmp_root vazio

def test_not_enough_space(tmp_path): ...
    # free_space=lambda p: 10 → DownloadError(NO_SPACE); nenhum runner foi criado

def test_audio_mp3_destination(tmp_path): ...
    # cria media.mp3 → base/"Áudios"/"Canal Teste"/"Vídeo de Teste.mp3"

def test_existing_file_gets_counter(tmp_path): ...
    # base/"Áudios"/"Canal Teste"/"Vídeo de Teste.mp3" já existe → resultado "Vídeo de Teste (2).mp3"

def test_fetch_info_live_is_rejected(): ...
    # run fake devolvendo JSON com live_status "is_live" → DownloadError com mensagem de ao vivo

def test_fetch_info_error_is_friendly(): ...
    # run fake rc 1, stderr "ERROR: Private video" → mensagem de privado
```

- [ ] **Step 2: Rodar e confirmar a falha.** Run: `.\.venv\Scripts\python -m pytest tests/test_downloader.py -v`
- [ ] **Step 3: Implementar `src/ytdl/downloader.py`.**
- [ ] **Step 4: Rodar a suíte inteira.** Run: `.\.venv\Scripts\python -m pytest -v`. Expected: tudo PASS.
- [ ] **Step 5: Verificação real (rede, sem interface)**

Crie `scripts/smoke.py`, que recebe a URL e o modo (`mp4 [altura]` ou `mp3`) e imprime o progresso e o caminho final, usando `load_tools()`, `fetch_info`, `plan_video` e `Job`. Rode com:
1. Um vídeo 1080p comum em `mp4 1080`: termina rápido, sem conversão.
2. Um vídeo 4K em `mp4`: mostra a fase "convert" com NVENC e o arquivo final abre no Media Player do Windows.
3. O mesmo vídeo em `mp3`: o arquivo tem capa e artista (confira em Propriedades → Detalhes).

Expected: os três arquivos aparecem nas pastas corretas, e `%LOCALAPPDATA%\YoutubeForDownload\tmp` fica vazio.

- [ ] **Step 6: Commit** — `git commit -m "feat: download/convert job with cancel, cleanup and nvenc fallback"`

---

### Task 8: Janela principal (`app.py`)

**Files:**
- Create: `src/ytdl/app.py`, `run_app.py`
- Modify: nenhum

**Interfaces:**
- Consumes: `load_tools`, `find_node` (Task 6); `fetch_info`, `Job`, `cleanup_stale_temp` (Task 7); `available_heights`, `plan_video`, `quality_label`, `format_duration` (Task 3); `extract_video_id`, `canonical_url`, `should_autofill` (Task 2); `load_config` (Task 2); `DownloadError`, `Cancelled`, `INVALID_LINK`, `NO_NODE_WARNING` (Task 5); `Progress` (Task 4).
- Produces: `main() -> None` (chamado por `run_app.py`), `class App(ctk.CTk)` com `self.open_settings()` (preenchido na Task 9).

**Layout (modelo B aprovado), de cima para baixo:**
1. Linha 1: `CTkEntry` com placeholder "Cole o link do YouTube aqui…" e um botão "⚙" (Configurações).
2. Prévia, escondida até carregar: miniatura de 160×90 (`CTkImage`) | título (negrito, com quebra) / "Canal · 12:34 · até 4K" / `CTkOptionMenu` de qualidade com "Melhor disponível (4K)" seguido de `quality_label(h)` para as demais resoluções.
3. Botões: "⬇ MP4" (vermelho), "♪ MP3" (azul), "📁 Abrir pasta" e "Cancelar" (este só aparece durante o download).
4. `CTkProgressBar` + label de status. Exemplos: "35% · 48 MB de 137 MB · faltam ~20s", "Convertendo para formato compatível… 42% (pode levar alguns minutos)", "Convertendo para MP3…", "Concluído: C:\…\título.mp4", ou a mensagem de erro em vermelho.

**Comportamento:**
- `ctk.set_appearance_mode("system")`. Título da janela "YouTube Downloader". Tamanho inicial de ~640×380.
- Logging: `RotatingFileHandler(app_data_dir()/"logs"/"app.log", maxBytes=1_000_000, backupCount=3)`.
- Na abertura: `cleanup_stale_temp`. Em uma thread: `load_tools()` (na primeira vez o status mostra "Preparando componentes…" com os botões desativados) e depois `update_ytdlp` em segundo plano, engolindo erros de rede. Se `find_node()` for None, mostra `NO_NODE_WARNING` no status.
- Todo trabalho pesado roda em `threading.Thread(daemon=True)` e devolve eventos por `queue.Queue`, lida a cada 100 ms com `self.after`. Os widgets só são tocados na thread principal.
- Edição do campo (`<KeyRelease>`, `<<Paste>>`) com debounce de 400 ms: se o `extract_video_id` for válido e diferente do atual, chama `fetch_info` + baixa a miniatura (`urllib` + Pillow) na thread. Se o link for inválido e o campo não estiver vazio, mostra `INVALID_LINK`.
- Auto-colar: na abertura e em `<FocusIn>` da janela, lê `self.clipboard_get()` (com try/except `TclError`) e, se `should_autofill(clip, entry, busy)`, preenche o campo e carrega a prévia.
- MP4: `plan_video(info, None se "Melhor disponível" senão altura)` → `Job.run_video` na thread. MP3: `Job.run_audio`. Durante o download, MP4 e MP3 e o campo ficam desativados e o Cancelar aparece.
- Abrir pasta: se houver um último arquivo, `subprocess.Popen(["explorer", "/select,", str(path)])`. Senão, `os.startfile(base_dir)` (criando a pasta se necessário).
- `DownloadError` → mostra `friendly.message`. Se `suggest_update`, acrescenta um botão "Atualizar agora" que roda `update_ytdlp` na thread. `Cancelled` → "Download cancelado."
- `WM_DELETE_WINDOW`: se houver um job, chama `job.cancel()`, espera a thread por até 5 s e depois `destroy()`.

- [ ] **Step 1: Implementar `app.py` e `run_app.py`**
- [ ] **Step 2: Rodar a suíte para garantir que nada quebrou.** Run: `.\.venv\Scripts\python -m pytest -q`. Expected: PASS.
- [ ] **Step 3: Verificação manual**

Run: `.\.venv\Scripts\python run_app.py`
Conferir:
1. Com um link copiado antes de abrir, o campo já vem preenchido e a prévia aparece.
2. Um link `&list=` mostra o vídeo, não a playlist.
3. Trocar para 720p e baixar MP4 → `Vídeos\<Canal>\<título>.mp4`.
4. Baixar o MP3 do mesmo link → `Áudios\…`.
5. Cancelar no meio → "Download cancelado.", sem arquivo no destino e com `tmp` vazio.
6. Fechar a janela no meio de um download → não sobra nenhum processo `yt-dlp.exe` ou `ffmpeg.exe` no Gerenciador de Tarefas.
7. Um link de vídeo privado ou removido mostra a mensagem amigável.
8. Nenhuma janela de console pisca.

- [ ] **Step 4: Commit** — `git commit -m "feat: main window with preview, quality picker, download and cancel"`

---

### Task 9: Janela de Configurações (`settings.py`)

**Files:**
- Create: `src/ytdl/settings.py`
- Modify: `src/ytdl/app.py` (o botão ⚙ abre a janela, e o app relê `base_dir` ao fechar)

**Interfaces:**
- Consumes: `Config`, `load_config`, `save_config` (Task 2); `ytdlp_version`, `update_ytdlp` (Task 6)
- Produces: `class SettingsWindow(ctk.CTkToplevel)` com `__init__(self, master: App, tools: Tools, on_saved: Callable[[Config], None])`.

**Conteúdo:**
- "Pasta principal": um campo somente leitura com o caminho e o botão "Escolher…" (`filedialog.askdirectory`). Ao escolher, salva na hora com `save_config` e chama `on_saved`.
- "Motor de download": "Versão: 2026.xx.xx" e o botão "Atualizar agora". Ele roda `update_ytdlp` numa thread, mostra "Atualizando…" e depois "Atualizado: <versão>" ou "Sem conexão. Tente mais tarde.".
- A janela é modal (`grab_set`) e fica centralizada sobre a principal.

- [ ] **Step 1: Implementar.**
- [ ] **Step 2: Verificação manual.** Trocar a pasta, baixar um MP3 e conferir que ele foi para a pasta nova. Fechar e reabrir o programa e confirmar que a pasta continua a escolhida. Usar "Atualizar agora" e conferir a versão exibida.
- [ ] **Step 3: Commit** — `git commit -m "feat: settings window (base folder, engine update)"`

---

### Task 10: Empacotamento e atalho

**Files:**
- Create: `scripts/build.ps1`, `scripts/create_shortcut.ps1`, `README.md` (curto, em português: como gerar o build e onde ficam os arquivos)

**Detalhes:**
- `build.ps1`:
  1. Localiza `ffmpeg.exe` e `ffprobe.exe` com `Get-Command`.
  2. Roda `.\.venv\Scripts\pyinstaller --noconfirm --windowed --name "YouTube Downloader" --paths src --collect-data customtkinter --add-binary "<ffmpeg.exe>;ffmpeg" --add-binary "<ffprobe.exe>;ffmpeg" run_app.py`.
  3. Resultado em `dist\YouTube Downloader\`.
- `create_shortcut.ps1`: usa `WScript.Shell` para criar `YouTube Downloader.lnk` na área de trabalho do usuário, apontando para `dist\YouTube Downloader\YouTube Downloader.exe`, com `WorkingDirectory` na mesma pasta.

- [ ] **Step 1: Escrever os scripts e rodar** `powershell -ExecutionPolicy Bypass -File scripts\build.ps1`. Expected: `dist\YouTube Downloader\YouTube Downloader.exe` existe e `dist\YouTube Downloader\_internal\ffmpeg\ffmpeg.exe` existe.
- [ ] **Step 2: Rodar** `scripts\create_shortcut.ps1`. Expected: o atalho aparece na área de trabalho.
- [ ] **Step 3: Matriz de teste final (abrindo pelo atalho)**
  1. 1080p H.264 → MP4 sem conversão.
  2. 4K VP9/AV1 → MP4 convertido. Abre no Media Player, que mostra 3840×2160 nas propriedades.
  3. 4K HDR → MP4 com cores naturais (não lavadas).
  4. 8K → MP4 em 3840×2160.
  5. Shorts → MP4 vertical.
  6. Link com `&list=` → só o vídeo.
  7. Vídeo indisponível → mensagem amigável.
  8. MP3 → 320 kbps com capa.
  9. Nenhuma janela de console pisca e nenhum processo fica órfão ao fechar.
- [ ] **Step 4: Commit** — `git commit -m "build: PyInstaller packaging and desktop shortcut"`
