# Perguntas frequentes

[← Voltar](../README.md)

### O Windows disse "O Windows protegeu o computador". É vírus?

Não. Esse aviso aparece para programas novos que não têm uma assinatura digital paga, que custa caro e precisa ser renovada todo ano. O ColouBaixô é gratuito e não tem essa assinatura. Clique em **Mais informações → Executar assim mesmo**. Os detalhes estão no [guia de instalação](INSTALACAO.md#2-o-windows-protegeu-o-computador).

### Meu antivírus reclamou do programa.

Alguns antivírus desconfiam de programas novos feitos em Python, sem motivo real (é o chamado "falso positivo"). Se o instalador veio da [página oficial de Releases](https://github.com/clauberteixeira/ColouBaixou/releases), você pode liberar o programa no antivírus.

### Apareceu "O YouTube bloqueou temporariamente os downloads".

O YouTube limita quem faz muitos downloads seguidos da mesma internet. A fila **pausa sozinha**. Espere algumas horas e clique em **▶ Continuar fila**. Isso é raro com uso normal.

### Onde ficou o arquivo?

Clique em **✔ Concluído** na fila, ou no botão **📁 Abrir pasta**. A pasta principal aparece no topo da tela, em **📁 Salvando em**. Vídeos ficam em `Vídeos\<Canal>` e áudios em `Áudios\<Canal>`.

### O vídeo em 4K demorou muito.

Muitos vídeos em 4K precisam ser **convertidos** para abrir em qualquer TV ou celular, e isso pesa no computador. Em computadores sem placa de vídeo NVIDIA, o programa já escolhe por padrão uma qualidade que não precisa de conversão. Se quiser mais rapidez, escolha **1080p** no seletor de qualidade.

### Por que não aparece a opção 4K (ou 8K)?

- O vídeo pode simplesmente não ter essa qualidade no YouTube.
- O programa vai **no máximo até 4K**. Vídeos em 8K são baixados em 4K, porque converter 8K leva horas e quase nenhum aparelho reproduz.

### O MP3 tem boa qualidade?

Sim: 320 kbps, a maior qualidade do formato MP3, com a capa do vídeo.

### Deu "Este vídeo é privado", "precisa de login" ou "exclusivo para membros".

O ColouBaixô baixa apenas vídeos **públicos**. Vídeos privados, com restrição de idade ou só para membros do canal não são suportados.

### Dá para baixar uma transmissão ao vivo?

Durante a transmissão, não. Depois que ela termina e fica salva no canal, sim.

### Parou de funcionar de repente.

O YouTube muda o site com frequência. O programa **atualiza o motor de download sozinho** ao abrir. Feche e abra de novo. Se aparecer a faixa *"Nova versão disponível"*, clique em **Atualizar agora**. Se continuar, [abra um relato de problema](https://github.com/clauberteixeira/ColouBaixou/issues/new/choose).

### Preciso de internet?

Sim, para baixar os vídeos e na primeira vez que o programa abre.

### Como desinstalar?

**Configurações do Windows → Aplicativos → Aplicativos instalados → ColouBaixô → Desinstalar.** Seus vídeos não são apagados.

### Como relatar um problema?

[Abra um relato aqui](https://github.com/clauberteixeira/ColouBaixou/issues/new/choose), contando o link do vídeo, a mensagem que apareceu e, se puder, anexe o arquivo de registro (log) `app.log`. Para encontrá-lo, aperte `Win + R`, cole `%LOCALAPPDATA%\YoutubeForDownload\logs` e dê Enter.
