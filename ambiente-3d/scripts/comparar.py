# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Foto real x render 3D, lado a lado, com o rodape de procedencia (Python 3 + Pillow).

Uso:
  python comparar.py fotos <pasta_ou_fotos...>
      tamanho, orientacao e lente equivalente 35 mm (EXIF) de cada foto: ponto de partida da "lente" de cada vista
  python comparar.py lado <cena.json> <pasta_renders> <pasta_saida> [--sem-mistura]
      1 imagem por vista que tem "foto": FOTO | 3D | MISTURA (as duas a 50%, mostra desalinhamento) + folha.jpg com todas
  python comparar.py assinar <pasta_ou_imagens...> --saida <pasta>
      copia as imagens finais com a faixa de procedencia embaixo (entrega)
  python comparar.py faixa --largura <px> --saida faixa.png
      so a faixa do rodape, na largura do video (o passeio.py poe embaixo de cada quadro)
  python comparar.py confere <cena.json> [--comparativos <pasta>] [--aprovada <arq>] [--aprovar]
      checklist anti-regressao antes de entregar: compara com a ultima versao APROVADA (cena.aprovada.json, ao lado
      do cena.json) e acusa objeto, abertura ou vista que sumiu; id repetido; foto que nao existe; e, com
      --comparativos, vista com foto sem comparativo novo. Sai 1 se achou FALHA. --aprovar grava a versao atual
      como aprovada (so depois que a pessoa aprovou as imagens).
