# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Pecas detalhadas (Blender 4.2+): mouse, teclado, painel de LED, cadeira, bloco espiral e lapis.

Cada funcao monta a peca em coordenadas locais (x = largura, y = profundidade, pra longe de quem senta; z = altura,
base em z = 0) e devolve a raiz (empty) pra quem chama posicionar e girar. Medidas reais em metros, desenho proprio:
sem asset de terceiro e sem logo de marca. Forma organica (mouse, almofada) = gaiola + subdivisao congelada na malha;
detalhe colado na superficie (vinco, fenda da roda) = decalque projetado por raio, nunca chutado na conta.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import teclado_layout as TL  # noqa: E402


# ------------------------------------------------------------------ base
def liga_nos(x):
    """Material/mundo com nos. Ate o Blender 4.x precisa de use_nodes = True; no 5.x os nos ja vem ligados e o
    use_nodes avisa que sai no 6.0 (la vira erro). Por isso so liga quando a versao pede."""
    if bpy.app.version < (5, 0, 0):
        x.use_nodes = True
    return x


def material(nome, cor, rough=0.5, metal=0.0, spec=0.5, coat=0.0, emis=None, emis_forca=0.0, relevo=0.0,
             relevo_escala=300.0):
    """Principled com relevo de ruido opcional (plastico emborrachado, tecido)."""
    m = bpy.data.materials.new(nome)
    liga_nos(m)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*cor, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    if emis:
        b.inputs["Emission Color"].default_value = (*emis, 1)
        b.inputs["Emission Strength"].default_value = emis_forca
    if relevo:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = relevo_escala
        nz.inputs["Detail"].default_value = 4.0
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = relevo
        bp.inputs["Distance"].default_value = 0.0004
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def objeto_bm(nome, bm, material=None, suave=True, normais=True):
    if normais:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(nome, me)
    bpy.context.collection.objects.link(o)
    if material:
        me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = suave
    return o


