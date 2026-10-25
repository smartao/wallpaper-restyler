# Automação de temas em wallpapers (ChatGPT)

Envia cada wallpaper de `entrada/` para o ChatGPT no navegador, aplica cada tema de
`temas.txt` e salva o resultado em `saida/<tema>/<imagem>-<tema>.png`.
Não usa API: controla o Chromium com a sua conta logada.

## Primeira vez

```bash
cd /home/sergei/Midias/Dev/Claude/pes-20261021-wallpapers-automatizcao

# faça login no ChatGPT na janela que abrir e depois aperte Enter no terminal
.venv/bin/python wallpapers.py --login
```

O login fica salvo em `perfil_chatgpt/`. Só repita se o ChatGPT deslogar.

Se a pasta `.venv/` não existir (ex.: projeto copiado para outra máquina):

```bash
uv venv .venv && uv pip install --python .venv/bin/python playwright pillow
```

## Uso do dia a dia

| Comando | O que faz |
|---|---|
| `.venv/bin/python wallpapers.py` | Processa todas as combinações pendentes (imagens × temas) |
| `.venv/bin/python wallpapers.py --listar` | Só mostra o que falta processar, sem abrir o navegador |
| `.venv/bin/python wallpapers.py --limite 5` | Processa no máximo 5 combinações |
| `.venv/bin/python wallpapers.py --temas neo-noir,evangelion` | Processa só esses temas |
| `.venv/bin/python wallpapers.py --manter-chats` | Não apaga as conversas do ChatGPT depois de salvar |
| `.venv/bin/python wallpapers.py --login` | Abre o navegador para (re)fazer login |
| `.venv/bin/python wallpapers.py --help` | Mostra todas as opções |

As opções podem ser combinadas, ex.: `--temas formula1 --limite 3`.

## Como funciona

- **Adicionar wallpapers:** coloque os arquivos (`.png`, `.jpg`, `.jpeg`, `.webp`) em `entrada/`.
- **Adicionar/editar temas:** edite `temas.txt`, uma linha por tema no formato `nome | prompt`.
  A linha `sufixo | ...` é anexada ao final de todos os prompts.
- **Retomar:** o que já existe em `saida/` é pulado. Pode interromper com `Ctrl+C`
  e rodar de novo que continua de onde parou. Para refazer uma imagem, apague o arquivo dela.
- **Conversas:** cada conversa é apagada do histórico do ChatGPT após salvar a imagem.
- **Erros:** um print da tela vai para `saida/_erros/`. Após 3 falhas seguidas o script para.
- **Durante a execução:** pode usar o computador normalmente; só não clique nem feche
  a janela do Chromium aberta pelo script. Se o PC suspender, a execução para.

## Edição em lote (`organizar.py`)

Leva as imagens geradas para um programa externo e traz de volta já separadas por tema:

```
saida/<tema>/   --exportar (cópia)-->  exportar/            (lote para o programa externo)
importar/       --importar (move)--->  finalizadas/<tema>/
```

| Comando | O que faz |
|---|---|
| `python3 organizar.py exportar` | Copia para `exportar/` (todas juntas) as imagens de `saida/` que ainda não foram exportadas |
| `python3 organizar.py exportar --todas` | Ignora `exportadas.txt` e exporta tudo de novo, inclusive o que já foi exportado |
| `python3 organizar.py exportar --simular` | Só mostra o que seria exportado, sem copiar nada |
| `python3 organizar.py exportar --todas --simular` | Só mostra o que seria exportado com `--todas` |
| `python3 organizar.py importar` | Move as imagens de `importar/` para `finalizadas/<tema>/`, de acordo com o sufixo do nome |
| `python3 organizar.py importar --simular` | Só mostra o que seria movido, sem mover nada |
| `python3 organizar.py --help` | Mostra todas as opções |

Opções:

- `--simular`: vale para `exportar` e `importar`; não altera nenhum arquivo.
- `--todas`: só tem efeito em `exportar`.

> **Apareceu "0 imagem(ns) copiada(s)" com imagens em `saida/`?** Elas já foram exportadas antes e
> estão registradas em `exportadas.txt`. Use `--todas` para exportar de novo, ou apague
> `exportadas.txt` (ou só as linhas das imagens desejadas).

Fluxo de um lote:

1. `python3 organizar.py exportar` e copie o conteúdo de `exportar/` para o programa externo.
2. Esvazie `exportar/` para o próximo lote.
3. Coloque as imagens editadas em `importar/` e rode `python3 organizar.py importar`.

- **Pode rodar com o `wallpapers.py` em execução:** `saida/` nunca é alterada; o próximo
  `exportar` pega só as imagens geradas depois do anterior. O registro fica em `exportadas.txt`
  (apague uma linha para exportar aquela imagem de novo).
- **Como o tema é reconhecido:** pelo final do nome: `<imagem>-<tema>.png`, `<imagem>-<tema>-02.png`
  ou `<imagem>-<tema>02.png`. Se dois temas servem (ex.: `akira` e `akira-psycho-pass`), vale o nome
  mais longo. Valem os temas de `temas.txt` (inclusive os comentados) e as pastas de `saida/` e `finalizadas/`.
- **Sem tema reconhecido:** a imagem fica em `importar/` e aparece listada no final.
- **Substituição:** na importação, um arquivo com o mesmo nome em `finalizadas/` é substituído.
  Na exportação, um arquivo que já está em `exportar/` é pulado (e não é registrado).
- `saida/_erros/` é ignorada na exportação.

## Se parar de funcionar

O ChatGPT muda o site de tempos em tempos. Os seletores ficam no início de
`wallpapers.py` (`SEL_EDITOR`, `SEL_ENVIAR`, `SEL_UPLOAD`, `SEL_PARAR`) e são o
primeiro lugar a ajustar. O botão de parar é reconhecido pelo texto "Parar"/"Stop",
então mudar o idioma do ChatGPT pode exigir ajuste.
