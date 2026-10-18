# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Monta a cena 3D de um ambiente a partir do cena.json (Blender 4.2+).

Uso: blender -b --factory-startup -P montar.py -- <cena.json> <saida.blend>

Coordenadas em metros. Olhando de dentro pra PAREDE DO FUNDO: x = largura (0 na parede da esquerda), y = profundidade
(0 na parede da frente, cresce pro fundo), z = altura (0 no piso). Objeto com rot 0 fica com o LADO DE USO virado pra -y
(tela do monitor, assento do sofa, portas do armario, quem senta na mesa, pe da cama); rot em graus, anti-horario visto
de cima, ou "olha_para": [x, y] gira o lado de uso pra esse ponto. Objeto de parede (quadro, tv, prateleira): pos e o
ponto NA FACE da parede, z = altura da base. Cores em sRGB, como saem do conta-gotas numa foto ("#aabbcc").
Tudo e desenho proprio procedural: sem asset de terceiro. Esquema completo: references/cena-json.md.
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import pecas as P  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(ARGS) < 2:
    raise SystemExit("uso: blender -b --factory-startup -P montar.py -- <cena.json> <saida.blend>")
CENA_JSON = os.path.abspath(ARGS[0])
SAIDA = os.path.abspath(ARGS[1])
PASTA = os.path.dirname(CENA_JSON)
CENA = json.load(open(CENA_JSON, encoding="utf-8"))
AVISOS = []


def aviso(m):
    AVISOS.append(m)
    print("AVISO", m, flush=True)


def caminho(rel):
    """Caminho de imagem do cena.json: relativo a pasta do cena.json. Ausente = None (com aviso)."""
    if not rel:
        return None
    p = rel if os.path.isabs(rel) else os.path.join(PASTA, rel)
    if not os.path.exists(p):
        aviso(f"imagem nao achada: {rel}")
        return None
    return p


# ------------------------------------------------------------------ cores e acabamentos
def srgb(c):
    """'#aabbcc' ou [r, g, b] (0-1 ou 0-255) em sRGB -> cor linear do Blender."""
    if isinstance(c, str):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(x * 2 for x in h)
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    elif max(c) > 1:
        c = [x / 255 for x in c]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])


def mat_madeira(nome, escura, clara, escala=28.0, distorcao=3.0, rough=0.42):
    """Madeira procedural: veio fino correndo ao longo do X local da peca (wave esticado) + manchas largas de ruido,
    cor entre escura e clara, verniz leve. escala = densidade do veio (28 = ~1 cm entre linhas)."""
    m = bpy.data.materials.new(nome)
    P.liga_nos(m)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.08, 1.0, 1.0)
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Y"
    wv.inputs["Scale"].default_value = escala
    wv.inputs["Distortion"].default_value = distorcao
    wv.inputs["Detail"].default_value = 3.0
    wv.inputs["Detail Scale"].default_value = 1.5
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 4.0
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "FLOAT"
    mx.inputs["Factor"].default_value = 0.45
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[0].color = (*escura, 1)
    cr.color_ramp.elements[1].position = 0.8
    cr.color_ramp.elements[1].color = (*clara, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], mx.inputs["A"])
    nt.links.new(nz.outputs["Fac"], mx.inputs["B"])
    nt.links.new(mx.outputs["Result"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.2
    b.inputs["Coat Roughness"].default_value = 0.2
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_tabuas(nome, escura, clara, comp=1.2, larg=0.19):
    """Piso de tabuas: assoalho em amarracao (Brick), cada tabua num tom, veio fino ao longo dela e junta escura."""
    m = bpy.data.materials.new(nome)
    P.liga_nos(m)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = comp
    br.inputs["Row Height"].default_value = larg
    br.inputs["Mortar Size"].default_value = 0.0015
    br.inputs["Mortar Smooth"].default_value = 0.2
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (*escura, 1)
    br.inputs["Color2"].default_value = (*clara, 1)
    br.inputs["Mortar"].default_value = (*(c * 0.35 for c in escura), 1)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.08, 6.0, 1.0)
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Y"
    wv.inputs["Scale"].default_value = 1.5
    wv.inputs["Distortion"].default_value = 6.0
    wv.inputs["Detail"].default_value = 3.0
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.inputs["Factor"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(br.outputs["Color"], mx.inputs["A"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.75, 0.75, 0.75, 1)
    cr.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(wv.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], mx.inputs["B"])
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.38
    b.inputs["Coat Weight"].default_value = 0.15
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_carpete(nome, escura, clara):
    """Carpete/tapete: trama fina (ruido em escala alta) com relevo, fosco."""
    m = bpy.data.materials.new(nome)
    P.liga_nos(m)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 260.0
    nz.inputs["Detail"].default_value = 6.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*escura, 1)
    cr.color_ramp.elements[1].color = (*clara, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.15
    return m


def mat_vidro(nome, cor):
    m = P.material(nome, cor, rough=0.02, spec=0.5)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.45
    for k, v in (("use_raytrace_refraction", True), ("use_transparent_shadow", True)):
        if hasattr(m, k):
            setattr(m, k, v)
    return m


def mat_vidro_fino(nome, cor):
    """Vidro de janela: atravessa sem desviar a imagem (refracao numa placa fina dobra o caixilho em listras) e
    reflete pouco, mais de lado (fresnel)."""
    m = bpy.data.materials.new(nome)
    P.liga_nos(m)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*cor, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.03
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.12
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Fresnel"], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    return m


def mat_imagem(nome, img, emissivo=False, forca=1.0, cor_vazia=(0.012, 0.012, 0.014)):
    """Imagem no UV do plano: tela (emissiva, com reflexo de vidro) ou impressa (quadro). Sem imagem = tela apagada."""
    m = bpy.data.materials.new(nome)
    P.liga_nos(m)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.15 if emissivo else 0.55
    if img:
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = bpy.data.images.load(img, check_existing=True)
        tx.extension = "EXTEND"
        uv = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(uv.outputs["UV"], tx.inputs["Vector"])
        if emissivo:
            b.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1)
            nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = forca
        else:
            nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*cor_vazia, 1)
    return m


