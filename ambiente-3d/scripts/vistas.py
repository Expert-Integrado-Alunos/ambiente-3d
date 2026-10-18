# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Renderiza as vistas da cena (Blender 4.2+).

Uso: blender -b --factory-startup <cena.blend> -P vistas.py -- <pasta_saida> [--so nome1,nome2] [--motor eevee|cycles]
     [--amostras N] [--largura 1080] [--cena cena.json]

- As vistas vem do cena.json (--cena, recomendado: le a versao atual sem remontar) ou, sem ele, das gravadas no .blend
  pelo montar.py. Cada vista: {"cam": [x, y, z], "alvo": [x, y, z], "lente": mm equivalente 35 mm, "foto": "fotos/a.jpg"}.
- Vista com "foto" sai na MESMA proporcao da foto (pra comparar lado a lado); sem foto, "res": [l, a] ou 1080x1350.
- --motor eevee (padrao, segundos por vista) | cycles (luz realista na GPU, com denoise; minutos por vista).
- Grava <pasta_saida>/<nome>.jpg e imprime 1 linha por vista.
- --factory-startup: sem ele o Blender carrega os complementos e preferencias da pessoa, que podem mudar o render.
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pecas as P  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not a:
    raise SystemExit("uso: blender -b --factory-startup cena.blend -P vistas.py -- <pasta_saida> [--so a,b] [--motor eevee|cycles]")
SAIDA = os.path.abspath(a[0])


def opcao(nome, padrao=None):
    return a[a.index(nome) + 1] if nome in a else padrao


MOTOR = opcao("--motor", "eevee")
if MOTOR not in ("eevee", "cycles"):
    raise SystemExit(f"--motor {MOTOR}: use eevee ou cycles")
AMOSTRAS = int(opcao("--amostras", "128" if MOTOR == "cycles" else "48"))
LARGURA = int(opcao("--largura", "1080"))
SO = set(opcao("--so", "").split(",")) - {""}
cena = bpy.context.scene
cam = bpy.data.objects["CAM"]
alvo = bpy.data.objects["ALVO"]
if opcao("--cena"):
    arq = os.path.abspath(opcao("--cena"))
    VISTAS = json.load(open(arq, encoding="utf-8")).get("vistas") or {}
    PASTA = os.path.dirname(arq)
else:
    VISTAS = json.loads(cena.get("vistas", "{}"))
    PASTA = cena.get("pasta", os.getcwd())


def liga_cycles():
    cena.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tipo in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = tipo
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == tipo for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == tipo
            cena.cycles.device = "GPU"
            break
    else:
        cena.cycles.device = "CPU"
    cena.cycles.samples = AMOSTRAS
    cena.cycles.use_adaptive_sampling = True
    cena.cycles.use_denoising = True
    print(f"motor cycles: {cena.cycles.device} {prefs.compute_device_type}, {AMOSTRAS} amostras", flush=True)


def tamanho_foto(rel):
    p = rel if os.path.isabs(rel) else os.path.join(PASTA, rel)
    if not os.path.exists(p):
        print(f"AVISO foto nao achada: {rel}", flush=True)
        return None
    img = bpy.data.images.load(p, check_existing=True)
    w, h = img.size
    return (w, h) if w and h else None


def colada(nome):
    """Avisa quando a camera esta dentro de um objeto ou colada nele: a vista sai tampada (ex.: cupula de luminaria)."""
    dg = bpy.context.evaluated_depsgraph_get()
    o = cam.matrix_world.translation
    frente = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, pt, _n, _i, obj, _m = cena.ray_cast(dg, o, frente)
    if ok and (pt - o).length < 0.35:
        print(f"AVISO vista {nome}: a camera esta a {(pt - o).length:.2f} m de '{obj.name}' bem na frente da lente; "
              f"a imagem vai sair tampada. Afaste a camera ou o objeto.", flush=True)
    for nome_obj in P.dentro(CAIXAS, o):
        print(f"AVISO vista {nome}: a camera esta DENTRO de '{nome_obj}'; confira a posicao.", flush=True)


if MOTOR == "cycles":
    liga_cycles()
else:
    cena.eevee.taa_render_samples = AMOSTRAS
cena.render.image_settings.file_format = "JPEG"
cena.render.image_settings.quality = 92
cena.render.use_motion_blur = False
cam.data.dof.use_dof = False
CAIXAS = P.caixas_de_colisao(cena)
os.makedirs(SAIDA, exist_ok=True)
t0 = time.time()
feitas = 0
for nome, v in VISTAS.items():
    if SO and nome not in SO:
        continue
    cam.location, alvo.location = v["cam"], v["alvo"]
    cam.data.lens = v.get("lente", 24)
    cam.data.sensor_fit = "AUTO"
    cam.data.sensor_width = 36
    rolagem = math.radians(v.get("rolagem", 0.0))       # camera torta na foto (graus, positivo = anti-horario)
    cam.constraints["Track To"].influence = 1.0
    tam = tamanho_foto(v["foto"]) if v.get("foto") else None
    if tam:
        w, h = tam
        cena.render.resolution_x, cena.render.resolution_y = LARGURA, round(LARGURA * h / w)
    else:
        rl, ra = v.get("res", [1080, 1350])
        cena.render.resolution_x, cena.render.resolution_y = LARGURA, round(LARGURA * ra / rl)
    cena.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    if rolagem:
        # o Track To fixa a camera; a rolagem entra girando em volta do eixo de visada depois do constraint
        m = cam.matrix_world.copy()
        cam.constraints["Track To"].influence = 0.0
        cam.matrix_world = m @ Matrix.Rotation(rolagem, 4, "Z")
    colada(nome)
    s = time.time()
    cena.render.filepath = os.path.join(SAIDA, f"{nome}.jpg")
    bpy.ops.render.render(write_still=True)
    feitas += 1
    print(f"VISTA {nome}: {cena.render.resolution_x}x{cena.render.resolution_y} em {time.time() - s:.1f} s "
          f"-> {cena.render.filepath}", flush=True)
print(f"VISTAS OK {feitas} em {time.time() - t0:.0f} s ({MOTOR})", flush=True)
