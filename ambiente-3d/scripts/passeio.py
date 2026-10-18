# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Video-passeio: a camera vai de vista em vista e sai um MP4 com o rodape de procedencia (Blender 4.2+).

Uso: blender -b --factory-startup <cena.blend> -P passeio.py -- <saida.mp4> --cena cena.json --rodape faixa.png
     [--ordem a,b,c] [--parada 1.0] [--trecho 3.0] [--fps 30] [--res 1080x1920] [--motor eevee|cycles] [--amostras N]
     [--manter-quadros] [--sem-rodape] [--so-conferir]

- A faixa do rodape sai do comparar.py (`comparar.py faixa --largura <L> --saida faixa.png`, L = largura do video):
  e a mesma assinatura das imagens. Sem --rodape o script recusa; --sem-rodape so quando a pessoa pedir.
- --ordem: vistas na ordem do passeio (padrao: a ordem do cena.json). Cada vista fica --parada s parada e a camera leva
  --trecho s ate a proxima, acelerando e freando suave. A "rolagem" das vistas nao entra no video.
- --res e o tamanho FINAL do video (padrao 1080x1920, celular em pe); o 3D ocupa a parte de cima e a faixa, a de baixo.
- Renderiza os quadros em PNG (<saida>_quadros/), junta com a faixa no editor de video do proprio Blender e grava o
  MP4 (H.264), sem ffmpeg externo. Os quadros sao apagados no fim, salvo --manter-quadros.
- Antes de renderizar, confere o caminho: AVISO quando a camera atravessa um movel entre duas vistas (ponha uma vista
  intermediaria sem foto, ou mude a ordem). --so-conferir para ai, sem renderizar (segundos): rode antes do Cycles.