PADRAO_COR = {"madeira": "#8a5a36", "tecido": "#6b6b6b", "couro": "#5a3a26", "metal": "#9a9a9a",
              "plastico": "#2a2a2a", "vidro": "#e4eef0", "espelho": "#e6e6e6", "pintura": "#ece8e1",
              "porcelanato": "#cfc8bd", "carpete": "#8c8478", "concreto": "#9a9893",
              "tabuas": "#9a6a42"}
_MATS = {}


def acab(spec, padrao="plastico"):
    """Acabamento: nome ('madeira'), cor ('#aabbcc' = acabamento padrao nessa cor) ou {"tipo", "cor", "cor2", "brilho"}.
    tipos: madeira, tabuas (assoalho; 'comprimento'/'largura' da tabua em m), tecido, couro, metal, plastico,
    vidro, espelho, pintura, porcelanato, carpete, concreto."""
    if spec is None:
        spec = padrao
    if isinstance(spec, str):
        spec = {"tipo": spec} if spec in PADRAO_COR else {"tipo": padrao, "cor": spec}
    tipo = spec.get("tipo", padrao)
    if tipo not in PADRAO_COR:
        aviso(f"acabamento desconhecido '{tipo}', usei plastico")
        tipo = "plastico"
    cor = spec.get("cor", PADRAO_COR[tipo])
    chave = json.dumps([tipo, cor, spec.get("cor2"), spec.get("brilho")])
    if chave in _MATS:
        return _MATS[chave]
    c = srgb(cor)
    nome = f"{tipo}_{len(_MATS)}"
    if tipo == "madeira":
        m = mat_madeira(nome, srgb(spec["cor2"]) if spec.get("cor2") else tuple(x * 0.6 for x in c), c)
    elif tipo == "tabuas":
        m = mat_tabuas(nome, srgb(spec["cor2"]) if spec.get("cor2") else tuple(x * 0.75 for x in c), c,
                       comp=float(spec.get("comprimento", 1.2)), larg=float(spec.get("largura", 0.19)))
    elif tipo == "carpete":
        m = mat_carpete(nome, srgb(spec["cor2"]) if spec.get("cor2") else tuple(x * 0.7 for x in c), c)
    elif tipo == "tecido":
        m = P.material(nome, c, rough=0.9, spec=0.2, relevo=0.25, relevo_escala=2500)
    elif tipo == "couro":
        m = P.material(nome, c, rough=0.45, spec=0.4, coat=0.1, relevo=0.08, relevo_escala=700)
    elif tipo == "metal":
        m = P.material(nome, c, rough=0.3, metal=1.0)
    elif tipo == "espelho":
        m = P.material(nome, c, rough=0.02, metal=1.0)
    elif tipo == "vidro":
        m = mat_vidro(nome, c)
    elif tipo == "pintura":
        m = P.material(nome, c, rough=0.85, spec=0.3)
    elif tipo == "porcelanato":
        m = P.material(nome, c, rough=0.22, spec=0.5, coat=0.1)
    elif tipo == "concreto":
        m = P.material(nome, c, rough=0.92, spec=0.25, relevo=0.2, relevo_escala=150)
    else:
        m = P.material(nome, c, rough=0.5, spec=0.4)
    if spec.get("brilho") is not None:
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1 - float(spec["brilho"])
    _MATS[chave] = m
    return m


# ------------------------------------------------------------------ geometria auxiliar
def plano_img(nome, larg, alt, material, y=0.0):
    """Retangulo no plano XZ virado pra -y, UV 0..1 (u na largura, v na altura), centro em (0, y, 0)."""
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new((sx * larg / 2, y, sz * alt / 2)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for lp, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uv].uv = c
    return P.objeto_bm(nome, bm, material, normais=False)


def sem_sombra(o):
    for k in ("visible_shadow",):
        if hasattr(o, k):
            setattr(o, k, False)


def giro(n):
    """Angulo (rad) que leva o -y local pra direcao n (no plano)."""
    return math.atan2(n.x, -n.y)


