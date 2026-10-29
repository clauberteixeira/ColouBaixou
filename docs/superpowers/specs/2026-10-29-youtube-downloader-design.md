# YouTube Downloader: desenho da ferramenta (Etapa 1)

Data: 2026-10-29

## Por que existe

O usuário quer guardar vídeos do YouTube no próprio computador para assistir depois e, às vezes, ficar só com o áudio. Hoje ele não tem uma ferramenta para isso. Ele quer colar o link, escolher vídeo ou áudio e receber o arquivo na melhor qualidade que o vídeo oferece, já organizado em pastas.

Uso pessoal, em um único computador Windows 11.

## Objetivos

- Colar um link do YouTube e baixar o **vídeo em MP4** na maior resolução disponível, **limitada a 4K** (decisão do usuário).
- Colar um link e baixar só o **áudio em MP3**.
- O MP4 precisa **abrir em qualquer player** (Windows, celular, TV). O objetivo é assistir, então compatibilidade vem antes de velocidade.
- Organizar os arquivos sozinho, em pastas por tipo e por canal.
- Continuar funcionando quando o YouTube mudar: atualizar automaticamente o componente de download.

## Fora do escopo (Etapa 1)

- Playlists inteiras (vai para a Etapa 2).
- Fila com vários downloads ou downloads simultâneos (Etapa 2).
- Legendas.
- Vídeos privados, só para membros ou com restrição de idade, que exigem login. O programa avisa e não tenta.
- Transmissões ao vivo em andamento.
- Outros sites além do YouTube.
- Versão web, celular, Mac ou Linux.

## O que seria um fracasso

- Um MP4 baixado que não abre ou abre sem imagem/som num player comum.
- O programa parar de funcionar semanas depois por causa de mudança no YouTube, sem jeito fácil de consertar.
- Arquivos jogados numa pasta qualquer, sem organização.
- Ter que usar linha de comando para qualquer coisa.

## Decisões do usuário

- **Programa de Windows**, aberto por ícone na área de trabalho (não página web).
- **Layout "B — Com prévia"**, escolhido entre três modelos:
  1. Campo para colar o link.
  2. Ao colar, aparece a capa (miniatura), o título, o canal, a duração e a qualidade máxima disponível.
  3. Seletor de qualidade, que já vem em "Melhor disponível" e permite escolher uma menor (ex.: 1080p, 720p).
  4. Botões **MP4**, **MP3** e **Abrir pasta**.
  5. Barra de progresso com %, MB baixados de MB total e tempo restante.
- **Pastas automáticas** dentro de uma pasta principal configurável:
  - `<pasta principal>\Vídeos\<Nome do Canal>\<título>.mp4`
  - `<pasta principal>\Áudios\<Nome do Canal>\<título>.mp3`
- **Duas etapas**: esta é a Etapa 1. Playlists e fila ficam para a Etapa 2.
- **Limite de 4K no MP4**: vídeos 8K são baixados em 4K (2160p). Motivo: converter 8K levaria horas nesta máquina, e o resultado não tocaria na maioria dos aparelhos.
- **Stack técnica**: o usuário deixou a escolha com o Claude (seção abaixo).

## Decisões técnicas (escolhas do Claude; o usuário entregou essas escolhas a ele)

Ambiente já existente na máquina: Windows 11, Python 3.12, Node.js, FFmpeg 8.1 (instalado via winget), placa NVIDIA RTX 4060 e processador AMD Ryzen 7 3800X. Falta o yt-dlp.

- **Linguagem:** Python 3.12.
- **Interface:** CustomTkinter (visual moderno, leve e simples de empacotar). Pillow para exibir a miniatura.
- **Motor de download:** o **executável standalone `yt-dlp.exe`**, chamado como subprocesso, e **não** a biblioteca Python embutida no `.exe`. Motivo: o `yt-dlp.exe` se atualiza sozinho (`yt-dlp -U`) sem precisar reempacotar o programa.
  - Metadados da prévia: `yt-dlp -J <url>` (JSON com título, canal, duração, miniatura e formatos).
  - Progresso: `--newline` com `--progress-template`, lido linha a linha.
