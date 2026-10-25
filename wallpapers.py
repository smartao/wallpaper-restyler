#!/usr/bin/env python3
"""Aplica vários temas a wallpapers usando o ChatGPT no navegador (sem API).

Uso:
    .venv/bin/python wallpapers.py --login     # 1ª vez: faça login no ChatGPT
    .venv/bin/python wallpapers.py             # processa entrada/ x temas.txt
    .venv/bin/python wallpapers.py --listar    # mostra o que falta fazer
    .venv/bin/python wallpapers.py --temas ghibli,cyberpunk --limite 5

Resultado: saida/<tema>/<nome-da-imagem>-<tema>.png
Depois de salvar cada imagem, a conversa é apagada do ChatGPT
(use --manter-chats para manter).
Combinações que já têm arquivo em saida/ são puladas, então dá para
interromper (Ctrl+C) e rodar de novo que ele continua de onde parou.
"""
import argparse
import base64
import random
import re
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "entrada"
SAIDA = BASE / "saida"
ERROS = SAIDA / "_erros"
PERFIL = BASE / "perfil_chatgpt"
TEMAS = BASE / "temas.txt"
CHROMIUM = "/usr/lib/chromium/chromium"
URL = "https://chatgpt.com/"
EXTENSOES = {".png", ".jpg", ".jpeg", ".webp"}

TEMPO_MAX_GERACAO = 6 * 60   # segundos esperando uma imagem ficar pronta
TEMPO_ESTAVEL = 8            # imagem sem mudar por N s = geração terminou
TEMPO_SEM_IMAGEM = 30        # parou de responder sem imagem por N s = falhou
PAUSA_ENTRE = (15, 45)       # pausa aleatória entre gerações (ritmo humano)
MAX_FALHAS_SEGUIDAS = 3

# Seletores da página do ChatGPT (mudam de tempos em tempos; ajuste aqui).
SEL_EDITOR = '.ProseMirror[contenteditable="true"]'
SEL_ENVIAR = 'form button[type="submit"]'
SEL_UPLOAD = 'input[type="file"][accept="image/*"]'
SEL_PARAR = 'form button[aria-label="Parar"], form button[aria-label="Stop"], form button[aria-label*="streaming" i]'

# Última imagem gerada pelo ChatGPT (alt "Imagem 1 gerada" / "Generated image").
JS_IMAGEM_GERADA = r"""
() => {
  const imgs = [...document.querySelectorAll('main img')].filter(i =>
    /gerad|generat/i.test(i.alt || '') && i.complete && i.naturalWidth >= 512);
  return imgs.length ? imgs[imgs.length - 1].src : null;
}
"""
# A imagem vem como blob:, que só pode ser lido de dentro da página.
JS_BAIXAR = r"""
async (src) => {
  const blob = await (await fetch(src)).blob();
  return await new Promise((ok, erro) => {
    const r = new FileReader();
    r.onload = () => ok(r.result.split(',')[1]);
    r.onerror = erro;
    r.readAsDataURL(blob);
  });
}
"""


# Mesma chamada que o "Excluir" do menu do chat faz (oculta a conversa do histórico).
JS_APAGAR_CONVERSA = r"""
async (id) => {
  const sessao = await (await fetch('/api/auth/session')).json();
  const r = await fetch('/backend-api/conversation/' + id, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + sessao.accessToken},
    body: JSON.stringify({is_visible: false}),
  });
  return r.status;
}
"""


class SessaoExpirada(Exception):
    pass


class FalhaGeracao(Exception):
    pass


def log(msg, erro=False):
    linha = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(vermelho(linha) if erro else linha, flush=True)


def vermelho(msg):
    return f"\033[31m{msg}\033[0m" if sys.stdout.isatty() else msg


def formatar_duracao(segundos):
    minutos = max(1, round(segundos / 60))
    return f"{minutos // 60}h {minutos % 60:02d} min" if minutos >= 60 else f"{minutos} min"