"""
import glob
import json
import os
import shutil
import sys

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    raise SystemExit("falta o Pillow: python -m pip install pillow")

RODAPE = ("Skill ambiente-3d · criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), "
          "educador e mentor de IA aplicada a negócios",
          "Programa de Implementação Acompanhada · Automações Inteligentes · material aberto: pode copiar, "
          "adaptar e usar · @ericluciano")
FONTES = ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
          "/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
          "/usr/share/fonts/TTF/DejaVuSans.ttf")
FONTES_N = ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf")


def fonte(tam, negrito=False):
    for f in (FONTES_N if negrito else ()) + FONTES:
        if os.path.exists(f):
            return ImageFont.truetype(f, tam)
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


def abre(p):
    return ImageOps.exif_transpose(Image.open(p)).convert("RGB")


def faixa(larg):
    """Faixa escura com as 2 linhas do rodape, ajustadas a largura."""
    tam = max(11, larg // 70)
    while tam > 9:
        f = fonte(tam)
        if all(f.getlength(t) <= larg - 2 * tam for t in RODAPE):
            break
        tam -= 1
    alt = int(tam * 3.4)
    img = Image.new("RGB", (larg, alt), (18, 18, 20))
    d = ImageDraw.Draw(img)
    d.text((tam, int(tam * 0.55)), RODAPE[0], font=fonte(tam), fill=(232, 232, 232))
    d.text((tam, int(tam * 1.85)), RODAPE[1], font=fonte(tam), fill=(160, 160, 160))
    return img


def com_rodape(img):
    f = faixa(img.width)
    out = Image.new("RGB", (img.width, img.height + f.height), (0, 0, 0))
    out.paste(img, (0, 0))
    out.paste(f, (0, img.height))
    return out


def rotulo(img, texto):
    d = ImageDraw.Draw(img)
    tam = max(16, img.width // 22)
    f = fonte(tam, negrito=True)
    w = f.getlength(texto)
    d.rectangle((0, 0, w + tam, tam * 1.6), fill=(0, 0, 0))
    d.text((tam / 2, tam * 0.25), texto, font=f, fill=(255, 220, 80))


def cmd_fotos(args):
    arqs = []
    for x in args:
        arqs += sorted(glob.glob(os.path.join(x, "*"))) if os.path.isdir(x) else [x]
    for p in arqs:
        if os.path.splitext(p)[1].lower() not in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
            continue
        try:
            im = Image.open(p)
        except Exception as e:                       # noqa: BLE001 (foto ilegivel: segue com as outras)
            print(f"{p}: nao abriu ({e})")
            continue
        ex = im.getexif()
        sub = ex.get_ifd(0x8769) if hasattr(ex, "get_ifd") else {}
        f35 = sub.get(0xA405) or ex.get(0xA405)
        fmm = sub.get(0x920A) or ex.get(0x920A)
        w, h = ImageOps.exif_transpose(im).size
        print(f"{os.path.basename(p)}: {w}x{h} {'retrato' if h > w else 'paisagem'}"
              f"{f', lente equivalente {f35} mm' if f35 else ''}{f', focal real {float(fmm):.1f} mm' if fmm else ''}"
              f"{'' if f35 else ' (sem EXIF de lente: comece com 26 mm na camera principal, 12 mm na ultra-wide 0,5x)'}")


def cmd_lado(args):
    if len(args) < 3:
        raise SystemExit("uso: comparar.py lado <cena.json> <pasta_renders> <pasta_saida> [--sem-mistura]")
    cena_json, renders, saida = args[:3]
    mistura = "--sem-mistura" not in args
    pasta = os.path.dirname(os.path.abspath(cena_json))
    vistas = json.load(open(cena_json, encoding="utf-8")).get("vistas") or {}
    os.makedirs(saida, exist_ok=True)
    feitas = []
    for nome, v in vistas.items():
        if not v.get("foto"):
            continue
        pf = v["foto"] if os.path.isabs(v["foto"]) else os.path.join(pasta, v["foto"])
        pr = os.path.join(renders, f"{nome}.jpg")
        if not (os.path.exists(pf) and os.path.exists(pr)):
            print(f"{nome}: falta {'a foto' if not os.path.exists(pf) else 'o render'}")
            continue
        foto, rend = abre(pf), abre(pr)
        alt = 900
        foto = foto.resize((round(foto.width * alt / foto.height), alt), Image.LANCZOS)
        rend = rend.resize(foto.size, Image.LANCZOS)
        paineis = [(foto, "FOTO"), (rend, "3D")]
        if mistura:
            paineis.append((Image.blend(foto, rend, 0.5), "MISTURA"))
        gap = 8
        larg = sum(p.width for p, _ in paineis) + gap * (len(paineis) - 1)
        lado = Image.new("RGB", (larg, alt), (255, 255, 255))
        x = 0
        for p, t in paineis:
            p = p.copy()
            rotulo(p, t)
            lado.paste(p, (x, 0))
            x += p.width + gap
        out = com_rodape(lado)
        dest = os.path.join(saida, f"{nome}.jpg")
        out.save(dest, quality=90)
        feitas.append(out)
        print(f"COMPARATIVO {nome} -> {dest}")
    if not feitas:
        raise SystemExit("nenhuma vista com foto e render: confira os nomes em 'vistas' e a pasta de renders")
    larg = max(i.width for i in feitas)
    folha = Image.new("RGB", (larg, sum(i.height for i in feitas)), (255, 255, 255))
    y = 0
    for i in feitas:
        folha.paste(i, (0, y))
        y += i.height
    if folha.width > 2400:
        folha = folha.resize((2400, round(folha.height * 2400 / folha.width)), Image.LANCZOS)
    folha.save(os.path.join(saida, "folha.jpg"), quality=88)
    print(f"FOLHA {os.path.join(saida, 'folha.jpg')} ({len(feitas)} vista(s))")


def cmd_assinar(args):
    if "--saida" not in args:
        raise SystemExit("uso: comparar.py assinar <pasta_ou_imagens...> --saida <pasta>")
    i = args.index("--saida")
    saida, fontes = args[i + 1], args[:i] + args[i + 2:]
    arqs = []
    for x in fontes:
        arqs += sorted(glob.glob(os.path.join(x, "*.jpg")) + glob.glob(os.path.join(x, "*.png"))) \
            if os.path.isdir(x) else [x]
    os.makedirs(saida, exist_ok=True)
    for p in arqs:
        dest = os.path.join(saida, os.path.splitext(os.path.basename(p))[0] + ".jpg")
        com_rodape(abre(p)).save(dest, quality=92)
        print(f"ASSINADA {dest}")


def cmd_faixa(args):
    if "--largura" not in args or "--saida" not in args:
        raise SystemExit("uso: comparar.py faixa --largura <px> --saida faixa.png")
    larg = int(args[args.index("--largura") + 1])
    dest = args[args.index("--saida") + 1]
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    f = faixa(larg)
    if f.height % 2:                                     # video H.264 exige altura par: a faixa ja nasce par
        f = f.crop((0, 0, f.width, f.height + 1))
    f.save(dest)
    print(f"FAIXA {dest}: {f.width}x{f.height}")


def por_id(lista, rotulo, falhas, avisos):
    """{id: item}; id repetido e FALHA (o Blender renomeia e a comparacao se perde); sem id vira <tipo>#<ordem>."""
    out = {}
    for k, x in enumerate(lista or []):
        chave = x.get("id")
        if not chave:
            chave = f"{x.get('tipo', '?')}#{k}"
            avisos.append(f"{rotulo} sem id ({chave}): de um id pra conferir se ele some ou muda")
        if chave in out:
            falhas.append(f"{rotulo} com id repetido: {chave}")
        out[chave] = x
    return out


def diferencas(a, b, campos):
    return [f"{c} {a.get(c)} -> {b.get(c)}" for c in campos if a.get(c) != b.get(c)]