"""
import json
import os
import shutil
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pecas as P  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not a or a[0].startswith("--"):
    raise SystemExit("uso: blender -b --factory-startup cena.blend -P passeio.py -- <saida.mp4> --cena cena.json "
                     "--rodape faixa.png [--ordem a,b] [--parada 1] [--trecho 3] [--fps 30] [--res 1080x1920]")
SAIDA = os.path.abspath(a[0])


def opcao(nome, padrao=None):
    return a[a.index(nome) + 1] if nome in a else padrao


MOTOR = opcao("--motor", "eevee")
if MOTOR not in ("eevee", "cycles"):
    raise SystemExit(f"--motor {MOTOR}: use eevee ou cycles")
AMOSTRAS = int(opcao("--amostras", "64" if MOTOR == "cycles" else "32"))
FPS = int(opcao("--fps", "30"))
PARADA, TRECHO = float(opcao("--parada", "1.0")), float(opcao("--trecho", "3.0"))
LARG, ALT = (int(x) for x in opcao("--res", "1080x1920").lower().split("x"))
if LARG % 2 or ALT % 2:
    raise SystemExit(f"--res {LARG}x{ALT}: o H.264 exige largura e altura pares")
RODAPE = opcao("--rodape")
SO_CONFERIR = "--so-conferir" in a
if not RODAPE and "--sem-rodape" not in a and not SO_CONFERIR:
    raise SystemExit("falta --rodape faixa.png (gere com: python comparar.py faixa --largura "
                     f"{LARG} --saida faixa.png). Video sem rodape so com --sem-rodape, quando a pessoa pedir.")

cena = bpy.context.scene
cam = bpy.data.objects["CAM"]
alvo = bpy.data.objects["ALVO"]
if opcao("--cena"):
    VISTAS = json.load(open(os.path.abspath(opcao("--cena")), encoding="utf-8")).get("vistas") or {}
else:
    VISTAS = json.loads(cena.get("vistas", "{}"))
ORDEM = [n for n in opcao("--ordem", ",".join(VISTAS)).split(",") if n]
falta = [n for n in ORDEM if n not in VISTAS]
if falta or len(ORDEM) < 2:
    raise SystemExit(f"--ordem precisa de 2+ vistas do cena.json; nao achei: {falta or ORDEM}")

alt_faixa = 0
if RODAPE:
    img_faixa = bpy.data.images.load(os.path.abspath(RODAPE))
    lf, alt_faixa = img_faixa.size
    if lf != LARG:
        raise SystemExit(f"a faixa tem {lf} px de largura e o video {LARG}: gere com --largura {LARG}")
ALT_3D = ALT - alt_faixa


def anima():
    """Parada em cada vista + trecho ate a proxima; bezier padrao do Blender = acelera e freia suave."""
    p, t = round(PARADA * FPS), round(TRECHO * FPS)
    f = 1
    for k, nome in enumerate(ORDEM):
        v = VISTAS[nome]
        for q in (f, f + p) if p else (f,):
            cam.location, alvo.location, cam.data.lens = v["cam"], v["alvo"], v.get("lente", 24)
            cam.keyframe_insert("location", frame=q)
            alvo.keyframe_insert("location", frame=q)
            cam.data.keyframe_insert("lens", frame=q)
        f += p + (t if k < len(ORDEM) - 1 else 0)
    return f


def confere_caminho(fim):
    """Camera dentro de um movel (a caixa de todas as pecas dele) em algum quadro = atravessou."""
    caixas = P.caixas_de_colisao(cena)
    achados = {}
    for q in range(1, fim + 1, 2):
        cena.frame_set(q)
        for nome in P.dentro(caixas, cam.matrix_world.translation):
            achados.setdefault(nome, q)
    if not achados:
        print(f"CAMINHO OK: a camera nao atravessa nenhum movel ({len(caixas)} conferidos)", flush=True)
    for nome, q in achados.items():
        print(f"AVISO passeio: no quadro {q} ({q / FPS:.1f} s) a camera atravessa '{nome}'. Ponha uma vista "
              f"intermediaria sem foto ou mude a --ordem.", flush=True)
    cena.frame_set(1)


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


def saida_video(s, caminho):
    im = s.render.image_settings
    if hasattr(im, "media_type"):                       # Blender 5.x separa imagem de video
        im.media_type = "VIDEO"
    im.file_format = "FFMPEG"
    ff = s.render.ffmpeg
    ff.format, ff.codec = "MPEG4", "H264"
    ff.constant_rate_factor = "HIGH"
    ff.ffmpeg_preset = "GOOD"
    ff.audio_codec = "NONE"
    s.render.filepath = caminho
    s.render.use_file_extension = False


def faixa_de_strips(se):
    return se.strips if hasattr(se, "strips") else se.sequences   # 'sequences' ate o 4.x


t0 = time.time()
cam.constraints["Track To"].influence = 1.0
fim = anima()
confere_caminho(fim)
if SO_CONFERIR:
    raise SystemExit(0)
QUADROS = SAIDA[:-4] + "_quadros" if SAIDA.lower().endswith(".mp4") else SAIDA + "_quadros"
os.makedirs(QUADROS, exist_ok=True)
if MOTOR == "cycles":
    liga_cycles()
else:
    cena.eevee.taa_render_samples = AMOSTRAS
cena.render.fps, cena.render.fps_base = FPS, 1.0
cena.frame_start, cena.frame_end = 1, fim
cena.render.resolution_x, cena.render.resolution_y, cena.render.resolution_percentage = LARG, ALT_3D, 100
cena.render.use_motion_blur = False
cam.data.dof.use_dof = False
cena.render.image_settings.file_format = "PNG"
cena.render.filepath = os.path.join(QUADROS, "q_")
print(f"passeio: {' -> '.join(ORDEM)} | {fim} quadros ({fim / FPS:.1f} s) em {LARG}x{ALT_3D} + faixa {alt_faixa} px "
      f"| {MOTOR}", flush=True)
bpy.ops.render.render(animation=True)
t_render = time.time() - t0

# montagem: quadros em cima, faixa embaixo, no editor de video do Blender (sem transformacao de cor: os PNG ja saem
# com a cor final da cena)
mont = bpy.data.scenes.new("MONTAGEM")
mont.render.resolution_x, mont.render.resolution_y, mont.render.resolution_percentage = LARG, ALT, 100
mont.render.fps, mont.render.fps_base = FPS, 1.0
mont.frame_start, mont.frame_end = 1, fim
try:
    mont.view_settings.view_transform = "Standard"
except TypeError:
    pass
mont.view_settings.look = "None"
mont.view_settings.exposure = 0.0
se = mont.sequence_editor_create()
st = faixa_de_strips(se)
nomes = sorted(x for x in os.listdir(QUADROS) if x.lower().endswith(".png"))
if len(nomes) != fim:
    raise SystemExit(f"esperava {fim} quadros em {QUADROS} e achei {len(nomes)}")
s3d = st.new_image("passeio", os.path.join(QUADROS, nomes[0]), channel=1, frame_start=1, fit_method="ORIGINAL")
for n in nomes[1:]:
    s3d.elements.append(n)
s3d.transform.offset_y = alt_faixa / 2                 # origem no centro: sobe metade da faixa = encosta no topo
if RODAPE:
    sf = st.new_image("rodape", os.path.abspath(RODAPE), channel=2, frame_start=1, fit_method="ORIGINAL")
    if hasattr(sf, "duration"):                         # 5.x; o frame_final_duration sai no 6.0
        sf.duration = fim
    else:
        sf.frame_final_duration = fim
    sf.transform.offset_y = -(ALT - alt_faixa) / 2
saida_video(mont, SAIDA)
if os.path.exists(SAIDA):
    os.remove(SAIDA)                                    # assim a conferencia abaixo prova que o MP4 e desta rodada
bpy.ops.render.render(animation=True, scene=mont.name)
if not os.path.exists(SAIDA) or os.path.getsize(SAIDA) < 1000:
    raise SystemExit(f"o MP4 nao saiu em {SAIDA}; os quadros ficaram em {QUADROS}")
if "--manter-quadros" not in a:
    shutil.rmtree(QUADROS, ignore_errors=True)
print(f"PASSEIO OK {SAIDA}: {fim / FPS:.1f} s, {LARG}x{ALT}, {os.path.getsize(SAIDA) / 1e6:.1f} MB, "
      f"render {t_render:.0f} s, total {time.time() - t0:.0f} s ({MOTOR})", flush=True)