# ------------------------------------------------------------------ ambiente: piso, paredes, aberturas, teto
def ambiente(a, aberturas):
    L, Pr, H = a["largura"], a["profundidade"], a.get("pe_direito", 2.7)
    e = a.get("espessura_parede", 0.12)
    piso = a.get("piso", "tabuas")          # piso de madeira = assoalho de tabuas (veio + juntas), nao bloco liso
    if piso == "madeira" or (isinstance(piso, dict) and piso.get("tipo") == "madeira"):
        piso = {**piso, "tipo": "tabuas"} if isinstance(piso, dict) else "tabuas"
    P.caixa("piso", (L + 2 * e, Pr + 2 * e, 0.04), (L / 2, Pr / 2, -0.02), acab(piso, "tabuas"))
    if a.get("teto", True):
        P.caixa("teto", (L + 2 * e, Pr + 2 * e, 0.04), (L / 2, Pr / 2, H + 0.02), acab(a.get("forro", "#f2f0ec"),
                                                                                         "pintura"))
    defs = {   # origem (u = 0), direcao de u, normal pra dentro, comprimento
        "fundo": (Vector((0, Pr, 0)), Vector((1, 0, 0)), Vector((0, -1, 0)), L),
        "frente": (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), L),
        "esquerda": (Vector((0, 0, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), Pr),
        "direita": (Vector((L, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), Pr),
    }
    m_padrao = a.get("parede", "pintura")
    por_parede = a.get("paredes", {})
    rodape = a.get("rodape", {"altura": 0.07, "cor": "#f4f2ee"})
    for nome, (o, d, n, comp) in defs.items():
        if nome in a.get("sem_parede", []):
            continue
        mw = acab(por_parede.get(nome, m_padrao), "pintura")
        abs_ = [ab for ab in aberturas if ab.get("parede") == nome]
        u0, u1 = (-e, comp + e) if nome in ("fundo", "frente") else (0.0, comp)
        cortes = {u0, u1}
        for ab in abs_:
            cortes |= {ab["centro"] - ab["largura"] / 2, ab["centro"] + ab["largura"] / 2}
        cortes = sorted(c for c in cortes if u0 <= c <= u1)
        for k, (ua, ub) in enumerate(zip(cortes, cortes[1:])):
            if ub - ua < 1e-4:
                continue
            meio = (ua + ub) / 2
            vao = next((ab for ab in abs_ if abs(meio - ab["centro"]) < ab["largura"] / 2), None)
            if vao:
                base = vao.get("peitoril", 1.0 if vao["tipo"] == "janela" else 0.0)
                faixas = [(0.0, base), (base + vao.get("altura", 2.1), H)]
            else:
                faixas = [(0.0, H)]
            for j, (z0, z1) in enumerate(faixas):
                if z1 - z0 < 1e-4:
                    continue
                c = o + d * meio - n * (e / 2) + Vector((0, 0, (z0 + z1) / 2))
                tam = (ub - ua, e, z1 - z0) if d.x else (e, ub - ua, z1 - z0)
                P.caixa(f"parede_{nome}_{k}_{j}", tam, c, mw)
        if rodape:
            mr = acab(rodape.get("cor", "#f4f2ee"), "pintura")
            ra = rodape.get("altura", 0.07)
            livres = [(0.0, comp)]
            for ab in abs_:
                if ab.get("peitoril", 1.0 if ab["tipo"] == "janela" else 0.0) < 0.05:
                    a0, a1 = ab["centro"] - ab["largura"] / 2, ab["centro"] + ab["largura"] / 2
                    livres = [s for t in livres for s in ((t[0], min(t[1], a0)), (max(t[0], a1), t[1])) if s[1] > s[0]]
            for k, (ua, ub) in enumerate(livres):
                c = o + d * ((ua + ub) / 2) + n * 0.006 + Vector((0, 0, ra / 2))
                P.caixa(f"rodape_{nome}_{k}", (ub - ua, 0.012, ra) if d.x else (0.012, ub - ua, ra), c, mr)
        for ab in abs_:
            centro = o + d * ab["centro"] - n * (e / 2)
            if ab["tipo"] == "janela":
                janela(ab, centro, n, e)
            elif ab["tipo"] == "porta":
                porta(ab, centro, n, e)
    return defs


def _local(centro, th, nome, tam, pos, material, bevel=0.0):
    """Caixa num referencial girado de th em volta de z com origem em centro (pos e tam no referencial local)."""
    c, s = math.cos(th), math.sin(th)
    p = Vector((centro.x + pos[0] * c - pos[1] * s, centro.y + pos[0] * s + pos[1] * c, centro.z + pos[2]))
    return P.caixa(nome, tam, p, material, bevel=bevel, rot=(0, 0, th))


def janela(ab, centro, n, e):
    w, h = ab["largura"], ab["altura"]
    base = ab.get("peitoril", 1.0)
    th = giro(n)
    zc = base + h / 2
    mc = acab(ab.get("caixilho", "#2b2b2b"), "metal")
    cx = ab.get("caixilho_largura", 0.04)
    prof = min(e * 0.5, 0.07)
    nome = ab.get("id", "janela")
    for sx in (-1, 1):
        _local(centro, th, f"{nome}_lado", (cx, prof, h), (sx * (w / 2 - cx / 2), 0, zc), mc)
    for sz in (-1, 1):
        _local(centro, th, f"{nome}_trava", (w, prof, cx), (0, 0, zc + sz * (h / 2 - cx / 2)), mc)
    div = max(1, int(ab.get("divisoes", 1)))
    for k in range(1, div):
        _local(centro, th, f"{nome}_montante", (cx * 0.8, prof, h), (-w / 2 + w * k / div, 0, zc), mc)
    vidro = _local(centro, th, f"{nome}_vidro", (w - 2 * cx, 0.006, h - 2 * cx), (0, 0, zc), mat_vidro_fino(f"{nome}_vidro", srgb("#f4f8f8")))
    sem_sombra(vidro)
    # lado de fora: foto da vista (ou ceu) num plano que brilha, longe o bastante pra ter paralaxe
    img = caminho(ab.get("vista"))
    m_vista = mat_imagem(f"{nome}_vista", img, emissivo=True, forca=ab.get("vista_forca", 1.6),
                         cor_vazia=srgb(ab.get("ceu", "#bcd3e6")))
    b = m_vista.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)      # so brilho: luz e sombra da sala nao marcam a paisagem
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    if not img:
        b.inputs["Emission Color"].default_value = (*srgb(ab.get("ceu", "#bcd3e6")), 1)
        b.inputs["Emission Strength"].default_value = ab.get("vista_forca", 1.6)
    dist = ab.get("vista_distancia", 1.5)      # longe o bastante pra mudar com o angulo da camera, grande pra cobrir
    pl = plano_img(f"{nome}_lado_de_fora", w + 3.0 * dist, h + 2.2 * dist, m_vista)
    c = centro - n * dist
    pl.location = (c.x, c.y, zc)
    pl.rotation_euler = (0, 0, th)
    sem_sombra(pl)


def porta(ab, centro, n, e):
    w, h = ab["largura"], ab.get("altura", 2.1)
    th = giro(n)
    nome = ab.get("id", "porta")
    mb = acab(ab.get("batente", ab.get("cor", "#f2f0ec")), "pintura")
    bat = 0.05
    for sx in (-1, 1):
        _local(centro, th, f"{nome}_batente", (bat, e + 0.02, h), (sx * (w / 2 - bat / 2), 0, h / 2), mb)
    _local(centro, th, f"{nome}_batente_topo", (w, e + 0.02, bat), (0, 0, h - bat / 2), mb)
    if not ab.get("folha", True):
        return
    mf = acab(ab.get("cor", "#f2f0ec"), "pintura")
    lw, lh, le = w - 2 * bat, h - bat - 0.008, 0.035
    # referencial local da abertura: -y = pra dentro do ambiente. Quem esta dentro olha pra +y: a esquerda dele e -x.
    lado = -1 if ab.get("dobradica", "esquerda") == "esquerda" else 1
    a = lado * math.radians(ab.get("abertura", 0))          # abre pra dentro: a ponta livre vai pra -y
    piv = Vector((lado * lw / 2, -e / 2, 0))                 # dobradica na face de dentro da parede
    c, s = math.cos(a), math.sin(a)

    def no_mundo(rel):
        q = Vector((rel[0] * c - rel[1] * s, rel[0] * s + rel[1] * c, rel[2])) + piv
        cc, ss = math.cos(th), math.sin(th)
        return Vector((centro.x + q.x * cc - q.y * ss, centro.y + q.x * ss + q.y * cc, q.z))
    P.caixa(f"{nome}_folha", (lw, le, lh), no_mundo((-lado * lw / 2, le / 2, lh / 2 + 0.004)), mf, bevel=0.002,
            rot=(0, 0, th + a))
    P.cilindro(f"{nome}_macaneta", 0.009, 0.12, no_mundo((-lado * (lw - 0.08), -0.03, 1.02)), acab("metal", "metal"),
               rot=(0, math.radians(90), th + a))


