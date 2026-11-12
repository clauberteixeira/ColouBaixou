# Novidades

## 1.7.1 (12/11/2026)

- **Login com a conta Google mais fácil:** o botão **Instalar o Firefox** instala sozinho (em português, sem pedir administrador) e já abre o login do Google. Quando a conta aparece, a opção liga sozinha, sem precisar clicar em Verificar.

## 1.7.0 (12/11/2026)

- **Conta do YouTube (opcional):** em ⚙ Configurações, ligue *Usar a conta do YouTube aberta no Firefox*. Com login, o bloqueio "não sou um robô" praticamente some. A tela mostra se o Firefox está instalado e se a conta foi encontrada, com botões para baixar o Firefox e para entrar no YouTube. Use uma conta secundária.

## 1.6.3 (12/11/2026)

- **Corrigido:** o fim digitado nos campos era ignorado quando a pessoa clicava em baixar sem apertar Enter, e o trecho ia até o fim da música.
- **Validação antes de baixar:** início depois do fim, letras nos campos ou início depois do fim do vídeo mostram o erro em vermelho e não baixam.
- **Conferência depois de baixar:** o programa mede o arquivo pronto; se passou do fim escolhido, corta o excesso sozinho.

## 1.6.2 (12/11/2026)

- **Campos de hora, minuto e segundo** para o início e o fim do trecho, junto com a linha do tempo. Digitar move as alças; arrastar as alças atualiza os campos.
- **Ritmo contra o bloqueio do YouTube:** as 3 primeiras consultas passam na hora; depois, uma a cada 20 segundos, com contagem na tela (*Aguardando 12 s*).
- **Menos pedidos ao YouTube:** o download reaproveita a consulta feita na prévia, em vez de consultar de novo. Isso diminui a chance do bloqueio "não sou um robô".
- **Aviso de bloqueio mais claro:** quando o YouTube recusa esta internet por um tempo, o aviso diz para esperar algumas horas e não sugere mais atualizar.

## 1.6.1 (12/11/2026)

- **Corrigido:** no MP3, o trecho não parava no fim escolhido. Agora MP3 e MP4 cortam exatamente no início e no fim.
- **Corrigido:** a tela travava ("Não está respondendo") enquanto um trecho baixava.
- **Baixa só o pedaço escolhido**, não o vídeo inteiro: trechos ficam prontos bem mais rápido.
- Ao clicar em baixar, a janela do trecho fecha e o andamento aparece na fila (*Baixando só o trecho…*).

## 1.6.0 (12/11/2026)

- **Escolher trecho com linha do tempo e vídeo**: o botão **✂ Baixar só um trecho…** abre uma janela com o vídeo. Arraste as alças da linha do tempo até o início e o fim, assista com som no ▶ e baixe o trecho em MP4 ou MP3. Substitui os campos de digitar o tempo.

## 1.5.0 (12/11/2026)

- **Baixar só um trecho**: na prévia, escolha de que tempo até que tempo baixar (ex.: de 1:30 até 2:45, ou de 1:30 até o fim). Funciona em MP4 e MP3, com corte no ponto exato. O arquivo leva o trecho no nome.

## 1.4.0 (01/11/2026)

- **Lembra o último formato**: o MP3 ou MP4 usado por último já vem marcado em *Formato para os próximos*, mesmo depois de fechar e abrir.
- **Nada mais fica cortado**: caminho da pasta, título e avisos quebram de linha, e as colunas da fila e da playlist acompanham a largura da janela. Títulos longos usam duas linhas.
- **Corrigido:** na playlist, as colunas Duração e Já baixado ficavam escondidas.
- **Abre exatamente no centro do monitor**, sem ficar atrás da barra de tarefas.

## 1.3.3 (01/11/2026)

- **Botão direito na fila**: selecione um vídeo e escolha **Cancelar** (ou **Cancelar download**) ou **Remover da lista**. A fila continua com os próximos.
- **Corrigido:** o botão **✕** de cada linha ficava cortado na borda da lista.

## 1.3.2 (01/11/2026)

- **A janela da playlist também lembra o tamanho** e abre sempre no centro da tela.

## 1.3.1 (01/11/2026)

- **Corrigido:** em alguns computadores o programa abria com "Não foi possível preparar os componentes" mesmo com a internet funcionando. O motor de download agora vem dentro do instalador (que passa a ter cerca de 87 MB), e as conexões seguras funcionam também em computadores recém-formatados.
- **A janela lembra o tamanho** (e se estava maximizada) ao fechar e abrir de novo.
- Se algo der errado ao abrir, a mensagem diz o motivo e o que fazer.
- **Corrigido:** o aviso de que falta um componente (Deno) sumia assim que aparecia.

## 1.3.0 (30/10/2026)

- **Fila mais rápida**: baixa vários vídeos ao mesmo tempo. Enquanto um converte, os próximos já estão baixando (3 de cada vez com placa NVIDIA, 2 nos demais computadores). No teste, 4 músicas saíram em 33 s, contra cerca de 75 s uma por vez.

## 1.2.0 (29/10/2026)

- **Nomes de arquivo limpos**: sai o que polui o título, como "[Vídeo Oficial]", "(Ao Vivo)", "| DVD …" e hashtags. Participações (feat./part.) continuam. No MP3, o título da música também sai limpo.
- A janela da playlist, as Configurações e a pergunta "Só este vídeo / Ver a playlist" agora abrem **centralizadas na tela**.

## 1.1.0 (29/10/2026)

- **Nunca baixa o mesmo vídeo duas vezes**: o programa lembra o que já foi baixado e reconhece os arquivos que já estão na pasta (por formato: MP3 e MP4 são independentes).
- **Tela da playlist renovada**: miniatura de cada vídeo, caixinhas de seleção bem visíveis, contador de selecionados e aviso "✔ Já baixado".
- Caixinhas de seleção redesenhadas também na fila.

## 1.0.2 (29/10/2026)

- A escolha da pasta fica só na tela principal (botão **📂 Escolher pasta**); as Configurações mostram atualizações e informações do programa.

## 1.0.1 (29/10/2026)

- A janela agora abre **centralizada na tela** (e se ajusta em telas pequenas de notebook).

## 1.0.0 (29/10/2026)

Primeira versão.

- Baixa vídeos do YouTube em **MP4** (até 4K, H.264, abre em qualquer aparelho) e áudio em **MP3** 320 kbps com capa.
- **Fila de downloads**: cole vários links de uma vez, confira e escolha com caixinhas, com MP4 ou MP3 em cada vídeo.
- **Playlists e Mix do YouTube**: escolha quais vídeos baixar.
- **Pasta visível e configurável**, com arquivos organizados por canal.
- **Adapta-se ao computador**: usa a placa de vídeo quando existir e evita conversões demoradas em computadores mais simples.
- **Download acelerado** (em partes paralelas).
- Se o YouTube bloquear temporariamente, a fila **pausa sozinha** e continua quando você mandar.
- O motor de download **se atualiza sozinho**, e o próprio programa avisa e **se atualiza com um clique** quando sai versão nova.
- Rodapé e seção "Sobre" com o desenvolvedor e links de ajuda.
- Instalador leve (~64 MB), sem pedir senha de administrador.
