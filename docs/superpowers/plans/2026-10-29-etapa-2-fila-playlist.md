# ColouBaixô: Etapa 2 (fila, playlist e pasta visível), plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Acrescentar ao app da Etapa 1:
- uma fila com caixinhas e formato por item;
- a entrada de vários links colados de uma vez;
- a escolha de vídeos de uma playlist ou Mix;
- a pasta de destino visível na tela principal.

O app passa a se chamar **ColouBaixô**.

**Architecture:**
- **`queue_model.py`:** toda a regra da fila (situações, duplicados, próximo item, cancelar e limpar) fica num modelo puro, testado sem Tk.
- **`playlist.py`:** a leitura da playlist (`yt-dlp --flat-playlist -J`) também é pura e testada.
- **A janela:** só desenha o modelo e roda dois trabalhadores em segundo plano, um que baixa (reaproveitando `Job`) e um que busca os detalhes dos itens colados. Ela continua seguindo o padrão `events` + `drain_events` da Etapa 1.

**Tech Stack:** o mesmo da Etapa 1: Python 3.12, CustomTkinter 6, yt-dlp.exe, FFmpeg, pytest e PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-29-etapa-2-fila-playlist-design.md` (e a Etapa 1: `docs/superpowers/specs/2026-10-29-youtube-downloader-design.md`)

## Global Constraints

- Tudo da Etapa 1 continua valendo: MP4 até 4K em H.264/AAC, MP3 320 kbps, pastas `Vídeos\<Canal>` e `Áudios\<Canal>`, tmp em `%LOCALAPPDATA%\YoutubeForDownload\tmp`, `CREATE_NO_WINDOW` e mensagens em pt-BR.
- Nome exibido: **ColouBaixô**. Nome de arquivo/exe: **ColouBaixou**. A pasta de dados `%LOCALAPPDATA%\YoutubeForDownload` **não muda**, para não perder a configuração.
- Um download por vez. Itens **Em revisão** nunca são baixados sem um clique em "Baixar selecionados".
- Duplicado = mesmo `video_id` **e** mesmo formato, enquanto o item não terminou (Em revisão, Na fila ou Baixando).
- Mix (`list=` começando com `RD`): limite de 50. Playlist normal: limite de 500.
- Widgets só são tocados na thread principal. Os trabalhadores só fazem `events.put`.
- Trabalho no branch `feature/etapa-2`, criado a partir do HEAD atual.

## Review Focus

1. **Texto colado misturado** (frases, links repetidos, link de playlist, link de outro site): entram só os vídeos válidos, na ordem e sem repetir. Teste `test_extract_video_ids_mixed_text` (Task 1).
2. **Remover o item que está baixando:** cancela aquele item e a fila segue para o próximo, sem ficar "ocupada" para sempre. Teste `test_remove_downloading_returns_it_and_next_continues` (Task 3).
3. **Colar links com a fila rodando:** os itens colados ficam Em revisão e não começam sozinhos. Teste `test_review_items_never_picked_even_while_running` (Task 3).
4. **Playlist com vídeos privados ou removidos, e Mix sem total conhecido:** nada quebra, os indisponíveis vêm desmarcados e bloqueados, e a lista é cortada no limite. Testes `test_unavailable_entries_flagged` e `test_mix_truncated_at_50` (Task 2).
5. **Trocar a pasta com a fila rodando:** o item atual termina na pasta antiga e os próximos vão para a nova. A pasta é lida no início de cada item. Verificação manual na Task 6.

---

### Task 1: `urls.py`: vários links e playlist

**Files:** Modify `src/ytdl/urls.py`. Test `tests/test_urls.py`.

**Interfaces:**
- Produces:
  - `extract_video_ids(text: str) -> list[str]`: acha todos os links de vídeo no texto (separados por espaço ou quebra de linha), na ordem e sem repetir.
  - `extract_playlist_id(text: str) -> str | None`: devolve o parâmetro `list` de um link do YouTube (watch, youtu.be, shorts ou `/playlist`). Devolve None se não houver, ou se o host não for do YouTube.
  - `is_mix(playlist_id: str) -> bool`: `playlist_id.startswith("RD")`.

- [ ] **Step 1: Testes que falham**

```python
def test_extract_video_ids_mixed_text():
    text = (f"olha esses:\nhttps://youtu.be/{ID}\nhttps://www.youtube.com/watch?v=abcdefghijk&list=PL1 "
            f"https://vimeo.com/1  https://youtu.be/{ID}?si=x\nyoutube.com/shorts/ZZZZZZZZZZZ")
    assert extract_video_ids(text) == [ID, "abcdefghijk", "ZZZZZZZZZZZ"]