# ------------------------------------------------------------------ objetos (coordenada local: base em z = 0, lado de uso em -y)
def o_caixa(o, nome):
    l, p, a = o.get("tam", [0.5, 0.5, 0.5])
    return P.raiz(nome, [P.caixa(nome + "_corpo", (l, p, a), (0, 0, a / 2), acab(o.get("acabamento")),
                                 bevel=o.get("bisel", 0.004))])


def o_cilindro(o, nome):
    r, a = o.get("raio", 0.2), o.get("altura", 0.5)
    return P.raiz(nome, [P.cilindro(nome + "_corpo", r, a, (0, 0, a / 2), acab(o.get("acabamento")),
                                    raio2=o.get("raio_topo"), verts=48)])


def o_mesa(o, nome):
    l, p, a = o.get("tam", [1.4, 0.7, 0.75])
    esp = o.get("espessura", 0.025)
    mt = acab(o.get("tampo", "madeira"), "madeira")
    estilo = o.get("estilo", "4pes")
    mp = acab(o.get("pes", "metal" if estilo != "painel" else o.get("tampo", "madeira")), "metal")
    pec = [P.caixa(nome + "_tampo", (l, p, esp), (0, 0, a - esp / 2), mt, bevel=0.002)]
    hp = a - esp
    if estilo == "painel":
        for sx in (-1, 1):
            pec.append(P.caixa(nome + "_lateral", (0.025, p - 0.02, hp), (sx * (l / 2 - 0.0125), 0, hp / 2), mp,
                               bevel=0.002))
        pec.append(P.caixa(nome + "_saia", (l - 0.05, 0.018, hp * 0.35), (0, p / 2 - 0.06, hp - hp * 0.175), mp))
    elif estilo == "standing":
        for sx in (-1, 1):
            x = sx * (l / 2 - 0.12)
            pec.append(P.caixa(nome + "_coluna", (0.075, 0.055, hp - 0.05), (x, 0, (hp - 0.05) / 2 + 0.03), mp,
                               bevel=0.004))
            pec.append(P.caixa(nome + "_pe", (0.065, p - 0.06, 0.03), (x, 0, 0.015), mp, bevel=0.006))
            pec.append(P.caixa(nome + "_suporte", (0.05, p - 0.12, 0.03), (x, 0, hp - 0.015), mp))
        pec.append(P.caixa(nome + "_travessa", (l - 0.3, 0.05, 0.04), (0, 0, hp - 0.05), mp))
    else:
        for sx in (-1, 1):
            for sy in (-1, 1):
                pec.append(P.caixa(nome + "_pe", (0.04, 0.04, hp), (sx * (l / 2 - 0.05), sy * (p / 2 - 0.05), hp / 2),
                                   mp, bevel=0.003))
    return P.raiz(nome, pec)