- **Runtime JavaScript:** versões recentes do yt-dlp precisam de um runtime JS externo para extrair formatos do YouTube por completo. O programa precisa garantir isso, seja usando o Node.js já instalado (`--js-runtimes node`), seja levando um Deno junto. A escolha fica com quem construir, mas o programa precisa funcionar na máquina do usuário sem configuração manual.
- **FFmpeg:** uma cópia de `ffmpeg.exe` e `ffprobe.exe` vai junto com o programa, para não depender do caminho do winget.
- **Arquivos auxiliares graváveis** (`yt-dlp.exe`, configuração) ficam em `%LOCALAPPDATA%\YoutubeForDownload\`, onde o programa tem permissão de escrita para se atualizar.
- **Empacotamento:** PyInstaller em modo pasta (não arquivo único, para abrir mais rápido) e um atalho na área de trabalho. Sem instalador formal na Etapa 1.

## Regras de comportamento

### Links aceitos
- `youtube.com/watch?v=…`, `youtu.be/…`, `youtube.com/shorts/…`, `music.youtube.com/watch?v=…`, `m.youtube.com/…`.
- Link com `&list=…` (vídeo dentro de playlist): baixa **só aquele vídeo** (`--no-playlist`).
- Link inválido ou de outro site: mensagem clara, sem travar.
- Ao abrir o programa ou trazer a janela para frente, se a área de transferência tiver um link do YouTube, ele já é colado no campo e a prévia é carregada (escolha do Claude).

### Vídeo (MP4)
- "Melhor disponível" = a maior resolução existente **até 2160p (4K)** e, nela, a maior taxa de quadros. Vídeos com resolução maior são baixados na versão de 4K que o YouTube oferece. Se não houver versão 4K, a de 8K é reduzida para 4K na conversão.
- Se o melhor vídeo já estiver em **H.264 (avc1)**, ele é combinado com áudio **AAC (m4a)** num MP4 sem recodificar.
- Se a resolução escolhida só existir em **VP9 ou AV1** (comum acima de 1080p), o vídeo é **convertido para H.264** com o FFmpeg, e o áudio vai em AAC. A tela avisa que a conversão pode levar alguns minutos e mostra o progresso dessa fase separado do download.
  - Usar a **codificação por hardware da RTX 4060 (NVENC H.264)** quando disponível e cair para x264 por software se ela falhar. A qualidade visual não pode cair visivelmente.
- **HDR** (escolha do Claude): ao escolher o formato, preferir a versão **SDR** (8 bits) quando o YouTube oferecer a mesma resolução em SDR. Se só existir HDR, fazer **tone mapping para SDR** na conversão para H.264, para as cores não ficarem lavadas.
- O seletor de qualidade lista apenas as resoluções que o vídeo realmente tem, até 4K. Shorts e vídeos verticais são identificados pela menor dimensão (ex.: 1080×1920 aparece como 1080p).

### Áudio (MP3)
- Baixa o melhor áudio disponível e converte para **MP3 320 kbps**.
- Embute a miniatura como capa e grava os metadados: título, canal como artista e data.

### Nomes e pastas
- Pasta principal padrão: `%USERPROFILE%\Downloads\YouTube`. Ela pode ser mudada numa pequena tela de **Configurações** e fica gravada para as próximas vezes.
- Os nomes de canal e de título têm os caracteres proibidos no Windows (`\ / : * ? " < > |`) e espaços/pontos finais removidos, e são encurtados para não estourar o limite de caminho.
- Se já existir um arquivo com o mesmo nome, o novo recebe ` (2)`, ` (3)` e assim por diante. Nada é sobrescrito.
- **Abrir pasta** abre o Explorer na pasta do último arquivo baixado, com o arquivo selecionado. Se ainda não houve download, abre a pasta principal.

### Durante o download
- Um download por vez. Enquanto baixa, os botões MP4/MP3 ficam desativados e aparece um botão **Cancelar**.
- Cancelar interrompe o processo e apaga os arquivos temporários parciais.
- Ao terminar, mostra "Concluído" com o caminho do arquivo.

### Erros (mensagens em português, sem termos técnicos)
- Sem internet.
- Vídeo indisponível, removido ou privado.
- Vídeo com restrição de idade ou só para membros ("precisa de login, não suportado").
- Transmissão ao vivo em andamento.
- Falha do yt-dlp que pode ser resolvida com atualização: sugere atualizar e oferece o botão.
- Espaço em disco insuficiente.
- Os detalhes técnicos vão para um arquivo de log em `%LOCALAPPDATA%\YoutubeForDownload\logs\`.

### Atualização do motor
- Ao abrir, o programa verifica em segundo plano se há versão nova do `yt-dlp.exe` e atualiza sem atrapalhar o uso. Se não houver internet, segue em silêncio.
- Em Configurações há também um botão manual "Atualizar agora" que mostra a versão atual.
- Na primeira execução, se o `yt-dlp.exe` não existir em `%LOCALAPPDATA%`, ele é baixado do GitHub oficial do projeto.

## Idioma e aparência
- Interface toda em português do Brasil.
- Janela única, no estilo do modelo B. Tema claro/escuro acompanhando o Windows (escolha do Claude).

## Testes
- Testes automatizados para as partes que não dependem de rede: limpeza de nomes, validação de links, leitura da linha de progresso, escolha de formato a partir de um JSON de exemplo do `yt-dlp -J` e montagem dos caminhos de destino.
- Teste manual com vídeos reais: um em 1080p H.264, um em 4K (VP9/AV1, que precisa de conversão), um em 4K HDR, um em 8K (precisa sair em 4K), um Shorts, um link com `&list=` e um vídeo indisponível. Os MP4 convertidos precisam abrir no Media Player do Windows com as cores corretas.

## Fica a critério de quem construir
- Estrutura de pastas do código e nomes de módulos.
- Como a interface conversa com o subprocesso (threads, filas).
- Escolha entre Node.js e Deno como runtime JS, desde que funcione sem configuração manual.
- Parâmetros exatos do FFmpeg na conversão para H.264, respeitando "sem perda visível de qualidade".
- Detalhes visuais (cores, espaçamentos, ícone).

## Etapa 2 (registro, não construir agora)
- Playlists: listar os vídeos, marcar quais baixar e salvar numa subpasta com o nome da playlist.
- Fila de downloads com histórico.