def test_extract_video_ids_none():
    assert extract_video_ids("nada aqui") == []

@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=N2boHnDVzqY&list=RDDB_DNxGnDzs&index=2", "RDDB_DNxGnDzs"),
    ("https://www.youtube.com/playlist?list=PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH", "PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH"),
    ("https://youtu.be/dQw4w9WgXcQ?list=PL123", "PL123"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", None),
    ("https://evil.com/playlist?list=PL123", None),
])
def test_extract_playlist_id(url, expected):
    assert extract_playlist_id(url) == expected

def test_is_mix():
    assert is_mix("RDDB_DNxGnDzs") and not is_mix("PL123")
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `.\.venv\Scripts\python -m pytest tests/test_urls.py -q`. Expected: ImportError.
- [ ] **Step 3: Implementar.** `extract_video_ids`: separar o texto por espaços em branco e aplicar `extract_video_id` em cada pedaço. `extract_playlist_id`: reaproveitar a checagem de host de `extract_video_id`.
- [ ] **Step 4: Rodar e ver passar** (suíte inteira: `.\.venv\Scripts\python -m pytest -q`).
- [ ] **Step 5: Commit** `feat: multi-link and playlist id parsing`.

---

### Task 2: `playlist.py` + `fetch_playlist`

**Files:** Create `src/ytdl/playlist.py` and `tests/fixtures/playlist_mix.json`. Modify `src/ytdl/commands.py` and `src/ytdl/downloader.py`. Test `tests/test_playlist.py`.

**Interfaces:**
- Consumes: `is_mix` (Task 1), `Tools`, `run_quiet`, `friendly_error`, `DownloadError` (Etapa 1).
- Produces:
  ```python
  MIX_LIMIT = 50; PLAYLIST_LIMIT = 500
  @dataclass(frozen=True)
  class PlaylistEntry: video_id: str; title: str; channel: str; duration: int; available: bool
  @dataclass(frozen=True)
  class Playlist: id: str; title: str; entries: tuple[PlaylistEntry, ...]; is_mix: bool; truncated: bool
  def playlist_limit(playlist_id: str) -> int
  def parse_playlist(data: dict, limit: int) -> Playlist
  def thumb_url(video_id: str) -> str          # f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
  # commands.py
  def playlist_args(t: Tools, url: str, limit: int) -> list[str]
      # [ytdlp, "--yes-playlist", "--flat-playlist", "-J", "--playlist-end", str(limit),
      #  "--encoding", "utf-8"] + js-runtimes (como base_args) + [url]   — NÃO usa base_args (que tem --no-playlist)
  # downloader.py
  def fetch_playlist(t: Tools, url: str, playlist_id: str, run=run_quiet) -> Playlist
  ```
- Regras de `parse_playlist`:
  - `available=False` quando `title` estiver em `("[Private video]", "[Deleted video]")` ou quando `availability` estiver em `("private", "needs_auth", "subscriber_only", "premium_only")`.
  - `channel` = `channel` ou `uploader` ou `"Desconhecido"`. `duration` = `int(duration or 0)`.
  - `is_mix` = `is_mix(data["id"])`.
  - `truncated` = `is_mix`, ou `len(entries_raw) > limit`, ou `(playlist_count or 0) > limit`.
  - Entradas são cortadas em `limit`. Entradas sem `id` são ignoradas.

- [ ] **Step 1: Fixture.** Gravar `tests/fixtures/playlist_mix.json` a partir da saída real, reduzida para 3 entradas. Comando: `yt-dlp --flat-playlist -J --playlist-end 3 "https://www.youtube.com/watch?v=N2boHnDVzqY&list=RDDB_DNxGnDzs"`. Manter só os campos `id`, `title`, `_type`, `entries[].{id,title,channel,uploader,duration,availability}` e `playlist_count`. Depois trocar a 3ª entrada por `{"id": "xxxxxxxxxxx", "title": "[Private video]", "duration": null}`.
- [ ] **Step 2: Testes que falham**

