# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Desenha as legendas do teclado (texto branco em fundo transparente) pra textura das teclas.

Uso: python gera_tex_teclado.py [saida.png]   (padrao: ../assets/tex/teclado.png; o montar.py gera na pasta do projeto se faltar)
A imagem cobre o corpo inteiro do teclado (W x D do teclado_layout) e o material das teclas a projeta de cima, nas
coordenadas do objeto TECLADO; por isso a legenda usa as mesmas contas do pecas.py (retangulos()).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from teclado_layout import D, SHIFT, W, retangulos  # noqa: E402

LARG = 4096
ALT = round(LARG * D / W)
PX = LARG / W                                        # pixels por metro


def fonte(tam):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tex", "teclado.png")
    img = Image.new("RGBA", (LARG, ALT), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    grande, media, pequena = fonte(round(0.0040 * PX)), fonte(round(0.0030 * PX)), fonte(round(0.0022 * PX))
    cor = (255, 255, 255, 235)
    for rot, cx, cy, larg, alt, principal in retangulos():
        if not rot:
            continue
        px, py = (cx + W / 2) * PX, (D / 2 - cy) * PX
        if principal and rot in SHIFT:               # 2 legendas: shift em cima, normal embaixo
            d.text((px, py - 0.0024 * PX), SHIFT[rot], font=media, fill=cor, anchor="mm")
            d.text((px, py + 0.0026 * PX), rot, font=media, fill=cor, anchor="mm")
        elif len(rot) == 1 or rot in ("\u2190", "\u2191", "\u2192", "\u2193"):
            d.text((px, py), rot, font=grande, fill=cor, anchor="mm")
        elif rot.startswith("F") and rot[1:].isdigit():
            d.text((px, py), rot, font=pequena, fill=cor, anchor="mm")
        else:                                        # palavra: no canto de baixo a esquerda, como no teclado real
            x0 = px - larg * PX / 2 + 0.0022 * PX
            d.text((x0, py + alt * PX / 2 - 0.0022 * PX), rot, font=pequena, fill=cor, anchor="ls")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    img.save(saida)
    print("OK teclado", saida, img.size)


if __name__ == "__main__":
    main()
