# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Acha o Blender instalado nesta maquina (sem instalar nada).

Uso: python blender_local.py
Imprime o caminho e a versao (rc 0) ou, se nao achar ou a versao for velha, o motivo e o caminho da instrucao de
instalacao (rc 1). A skill precisa do Blender 4.2 ou mais novo. Instalar e decisao de quem usa: ver
references/instalar-blender.md (so com o OK da pessoa).
"""
import glob
import os
import platform
import re
import shutil
import subprocess
import sys

MINIMO = (4, 2)


def candidatos():
    env = os.environ.get("BLENDER")
    if env:
        yield env
    achado = shutil.which("blender")
    if achado:
        yield achado
    so = platform.system()
    if so == "Windows":
        for base in (os.environ.get("ProgramFiles", "C:/Program Files"), os.environ.get("LOCALAPPDATA", "")):
            yield from sorted(glob.glob(os.path.join(base, "Blender Foundation", "Blender*", "blender.exe")),
                              reverse=True)
        yield from sorted(glob.glob("C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"))
    elif so == "Darwin":
        yield "/Applications/Blender.app/Contents/MacOS/Blender"
        yield os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender")
    else:
        yield from ("/snap/bin/blender", "/usr/bin/blender", "/var/lib/flatpak/exports/bin/org.blender.Blender")
        yield from sorted(glob.glob(os.path.expanduser("~/blender*/blender")), reverse=True)


def versao(exe):
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"Blender (\d+)\.(\d+)(?:\.(\d+))?", out)
    return tuple(int(x or 0) for x in m.groups()) if m else None


def main():
    vistos = set()
    velho = None
    for exe in candidatos():
        if not exe or exe in vistos or not os.path.exists(exe):
            continue
        vistos.add(exe)
        v = versao(exe)
        if not v:
            continue
        if v[:2] >= MINIMO:
            print(f"BLENDER {exe}")
            print(f"VERSAO {'.'.join(map(str, v))}")
            return 0
        velho = (exe, v)
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "instalar-blender.md")
    if velho:
        print(f"Blender {'.'.join(map(str, velho[1]))} em {velho[0]} e velho: a skill precisa do "
              f"{MINIMO[0]}.{MINIMO[1]} ou mais novo.")
    else:
        print("Blender nao encontrado (procurei no PATH, na variavel BLENDER e nas pastas padrao).")
    print(f"Como instalar (so com o OK de quem usa): {ref}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