```python
DATA = json.loads((FIX / "playlist_mix.json").read_text("utf-8"))

def test_parse_mix_basic():
    p = parse_playlist(DATA, 50)
    assert p.is_mix and p.truncated and p.id == "RDDB_DNxGnDzs"
    assert [e.video_id for e in p.entries][:2] == ["N2boHnDVzqY", "DB_DNxGnDzs"]
    assert p.entries[0].channel == "Diego e Victor Hugo"

def test_unavailable_entries_flagged():
    assert parse_playlist(DATA, 50).entries[2].available is False

def test_mix_truncated_at_50():
    many = dict(DATA, entries=[dict(DATA["entries"][0], id=f"{i:011d}") for i in range(60)])
    assert len(parse_playlist(many, 50).entries) == 50

def test_normal_playlist_truncated_flag():
    d = dict(DATA, id="PL1", playlist_count=600)
    p = parse_playlist(d, 500)
    assert not p.is_mix and p.truncated

def test_limits():
    assert playlist_limit("RDxyz") == 50 and playlist_limit("PL1") == 500

def test_playlist_args_yes_playlist_flat():
    a = playlist_args(Tools(Path("y.exe"), Path("ff"), None), "U", 50)
    assert "--no-playlist" not in a and "--yes-playlist" in a and "--flat-playlist" in a
    assert a[a.index("--playlist-end") + 1] == "50" and a[-1] == "U"

def test_fetch_playlist_error_is_friendly():
    run = lambda args, timeout=None: subprocess.CompletedProcess([], 1, "", "ERROR: The playlist does not exist")
    with pytest.raises(DownloadError):
        fetch_playlist(TOOLS, "U", "PL1", run=run)
```

- [ ] **Step 3: Ver falhar → implementar → ver passar** (suíte inteira).
- [ ] **Step 4: Verificação real.** Rodar `fetch_playlist` no Mix do usuário e numa playlist normal (`PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH`) e imprimir o título, a quantidade de entradas e o `truncated`. Esperado: Mix com 50 entradas e truncated=True; a playlist normal com 246 entradas e truncated=False.
- [ ] **Step 5: Commit** `feat: playlist listing via yt-dlp flat-playlist`.

---

### Task 3: `queue_model.py`

**Files:** Create `src/ytdl/queue_model.py`. Test `tests/test_queue_model.py`.

**Interfaces:**
- Consumes: `VideoInfo` (Etapa 1), `Progress` (Etapa 1).
- Produces:
  ```python
  class Status(Enum): REVIEW, QUEUED, DOWNLOADING, DONE, ERROR, CANCELLED
  ACTIVE = {Status.REVIEW, Status.QUEUED, Status.DOWNLOADING}
  FINISHED = {Status.DONE, Status.ERROR, Status.CANCELLED}
  Kind = Literal["video", "audio"]

  @dataclass
  class Item:
      id: int; video_id: str; kind: Kind; status: Status
      checked: bool = True
      title: str | None = None; channel: str | None = None; duration: int | None = None
      info: VideoInfo | None = None; res: int | None = None      # res só vem da prévia
      progress: Progress | None = None; error: str | None = None; path: Path | None = None

  class QueueModel:
      items: list[Item]
      def add(self, video_id: str, kind: Kind, status: Status, **fields) -> Item | None   # None se duplicado
      def get(self, item_id: int) -> Item | None
      def set_kind(self, item_id: int, kind: Kind) -> bool     # só REVIEW/QUEUED; recusa se virar duplicado
      def set_checked(self, item_id: int, checked: bool) -> bool   # só REVIEW
      def review_checked_count(self) -> int
      def release_checked(self) -> int                          # REVIEW+checked → QUEUED, devolve quantos
      def current(self) -> Item | None                          # o DOWNLOADING
      def next_item(self) -> Item | None                        # primeiro QUEUED (ordem de liberação)
      def start(self, item_id: int) -> None                     # QUEUED → DOWNLOADING
      def finish(self, item_id: int, path: Path) -> None        # → DONE
      def fail(self, item_id: int, message: str) -> None        # → ERROR (de qualquer situação ativa)
      def mark_cancelled(self, item_id: int) -> None            # → CANCELLED
      def remove(self, item_id: int) -> Item | None             # tira da lista e devolve o item removido
      def cancel_all(self) -> Item | None                       # QUEUED → CANCELLED; devolve o DOWNLOADING (quem chama cancela o Job)
      def clear_finished(self) -> int
  ```
- A ordem de liberação é guardada num contador `released_seq`, atribuído quando o item vira QUEUED, seja pelo `add` com QUEUED ou pelo `release_checked`. `next_item` devolve o QUEUED com o menor `released_seq`. A lista visual continua na ordem de inserção.

- [ ] **Step 1: Testes que falham** (um teste por regra):

