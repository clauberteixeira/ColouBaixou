# YouTube Downloader: Etapa 2 (fila, playlist e pasta visível)

Data: 2026-10-29
Base: Etapa 1, já construída e em uso (`docs/superpowers/specs/2026-10-29-youtube-downloader-design.md`). Tudo o que não está escrito aqui segue a Etapa 1: regras de MP4/MP3, limite de 4K, HDR, nomes de arquivo, pastas por canal, mensagens de erro, atualização do motor e o download acelerado (8 partes paralelas, NVENC p4).

## Por que

Usando a Etapa 1, o usuário percebeu três incômodos:
1. Para baixar 2, 3, 5 vídeos ele precisa colar e esperar um por um.
2. Ao copiar um link de dentro de uma playlist (inclusive Mix do YouTube, como `watch?v=…&list=RD…`), ele quer poder baixar a playlist toda ou escolher só alguns vídeos.
3. A pasta de destino fica escondida no ⚙. Ele quer vê-la e trocá-la na tela principal. A escolha continua gravada como padrão.

## Objetivos

- Uma **fila** na tela principal: os vídeos baixam um de cada vez, em sequência, sem precisar ficar olhando.
- **Colar vários links de uma vez** (um por linha, ou separados por espaço) e todos entrarem na fila.
- **Caixinha de seleção em cada item da fila**, para baixar só o que o usuário quiser.
- **MP4 ou MP3 por item**, com uma escolha geral ("Formato para os próximos") que vale para os novos itens.
- **Link com playlist**: perguntar "Só este vídeo" ou "Ver a playlist". Em "Ver a playlist", mostrar a lista com caixinhas, "Marcar todos", a escolha MP4/MP3 e "Adicionar N à fila".
- **Pasta visível**: a linha "📁 Salvando em: <caminho> [Alterar]" na tela principal.

## Fora do escopo

- Guardar a fila quando o programa é fechado (ela some ao fechar).
- Baixar vários vídeos ao mesmo tempo (é sempre um por vez).
- Escolher a resolução por item da fila: itens da fila usam "Melhor disponível". A resolução continua escolhível só na prévia de um link único.
- Links de canal (`/@canal`, `/videos`) como fonte de lista.
- Reordenar a fila arrastando.

## O que seria um fracasso

- Um vídeo com erro parar a fila inteira.
- Fechar o programa no meio da fila deixar arquivo pela metade ou processo rodando (mesma garantia da Etapa 1).
- Colar um link de Mix travar o programa tentando ler uma playlist "infinita".
- A tela travar enquanto a playlist carrega.

## Decisões do usuário

- Layout aprovado no modelo visual (três telas: principal com fila, pergunta da playlist, escolha da playlist).
- Escolha de formato: **o usuário define**. Há uma escolha geral MP4/MP3 para os novos itens, e cada item que ainda está aguardando pode ser trocado individualmente.
- **Caixinhas de seleção** nos itens da fila, para baixar só os que ele quiser.
- Pasta principal: continua com um padrão (`Downloads\YouTube`), mas fica visível na tela principal e o usuário troca quando quiser. A escolha fica gravada.

## Comportamento

### Tela principal (de cima para baixo)
1. Campo de link (agora aceita vários links) + ⚙.
2. Linha da pasta: "📁 Salvando em: `<caminho>`" + botão **Alterar** (o mesmo seletor e a mesma gravação do ⚙ → Escolher…).
3. Prévia do link único: igual à Etapa 1 (capa, título, canal, duração, qualidade).
4. Botões **⬇ MP4** e **♪ MP3** (da prévia) e **📁 Abrir pasta**.
5. **Fila**: título "Fila (N)" à esquerda e a chave "Formato para os próximos: MP4 | MP3" à direita. Abaixo, a lista com rolagem e os botões **Baixar selecionados (N)** (só aparece quando há itens Em revisão), **Cancelar tudo** e **Limpar finalizados**.

### Item da fila
- Caixinha de seleção, miniatura pequena, título (cortado com "…"), canal, formato (MP4/MP3) e situação.
- Situações: **Em revisão** (colado, esperando o usuário conferir), **Na fila** ("Aguardando"), **Baixando** (barra + "62% · 48 MB de 77 MB · faltam ~5s"), **Convertendo…**, **✔ Concluído** (clicar abre a pasta com o arquivo selecionado), **Erro: <mensagem amigável da Etapa 1>**, **Cancelado**.
- **✕** remove o item. Se ele estiver baixando, cancela primeiro.
- O formato pode ser alterado enquanto o item estiver **Em revisão** ou **Na fila**. A caixinha só existe enquanto ele está **Em revisão**.
- O mesmo vídeo **no mesmo formato** não entra duas vezes enquanto ainda não terminou (Em revisão, Na fila ou Baixando). Ao tentar, um aviso curto diz "Já está na fila". O mesmo vídeo em MP4 e em MP3 pode entrar (escolha do Claude: ter o clipe e a música é um uso comum).