def o_cadeira(o, nome):
    if o.get("estilo", "escritorio") == "escritorio":
        r = P.cadeira(nome + "_corpo", tecido=srgb(o.get("cor", "#2e2e2e")), concha=srgb(o.get("cor2", "#3a3a3a")),
                      base=srgb(o.get("cor_base", "#141414")))
        r.rotation_euler = (0, 0, math.pi)     # o pecas.cadeira olha pra +y; aqui o lado de uso (o assento) e -y
        return P.raiz(nome, [r])
    ma = acab(o.get("acabamento", "madeira"), "madeira")
    ms = acab(o.get("assento", o.get("acabamento", "madeira")), "madeira")
    hs = o.get("altura_assento", 0.45)
    pec = [P.caixa(nome + "_assento", (0.44, 0.42, 0.03), (0, 0, hs - 0.015), ms, bevel=0.004)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            pec.append(P.caixa(nome + "_pe", (0.03, 0.03, hs - 0.03), (sx * 0.19, sy * 0.18, (hs - 0.03) / 2), ma))
        pec.append(P.caixa(nome + "_encosto_pe", (0.03, 0.03, 0.42), (sx * 0.19, 0.18, hs + 0.21), ma))
    pec.append(P.caixa(nome + "_encosto", (0.4, 0.025, 0.16), (0, 0.185, hs + 0.33), ma, bevel=0.004))
    return P.raiz(nome, pec)


def o_monitor(o, nome):
    lt, at = o.get("tela", [0.6, 0.34])
    hb = o.get("altura_base", 0.12)
    mc = acab(o.get("acabamento", "#1a1a1a"), "plastico")
    img = caminho(o.get("imagem"))
    mt = mat_imagem(nome + "_tela", img, emissivo=True, forca=o.get("brilho", 1.0))
    pec = []
    raio = o.get("curvo")
    zc = hb + at / 2
    if raio:
        import bmesh
        ang = lt / raio
        n = 32
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        cols = []
        for k in range(n + 1):                 # curva concava pra quem olha (as pontas vem pra -y)
            t = -ang / 2 + ang * k / n
            x, y = raio * math.sin(t), -raio * (1 - math.cos(t))
            cols.append((bm.verts.new((x, y - 0.006, zc - at / 2)), bm.verts.new((x, y - 0.006, zc + at / 2))))
        for k in range(n):
            f = bm.faces.new((cols[k][0], cols[k + 1][0], cols[k + 1][1], cols[k][1]))
            for lp, (u, v) in zip(f.loops, ((k / n, 0), ((k + 1) / n, 0), ((k + 1) / n, 1), (k / n, 1))):
                lp[uvl].uv = (u, v)
        tela = P.objeto_bm(nome + "_tela", bm, mt, normais=False)
        casco = []
        for k in range(n):
            t = -ang / 2 + ang * (k + 0.5) / n
            casco.append(P.caixa(nome + "_casco", (lt / n * 1.04, 0.02, at + 0.016),
                                 (raio * math.sin(t), -raio * (1 - math.cos(t)) + 0.005, zc), mc, rot=(0, 0, -t)))
        pec += [tela] + casco
    else:
        tela = plano_img(nome + "_tela", lt, at, mt, y=-0.0125)
        tela.location.z = zc
        pec += [tela, P.caixa(nome + "_casco", (lt + 0.016, 0.022, at + 0.016), (0, 0, zc), mc, bevel=0.003)]
    if o.get("suporte", "pe") == "pe":
        pec.append(P.caixa(nome + "_haste", (0.05, 0.025, zc), (0, 0.06, zc / 2), mc, bevel=0.004))
        pec.append(P.caixa(nome + "_base", (0.24, 0.18, 0.012), (0, 0.04, 0.006), mc, bevel=0.004))
    return P.raiz(nome, pec)


def o_notebook(o, nome):
    lw, lp = o.get("tam", [0.32, 0.22])
    ab = math.radians(o.get("abertura", 110))
    mc = acab(o.get("acabamento", "#8c8c90"), "metal")
    img = caminho(o.get("imagem"))
    base = P.caixa(nome + "_base", (lw, lp, 0.012), (0, 0, 0.006), mc, bevel=0.003)
    tecl = P.caixa(nome + "_teclado", (lw * 0.88, lp * 0.42, 0.001), (0, lp * 0.08, 0.0125), acab("#151515"))
    h = lp
    phi = math.radians(90) - ab                # tampa: dobradica no fundo da base, abre ab graus a partir da base
    eixo = Vector((0, -math.sin(phi), math.cos(phi)))
    frente = Vector((0, -math.cos(phi), -math.sin(phi)))
    mid = Vector((0, lp / 2, 0.012)) + eixo * (h / 2)
    tampa = P.caixa(nome + "_tampa", (lw, 0.007, h), mid, mc, bevel=0.002, rot=(phi, 0, 0))
    tela = plano_img(nome + "_tela", lw * 0.92, h * 0.86, mat_imagem(nome + "_tela", img, emissivo=True))
    tela.location = mid + frente * 0.0037
    tela.rotation_euler = (phi, 0, 0)
    return P.raiz(nome, [base, tecl, tampa, tela])


def o_teclado(o, nome):
    tex = os.path.join(os.path.dirname(AQUI), "assets", "tex", "teclado.png")
    r = P.teclado(nome, legendas=tex if os.path.exists(tex) else None, cor_corpo=srgb(o.get("cor", "#2b2b2e")))
    return r


def o_mouse(o, nome):
    return P.mouse(nome, cor=srgb(o.get("cor", "#1d1d1f")))


def o_estante(o, nome):
    l, p, a = o.get("tam", [0.8, 0.3, 1.8])
    m = acab(o.get("acabamento", "madeira"), "madeira")
    esp = 0.018
    n = max(1, int(o.get("prateleiras", 4)))
    pec = [P.caixa(nome + "_lado", (esp, p, a), (sx * (l / 2 - esp / 2), 0, a / 2), m) for sx in (-1, 1)]
    pec.append(P.caixa(nome + "_fundo", (l, 0.006, a), (0, p / 2 - 0.003, a / 2), m))
    niveis = [0.06 + (a - 0.06 - esp) * k / n for k in range(n + 1)]
    for z in niveis:
        pec.append(P.caixa(nome + "_prateleira", (l - 2 * esp, p - 0.01, esp), (0, -0.003, z + esp / 2), m))
    if o.get("livros", True):
        rnd = random.Random(o.get("semente", 3))
        cores = [srgb(c) for c in o.get("cores_livros", ["#7a2e2a", "#2c4a6b", "#d9cfbf", "#3d5c3a", "#b58a3c",
                                                         "#262626", "#8a8a84"])]
        for z0, z1 in zip(niveis, niveis[1:]):
            x = -l / 2 + esp + 0.01
            fim = l / 2 - esp - rnd.uniform(0.05, l * 0.35)
            while x < fim:
                lw = rnd.uniform(0.018, 0.045)
                lh = min(z1 - z0 - esp - 0.02, rnd.uniform(0.17, 0.28))
                lp = min(p - 0.04, rnd.uniform(0.14, 0.22))
                mat_l = P.material(f"{nome}_livro", rnd.choice(cores), rough=0.6, spec=0.3)
                pec.append(P.caixa(nome + "_livro", (lw, lp, lh), (x + lw / 2, p / 2 - 0.01 - lp / 2,
                                                                     z0 + esp + lh / 2), mat_l, bevel=0.0015))
                x += lw + rnd.uniform(0.0, 0.004)
    return P.raiz(nome, pec)


def o_armario(o, nome):
    l, p, a = o.get("tam", [1.2, 0.55, 2.1])
    m = acab(o.get("acabamento", "#e9e5de"), "pintura")
    mp = acab(o.get("puxador", "metal"), "metal")
    nd = max(1, int(o.get("portas", 2)))
    pec = [P.caixa(nome + "_corpo", (l, p, a), (0, 0, a / 2), m, bevel=0.002)]
    mv = acab("#202020")
    for k in range(1, nd):
        pec.append(P.caixa(nome + "_fresta", (0.003, 0.002, a - 0.04), (-l / 2 + l * k / nd, -p / 2 - 0.0005, a / 2),
                           mv))
    for k in range(nd):
        x = -l / 2 + l * (k + 0.5) / nd + (l / nd * 0.38) * (1 if k % 2 == 0 else -1)
        pec.append(P.caixa(nome + "_puxador", (0.012, 0.025, 0.18), (x, -p / 2 - 0.015, min(a / 2, 1.05)), mp,
                           bevel=0.003))
    return P.raiz(nome, pec)


def o_sofa(o, nome):
    l, p, a = o.get("tam", [2.0, 0.9, 0.82])
    mt = acab(o.get("acabamento", "tecido"), "tecido")
    n = max(1, int(o.get("lugares", 3)))
    hs = o.get("altura_assento", 0.43)
    braco = o.get("braco", 0.16)
    pec = [P.almofada(nome + "_base", (l, p, hs - 0.16), (0, 0, 0.06 + (hs - 0.16) / 2), mt, 0.02)]
    for sx in (-1, 1):
        pec.append(P.almofada(nome + "_braco", (braco, p, a * 0.75 - 0.06), (sx * (l / 2 - braco / 2), 0,
                                                                             0.06 + (a * 0.75 - 0.06) / 2), mt, 0.04))
    lw = (l - 2 * braco) / n
    for k in range(n):
        x = -l / 2 + braco + lw * (k + 0.5)
        pec.append(P.almofada(nome + "_assento", (lw - 0.01, p - 0.22, 0.16), (x, -0.1, hs - 0.08), mt, 0.04))
        pec.append(P.almofada(nome + "_encosto", (lw - 0.01, 0.2, a - hs), (x, p / 2 - 0.12, hs + (a - hs) / 2 - 0.02),
                              mt, 0.05, rot=(math.radians(-8), 0, 0)))
    mp = acab(o.get("pes", "#1a1a1a"), "plastico")
    for sx in (-1, 1):
        for sy in (-1, 1):
            pec.append(P.cilindro(nome + "_pe", 0.02, 0.06, (sx * (l / 2 - 0.06), sy * (p / 2 - 0.06), 0.03), mp))
    return P.raiz(nome, pec)


def o_cama(o, nome):
    l, c = o.get("tam", [1.38, 1.88])
    hb = o.get("altura", 0.5)
    mb = acab(o.get("acabamento", "tecido"), "tecido")
    mr = acab(o.get("roupa", "#e8e4dc"), "tecido")
    pec = [P.almofada(nome + "_base", (l + 0.04, c + 0.04, hb - 0.25), (0, 0, 0.08 + (hb - 0.25) / 2), mb, 0.015),
           P.almofada(nome + "_colchao", (l, c, 0.25), (0, 0, hb - 0.125), mr, 0.05)]
    pec.append(P.almofada(nome + "_edredom", (l + 0.06, c * 0.62, 0.05), (0, -c * 0.19, hb + 0.02), mr, 0.025))
    mt = acab(o.get("travesseiro", "#f4f2ee"), "tecido")
    nt = 2 if l > 1.1 else 1
    for k in range(nt):
        x = 0 if nt == 1 else (-1 + 2 * k) * l / 4
        pec.append(P.almofada(nome + "_travesseiro", (l / nt - 0.1, 0.42, 0.12), (x, c / 2 - 0.3, hb + 0.06), mt,
                              0.05))
    if o.get("cabeceira", True):
        pec.append(P.almofada(nome + "_cabeceira", (l + 0.1, 0.08, 1.15), (0, c / 2 + 0.06, 0.575), mb, 0.02))
    return P.raiz(nome, pec)


def o_planta(o, nome):
    h = o.get("altura", 1.2)
    rv = o.get("raio_vaso", 0.16)
    mv = acab(o.get("vaso", "#d9d4cc"), "porcelanato")
    mf = P.material(nome + "_folhas", srgb(o.get("folhagem", "#3f6b35")), rough=0.6, spec=0.35)
    hv = min(0.45, h * 0.3)
    pec = [P.cilindro(nome + "_vaso", rv, hv, (0, 0, hv / 2), mv, raio2=rv * 1.15, verts=40),
           P.cilindro(nome + "_terra", rv * 1.1, 0.01, (0, 0, hv - 0.02), acab("#3a2a1e", "concreto"), verts=40)]
    rnd = random.Random(o.get("semente", 5))
    copa = o.get("raio", max(0.22, h * 0.28))
    for k in range(9):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=copa * rnd.uniform(0.45, 0.7))
        s = bpy.context.active_object
        s.name = nome + "_copa"
        s.location = (rnd.uniform(-copa, copa) * 0.6, rnd.uniform(-copa, copa) * 0.6,
                      hv + (h - hv) * rnd.uniform(0.35, 0.85))
        s.data.materials.append(mf)
        md = s.modifiers.new("relevo", "DISPLACE")
        tx = bpy.data.textures.new(nome + "_nuvem", "CLOUDS")
        tx.noise_scale = 0.12
        md.texture = tx
        md.strength = copa * 0.35
        for p in s.data.polygons:
            p.use_smooth = True
        pec.append(s)
    pec.append(P.cilindro_entre(nome + "_caule", (0, 0, hv - 0.02), (0, 0, hv + (h - hv) * 0.5), 0.012,
                                acab("#4a3a28", "madeira")))
    return P.raiz(nome, pec)