```python
def test_add_and_duplicate_same_kind_rejected(): ...      # add(v,"video",QUEUED) ok; add(v,"video",REVIEW) → None; add(v,"audio",QUEUED) ok
def test_duplicate_allowed_after_finished(): ...          # finish → add(v,"video",...) ok
def test_review_items_never_picked_even_while_running(): ...
    # q1=add(a,QUEUED); start(q1); add(b,REVIEW); add(c,REVIEW) → next_item() is None
def test_release_checked_only_marked(): ...               # 3 REVIEW, desmarca 1 → release_checked()==2; o desmarcado segue REVIEW
def test_next_item_follows_release_order(): ...           # REVIEW x,y; add(z,QUEUED); release_checked() → next: z, depois x, depois y
def test_error_does_not_stop_queue(): ...                 # fail(q1) → next_item() é o q2
def test_cancel_all_keeps_review(): ...                   # DOWNLOADING d, QUEUED e, REVIEW f → cancel_all() is d-item; e CANCELLED; f REVIEW
def test_remove_downloading_returns_it_and_next_continues(): ...
    # remove(d) devolve d com status DOWNLOADING; d some de items; next_item() é o próximo QUEUED
def test_set_kind_and_checked_locked_after_start(): ...   # start → set_kind False, set_checked False
def test_set_kind_rejects_duplicate(): ...                # (v,video) e (v,audio) ativos → set_kind(audio→video) False
def test_clear_finished(): ...                            # DONE+ERROR+CANCELLED removidos; REVIEW/QUEUED ficam; devolve 3
def test_review_checked_count(): ...
```

- [ ] **Step 2: Ver falhar → implementar → ver passar** (suíte inteira).
- [ ] **Step 3: Commit** `feat: download queue model`.

---

### Task 4: Tela principal: pasta visível, fila e trabalhadores

**Files:** Create `src/ytdl/queue_view.py`. Modify `src/ytdl/app.py`.

**Interfaces:**
- Consumes: `QueueModel`, `Status`, `Item` (Task 3); `extract_video_ids`, `extract_playlist_id` (Task 1); `thumb_url` (Task 2); `describe` (Etapa 1).
- Produces:
  - `class QueueView(ctk.CTkScrollableFrame)` com `render(items: list[Item]) -> None` (redesenha reaproveitando as linhas por `item.id`) e os callbacks `on_toggle(id, bool)`, `on_kind(id, kind)`, `on_remove(id)` e `on_open(id)`.
  - `QueueView.set_thumb(video_id: str, image) -> None`.
  - No `App`: `add_to_queue(entries: list[tuple[str, dict]], kind: Kind, status: Status) -> int`, onde `dict` traz title/channel/duration/info/res, e `pump_queue() -> None`.

**Comportamento (spec, seção "Comportamento"):**
- **Linha da pasta:** "📁 Salvando em: `<base_dir>`" + o botão **Alterar** (`filedialog.askdirectory`, `save_config`, `self.settings = …`). `_on_settings_saved` também atualiza essa linha.
- **Botões MP4/MP3 da prévia:** `add_to_queue([(video_id, {"title", "channel", "duration", "info", "res"})], kind, Status.QUEUED)`. Se for duplicado, o status mostra "Já está na fila". Em seguida `pump_queue()`. A prévia **não é limpa**, e o campo **não fica desativado** durante downloads.
- **Colagem:** o handler de `<<Paste>>` lê a área de transferência. Se `len(extract_video_ids(clip)) >= 2`, adiciona todos como `Status.REVIEW` com o formato geral, mostra "N links adicionados para revisão" (e "N links não reconhecidos", se houver pedaços que parecem link mas falharam) e devolve `"break"`. `_check_entry` faz o mesmo se o texto digitado tiver 2 ou mais IDs, e limpa o campo depois.
- **Cabeçalho da fila:** "Fila (N)" e um `CTkSegmentedButton(values=["MP4", "MP3"])` para o formato geral (`self.default_kind`). Botões **Baixar selecionados (N)** (visível só se `review_checked_count() > 0`; faz `release_checked()` + `pump_queue()`), **Cancelar tudo** (`cancel_all()` e, se devolver um item, `self.job.cancel()`) e **Limpar finalizados**.
- **`pump_queue`:** se não houver `self.job` e houver um `next_item`, faz `start(item)`. Captura `base = self.settings.base_dir` nesse momento. Abre uma thread que:
  - chama `fetch_info` se `item.info` for None;
  - para `kind == "video"`, roda `Job.run_video(url, info, plan_video(info, item.res), base)`;
  - para `kind == "audio"`, roda `run_audio`.
  - Os eventos `q_progress(item_id, Progress)`, `q_done(item_id, path)`, `q_failed(item_id, msg)` e `q_cancelled(item_id)` voltam pela fila de eventos. Cada handler atualiza o modelo, zera `self.job`, chama `render` e depois `pump_queue()`.