### Como os itens entram e quando a fila anda

Cada item tem uma situação. Antes de baixar, existem duas:
- **Em revisão**: entrou por colagem múltipla e espera o usuário conferir. Caixinha e formato podem ser alterados. Nunca é baixado sozinho.
- **Na fila**: o usuário já liberou o item. É baixado quando chegar a vez, na ordem em que foi liberado.

(Escolha do Claude: isso garante que o usuário confira os links colados antes de qualquer download, que é o motivo das caixinhas.)

- **MP4/MP3 da prévia (link único)**: o item entra **Na fila**, com aquele formato e a qualidade escolhida na prévia, no **fim da fila**. Se nada estiver baixando, começa na hora.
- **Colar texto com 2 ou mais links**: todos os links de vídeo válidos entram **Em revisão, marcados**, com o formato geral. Isso vale também se a fila estiver rodando: eles nunca começam sozinhos. Links inválidos no meio são ignorados, com o aviso "N links não reconhecidos". Links com playlist dentro de uma colagem múltipla entram só como o vídeo.
- **Baixar selecionados (N)**: N é o número de itens Em revisão e marcados. O botão passa todos eles para **Na fila**, na ordem da lista, e a fila começa se estiver parada. Os desmarcados continuam Em revisão.
- **Playlist** ("Adicionar N à fila"): os vídeos marcados entram direto **Na fila**, porque o usuário já escolheu na janela.
- A fila baixa os itens **Na fila** em ordem. Quando um termina, com sucesso ou erro, passa para o próximo. Quando não sobra nenhum, ela para.
- **Cancelar tudo**: cancela o item que está baixando e passa todos os itens **Na fila** para **Cancelado**. Os itens Em revisão não mudam (escolha do Claude: o usuário deixou esses de propósito).
- **Limpar finalizados** (escolha do Claude: o nome no modelo era "Limpar concluídos"): remove da lista os itens **Concluído, Erro e Cancelado**.
- Enquanto a fila roda, o campo de link e a prévia **continuam utilizáveis** para adicionar mais itens. Isso muda a Etapa 1, que bloqueava o campo durante o download.

### Prévia de cada item
- Itens que vêm de colagem múltipla entram na hora com o link como título provisório. Os detalhes (título, canal, capa) são buscados em segundo plano, um por vez, sem travar a tela.
- Itens que vêm da playlist já entram com título, canal, duração e capa da listagem.
- Se a busca de detalhes falhar (vídeo privado, removido etc.), o item vira **Erro** com a mensagem amigável e não é baixado.

### Link com playlist
- Um link com `list=` (watch, youtu.be, shorts) mostra a pergunta: "Este vídeo faz parte da playlist **<nome>**." com os botões **Só este vídeo** e **Ver a playlist**.
  - **Só este vídeo**: segue como link único (prévia normal).
  - Links `youtube.com/playlist?list=…` (sem vídeo) vão direto para a escolha da playlist.
- O nome e a lista vêm de `yt-dlp --flat-playlist -J` (rápido: traz título, canal, duração e miniaturas de cada vídeo).
- Limite: **Mix do YouTube** (`list=` começando com `RD`) mostra os **primeiros 50**, com a observação "Mix do YouTube: mostrando os primeiros 50". Playlists normais mostram até **500** vídeos. Acima disso, aparece "mostrando os primeiros 500".
- Janela de escolha: caixinha por vídeo (**todas desmarcadas** ao abrir, exceto o vídeo do link, que vem marcado), **Marcar todos / Desmarcar todos**, a chave **MP4 | MP3** (começa no formato geral), e o botão **Adicionar N à fila** (desativado com N=0).
- Vídeos indisponíveis na playlist ("[Private video]", "[Deleted video]") aparecem desmarcados e sem poder marcar.
- Enquanto a playlist carrega: "Carregando a playlist…" e os botões desativados. Erro: mensagem amigável.
- Destino: igual à Etapa 1, **pasta por canal**. Não há pasta com o nome da playlist.

### Pasta visível
- A linha "📁 Salvando em" mostra `config.base_dir`. **Alterar** abre o seletor de pasta, grava na hora (`config.json`) e atualiza a linha.
- A mudança vale para os itens que **ainda vão começar**. O item em andamento termina na pasta antiga.
- ⚙ → Escolher… e o botão Alterar ficam sincronizados.