def o_luminaria(o, nome):
    tipo = o.get("estilo", "piso")
    mc = acab(o.get("acabamento", "#1e1e1e"), "metal")
    ma = P.material(nome + "_cupula", srgb(o.get("cupula", "#efe9df")), rough=0.8, spec=0.2,
                    emis=srgb(o.get("cor_luz", "#ffd9a8")), emis_forca=o.get("brilho_cupula", 1.5))
    h = o.get("altura", 1.55 if tipo == "piso" else 0.45)
    pec = []
    if tipo == "pendente":
        pec.append(P.cilindro_entre(nome + "_fio", (0, 0, 0), (0, 0, h), 0.002, mc))
        zc = 0.0
        pec.append(P.cilindro(nome + "_cupula", 0.16, 0.18, (0, 0, zc), ma, raio2=0.05, verts=48))
    else:
        rb = 0.14 if tipo == "piso" else 0.08
        pec.append(P.cilindro(nome + "_base", rb, 0.02, (0, 0, 0.01), mc, verts=40))
        pec.append(P.cilindro_entre(nome + "_haste", (0, 0, 0.02), (0, 0, h - 0.12), 0.01, mc))
        zc = h - 0.1
        r = 0.2 if tipo == "piso" else 0.12
        pec.append(P.cilindro(nome + "_cupula", r, r * 1.1, (0, 0, zc), ma, raio2=r * 0.7, verts=48))
    d = bpy.data.lights.new(nome + "_luz", "POINT")
    d.energy = o.get("forca", 40)
    d.color = srgb(o.get("cor_luz", "#ffd9a8"))
    d.shadow_soft_size = 0.08
    lz = bpy.data.objects.new(nome + "_luz", d)
    bpy.context.collection.objects.link(lz)
    lz.location = (0, 0, zc - 0.02)
    pec.append(lz)
    return P.raiz(nome, pec)