def cmd_confere(args):
    if not args:
        raise SystemExit("uso: comparar.py confere <cena.json> [--comparativos <pasta>] [--aprovada <arq>] [--aprovar]")
    cena_json = os.path.abspath(args[0])
    pasta = os.path.dirname(cena_json)
    opc = {n: args[args.index(n) + 1] for n in ("--comparativos", "--aprovada") if n in args[:-1]}
    aprovada = os.path.abspath(opc.get("--aprovada", os.path.join(pasta, "cena.aprovada.json")))
    atual = json.load(open(cena_json, encoding="utf-8"))
    falhas, avisos, perdas = [], [], []                  # perdas = sumiu desde a aprovada (regressao)
    objs = por_id(atual.get("objetos"), "objeto", falhas, avisos)
    abs_ = por_id(atual.get("aberturas"), "abertura", falhas, avisos)
    vistas = atual.get("vistas") or {}
    for nome, v in vistas.items():
        if v.get("foto"):
            pf = v["foto"] if os.path.isabs(v["foto"]) else os.path.join(pasta, v["foto"])
            if not os.path.exists(pf):
                falhas.append(f"vista {nome}: a foto {v['foto']} nao existe")
    if "--comparativos" in opc:
        comp = os.path.abspath(opc["--comparativos"])
        mudou = os.path.getmtime(cena_json)
        for nome, v in vistas.items():
            if not v.get("foto"):
                continue
            pc = os.path.join(comp, f"{nome}.jpg")
            if not os.path.exists(pc):
                falhas.append(f"vista {nome}: tem foto e nao tem comparativo em {comp} (rode vistas + comparar lado)")
            elif os.path.getmtime(pc) < mudou:
                falhas.append(f"vista {nome}: o comparativo e mais velho que o cena.json (refaca vistas + lado)")
    if os.path.exists(aprovada):
        ant = json.load(open(aprovada, encoding="utf-8"))
        lixo = []
        a_objs = por_id(ant.get("objetos"), "objeto", lixo, lixo)
        a_abs = por_id(ant.get("aberturas"), "abertura", lixo, lixo)
        a_vistas = ant.get("vistas") or {}
        for rot, velho, novo, campos in (("objeto", a_objs, objs, ("tipo", "pos", "tam", "rot", "estilo")),
                                         ("abertura", a_abs, abs_, ("parede", "tipo", "centro", "largura", "altura")),
                                         ("vista", a_vistas, vistas, ("cam", "alvo", "lente", "rolagem"))):
            for chave, x in velho.items():
                if chave not in novo:
                    perdas.append(f"{rot} {chave} estava na versao aprovada e sumiu")
                    continue
                dif = diferencas(x, novo[chave], campos)
                if dif:
                    avisos.append(f"{rot} {chave} mudou desde a aprovada: {'; '.join(dif)} (confirme que foi de proposito)")
            for chave in novo:
                if chave not in velho:
                    avisos.append(f"{rot} {chave} e novo desde a aprovada")
        for nome, x in a_vistas.items():
            if x.get("foto") and nome in vistas and not vistas[nome].get("foto"):
                perdas.append(f"vista {nome} perdeu a foto de referencia (sem ela nao ha comparacao)")
        dif = diferencas(ant.get("ambiente") or {}, atual.get("ambiente") or {}, ("largura", "profundidade", "pe_direito"))
        if dif:
            avisos.append(f"medidas do ambiente mudaram: {'; '.join(dif)}")
        if len(ant.get("luzes") or []) != len(atual.get("luzes") or []):
            avisos.append(f"luzes: {len(ant.get('luzes') or [])} na aprovada, {len(atual.get('luzes') or [])} agora")
    else:
        avisos.append(f"sem versao aprovada ainda ({os.path.basename(aprovada)}): nada a comparar; quando a pessoa "
                      f"aprovar as imagens, rode de novo com --aprovar")
    aprovar = "--aprovar" in args
    if aprovar:                                          # a pessoa viu as imagens novas e aprovou a remocao
        avisos += [f"{t} (aceito: a pessoa aprovou esta versao)" for t in perdas]
    else:
        falhas += [f"{t}; se foi de proposito e a pessoa aprovou as imagens, rode com --aprovar" for t in perdas]
    for t in avisos:
        print(f"AVISO {t}")
    for t in falhas:
        print(f"FALHA {t}")
    if falhas:
        print(f"CONFERE FALHOU: {len(falhas)} falha(s), {len(avisos)} aviso(s)")
        raise SystemExit(1)
    print(f"CONFERE OK: {len(objs)} objeto(s), {len(abs_)} abertura(s), {len(vistas)} vista(s), {len(avisos)} aviso(s)")
    if aprovar:
        shutil.copyfile(cena_json, aprovada)
        print(f"APROVADA {aprovada}")


def main():
    cmds = {"fotos": cmd_fotos, "lado": cmd_lado, "assinar": cmd_assinar, "faixa": cmd_faixa, "confere": cmd_confere}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        raise SystemExit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