def congela(o):
    """Aplica os modificadores na malha (sem operador): a peca fica com a forma final pra raio e decalque."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    velho = o.data
    o.modifiers.clear()
    o.data = me
    if velho.users == 0:
        bpy.data.meshes.remove(velho)
    return o


def bisel(o, largura, segmentos=3, angulo=30, limite="ANGLE"):
    md = o.modifiers.new("bisel", "BEVEL")
    md.width = largura
    md.segments = segmentos
    md.limit_method = limite
    if limite == "ANGLE":
        md.angle_limit = math.radians(angulo)
    return md


def subdivide(o, n=2):
    md = o.modifiers.new("subdiv", "SUBSURF")
    md.levels = md.render_levels = n
    return md


def caixa(nome, tam, pos, material=None, bevel=0.0, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=tam, verts=bm.verts)
    o = objeto_bm(nome, bm, material, suave=bool(bevel))
    o.location, o.rotation_euler = pos, rot
    if bevel:
        bisel(o, bevel)
    return o


def cilindro(nome, raio, alt, pos, material=None, rot=(0, 0, 0), verts=32, raio2=None, suave=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=raio, radius2=raio if raio2 is None else raio2,
                          depth=alt)
    o = objeto_bm(nome, bm, material, suave=suave)
    o.location, o.rotation_euler = pos, rot
    return o


def cilindro_entre(nome, p1, p2, raio, material=None, verts=16, raio2=None):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    o = cilindro(nome, raio, d.length, (p1 + p2) / 2, material, verts=verts, raio2=raio2)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")       # cone: raio na ponta p1, raio2 na p2
    return o


def raiz(nome, pecas):
    r = bpy.data.objects.new(nome, None)
    r.empty_display_size = 0.05
    bpy.context.collection.objects.link(r)
    for o in pecas:
        o.parent = r
    return r


def caixas_de_colisao(cena):
    """Caixas pra saber se a camera esta DENTRO de algo. 1 por movel do cena.json: a raiz com TODAS as pecas, no espaco
    dela (segue a rotacao), senao a camera passando entre o tampo e os pes da mesa, ou entre as prateleiras, nao conta.
    Mais 1 por malha pequena solta (< 6 m3, fora de movel). Devolve [(nome, inversa do mundo, lo, hi)]."""
    out = []
    for r in cena.objects:
        if "cena_json" not in r.keys():
            continue
        inv = r.matrix_world.inverted()
        cs = [inv @ (ch.matrix_world @ Vector(c)) for ch in r.children_recursive if ch.type == "MESH"
              for c in ch.bound_box]
        if cs:
            out.append((r.name, inv, Vector([min(c[i] for c in cs) for i in range(3)]),
                        Vector([max(c[i] for c in cs) for i in range(3)])))
    for ob in cena.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        p = ob.parent
        while p is not None and "cena_json" not in p.keys():
            p = p.parent
        if p is not None:
            continue
        cs = [Vector(c) for c in ob.bound_box]
        lo = Vector([min(c[i] for c in cs) for i in range(3)])
        hi = Vector([max(c[i] for c in cs) for i in range(3)])
        d = hi - lo
        if 0 < d.x * d.y * d.z * abs(ob.matrix_world.to_3x3().determinant()) < 6:
            out.append((ob.name, ob.matrix_world.inverted(), lo, hi))
    return out


def dentro(caixas, ponto):
    """Nomes das caixas que contem o ponto (mundo)."""
    return [n for n, inv, lo, hi in caixas if all(lo[i] < (inv @ ponto)[i] < hi[i] for i in range(3))]


def acerta(o, origem, direcao, dist=2.0):
    """Raio contra a malha (espaco do objeto). Devolve (ponto, normal) ou (None, None)."""
    ok, loc, nor, _ = o.ray_cast(Vector(origem), Vector(direcao).normalized(), distance=dist)
    return (loc, nor) if ok else (None, None)


def _no_contorno(u, v, curva):
    """Leva o ponto (u, v) do quadrado [-1, 1]^2 pra superelipse |u|^curva + |v|^curva = 1 (2 = elipse, 4 = retangulo de
    cantos redondos). Sem curva, devolve o proprio quadrado."""
    if not curva or (u == 0 and v == 0):
        return u, v
    f = max(abs(u), abs(v))
    d = math.hypot(u, v)
    dx, dy = u / d, v / d
    s = (abs(dx) ** curva + abs(dy) ** curva) ** (-1 / curva)
    return f * s * dx, f * s * dy


def retalho(nome, alvo, centro, eu, ev, ru, rv, material, nu=12, nv=12, folga=0.00025, curva=None, alcance=0.5):
    """Retalho fino colado na superficie do alvo em qualquer direcao: grade (2ru x 2rv) no plano eu x ev em volta do
    centro, projetada por raio contra a malha (espaco do objeto). eu x ev aponta pra FORA da superficie."""
    bpy.context.view_layer.update()
    eu, ev = Vector(eu).normalized(), Vector(ev).normalized()
    fora = eu.cross(ev).normalized()
    c = Vector(centro)
    bm = bmesh.new()
    grade = []
    for j in range(nv + 1):
        linha = []
        for i in range(nu + 1):
            u, v = _no_contorno(-1 + 2 * i / nu, -1 + 2 * j / nv, curva)
            q = c + eu * (u * ru) + ev * (v * rv)
            loc, nor = acerta(alvo, q + fora * alcance, -fora, alcance * 2)
            linha.append(bm.verts.new(loc + nor * folga) if loc is not None else None)
        grade.append(linha)
    for j in range(nv):
        for i in range(nu):
            f = (grade[j][i], grade[j][i + 1], grade[j + 1][i + 1], grade[j + 1][i])
            if all(f):
                bm.faces.new(f)
    return objeto_bm(nome, bm, material, normais=False)


def decalque(nome, alvo, cx, cy, rx, ry, material, nx=12, ny=12, folga=0.00025, elipse=False, z0=0.5):
    """Retalho visto de cima (projetado de z0 pra baixo). elipse=True leva o quadrado pro disco (contorno liso)."""
    return retalho(nome, alvo, (cx, cy, 0.0), (1, 0, 0), (0, 1, 0), rx, ry, material, nx, ny, folga,
                   2 if elipse else None, alcance=z0)


def retalho_tangente(nome, alvo, ponto, normal, ru, rv, material, nu=12, nv=8, folga=0.00025, curva=4):
    """Retalho deitado na superficie num ponto de lado: rv ao longo do comprimento (y), ru na outra direcao."""
    ev = Vector((0, 1, 0)) - normal * normal.y          # comprimento projetado no plano tangente
    ev.normalize()
    eu = ev.cross(normal)                               # eu x ev = normal
    return retalho(nome, alvo, ponto, eu, ev, ru, rv, material, nu, nv, folga, curva, alcance=0.02)


def normaliza_medidas(o, larg, comp, alt):
    """Escala a malha pras medidas reais (bbox) e poe a base em z = 0, centrada em x e y."""
    vs = [v.co for v in o.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    c = (mn + mx) / 2
    s = Matrix.Diagonal((larg / (mx.x - mn.x), comp / (mx.y - mn.y), alt / (mx.z - mn.z), 1.0))
    o.data.transform(s @ Matrix.Translation((-c.x, -c.y, -mn.z)))
    o.data.update()


def roda_serrilhada(nome, raio, larg, dentes, fundo, material):
    """Roda com eixo em X e serrilha (dentes alternando raio cheio e raio*fundo)."""
    bm = bmesh.new()
    n = dentes * 2
    aneis = []
    for s in (-0.5, 0.5):
        aneis.append([bm.verts.new((s * larg, (raio if k % 2 == 0 else raio * fundo) * math.cos(2 * math.pi * k / n),
                                    (raio if k % 2 == 0 else raio * fundo) * math.sin(2 * math.pi * k / n)))
                      for k in range(n)])
    for k in range(n):
        bm.faces.new((aneis[0][k], aneis[0][(k + 1) % n], aneis[1][(k + 1) % n], aneis[1][k]))
    bm.faces.new(aneis[0])
    bm.faces.new(aneis[1])
    o = objeto_bm(nome, bm, material, suave=False)
    bisel(o, raio * 0.04, 1, 50)
    return o


# ------------------------------------------------------------------ mouse ergonomico de mao direita (com asa do polegar)
MOUSE = (0.0843, 0.1249, 0.051)     # largura (com o apoio do polegar), comprimento, altura

# corte do corpo (u na largura, w na altura), da base no meio dando a volta pela esquerda: sem asa e com a asa do polegar
# (aba fina que sai embaixo, prateleira onde o polegar deita, concha e o lado da roda do polegar). A direita e igual.
_CORTE_SEM_ASA = [(-0.75, 0.0), (-0.90, 0.05), (-0.97, 0.13), (-0.995, 0.22), (-1.0, 0.33), (-0.99, 0.52),
                  (-0.86, 0.80), (-0.45, 0.98), (0.05, 0.97), (0.45, 0.85), (0.80, 0.64), (0.98, 0.36), (0.99, 0.10),
                  (0.78, 0.0), (0.0, 0.0)]
_CORTE_ASA = [(-1.50, 0.0), (-1.68, 0.07), (-1.67, 0.17), (-1.28, 0.25), (-0.97, 0.33), (-1.03, 0.53),
              (-0.86, 0.80), (-0.45, 0.98), (0.05, 0.97), (0.45, 0.85), (0.80, 0.64), (0.98, 0.36), (0.99, 0.10),
              (0.78, 0.0), (0.0, 0.0)]
# estacoes de tras (v=0) pra frente (v=1): largura e altura relativas e quanto da asa aparece. Topo alto atras do meio,
# frente dos botoes mais baixa; a asa vai de ~1/5 a ~4/5 do comprimento.
_ESTACOES = [(0.00, 0.40, 0.38, 0.0), (0.06, 0.74, 0.66, 0.05), (0.18, 0.93, 0.90, 0.45), (0.33, 1.0, 1.0, 0.95),
             (0.48, 1.0, 0.98, 1.0), (0.62, 0.98, 0.88, 0.8), (0.76, 0.94, 0.74, 0.35), (0.90, 0.88, 0.60, 0.0),
             (1.00, 0.74, 0.52, 0.0)]


def _mat_corpo_mouse(nome, cor):
    """Plastico grafite fosco com a emenda escura da base (linha a ~3,5 mm da mesa) e a base um tom abaixo: por
    altura no shader, sem trocar material por face (o que deixava degrau na malha)."""
    m = material(nome, cor, rough=0.68, spec=0.25, relevo=0.04)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.interpolation = "CONSTANT"
    el = cr.color_ramp.elements
    el[0].position, el[0].color = 0.0, (*(c * 0.7 for c in cor), 1)
    el[1].position, el[1].color = 0.0041, (*cor, 1)
    el.new(0.0033).color = (0.002, 0.002, 0.0022, 1)
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m


def mouse(nome="mouse", cor=(0.011, 0.011, 0.012)):
    """Mouse ergonomico de mao direita: asa do polegar (aba larga embaixo, prateleira e concha), topo alto atras do meio
    descendo pra direita, roda de aco escuro serrilhada, roda do polegar e 2 botoes laterais colados na superficie,
    vinco entre os botoes e emenda da base. Frente = +y."""
    L, Wt, H = MOUSE
    m_corpo = _mat_corpo_mouse(nome + "_corpo", cor)
    m_vinco = material(nome + "_vinco", (0.002, 0.002, 0.0022), rough=0.8, spec=0.1)
    m_aco = material(nome + "_aco", (0.16, 0.16, 0.17), rough=0.32, metal=1.0)
    m_borracha = material(nome + "_borracha", (0.008, 0.008, 0.009), rough=0.6)
    m_botao = material(nome + "_botao", tuple(c * 1.25 for c in cor), rough=0.5, spec=0.35)

    def corte(asa):
        return [(a[0] + (b[0] - a[0]) * asa, a[1] + (b[1] - a[1]) * asa) for a, b in zip(_CORTE_SEM_ASA, _CORTE_ASA)]
    wc = 0.0318
    bm = bmesh.new()
    aneis = []
    for v, kw, kh, asa in _ESTACOES:
        aneis.append([bm.verts.new((u * kw * wc, (v - 0.5) * L, w * kh * H)) for u, w in corte(asa)])
    n = len(aneis[0])
    for a, b in zip(aneis, aneis[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bm.faces.new(aneis[0])
    bm.faces.new(aneis[-1])
    corpo = objeto_bm(nome + "_corpo", bm, m_corpo)
    subdivide(corpo, 3)
    congela(corpo)
    normaliza_medidas(corpo, Wt, L, H)
    if not corpo.data.materials:
        corpo.data.materials.append(m_corpo)
    bpy.context.view_layer.update()
    pecas = [corpo]

    # roda principal (aco serrilhado) saindo ~3,5 mm da fenda, um pouco a esquerda do meio
    xw, yw = -0.004, 0.031
    topo, _ = acerta(corpo, (xw, yw, 0.5), (0, 0, -1))
    R = 0.0105
    roda = roda_serrilhada(nome + "_roda", R, 0.0068, 30, 0.93, m_aco)
    roda.location = (xw, yw, topo.z + 0.0035 - R)
    pecas.append(roda)
    pecas.append(decalque(nome + "_fenda", corpo, xw, yw, 0.0047, 0.0135, m_vinco, 10, 16, elipse=True))
    # vinco entre os 2 botoes (da roda ate a frente) e a emenda de tras dos botoes
    pecas.append(decalque(nome + "_vinco", corpo, xw, (yw + 0.0135 + L / 2) / 2, 0.0005, (L / 2 - yw - 0.0135) / 2,
                          m_vinco, 1, 24))
    pecas.append(decalque(nome + "_emenda", corpo, 0.0, yw - 0.026, 0.030, 0.0004, m_vinco, 28, 1))
    pecas.append(decalque(nome + "_modo", corpo, xw, yw - 0.0175, 0.0035, 0.0028, m_botao, 6, 6, folga=0.0004,
                          elipse=True))

    # roda do polegar (eixo na superficie lateral, perpendicular ao rolar) e, atras dela, os 2 botoes laterais:
    # retalho escuro (a fresta) e o botao por cima, os dois colados na curva do lado
    y_tw, z_tw = 0.006, 0.027
    lado, nor = acerta(corpo, (-0.3, y_tw, z_tw), (1, 0, 0), 1.0)
    if lado is not None:
        eixo = nor.cross(Vector((0, 1, 0))).normalized()
        Rp = 0.0092
        rp = roda_serrilhada(nome + "_roda_polegar", Rp, 0.0055, 26, 0.9, m_borracha)
        rp.rotation_mode = "QUATERNION"
        rp.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(eixo)
        rp.location = lado - nor * (Rp - 0.0028)
        pecas.append(rp)
        pecas.append(retalho_tangente(nome + "_roda_polegar_fenda", corpo, lado, nor, 0.0042, 0.0105, m_vinco,
                                      10, 16, folga=0.0002))
        for k, dy in enumerate((-0.0150, -0.0275)):
            p, nb = acerta(corpo, (-0.3, y_tw + dy, z_tw - 0.004), (1, 0, 0), 1.0)
            if p is None:
                continue
            pecas.append(retalho_tangente(f"{nome}_lateral_fresta_{k}", corpo, p, nb, 0.0029, 0.0062, m_vinco,
                                          8, 12, folga=0.0002))
            pecas.append(retalho_tangente(f"{nome}_lateral_{k}", corpo, p, nb, 0.0023, 0.0056, m_botao,
                                          8, 12, folga=0.0006))
    return raiz(nome.upper(), pecas)


# ------------------------------------------------------------------ teclado full-size baixo
def _tecla_malha(nome, a, b, alt=0.0042, prato=0.00045, saia=0.0006):
    """Tecla baixa com prato concavo: topo a x b, saia um pouco maior na base, sem fundo (nao aparece)."""
    nx, ny = max(4, round(a / 0.0035)), max(4, round(b / 0.0035))
    bm = bmesh.new()
    top = [[bm.verts.new(((-1 + 2 * i / nx) * a / 2, (-1 + 2 * j / ny) * b / 2,
                          alt - prato * (1 - (-1 + 2 * i / nx) ** 2) * (1 - (-1 + 2 * j / ny) ** 2)))
            for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]))
    borda = ([top[0][i] for i in range(nx)] + [top[j][nx] for j in range(ny)] +
             [top[ny][i] for i in range(nx, 0, -1)] + [top[j][0] for j in range(ny, 0, -1)])
    sx, sy = (a / 2 + saia) / (a / 2), (b / 2 + saia) / (b / 2)
    base = [bm.verts.new((v.co.x * sx, v.co.y * sy, 0.0)) for v in borda]
    k = len(borda)
    for i in range(k):
        bm.faces.new((borda[i], base[i], base[(i + 1) % k], borda[(i + 1) % k]))
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def mat_teclas(nome, legendas, dono, cor=(0.012, 0.012, 0.014)):
    """Tecla fosca com a legenda branca projetada de cima nas coordenadas do objeto TECLADO (imagem = corpo inteiro)."""
    m = material(nome, cor, rough=0.58, spec=0.28)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    if not (legendas and os.path.exists(legendas)):
        return m
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.object = dono
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / TL.W, 1 / TL.D, 1.0)
    mp.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(legendas, check_existing=True)
    tx.extension = "CLIP"
    tx.interpolation = "Cubic"
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (*cor, 1)
    mx.inputs["B"].default_value = (0.62, 0.62, 0.6, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Alpha"], mx.inputs["Factor"])
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    return m


def teclado(nome="teclado", legendas=None, cor_corpo=(0.022, 0.022, 0.025)):
    """Teclado full-size baixo (430 x 132 x 20,5 mm) em cunha: corpo de cantos arredondados, 109 teclas com prato
    concavo e legenda branca (textura do gera_tex_teclado.py). Frente (quem digita) = -y."""
    W, D = TL.W, TL.D
    hf, hb = 0.0075, 0.0160                   # altura do corpo na frente e no fundo (teclas somam ~4,5 mm)
    inclina = math.atan((hb - hf) / D)
    r = raiz(nome.upper(), [])                # a raiz existe antes do material (as legendas usam as coordenadas dela)
    m_corpo = material(nome + "_corpo", cor_corpo, rough=0.42, spec=0.4, relevo=0.01, relevo_escala=600)
    m_tecla = mat_teclas(nome + "_teclas", legendas, r)
    # corpo: retangulo de cantos arredondados extrudado, topo em rampa
    rc, seg = 0.009, 6
    cont = []
    for cxs, cys, a0 in ((W / 2 - rc, -D / 2 + rc, -90), (W / 2 - rc, D / 2 - rc, 0), (-W / 2 + rc, D / 2 - rc, 90),
                         (-W / 2 + rc, -D / 2 + rc, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            cont.append((cxs + rc * math.cos(a), cys + rc * math.sin(a)))
    bm = bmesh.new()
    baixo = [bm.verts.new((x, y, 0.0)) for x, y in cont]
    cima = [bm.verts.new((x, y, hf + (hb - hf) * (y + D / 2) / D)) for x, y in cont]
    n = len(cont)
    for i in range(n):
        bm.faces.new((baixo[i], baixo[(i + 1) % n], cima[(i + 1) % n], cima[i]))
    bm.faces.new(cima)
    bm.faces.new(list(reversed(baixo)))
    corpo = objeto_bm(nome + "_corpo", bm, m_corpo)
    bisel(corpo, 0.0022, 3, 30)
    corpo.modifiers.new("normais", "WEIGHTED_NORMAL").keep_sharp = True
    corpo.parent = r
    malhas = {}
    for rot, cx, cy, a, b, _ in TL.retangulos():
        chave = (round(a, 5), round(b, 5))
        if chave not in malhas:
            malhas[chave] = _tecla_malha(f"{nome}_tecla_{len(malhas)}", a, b)
            malhas[chave].materials.append(m_tecla)
        o = bpy.data.objects.new(f"{nome}_t_{rot or 'espaco'}", malhas[chave])
        bpy.context.collection.objects.link(o)
        o.location = (cx, cy, hf + (hb - hf) * (cy + D / 2) / D + 0.0004)
        o.rotation_euler = (inclina, 0, 0)
        bisel(o, 0.0007, 2, 40)
        o.parent = r
    return r


# ------------------------------------------------------------------ painel de LED (escudo arredondado em haste)
def painel_led(nome, larg=0.19, alt=0.165, prof=0.024, forca=6.0, cor_luz=(1.0, 0.97, 0.92)):
    """Painel de LED de mesa: contorno de escudo (quadrado bem arredondado, base mais estreita), difusor branco que
    acende, casco preto com borda fina e uma rotula atras. Face acesa virada pra -y local."""
    m_casco = material(nome + "_casco", (0.012, 0.012, 0.013), rough=0.45, spec=0.45)
    m_dif = material(nome + "_difusor", (0.9, 0.9, 0.88), rough=0.6, emis=cor_luz, emis_forca=forca)

    def contorno(enc=1.0, nseg=72):
        pts = []
        for k in range(nseg):
            t = 2 * math.pi * k / nseg
            c, s = math.cos(t), math.sin(t)
            x = math.copysign(abs(c) ** (2 / 4.2), c)
            z = math.copysign(abs(s) ** (2 / 4.2), s)
            afina = 1 - 0.2 * ((1 - z) / 2) ** 1.6
            pts.append((x * larg / 2 * afina * enc, z * alt / 2 * enc))
        return pts
    bm = bmesh.new()
    frente = [bm.verts.new((x, 0.0, z)) for x, z in contorno()]
    dentro = [bm.verts.new((x, 0.0, z)) for x, z in contorno(0.94)]
    tras = [bm.verts.new((x, prof, z)) for x, z in contorno(0.86)]
    n = len(frente)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((frente[i], frente[j], tras[j], tras[i]))
        bm.faces.new((dentro[i], dentro[j], frente[j], frente[i]))
    bm.faces.new(list(reversed(tras)))
    casco = objeto_bm(nome + "_casco", bm, m_casco)
    bisel(casco, 0.0025, 3, 25)
    bm = bmesh.new()
    meio = bm.verts.new((0.0, -0.0012, 0.0))
    borda = [bm.verts.new((x, -0.0012 * (1 - (x / larg * 2) ** 2), z)) for x, z in contorno(0.945)]
    for i in range(len(borda)):
        bm.faces.new((meio, borda[i], borda[(i + 1) % len(borda)]))      # normal pra -y (a face acesa)
    dif = objeto_bm(nome + "_difusor", bm, m_dif, normais=False)
    rotula = cilindro(nome + "_rotula", 0.011, 0.03, (0, prof + 0.012, -0.01), m_casco, rot=(math.radians(90), 0, 0))
    return raiz(nome, [casco, dif, rotula])


# ------------------------------------------------------------------ cadeira de escritorio generica
def _curva_encosto(o, raio):
    """Encurva a malha em volta de quem senta (as pontas em x vao pra +y)."""
    for v in o.data.vertices:
        a = v.co.x / raio
        v.co.x, v.co.y = raio * math.sin(a), v.co.y + raio * (1 - math.cos(a))
    o.data.update()


def almofada(nome, tam, pos, material, raio, rot=(0, 0, 0), sub=1):
    o = caixa(nome, tam, pos, material, rot=rot)
    bisel(o, raio, 4, limite="NONE")
    if sub:
        subdivide(o, sub)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def placa_arco(nome, larg, alt, arco, esp, material, nseg=24):
    """Placa de topo em arco (concha traseira do encosto), no plano XZ, espessura em +y; base em z = 0."""
    pts = [(-larg / 2, 0.0), (larg / 2, 0.0)]
    for k in range(nseg + 1):
        x = larg / 2 - larg * k / nseg
        pts.append((x, alt + arco * math.sqrt(max(0.0, 1 - (2 * x / larg) ** 2))))
    bm = bmesh.new()
    f = [bm.verts.new((x, 0.0, z)) for x, z in pts]
    t = [bm.verts.new((x, esp, z)) for x, z in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], f[j], t[j], t[i]))
    bm.faces.new(f)
    bm.faces.new(list(reversed(t)))
    o = objeto_bm(nome, bm, material)
    bisel(o, min(esp * 0.45, 0.006), 3, 30)
    return o


def cadeira(nome="cadeira", tecido=(0.085, 0.083, 0.08), concha=(0.2, 0.19, 0.175), base=(0.012, 0.012, 0.013)):
    """Cadeira de escritorio: base estrela de 5 pes com rodizio duplo, pistao, assento e encosto estofados (encosto
    curvo com concha clara atras e espinha vertical com botao), bracos em T. Frente (pra mesa) = +y."""
    m_tec = material(nome + "_tecido", tecido, rough=0.9, spec=0.2, relevo=0.25, relevo_escala=2500)
    m_con = material(nome + "_concha", concha, rough=0.55, spec=0.35)
    m_esp = material(nome + "_espinha", tuple(c * 1.15 for c in concha), rough=0.5, spec=0.35)
    m_base = material(nome + "_base", base, rough=0.4, spec=0.5)
    m_metal = material(nome + "_metal", (0.05, 0.05, 0.055), rough=0.3, metal=0.9)
    m_apoio = material(nome + "_apoio", (0.03, 0.03, 0.032), rough=0.7, spec=0.3)
    pecas = []
    # base: cubo central + 5 pes afinando + rodizio duplo
    pecas.append(cilindro(nome + "_cubo", 0.05, 0.055, (0, 0, 0.115), m_base, verts=24))
    for k in range(5):
        a = math.radians(90 + 72 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        lat = Vector((-d.y, d.x, 0))
        bm = bmesh.new()
        secs = []
        for t, w, h, z in ((0.03, 0.05, 0.045, 0.118), (0.33, 0.032, 0.024, 0.07)):
            c = d * t
            secs.append([bm.verts.new(c + lat * sx * w / 2 + Vector((0, 0, z + sz * h / 2)))
                         for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((secs[0][i], secs[0][j], secs[1][j], secs[1][i]))
        bm.faces.new(secs[0])
        bm.faces.new(list(reversed(secs[1])))
        pe = objeto_bm(f"{nome}_pe_{k}", bm, m_base)
        bisel(pe, 0.008, 3, 30)
        pecas.append(pe)
        ponta = d * 0.315
        giro = a + math.radians(random.Random(k).uniform(-40, 40))
        capo = caixa(f"{nome}_capo_{k}", (0.032, 0.05, 0.026), ponta + Vector((0, 0, 0.05)), m_base, bevel=0.009,
                     rot=(0, 0, giro))
        pecas.append(capo)
        for s in (-1, 1):
            off = Vector((math.cos(giro), math.sin(giro), 0)) * s * 0.011
            pecas.append(cilindro(f"{nome}_roda_{k}_{s}", 0.025, 0.012, ponta + off + Vector((0, 0, 0.025)), m_base,
                                  rot=(0, math.radians(90), giro), verts=24))
    pecas.append(cilindro(nome + "_capa_pistao", 0.036, 0.16, (0, 0, 0.21), m_base, raio2=0.03, verts=24))
    pecas.append(cilindro(nome + "_pistao", 0.024, 0.12, (0, 0, 0.33), m_metal, verts=24))
    pecas.append(caixa(nome + "_mecanismo", (0.2, 0.26, 0.055), (0, 0.0, 0.405), m_base, bevel=0.01))
    # assento
    pecas.append(caixa(nome + "_bandeja", (0.46, 0.44, 0.02), (0, 0.01, 0.44), m_con, bevel=0.008))
    pecas.append(almofada(nome + "_assento", (0.5, 0.48, 0.075), (0, 0.02, 0.485), m_tec, 0.032))
    # encosto: almofada curva, concha clara atras (topo em arco), espinha vertical com botao
    enc = almofada(nome + "_encosto", (0.45, 0.055, 0.5), (0, 0, 0), m_tec, 0.026)
    congela(enc)
    _curva_encosto(enc, 0.55)
    enc.location, enc.rotation_euler = (0, -0.235, 0.81), (math.radians(8), 0, 0)
    con = placa_arco(nome + "_concha", 0.44, 0.24, 0.075, 0.018, m_con)
    congela(con)
    _curva_encosto(con, 0.55)
    con.location, con.rotation_euler = (0, -0.285, 0.555), (math.radians(8), 0, 0)
    esp = caixa(nome + "_espinha", (0.105, 0.03, 0.38), (0, -0.305, 0.6), m_esp, bevel=0.014,
                rot=(math.radians(8), 0, 0))
    botao = cilindro(nome + "_botao", 0.019, 0.014, (0.036, -0.322, 0.47), m_con, rot=(math.radians(98), 0, 0))
    pecas += [enc, con, esp, botao]
    # bracos em T: haste clara saindo de baixo do assento, apoio escuro em cima
    for sx in (-1, 1):
        pecas.append(cilindro_entre(f"{nome}_braco_base_{sx}", (sx * 0.1, -0.05, 0.42), (sx * 0.235, -0.05, 0.43),
                                    0.016, m_con))
        pecas.append(cilindro_entre(f"{nome}_braco_haste_{sx}", (sx * 0.235, -0.05, 0.42), (sx * 0.255, -0.03, 0.635),
                                    0.017, m_con))
        pecas.append(almofada(f"{nome}_braco_apoio_{sx}", (0.075, 0.25, 0.03), (sx * 0.255, 0.0, 0.655), m_apoio,
                              0.012))
    return raiz(nome.upper(), pecas)


# ------------------------------------------------------------------ bloco espiral
def mat_borda_papel(nome):
    """Lateral da pilha de folhas: listras finas horizontais (uma por folha) entre branco e cinza."""
    m = material(nome, (0.8, 0.78, 0.74), rough=0.9, spec=0.1)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 2600.0
    wv.inputs["Distortion"].default_value = 3.0
    wv.inputs["Detail"].default_value = 2.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.5, 0.48, 0.45, 1)
    cr.color_ramp.elements[1].color = (0.84, 0.82, 0.77, 1)
    cr.color_ramp.elements[0].position = 0.15
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m


def bloco_espiral(nome, m_pagina, pag_w, pag_h, zp, furos_x, furo_y, m_capa, m_espiral):
    """Bloco deitado: capa dura, pilha de folhas com a lateral listrada, 3 folhas soltas um pouco fora do esquadro, a
    pagina de cima (m_pagina, com a escrita) e espiral dupla nos furos. Devolve as pecas (quem chama faz a raiz)."""
    m_borda = mat_borda_papel(nome + "_borda")
    m_folha = material(nome + "_folha", (0.84, 0.82, 0.77), rough=0.9, spec=0.1)
    pecas = [caixa(nome + "_capa", (pag_w + 0.014, pag_h + 0.026, 0.004), (0, 0.006, 0.002), m_capa, bevel=0.0015),
             caixa(nome + "_folhas", (pag_w + 0.001, pag_h + 0.001, 0.009), (0, 0, 0.0085), m_borda, bevel=0.0006)]
    rnd = random.Random(7)
    for k in range(3):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bmesh.ops.scale(bm, vec=(pag_w, pag_h, 1), verts=bm.verts)
        f = objeto_bm(f"{nome}_solta_{k}", bm, m_folha, normais=False)
        f.location = (rnd.uniform(-0.0009, 0.0009), rnd.uniform(-0.0012, 0.0004), 0.01305 + 0.00004 * k)
        f.rotation_euler = (0, 0, math.radians(rnd.uniform(-0.45, 0.45)))
        pecas.append(f)
    bm = bmesh.new()
    vs = [bm.verts.new((sx * pag_w / 2, sy * pag_h / 2, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for lp, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uv].uv = c
    pag = objeto_bm("papel", bm, m_pagina, normais=False)
    pag.location = (0, 0, zp)
    pecas.append(pag)
    for k, x in enumerate(furos_x):
        for s in (-1, 1):                     # espiral dupla: 2 voltas de arame por furo
            bpy.ops.mesh.primitive_torus_add(major_radius=0.0058, minor_radius=0.00055, major_segments=28,
                                             minor_segments=8, location=(x + s * 0.001, furo_y, zp - 0.004),
                                             rotation=(0, math.radians(90), 0))
            o = bpy.context.active_object
            o.name = f"{nome}_espiral_{k}_{s}"
            o.data.materials.append(m_espiral)
            for p in o.data.polygons:
                p.use_smooth = True
            pecas.append(o)
    return pecas


# ------------------------------------------------------------------ lapis
def lapis(nome="LAPIS", comp=0.15, cor=(0.62, 0.27, 0.0)):
    """Lapis sextavado apontado: grafite na ponta (z = 0), cone de madeira que corta o sextavado em 6 arcos (a borda
    ondulada da tinta), corpo pintado com quina levemente arredondada, ponteira de metal com frisos e borracha. Eixo +z."""
    ap = 0.00345                              # apotema (7 mm entre faces)
    m_tinta = material(nome + "_tinta", cor, rough=0.34, spec=0.4, coat=0.12)
    m_madeira = material(nome + "_madeira", (0.55, 0.36, 0.2), rough=0.75, spec=0.2, relevo=0.15, relevo_escala=900)
    m_grafite = material(nome + "_grafite", (0.035, 0.035, 0.04), rough=0.35, metal=0.4)
    m_metal = material(nome + "_metal", (0.75, 0.62, 0.35), rough=0.3, metal=1.0)
    m_borr = material(nome + "_borracha", (0.75, 0.32, 0.32), rough=0.75, spec=0.2)
    NA = 72                                   # 12 amostras por face do sextavado

    def r_hex(f):
        d = (f % (math.pi / 3)) - math.pi / 6
        return ap / math.cos(d)

    def r_cone(z):
        return 0.00025 + (0.001 - 0.00025) * z / 0.0035 if z < 0.0035 else 0.001 + 0.17 * (z - 0.0035)
    zs = [0.0] + [0.0003 * i for i in range(1, 80)] + [0.024 + (comp - 0.024) * i / 12 for i in range(1, 13)]
    bm = bmesh.new()
    aneis = []
    for z in zs:
        aneis.append([bm.verts.new((min(r_hex(f), r_cone(z)) * math.cos(f), min(r_hex(f), r_cone(z)) * math.sin(f), z))
                      for f in (2 * math.pi * k / NA for k in range(NA))])
    for a, b in zip(aneis, aneis[1:]):
        for k in range(NA):
            bm.faces.new((a[k], a[(k + 1) % NA], b[(k + 1) % NA], b[k]))
    bm.faces.new(list(reversed(aneis[0])))
    bm.faces.new(aneis[-1])
    corpo = objeto_bm(nome + "_corpo", bm, m_tinta)
    corpo.data.materials.append(m_madeira)
    corpo.data.materials.append(m_grafite)
    for p in corpo.data.polygons:
        z = p.center.z
        fz = math.atan2(p.center.y, p.center.x)
        if z < 0.0035:
            p.material_index = 2
        elif z < 0.023 and r_cone(z) < r_hex(fz) - 0.00002:
            p.material_index = 1
    # ponteira de metal com frisos + borracha arredondada
    bm = bmesh.new()
    perfil = []
    for i in range(41):
        z = comp + 0.011 * i / 40
        perfil.append((0.0040 + (0.00018 if (i // 3) % 2 and 6 < i < 34 else 0.0), z))
    aneis = [[bm.verts.new((r * math.cos(2 * math.pi * k / 32), r * math.sin(2 * math.pi * k / 32), z))
              for k in range(32)] for r, z in perfil]
    for a, b in zip(aneis, aneis[1:]):
        for k in range(32):
            bm.faces.new((a[k], a[(k + 1) % 32], b[(k + 1) % 32], b[k]))
    pont = objeto_bm(nome + "_ponteira", bm, m_metal)
    borr = cilindro(nome + "_borracha", 0.0036, 0.009, (0, 0, comp + 0.0145), m_borr, verts=32)
    bisel(borr, 0.0016, 4, 30)
    return raiz(nome + "_RAIZ", [corpo, pont, borr])