def o_painel_led(o, nome):
    larg, alt = o.get("tam", [0.19, 0.165])
    return P.painel_led(nome, larg=larg, alt=alt, forca=o.get("forca", 6.0), cor_luz=srgb(o.get("cor_luz", "#fff7eb")))


def o_quadro(o, nome):
    l, a = o.get("tam", [0.6, 0.8])
    mm = acab(o.get("moldura", "#1c1c1c"), "madeira" if o.get("moldura") == "madeira" else "plastico")
    img = caminho(o.get("imagem"))
    mi = mat_imagem(nome + "_arte", img, emissivo=False, cor_vazia=srgb(o.get("cor", "#d8d2c6")))
    mol = o.get("moldura_largura", 0.03)
    pec = [P.caixa(nome + "_moldura", (l, 0.03, a), (0, -0.015, a / 2), mm, bevel=0.002)]
    arte = plano_img(nome + "_arte", l - 2 * mol, a - 2 * mol, mi, y=-0.0305)
    arte.location.z = a / 2
    pec.append(arte)
    return P.raiz(nome, pec)


def o_tv(o, nome):
    l, a = o.get("tam", [1.23, 0.71])
    img = caminho(o.get("imagem"))
    mt = mat_imagem(nome + "_tela", img, emissivo=True, forca=o.get("brilho", 1.0))
    pec = [P.caixa(nome + "_casco", (l + 0.012, 0.045, a + 0.012), (0, -0.03, a / 2), acab("#111111"), bevel=0.003)]
    tela = plano_img(nome + "_tela", l, a, mt, y=-0.0526)
    tela.location.z = a / 2
    pec.append(tela)
    return P.raiz(nome, pec)


def o_prateleira(o, nome):
    l, p, esp = o.get("tam", [0.8, 0.22, 0.025])
    m = acab(o.get("acabamento", "madeira"), "madeira")
    pec = [P.caixa(nome + "_tabua", (l, p, esp), (0, -p / 2, esp / 2), m, bevel=0.002)]
    if o.get("suportes", True):
        ms = acab(o.get("suporte", "#1c1c1c"), "metal")
        for sx in (-1, 1):
            pec.append(P.caixa(nome + "_mao_francesa", (0.02, p * 0.8, 0.02), (sx * l * 0.35, -p * 0.4, -0.01), ms))
    return P.raiz(nome, pec)


def o_tapete(o, nome):
    l, p = o.get("tam", [2.0, 1.4])
    e = o.get("espessura", 0.012)
    return P.raiz(nome, [P.caixa(nome + "_corpo", (l, p, e), (0, 0, e / 2), acab(o.get("acabamento", "carpete"),
                                                                                    "carpete"), bevel=0.004)])


def o_cortina(o, nome):
    import bmesh
    l, a = o.get("tam", [1.6, 2.4])
    m = acab(o.get("acabamento", "#e8e1d4"), "tecido")
    ondas = max(4, int(l / 0.12))
    nx, nz = ondas * 6, 8
    bm = bmesh.new()
    g = [[bm.verts.new((-l / 2 + l * i / nx, -0.04 - 0.03 * math.sin(2 * math.pi * ondas * i / nx), a * j / nz))
          for i in range(nx + 1)] for j in range(nz + 1)]
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((g[j][i], g[j][i + 1], g[j + 1][i + 1], g[j + 1][i]))
    pano = P.objeto_bm(nome + "_pano", bm, m, normais=False)
    pano.modifiers.new("espessura", "SOLIDIFY").thickness = 0.004
    trilho = P.cilindro_entre(nome + "_trilho", (-l / 2 - 0.05, -0.05, a + 0.02), (l / 2 + 0.05, -0.05, a + 0.02),
                              0.01, acab("metal", "metal"))
    return P.raiz(nome, [pano, trilho])


TIPOS = {"caixa": o_caixa, "cilindro": o_cilindro, "mesa": o_mesa, "cadeira": o_cadeira, "monitor": o_monitor,
         "notebook": o_notebook, "teclado": o_teclado, "mouse": o_mouse, "estante": o_estante, "armario": o_armario,
         "sofa": o_sofa, "cama": o_cama, "planta": o_planta, "luminaria": o_luminaria, "painel_led": o_painel_led,
         "quadro": o_quadro, "tv": o_tv, "prateleira": o_prateleira, "tapete": o_tapete, "cortina": o_cortina}


def objetos(lista):
    vistos = {}
    for k, o in enumerate(lista):
        tipo = o.get("tipo")
        if tipo not in TIPOS:
            aviso(f"objeto {k}: tipo desconhecido '{tipo}' (tipos: {', '.join(sorted(TIPOS))}); virou caixa")
            tipo = "caixa"
        base = o.get("id") or tipo
        vistos[base] = vistos.get(base, 0) + 1
        nome = base if vistos[base] == 1 else f"{base}_{vistos[base]}"
        r = TIPOS[tipo](o, nome)
        pos = list(o.get("pos", [0, 0, 0])) + [0.0] * 3
        r.location = (pos[0], pos[1], pos[2])
        if "olha_para" in o:
            alvo = Vector((o["olha_para"][0], o["olha_para"][1], 0)) - Vector((pos[0], pos[1], 0))
            r.rotation_euler = (0, 0, giro(alvo.normalized()) if alvo.length > 1e-6 else 0)
        else:
            r.rotation_euler = (0, 0, math.radians(o.get("rot", 0)))
        r["cena_json"] = json.dumps(o, ensure_ascii=False)


# ------------------------------------------------------------------ luz, mundo, camera, render
def luz(nome, tipo, pos, alvo, energia, cor, tam=0.5, cone=60):
    d = bpy.data.lights.new(nome, tipo)
    d.energy = energia
    d.color = cor
    if tipo == "AREA":
        d.shape = "RECTANGLE"
        d.size, d.size_y = (tam, tam) if not isinstance(tam, (list, tuple)) else tam
    elif tipo == "SPOT":
        d.spot_size = math.radians(cone)
        d.spot_blend = 0.5
    o = bpy.data.objects.new(nome, d)
    o.location = pos
    bpy.context.collection.objects.link(o)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    return o


