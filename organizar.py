#!/usr/bin/env python3
"""Move as imagens entre saida/ e as pastas exportar/ e importar/.

Uso:
    python3 organizar.py exportar      # saida/<tema>/*  ->  exportar/
    python3 organizar.py importar      # importar/*      ->  saida/<tema>/
    python3 organizar.py importar --simular   # só mostra o que faria

O tema de cada imagem é lido do sufixo do nome: <imagem>-<tema>.png ou
<imagem>-<tema>-02.png. Quando dois temas servem (ex.: akira e
akira-psycho-pass), vale o mais longo.
Arquivos que já existem no destino nunca são sobrescritos.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
SAIDA = BASE / "saida"
EXPORTAR = BASE / "exportar"
IMPORTAR = BASE / "importar"
TEMAS = BASE / "temas.txt"
EXTENSOES = {".png", ".jpg", ".jpeg", ".webp"}
PASTAS_IGNORADAS = {"_erros"}


def nomes_dos_temas():
    """Temas de temas.txt mais as pastas que já existem em saida/."""
    nomes = set()
    if TEMAS.exists():
        for linha in TEMAS.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "|" in linha:
                nome = linha.split("|", 1)[0].strip()
                if nome != "sufixo":
                    nomes.add(nome)
    if SAIDA.exists():
        nomes.update(p.name for p in SAIDA.iterdir() if p.is_dir())
    return nomes - PASTAS_IGNORADAS


def tema_da_imagem(arquivo, temas):
    stem = re.sub(r"-\d+$", "", arquivo.stem)  # tira a versão: -02, -03...
    candidatos = [t for t in temas if stem.endswith(f"-{t}")]
    return max(candidatos, key=len) if candidatos else None


def imagens(pasta):
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


def mover(origem, destino, simular):
    if destino.exists():
        print(f"  PULADO (já existe): {destino.relative_to(BASE)}")
        return False
    print(f"  {origem.relative_to(BASE)}  ->  {destino.relative_to(BASE)}")
    if not simular:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(origem, destino)
    return True


def exportar(simular):
    movidas = 0
    for pasta in sorted(p for p in SAIDA.iterdir() if p.is_dir() and p.name not in PASTAS_IGNORADAS):
        for img in imagens(pasta):
            movidas += mover(img, EXPORTAR / img.name, simular)
    print(f"{movidas} imagem(ns) {'seriam movidas' if simular else 'movida(s)'} para exportar/")


def importar(simular):
    temas = nomes_dos_temas()
    movidas, sem_tema = 0, []
    for img in imagens(IMPORTAR):
        tema = tema_da_imagem(img, temas)
        if tema is None:
            sem_tema.append(img.name)
            continue
        movidas += mover(img, SAIDA / tema / img.name, simular)
    print(f"{movidas} imagem(ns) {'seriam movidas' if simular else 'movida(s)'} para saida/")
    if sem_tema:
        print(f"{len(sem_tema)} imagem(ns) sem tema reconhecido (ficaram em importar/):")
        for nome in sem_tema:
            print(f"  {nome}")


def main():
    parser = argparse.ArgumentParser(description="Move imagens entre saida/, exportar/ e importar/.")
    parser.add_argument("acao", choices=["exportar", "importar"])
    parser.add_argument("--simular", action="store_true", help="só mostra o que seria movido")
    args = parser.parse_args()

    for pasta in (SAIDA, EXPORTAR, IMPORTAR):
        pasta.mkdir(exist_ok=True)
    if args.acao == "exportar":
        exportar(args.simular)
    else:
        importar(args.simular)


if __name__ == "__main__":
    sys.exit(main())