- **Remover (✕):** `item = model.remove(id)`. Se `item.status == DOWNLOADING`, chama `self.job.cancel()`. O `q_cancelled` daquele id, quando chegar, só zera o job e chama `pump_queue`, porque o item já saiu do modelo.
- **Detalhes dos itens colados:** uma thread "detalhes" que processa, um por vez, os itens REVIEW/QUEUED com `title is None`. Ela chama `fetch_info`, que gera `q_info(item_id, info)` (preenche title/channel/duration/info) ou `q_info_failed(item_id, msg)` (vira `model.fail`).
- **Miniaturas:** carregadas em segundo plano por `thumb_url(video_id)`, num cache `video_id → CTkImage(56×32)`, e aplicadas com `set_thumb`.
- **Linha do item:**
  - caixinha, só em REVIEW;
  - miniatura;
  - título cortado em 60 caracteres e o canal;
  - `CTkOptionMenu` MP4/MP3, ativo em REVIEW/QUEUED;
  - texto da situação: "Em revisão", "Aguardando", `describe(progress)` + barra quando estiver baixando, "✔ Concluído" (clicável: `explorer /select`), "Erro: <msg>" em vermelho ou "Cancelado";
  - botão ✕.
- **Fechar:** se houver `self.job`, pergunta com `tkinter.messagebox.askyesno("ColouBaixô", "Há downloads em andamento. Fechar e cancelar?")`. Se a resposta for Sim, segue o `_on_close` da Etapa 1.
- **Tamanho da janela:** `geometry("760x640")`, `minsize(640, 520)`. A fila ocupa o espaço que sobra (`grid_rowconfigure(<linha da fila>, weight=1)`).
- **O que sai do código da Etapa 1:** a barra de progresso e o botão Cancelar soltos (o progresso agora fica em cada item), e `_start_download` vira `add_to_queue`.

- [ ] **Step 1: Implementar `queue_view.py` e as mudanças no `app.py`.**
- [ ] **Step 2: Suíte inteira passa.**
- [ ] **Step 3: Verificação com script** (como na Etapa 1, dirigindo a janela de verdade e tirando prints com a janela em primeiro plano):
  1. colar 3 links, desmarcar 1 e clicar em Baixar selecionados: baixam só 2;
  2. colar 2 links enquanto um baixa: eles ficam "Em revisão";
  3. remover o item que está baixando: o próximo começa e `tmp` fica vazio;
  4. um link de vídeo removido no meio da fila: aparece "Erro" e a fila segue;
  5. MP4 e depois MP3 do mesmo vídeo: os dois entram, e um 2º MP4 recebe "Já está na fila";
  6. Cancelar tudo e Limpar finalizados.
- [ ] **Step 4: Commit** `feat: download queue UI with review checkboxes and visible folder`.

---

### Task 5: Pergunta da playlist e janela de escolha

**Files:** Create `src/ytdl/playlist_window.py`. Modify `src/ytdl/app.py`.

**Interfaces:**
- Consumes: `extract_playlist_id`, `is_mix` (Task 1); `fetch_playlist`, `Playlist`, `PlaylistEntry`, `MIX_LIMIT`, `PLAYLIST_LIMIT`, `thumb_url` (Task 2); `App.add_to_queue`, `App.pump_queue` (Task 4).
- Produces:
  - `ask_playlist(master, playlist_title: str | None) -> Literal["video", "playlist", None]`: modal pequeno com "Este vídeo faz parte de uma playlist." e os botões **Só este vídeo** e **Ver a playlist**. None = fechou.
  - `class PlaylistWindow(ctk.CTkToplevel)` com `__init__(self, master, tools, url, playlist_id, preselect: str | None, default_kind, on_add: Callable[[list[PlaylistEntry], Kind], None])`.

**Comportamento:**
- **Em `_check_entry`:**
  - se o link tiver **vídeo e playlist** e esse texto ainda não foi perguntado (`self._asked_playlist`), chama `ask_playlist`. "video" segue para a prévia normal. "playlist" abre a `PlaylistWindow` com `preselect = video_id`.
  - Se o link tiver **só playlist** (`/playlist?list=`), abre a `PlaylistWindow` direto, com `preselect=None`.