def iluminacao(c, a, defs, aberturas):
    L, Pr, H = a["largura"], a["profundidade"], a.get("pe_direito", 2.7)
    lista = c.get("luzes")
    if lista is None:
        lista = [{"tipo": "teto", "pos": [L / 2, Pr / 2]}]
    for k, lz in enumerate(lista):
        t = lz.get("tipo", "area")
        cor = srgb(lz.get("cor", "#fff1e0"))
        pos = list(lz.get("pos", [L / 2, Pr / 2, H - 0.05]))
        if t == "teto":
            z = H - 0.03
            tam = lz.get("tam", 0.5)
            luz(f"luz_teto_{k}", "AREA", (pos[0], pos[1], z), (pos[0], pos[1], 0), lz.get("forca", 180), cor, tam)
            m = P.material(f"plafon_{k}", (0.9, 0.9, 0.88), rough=0.6, emis=cor, emis_forca=lz.get("brilho", 4.0))
            tx, ty = (tam, tam) if not isinstance(tam, (list, tuple)) else tam
            P.caixa(f"plafon_{k}", (tx, ty, 0.02), (pos[0], pos[1], H - 0.01), m)
            reb = lz.get("rebate", 0.3)     # luz que volta do piso e das paredes: sem ela o teto fica preto no Eevee
            if reb:
                r = luz(f"luz_rebate_{k}", "AREA", (pos[0], pos[1], 0.35), (pos[0], pos[1], H),
                        lz.get("forca", 180) * reb, cor, min(L, Pr) * 0.8)
                r.data.use_shadow = False
                r.visible_camera = r.visible_glossy = False
        elif t == "sol":
            d = bpy.data.lights.new(f"sol_{k}", "SUN")
            d.energy = lz.get("forca", 3.0)
            d.color = cor
            d.angle = math.radians(1.5)
            o = bpy.data.objects.new(f"sol_{k}", d)
            bpy.context.collection.objects.link(o)
            az, el = math.radians(lz.get("azimute", 200)), math.radians(lz.get("elevacao", 35))
            dirv = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), -math.sin(el)))
            o.rotation_mode = "QUATERNION"
            o.rotation_quaternion = dirv.to_track_quat("-Z", "Y")
        else:
            tipo_b = {"area": "AREA", "ponto": "POINT", "spot": "SPOT"}.get(t, "AREA")
            luz(f"luz_{k}", tipo_b, pos, lz.get("alvo", [pos[0], pos[1], 0]), lz.get("forca", 100), cor,
                lz.get("tam", 0.5), lz.get("cone", 60))
    sol = c.get("sol", "auto")
    janelas = [ab for ab in aberturas if ab.get("tipo") == "janela"]
    if sol == "auto" and janelas and not any(lz.get("tipo") == "sol" for lz in lista):
        ab = janelas[0]
        n = defs[ab["parede"]][2]                       # normal pra dentro: o sol entra pela 1a janela
        el = math.radians(35)
        dirv = Vector((n.x * math.cos(el), n.y * math.cos(el), -math.sin(el)))
        d = bpy.data.lights.new("sol_janela", "SUN")
        d.energy = 2.5
        d.color = srgb("#fff3e0")
        d.angle = math.radians(1.5)
        o = bpy.data.objects.new("sol_janela", d)
        bpy.context.collection.objects.link(o)
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = dirv.to_track_quat("-Z", "Y")
    mundo = bpy.data.worlds.new("mundo")
    P.liga_nos(mundo)
    bg = mundo.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb(c.get("mundo", {}).get("cor", "#2a2e33")), 1)
    bg.inputs["Strength"].default_value = c.get("mundo", {}).get("forca", 0.6)
    bpy.context.scene.world = mundo


def camera_e_render(c):
    cena = bpy.context.scene
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 24
    cam_d.sensor_fit = "AUTO"
    cam_d.sensor_width = 36
    cam_d.clip_start = 0.02
    cam = bpy.data.objects.new("CAM", cam_d)
    bpy.context.collection.objects.link(cam)
    alvo = bpy.data.objects.new("ALVO", None)
    alvo.empty_display_size = 0.05
    bpy.context.collection.objects.link(alvo)
    t = cam.constraints.new("TRACK_TO")
    t.target = alvo
    t.track_axis = "TRACK_NEGATIVE_Z"
    t.up_axis = "UP_Y"
    cena.camera = cam
    vistas = c.get("vistas") or {}
    if not vistas:
        a = c["ambiente"]
        vistas = {"porta": {"cam": [a["largura"] * 0.5, 0.25, 1.55],
                            "alvo": [a["largura"] * 0.5, a["profundidade"], 1.0], "lente": 18}}
        aviso("cena sem vistas: criei a vista 'porta' (da parede da frente olhando o fundo)")
    cena["vistas"] = json.dumps(vistas, ensure_ascii=False)
    cena["pasta"] = PASTA
    v = next(iter(vistas.values()))
    cam.location, alvo.location, cam_d.lens = v["cam"], v["alvo"], v.get("lente", 24)
    try:
        cena.render.engine = "BLENDER_EEVEE"
    except TypeError:
        cena.render.engine = "BLENDER_EEVEE_NEXT"
    ee = cena.eevee
    for k, val in (("use_raytracing", True), ("taa_render_samples", 32), ("use_shadows", True),
                   ("shadow_ray_count", 2), ("shadow_step_count", 8), ("use_fast_gi", True)):
        if hasattr(ee, k):
            setattr(ee, k, val)
    cena.render.resolution_x, cena.render.resolution_y = 1080, 1350
    cena.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            cena.view_settings.look = look
            break
        except TypeError:
            pass
    cena.view_settings.exposure = c.get("exposicao", 0.0)
    cena.unit_settings.system = "METRIC"


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    a = CENA["ambiente"]
    aberturas = CENA.get("aberturas", [])
    for k, ab in enumerate(aberturas):
        ab.setdefault("id", f"{ab.get('tipo', 'vao')}_{k}")
    defs = ambiente(a, aberturas)
    objetos(CENA.get("objetos", []))
    iluminacao(CENA, a, defs, aberturas)
    camera_e_render(CENA)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=SAIDA)
    n = sum(1 for o in bpy.data.objects if o.type == "MESH")
    print(f"MONTADO {SAIDA}: {len(CENA.get('objetos', []))} objetos do cena.json, {n} malhas, "
          f"{len(AVISOS)} aviso(s)", flush=True)


main()
