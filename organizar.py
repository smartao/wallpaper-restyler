#!/usr/bin/env python3
"""Leva as imagens de saida/ para edição em lote e traz de volta para finalizadas/.

Fluxo:
    saida/<tema>/*  --exportar (cópia)-->  exportar/        (lote para o programa externo)
    importar/*      --importar (move)--->  finalizadas/<tema>/

Uso:
    python3 organizar.py exportar      # copia para exportar/ só o que ainda não foi exportado
    python3 organizar.py exportar --todas     # exporta tudo de novo
    python3 organizar.py importar      # importar/* -> finalizadas/<tema>/
    python3 organizar.py importar --simular   # só mostra o que faria

saida/ nunca é alterada, então dá para exportar enquanto o wallpapers.py roda.
As imagens já exportadas ficam registradas em exportadas.txt.

O tema de cada imagem é lido do sufixo do nome: <imagem>-<tema>.png,
<imagem>-<tema>-02.png ou <imagem>-<tema>02.png. Quando dois temas servem
(ex.: akira e akira-psycho-pass), vale o mais longo.
Na importação, um arquivo com o mesmo nome em finalizadas/ é substituído.
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
FINALIZADAS = BASE / "finalizadas"
TEMAS = BASE / "temas.txt"
REGISTRO = BASE / "exportadas.txt"
EXTENSOES = {".png", ".jpg", ".jpeg", ".webp"}
PASTAS_IGNORADAS = {"_erros"}


def nomes_dos_temas():
    """Temas de temas.txt (inclusive os comentados) mais as pastas de saida/ e finalizadas/."""
    nomes = set()
    if TEMAS.exists():
        for linha in TEMAS.read_text(encoding="utf-8").splitlines():
            linha = linha.strip().lstrip("#").strip()
            if "|" in linha:
                nome = linha.split("|", 1)[0].strip()
                if nome != "sufixo" and re.fullmatch(r"[\w-]+", nome):
                    nomes.add(nome)
    for pasta in (SAIDA, FINALIZADAS):
        if pasta.exists():
            nomes.update(p.name for p in pasta.iterdir() if p.is_dir())
    return nomes - PASTAS_IGNORADAS


def tema_da_imagem(arquivo, temas):
    # aceita versão no final: -02, _02, 02...
    candidatos = [t for t in temas if re.search(rf"-{re.escape(t)}(?:[-_ ]?\d+)?$", arquivo.stem)]
    return max(candidatos, key=len) if candidatos else None


def imagens(pasta):
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


def mover(origem, destino, simular, substituir=False):
    existe = destino.exists()
    if existe and not substituir:
        print(f"  PULADO (já existe): {destino.relative_to(BASE)}")
        return False
    aviso = "  (SUBSTITUÍDO)" if existe else ""
    print(f"  {origem.relative_to(BASE)}  ->  {destino.relative_to(BASE)}{aviso}")
    if not simular:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if existe:
            destino.unlink()
        shutil.move(origem, destino)
    return True


def ler_registro():
    if not REGISTRO.exists():
        return set()
    return set(REGISTRO.read_text(encoding="utf-8").splitlines())


def exportar(simular, todas):
    registro = set() if todas else ler_registro()
    copiadas = []
    for pasta in sorted(p for p in SAIDA.iterdir() if p.is_dir() and p.name not in PASTAS_IGNORADAS):
        for img in imagens(pasta):
            chave = f"{pasta.name}/{img.name}"
            if chave in registro:
                continue
            destino = EXPORTAR / img.name
            if destino.exists():
                print(f"  PULADO (já existe): {destino.relative_to(BASE)}")
                continue
            print(f"  {img.relative_to(BASE)}  ->  {destino.relative_to(BASE)}")
            if not simular:
                shutil.copy2(img, destino)
            copiadas.append(chave)
    if copiadas and not simular:
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.writelines(f"{chave}\n" for chave in copiadas)
    print(f"{len(copiadas)} imagem(ns) {'seriam copiadas' if simular else 'copiada(s)'} para exportar/")


def importar(simular):
    temas = nomes_dos_temas()
    movidas, sem_tema = 0, []
    for img in imagens(IMPORTAR):
        tema = tema_da_imagem(img, temas)
        if tema is None:
            sem_tema.append(img.name)
            continue
        movidas += mover(img, FINALIZADAS / tema / img.name, simular, substituir=True)
    print(f"{movidas} imagem(ns) {'seriam movidas' if simular else 'movida(s)'} para finalizadas/")
    if sem_tema:
        print(f"{len(sem_tema)} imagem(ns) sem tema reconhecido (ficaram em importar/):")
        for nome in sem_tema:
            print(f"  {nome}")


def main():
    parser = argparse.ArgumentParser(description="Copia imagens de saida/ para exportar/ e move de importar/ para finalizadas/.")
    parser.add_argument("acao", choices=["exportar", "importar"])
    parser.add_argument("--simular", action="store_true", help="só mostra o que seria feito")
    parser.add_argument("--todas", action="store_true", help="exportar: ignora exportadas.txt e exporta tudo")
    args = parser.parse_args()

    for pasta in (SAIDA, EXPORTAR, IMPORTAR, FINALIZADAS):
        pasta.mkdir(exist_ok=True)
    if args.acao == "exportar":
        exportar(args.simular, args.todas)
    else:
        importar(args.simular)


if __name__ == "__main__":
    sys.exit(main())
