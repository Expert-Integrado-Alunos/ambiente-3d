# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Bateria do 'comparar.py confere': cada sabotagem tem que sair rc 1 com a FALHA certa; os pares bons, rc 0.

Uso: python testes/teste_confere.py   (Python 3, sem Blender). Sai 1 se algum caso falhar.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(RAIZ, "ambiente-3d", "scripts", "comparar.py")
EX = os.path.join(RAIZ, "ambiente-3d", "assets", "exemplo-cena.json")
BASE = tempfile.mkdtemp(prefix="confere-")


def prepara(nome):
    d = os.path.join(BASE, nome)
    os.makedirs(os.path.join(d, "fotos"), exist_ok=True)
    os.makedirs(os.path.join(d, "comp"), exist_ok=True)
    c = json.load(open(EX, encoding="utf-8"))
    c["vistas"]["porta"]["foto"] = "fotos/porta.jpg"          # 1 vista com foto
    open(os.path.join(d, "fotos", "porta.jpg"), "wb").write(b"x")
    json.dump(c, open(os.path.join(d, "cena.json"), "w", encoding="utf-8"))
    r = roda(d, "--aprovar")
    assert r[0] == 0, r
    return d, c


def roda(d, *extra):
    p = subprocess.run([sys.executable, S, "confere", os.path.join(d, "cena.json"), *extra],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def grava(d, c):
    json.dump(c, open(os.path.join(d, "cena.json"), "w", encoding="utf-8"))


casos = []


def caso(nome, esperado_rc, trecho, fn, *extra):
    d, c = prepara(nome)
    fn(d, c)
    rc, out = roda(d, *extra)
    ok = rc == esperado_rc and trecho in out
    casos.append((ok, nome, rc, out.strip().splitlines()[-2:] if not ok else trecho))


caso("objeto_sumiu", 1, "objeto planta estava na versao aprovada e sumiu",
     lambda d, c: grava(d, {**c, "objetos": [o for o in c["objetos"] if o["id"] != "planta"]}))
caso("objeto_sumiu_aprovado", 0, "(aceito: a pessoa aprovou esta versao)",
     lambda d, c: grava(d, {**c, "objetos": [o for o in c["objetos"] if o["id"] != "planta"]}), "--aprovar")
caso("abertura_sumiu", 1, "abertura porta estava na versao aprovada e sumiu",
     lambda d, c: grava(d, {**c, "aberturas": [a for a in c["aberturas"] if a["id"] != "porta"]}))
caso("vista_sumiu", 1, "vista canto estava na versao aprovada e sumiu",
     lambda d, c: grava(d, {**c, "vistas": {k: v for k, v in c["vistas"].items() if k != "canto"}}))


def perde_foto(d, c):
    c["vistas"]["porta"].pop("foto")
    grava(d, c)


caso("vista_perdeu_foto", 1, "vista porta perdeu a foto de referencia", perde_foto)


def id_repetido(d, c):
    c["objetos"].append({**c["objetos"][0]})
    grava(d, c)


caso("id_repetido", 1, "objeto com id repetido: mesa", id_repetido)
caso("id_repetido_nem_aprovar", 1, "objeto com id repetido: mesa", id_repetido, "--aprovar")
caso("foto_nao_existe", 1, "a foto fotos/porta.jpg nao existe",
     lambda d, c: os.remove(os.path.join(d, "fotos", "porta.jpg")))


def mexe_mesa(d, c):
    c["objetos"][0]["pos"] = [1.0, 3.0, 0]
    grava(d, c)


caso("mudou_e_aviso", 0, "objeto mesa mudou desde a aprovada: pos", mexe_mesa)
caso("sem_comparativo", 1, "vista porta: tem foto e nao tem comparativo", lambda d, c: None, "--comparativos",
     os.path.join(BASE, "sem_comparativo", "comp"))


def comparativo_velho(d, c):
    pc = os.path.join(d, "comp", "porta.jpg")
    open(pc, "wb").write(b"x")
    velho = time.time() - 3600
    os.utime(pc, (velho, velho))


caso("comparativo_velho", 1, "o comparativo e mais velho que o cena.json", comparativo_velho, "--comparativos",
     os.path.join(BASE, "comparativo_velho", "comp"))


def comparativo_novo(d, c):
    pc = os.path.join(d, "comp", "porta.jpg")
    open(pc, "wb").write(b"x")
    novo = time.time() + 5
    os.utime(pc, (novo, novo))


caso("comparativo_novo_ok", 0, "CONFERE OK", comparativo_novo, "--comparativos",
     os.path.join(BASE, "comparativo_novo_ok", "comp"))

for ok, nome, rc, det in casos:
    print(f"{'OK ' if ok else 'ERRO'} {nome} rc={rc} {det}")
print(f"{sum(c[0] for c in casos)}/{len(casos)}")
if all(c[0] for c in casos):
    shutil.rmtree(BASE, ignore_errors=True)
else:
    raise SystemExit(f"falhou; arquivos em {BASE}")