def carregar_temas():
    temas, sufixo = {}, ""
    for n, linha in enumerate(TEMAS.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "|" not in linha:
            sys.exit(f"temas.txt linha {n}: falta o '|' entre nome e prompt")
        nome, prompt = (p.strip() for p in linha.split("|", 1))
        if nome == "sufixo":
            sufixo = prompt
        elif not re.fullmatch(r"[\w-]+", nome):
            sys.exit(f"temas.txt linha {n}: nome '{nome}' inválido (use letras, números, - ou _)")
        else:
            temas[nome] = prompt
    return {nome: f"{prompt} {sufixo}".strip() for nome, prompt in temas.items()}


def listar_imagens():
    return sorted(p for p in ENTRADA.iterdir() if p.suffix.lower() in EXTENSOES)


def tarefas_pendentes(imagens, temas, limite):
    # Temas em ordem alfabética; todas as imagens passam por um tema antes de ir para o próximo.
    pendentes = [
        (img, nome, prompt)
        for nome, prompt in sorted(temas.items())
        for img in imagens
        if not (SAIDA / nome / f"{img.stem}-{nome}.png").exists()
    ]
    return pendentes[:limite] if limite else pendentes


def abrir_navegador(p):
    return p.chromium.launch_persistent_context(
        str(PERFIL),
        executable_path=CHROMIUM,
        headless=False,
        viewport=None,
        ignore_default_args=["--enable-automation"],
        args=[
            "--disable-blink-features=AutomationControlled",
            # evita que o Chromium "congele" a janela quando minimizada/escondida
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--window-size=1280,900",
        ],
    )


def aguardar_imagem(page):
    inicio = time.time()
    ultimo_src, desde = None, time.time()
    parado_desde = None
    while time.time() - inicio < TEMPO_MAX_GERACAO:
        src = page.evaluate(JS_IMAGEM_GERADA)
        gerando = page.locator(SEL_PARAR).count() > 0

        if not src or gerando or src != ultimo_src:
            ultimo_src, desde = src, time.time()
        elif time.time() - desde >= TEMPO_ESTAVEL:
            return src

        # Parou de responder e nenhuma imagem apareceu (recusa, limite, pergunta...)
        if not src and not gerando:
            parado_desde = parado_desde or time.time()
            if time.time() - parado_desde >= TEMPO_SEM_IMAGEM:
                raise FalhaGeracao("ChatGPT terminou de responder sem gerar imagem (veja o print)")
        else:
            parado_desde = None
        time.sleep(2)
    raise FalhaGeracao(f"tempo esgotado ({TEMPO_MAX_GERACAO}s) esperando a imagem")


def apagar_conversa(page):
    m = re.search(r"/c/([0-9a-f-]{36})", page.url)
    if not m:
        log("   aviso: não achei o id da conversa para apagar")
        return
    try:
        status = page.evaluate(JS_APAGAR_CONVERSA, m.group(1))
    except Exception as e:
        status = e
    if status != 200:
        log(f"   aviso: não consegui apagar a conversa ({status})")


def processar(page, imagem, prompt, destino, apagar):
    page.goto(URL, wait_until="domcontentloaded")
    caixa = page.locator(SEL_EDITOR)
    try:
        caixa.wait_for(timeout=60_000)
    except Exception:
        raise SessaoExpirada("caixa de texto do ChatGPT não apareceu (deslogado ou página mudou)")
    if page.locator('[data-testid="login-button"]').count():
        raise SessaoExpirada("não está logado; rode com --login")

    page.locator(SEL_UPLOAD).first.set_input_files(str(imagem))
    caixa.click()
    page.keyboard.insert_text(prompt)
    time.sleep(3)  # dá tempo do upload terminar
    page.locator(f"{SEL_ENVIAR}:not([disabled])").click(timeout=120_000)

    src = aguardar_imagem(page)
    dados = base64.b64decode(page.evaluate(JS_BAIXAR, src))

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    Image.open(BytesIO(dados)).save(temporario, "PNG")
    temporario.replace(destino)

    if apagar:
        apagar_conversa(page)


def modo_login():
    with sync_playwright() as p:
        ctx = abrir_navegador(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL)
        input("Faça login no ChatGPT na janela aberta e depois pressione Enter aqui... ")
        ctx.close()
    log("Sessão salva em perfil_chatgpt/. Agora rode sem --login.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--login", action="store_true", help="abre o navegador para fazer login")
    ap.add_argument("--listar", action="store_true", help="só lista o que falta processar")
    ap.add_argument("--temas", help="processa só estes temas (separados por vírgula)")
    ap.add_argument("--limite", type=int, help="processa no máximo N combinações")
    ap.add_argument("--manter-chats", action="store_true",
                    help="não apaga as conversas do ChatGPT depois de salvar a imagem")
    args = ap.parse_args()

    if args.login:
        return modo_login()

    ENTRADA.mkdir(exist_ok=True)
    temas = carregar_temas()
    filtro = set(args.temas.split(",")) if args.temas else None
    if filtro and (desconhecidos := filtro - temas.keys()):
        sys.exit(f"Temas não encontrados em temas.txt: {', '.join(sorted(desconhecidos))}")
    if filtro:
        temas = {nome: prompt for nome, prompt in temas.items() if nome in filtro}

    imagens = listar_imagens()
    log(f"{len(imagens)} imagem(ns) para processar | {len(temas)} tema(s) ativado(s)")
    pendentes = tarefas_pendentes(imagens, temas, args.limite)
    log(f"{len(pendentes)} combinação(ões) pendente(s)")
    if args.listar:
        for img, nome, _ in pendentes:
            print(f"  {img.name}  ->  {nome}")
        return
    if not pendentes:
        return

    feitos, falhas_seguidas = 0, 0
    inicio_lote = time.time()
    with sync_playwright() as p:
        ctx = abrir_navegador(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for i, (img, nome, prompt) in enumerate(pendentes, 1):
                destino = SAIDA / nome / f"{img.stem}-{nome}.png"
                log(f"({i}/{len(pendentes)}) {img.name} -> {nome}")
                try:
                    processar(page, img, prompt, destino, not args.manter_chats)
                    feitos += 1
                    falhas_seguidas = 0
                    log(f"   Status: ok {destino.relative_to(BASE)}")
                except SessaoExpirada as e:
                    log(f"   PARANDO: {e}")
                    break
                except Exception as e:
                    falhas_seguidas += 1
                    ERROS.mkdir(parents=True, exist_ok=True)
                    shot = ERROS / f"{img.stem}__{nome}__{datetime.now():%H%M%S}.png"
                    try:
                        page.screenshot(path=str(shot), full_page=True)
                    except Exception:
                        shot = None
                    log(f"   FALHOU: {e}" + (f" (print: {shot.relative_to(BASE)})" if shot else ""), erro=True)
                    if falhas_seguidas >= MAX_FALHAS_SEGUIDAS:
                        log(f"   PARANDO: {MAX_FALHAS_SEGUIDAS} falhas seguidas (limite atingido ou site mudou?)")
                        break
                if i < len(pendentes):
                    media = (time.time() - inicio_lote) / i
                    log(f"   Tempo Estimado: {formatar_duracao(media * (len(pendentes) - i))}")
                log(f"   Progresso: {i * 100 // len(pendentes)}%")
                if i < len(pendentes):
                    time.sleep(random.uniform(*PAUSA_ENTRE))
        except KeyboardInterrupt:
            log("Interrompido pelo usuário.")
        finally:
            ctx.close()
    log(f"Concluído: {feitos} imagem(ns) gerada(s).")


if __name__ == "__main__":
    main()