### Fechar o programa
- Com fila em andamento: pergunta "Há downloads em andamento. Fechar e cancelar?" (Sim/Não). Sim cancela o item atual com a limpeza da Etapa 1 e fecha.

## Decisões técnicas (escolhas do Claude)

- Reaproveitar `Job` (Etapa 1) para cada item. A fila é um controlador sem interface (`queue_model.py`) com os itens e as regras de "próximo item", testado sem Tk. A janela só desenha.
- Lista da fila e da playlist com `CTkScrollableFrame`. Miniaturas pequenas (56×32) baixadas em segundo plano.
- Extração de links de um texto colado: regex sobre o texto inteiro + `extract_video_id`, sem repetir links e mantendo a ordem.
- Detecção de playlist: o parâmetro `list` do link, ou o caminho `/playlist`. A função pura `extract_playlist_id(text) -> str | None` fica em `urls.py`.

## Testes

- Automatizados (sem rede, sem Tk):
  - extração de vários links de um texto (ordem, repetidos, inválidos, links com playlist);
  - `extract_playlist_id` (watch com list, `/playlist`, Mix `RD…`, sem list);
  - leitura do JSON de `--flat-playlist` (fixture real reduzida, itens privados/removidos, limite de 50 no Mix);
  - regras da fila: só itens Na fila são baixados, e itens Em revisão nunca, nem quando a fila já está rodando; Baixar selecionados libera só os marcados; erro não para a fila; Cancelar tudo não mexe nos itens Em revisão; Limpar finalizados; remover o item em andamento; duplicado = mesmo vídeo + mesmo formato; formato travado depois que o download começa.
- Manual com vídeos reais: colar 3 links e desmarcar 1; o Mix do print do usuário (`watch?v=N2boHnDVzqY&list=RDDB_DNxGnDzs`) escolhendo 3 vídeos em MP3; uma playlist normal; um vídeo removido no meio da fila; fechar com a fila rodando; trocar a pasta com a fila rodando.

## Fica a critério de quem construir
- Estrutura interna dos widgets e como a lista é redesenhada.
- Texto exato dos avisos curtos, desde que em português simples.
- Altura da área da fila e tamanho da janela (pode crescer).

## Adendo: rodar em qualquer computador e instalador

Pedido do usuário: o programa vai ser passado para outras pessoas (esposa, sogro), em computadores possivelmente mais fracos e sem placa NVIDIA. Ele precisa se adaptar ao hardware de cada um, ser leve e ter um instalador. O usuário deixou o "como" com o Claude.

### Adaptação ao hardware (escolha do Claude)
- Ao preparar os componentes, o programa testa os codificadores por hardware nesta ordem: **NVIDIA (h264_nvenc) → Intel Quick Sync (h264_qsv) → AMD (h264_amf)**. O teste é codificar alguns quadros de uma imagem sintética. O primeiro que funcionar é usado. Se nenhum funcionar, a máquina é tratada como "sem aceleração".
- A conversão tenta o codificador detectado e, se ele falhar, cai para o processador (x264), sem erro para o usuário.
- **Com aceleração**, tudo segue como na Etapa 1: "Melhor disponível" vai até 4K.
- **Sem aceleração**:
  - "Melhor disponível" passa a ser a maior resolução que existe em H.264 SDR, ou seja, sem conversão (normalmente 1080p).
  - Nessa resolução, o vídeo H.264 é preferido mesmo com menos quadros por segundo.
  - Resoluções acima disso continuam no seletor, com o rótulo "(lenta neste PC)".
  - Itens da fila e da playlist seguem a mesma regra.
  - Se o vídeo não tiver nenhuma versão H.264, vale a regra normal.
- O download (8 partes paralelas) não depende do hardware.

### Componentes em qualquer máquina
- Runtime JavaScript do yt-dlp: usa o Node.js se existir. Se não existir, o **Deno** é baixado na primeira execução para `%LOCALAPPDATA%\YoutubeForDownload\bin\`, como já acontece com o yt-dlp.
- FFmpeg: trocar a versão "full" (2 × 213 MB) pela **"essentials"** do mesmo autor (Gyan), desde que ela tenha os codificadores por hardware, o libx264 e o zscale/tonemap. Isso é conferido antes de trocar.

### Instalador
- **Inno Setup**, em português, instalação por usuário (sem pedir administrador), em `%LOCALAPPDATA%\Programs\ColouBaixou`.
- Atalho na área de trabalho e no menu Iniciar, com desinstalação pelo Windows.
- Windows 10/11 64 bits.
- Arquivo gerado: `ColouBaixou-Setup-<versão>.exe`.
- O programa não tem assinatura digital: o README explica o aviso "O Windows protegeu o computador" (Mais informações → Executar assim mesmo).
