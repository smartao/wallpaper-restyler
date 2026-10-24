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

## Exportar e importar imagens (`organizar.py`)

Move as imagens geradas entre `saida/` e as pastas `exportar/` e `importar/`.

| Comando | O que faz |
|---|---|
| `python3 organizar.py exportar` | Move as imagens de todas as pastas de tema de `saida/` para `exportar/` (todas juntas na mesma pasta) |
| `python3 organizar.py importar` | Move as imagens de `importar/` para `saida/<tema>/`, de acordo com o sufixo do nome |
| `python3 organizar.py <ação> --simular` | Só mostra o que seria movido, sem mover nada |

- **Como o tema é reconhecido:** pelo final do nome, `<imagem>-<tema>.png` ou `<imagem>-<tema>-02.png`.
  Se dois temas servem (ex.: `akira` e `akira-psycho-pass`), vale o nome mais longo.
  Valem os temas de `temas.txt` e as pastas que já existem em `saida/`.
- **Sem tema reconhecido:** a imagem fica em `importar/` e aparece listada no final.
- **Nada é sobrescrito:** se o arquivo já existe no destino, ele é pulado com um aviso.
- `saida/_erros/` é ignorada na exportação.
- **Atenção:** enquanto as imagens estiverem em `exportar/`, o `wallpapers.py` acha que
  essas combinações estão pendentes e gera tudo de novo. Rode `importar` antes de voltar a usá-lo.

## Se parar de funcionar

O ChatGPT muda o site de tempos em tempos. Os seletores ficam no início de
`wallpapers.py` (`SEL_EDITOR`, `SEL_ENVIAR`, `SEL_UPLOAD`, `SEL_PARAR`) e são o
primeiro lugar a ajustar. O botão de parar é reconhecido pelo texto "Parar"/"Stop",
então mudar o idioma do ChatGPT pode exigir ajuste.