- **`PlaylistWindow`:**
  - Ao abrir, mostra "Carregando a playlist…" e chama `fetch_playlist` numa thread.
  - Depois mostra o título, a observação ("Mix do YouTube: mostrando os primeiros 50" ou "mostrando os primeiros 500" quando `truncated` e não é Mix) e uma lista rolável (`CTkScrollableFrame`). Cada linha tem caixinha (desativada se `not available`), miniatura, título, canal e duração (`format_duration`).
  - Embaixo: **Marcar todos / Desmarcar todos** (só os disponíveis), um `CTkSegmentedButton` MP4/MP3 (começa no `default_kind`) e **Adicionar N à fila** (desativado quando N=0).
  - Adicionar chama `on_add(marcados, kind)` e fecha.
  - Em caso de erro: mensagem amigável em vermelho e o botão Fechar.
  - É modal (`grab_set` depois de 50 ms) e centralizada.
- **`on_add` no App:** chama `add_to_queue([(e.video_id, {"title", "channel", "duration"})...], kind, Status.QUEUED)` e depois `pump_queue()`. O status mostra "N vídeos adicionados à fila" e, se houver, "(M já estavam na fila)".

- [ ] **Step 1: Implementar.**
- [ ] **Step 2: Suíte inteira passa.**
- [ ] **Step 3: Verificação com script:**
  1. o Mix do usuário (`watch?v=N2boHnDVzqY&list=RDDB_DNxGnDzs&index=2`): aparece a pergunta; "Ver a playlist" mostra 50 itens com `N2boHnDVzqY` marcado; marcar mais 2 em MP3 e adicionar: os 3 baixam em `Áudios\<canal>`;
  2. "Só este vídeo" leva à prévia normal;
  3. uma playlist normal `/playlist?list=PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH` abre direto com 246 itens.
- [ ] **Step 4: Commit** `feat: playlist prompt and picker window`.

---

### Task 6: Nome ColouBaixô, empacotamento e teste final

**Files:** Modify `src/ytdl/app.py` (título), `src/ytdl/settings.py` (título "Configurações — ColouBaixô"), `scripts/build.ps1`, `scripts/create_shortcut.ps1` e `README.md`.

- **`build.ps1`:** `--name "ColouBaixou"`. O guarda de "programa aberto" checa os processos `ColouBaixou` e `YouTube Downloader`.
- **`create_shortcut.ps1`:** cria `ColouBaixô.lnk`, apontando para `dist\ColouBaixou\ColouBaixou.exe`, e apaga o antigo `YouTube Downloader.lnk` da área de trabalho, se existir.
- **`README.md`:** título "ColouBaixô", explicação da fila e da playlist, e os caminhos novos.
- **Limpeza:** apagar `dist\YouTube Downloader\` antigo depois que o build novo funcionar (é gerado, não tem dados do usuário).

- [ ] **Step 1:** Fazer as mudanças e rodar a suíte inteira.
- [ ] **Step 2:** Rodar `scripts\build.ps1` e `scripts\create_shortcut.ps1`. Esperado: `dist\ColouBaixou\ColouBaixou.exe` e `_internal\ffmpeg\ffmpeg.exe` existem, o atalho novo existe e o antigo sumiu.
- [ ] **Step 3:** Abrir pelo atalho. A janela tem o título "ColouBaixô". Testar no `.exe`: colar 2 links, baixar selecionados, fechar no meio (aparece a confirmação, não sobra processo e o `tmp` fica vazio). Trocar a pasta pelo botão **Alterar** com a fila rodando: o item atual termina na pasta antiga e o próximo vai para a nova.
- [ ] **Step 4: Commit** `feat: rename app to ColouBaixô and package it`.

---

### Task 7: Publicar no GitHub

- [ ] **Step 1:** Integrar os branches em `main` localmente: `git checkout main && git merge --no-ff feature/etapa-1 && git merge --no-ff feature/etapa-2`. A suíte inteira precisa passar em `main`.
- [ ] **Step 2:** Confirmar que `.gitignore` exclui `.venv/`, `dist/`, `build/` e `.superpowers/`. `git status` limpo e `git ls-files` sem binários grandes.
- [ ] **Step 3:** `git remote add origin https://github.com/clauberteixeira/ColouBaixou.git` (o repositório o usuário cria pela web) e `git push -u origin main`.
- [ ] **Step 4:** Conferir o resultado com `gh repo view clauberteixeira/ColouBaixou`.
