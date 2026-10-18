# Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
# mentor de IA aplicada a negócios. Material aberto (licença MIT, ver LICENSE): pode copiar, adaptar e usar.
"""Layout do teclado full-size baixo (430,2 x 131,6 x 20,5 mm, perfil baixo), sem bpy.

O pecas.py monta as teclas e o gera_tex_teclado.py desenha as legendas com as MESMAS contas (retangulos()), entao a
legenda cai sempre no meio da tecla. Coordenadas locais do teclado em metros: x da esquerda (-W/2) pra direita (+W/2),
y da frente (-D/2, perto de quem digita) pro fundo (+D/2, perto do monitor).
"""
W, D = 0.4302, 0.1316          # corpo
PASSO = 0.0182                 # 1u (22,5u de largura cabem com 10 mm de borda de cada lado)
VAO = 0.0030                   # vao entre teclas vizinhas
LINHA_F = 0.72                 # altura (em u) da fileira de funcao, mais baixa que as outras
MARGEM_X = (W - 22.5 * PASSO) / 2
MARGEM_FUNDO = 0.0120

# legenda de cima (com shift) das teclas que tem duas
SHIFT = {"`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", "8": "*", "9": "(",
         "0": ")", "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|", ";": ":", "'": '"', ",": "<", ".": ">",
         "/": "?"}


def teclas():
    """(legenda, x_u, linha, largura_u, altura_u): linha 0 = funcao (no fundo), 5 = barra de espaco (na frente)."""
    t = []

    def linha(r, itens, x=0.0):
        for rot, w in itens:
            if rot is not None:
                t.append((rot, x, r, w, 1.0))
            x += w

    linha(0, [("esc", 1), (None, 1), ("F1", 1), ("F2", 1), ("F3", 1), ("F4", 1), (None, 0.5), ("F5", 1), ("F6", 1),
              ("F7", 1), ("F8", 1), (None, 0.5), ("F9", 1), ("F10", 1), ("F11", 1), ("F12", 1)])
    linha(0, [("prt sc", 1), ("scr lk", 1), ("pause", 1)], 15.25)
    linha(0, [("calc", 1), ("snip", 1), ("menu", 1), ("lock", 1)], 18.5)
    linha(1, [(c, 1) for c in "`1234567890-="] + [("backspace", 2)])
    linha(1, [("ins", 1), ("home", 1), ("pg up", 1)], 15.25)
    linha(1, [("num", 1), ("/", 1), ("*", 1), ("-", 1)], 18.5)
    linha(2, [("tab", 1.5)] + [(c, 1) for c in "QWERTYUIOP[]"] + [("\\", 1.5)])
    linha(2, [("del", 1), ("end", 1), ("pg dn", 1)], 15.25)
    linha(2, [("7", 1), ("8", 1), ("9", 1)], 18.5)
    t.append(("+", 21.5, 2, 1, 2.0))
    linha(3, [("caps lock", 1.75)] + [(c, 1) for c in "ASDFGHJKL;'"] + [("enter", 2.25)])
    linha(3, [("4", 1), ("5", 1), ("6", 1)], 18.5)
    linha(4, [("shift", 2.25)] + [(c, 1) for c in "ZXCVBNM,./"] + [("shift", 2.75)])
    linha(4, [("↑", 1)], 16.25)
    linha(4, [("1", 1), ("2", 1), ("3", 1)], 18.5)
    t.append(("enter", 21.5, 4, 1, 2.0))
    linha(5, [("ctrl", 1.25), ("fn", 1.25), ("start", 1.25), ("alt", 1.25), ("", 6.25), ("alt", 1.25), ("fn", 1.25),
              ("menu", 1.25), ("ctrl", 1.25)])
    linha(5, [("←", 1), ("↓", 1), ("→", 1)], 15.25)
    linha(5, [("0", 2), (".", 1)], 18.5)
    return t


def topo_linha(r):
    """Distancia (em u) do topo da linha r ao topo da area das teclas."""
    return 0.0 if r == 0 else LINHA_F + 0.28 + (r - 1) * 1.0


def retangulos():
    """[(legenda, cx, cy, larg, alt, principal)] em metros, no espaco local do teclado (topo de cada tecla, sem o vao);
    principal = bloco de letras/numeros (so ele tem a 2a legenda do shift; o teclado numerico nao)."""
    out = []
    for rot, xu, r, wu, hu in teclas():
        alt_u = LINHA_F if r == 0 else hu
        cx = -W / 2 + MARGEM_X + (xu + wu / 2) * PASSO
        cy = D / 2 - MARGEM_FUNDO - (topo_linha(r) + alt_u / 2) * PASSO
        out.append((rot, cx, cy, wu * PASSO - VAO, alt_u * PASSO - VAO, xu < 15))
    return out
