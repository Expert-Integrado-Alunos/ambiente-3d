# cena.json — esquema completo

> Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
> mentor de IA aplicada a negócios. Material aberto (licença MIT): pode copiar, adaptar e usar.

Um arquivo JSON descreve o ambiente inteiro. Caminhos de imagem são relativos à pasta do `cena.json`. Tudo em metros
e graus. Cores em hex sRGB (`"#aabbcc"`), como saem do conta-gotas numa foto. Exemplo completo e testado:
`assets/exemplo-cena.json`.

## Coordenadas

Fique de pé olhando pra **parede do fundo**:

- **x** = largura: 0 na parede da esquerda, `largura` na da direita.
- **y** = profundidade: 0 na parede da frente (atrás de você), `profundidade` na do fundo.
- **z** = altura: 0 no piso.

`pos` de um objeto é o centro da base dele no piso (`[x, y]` ou `[x, y, z]`; z > 0 pra objeto em cima de outro, como
o monitor em cima da mesa: z = altura da mesa).

### Rotação

`rot` (graus, anti-horário visto de cima) gira o objeto em volta do próprio centro. Com `rot: 0` o **lado de uso**
fica virado pra frente (-y): tela do monitor, assento e encosto do sofá, portas do armário, pé da cama, o lado onde se
senta na mesa. Na cadeira, lado de uso = pra onde a pessoa sentada olha.

| Objeto encostado na parede... | rot |
|---|---|
| do fundo (lado de uso pra dentro do cômodo) | 0 |
| da esquerda | 90 |
| da direita | -90 |
| da frente | 180 |

Alternativa sem conta: `"olha_para": [x, y]` gira o lado de uso pra esse ponto (cadeira olhando pra mesa, sofá
olhando pra TV). Objeto de parede (`quadro`, `tv`, `prateleira`, `cortina`): `pos` é o ponto NA FACE da parede e z é
a altura da base dele; use a rot da tabela.

## ambiente

```json
"ambiente": {
  "largura": 3.2, "profundidade": 3.6, "pe_direito": 2.7, "espessura_parede": 0.12,
  "piso": {"tipo": "tabuas", "cor": "#9a6a42", "cor2": "#6e4628", "comprimento": 1.2, "largura": 0.19},
  "parede": "#ece8e1",
  "paredes": {"fundo": "#d9d2c5", "esquerda": {"tipo": "madeira", "cor": "#8a5a36"}},
  "forro": "#f2f0ec", "teto": true,
  "rodape": {"altura": 0.07, "cor": "#f4f2ee"},
  "sem_parede": []
}
```

- `paredes` troca o acabamento de uma parede (`fundo`, `frente`, `esquerda`, `direita`); o resto usa `parede`.
- `sem_parede: ["frente"]` tira uma parede (planta aberta, ou pra câmera ficar "fora" do cômodo).
- `teto: false` tira o teto (vista de cima tipo maquete). `rodape: null` tira o rodapé.

## Acabamentos

Onde o esquema pede acabamento (`acabamento`, `tampo`, `piso`, `parede`...), vale:

- nome: `"madeira"`, `"tabuas"`, `"tecido"`, `"couro"`, `"metal"`, `"plastico"`, `"vidro"`, `"espelho"`, `"pintura"`,
  `"porcelanato"`, `"carpete"`, `"concreto"`;
- só a cor: `"#3a2a1f"` (acabamento padrão daquele lugar nessa cor);
- completo: `{"tipo": "madeira", "cor": "#c9a57a", "cor2": "#8a6a48", "brilho": 0.6}` (`cor2` = tom escuro do veio
  ou da trama; `brilho` 0 = fosco, 1 = espelhado).

`madeira` = veio fino correndo ao longo da peça (tampo, estante, painel). `tabuas` = assoalho com juntas e tom
variando por tábua (`comprimento` e `largura` da tábua em m); piso `"madeira"` vira `"tabuas"` sozinho.

## aberturas

```json
"aberturas": [
  {"id": "janela", "parede": "fundo", "tipo": "janela", "centro": 1.6, "largura": 1.6, "altura": 1.4,
   "peitoril": 0.95, "divisoes": 2, "caixilho": "#2b2b2b", "ceu": "#bcd3e6", "vista": "fotos/paisagem.jpg"},
  {"id": "porta", "parede": "frente", "tipo": "porta", "centro": 0.6, "largura": 0.8, "altura": 2.1,
   "dobradica": "esquerda", "abertura": 70, "cor": "#f2f0ec"},
  {"id": "passagem", "parede": "direita", "tipo": "vao", "centro": 2.8, "largura": 1.0, "altura": 2.1}
]
```

- `centro`: posição do meio da abertura AO LONGO da parede, em metros: em `fundo` e `frente` é o x; em `esquerda` e
  `direita` é o y.
- Janela: `peitoril` (altura do parapeito, padrão 1,0), `divisoes` (folhas), `caixilho` e `caixilho_largura`,
  `vista` (foto do que se vê lá fora; sem ela, céu liso na cor `ceu`), `vista_forca` (brilho, padrão 1,6),
  `vista_distancia` (quão longe fica a paisagem; padrão 1,5).
- Porta: `dobradica` (`esquerda`/`direita`, vista de dentro), `abertura` (0 = fechada, 90 = escancarada), `cor`,
  `batente`, `folha: false` (só o batente).
- `vao`: buraco na parede, sem nada.

## objetos

Todo objeto tem `tipo`, `pos` e, opcional, `id` (nome no Blender), `rot` ou `olha_para`. Tipo desconhecido vira
caixa com aviso. Dê `id` a todo objeto e abertura: é por ele que o `comparar.py confere` percebe o que sumiu ou
mudou desde a versão aprovada (sem `id`, ele avisa e confere pela ordem, que muda quando se apaga um item).

| tipo | campos (padrão) |
|---|---|
| `caixa` | `tam` [l, p, a] (0,5³), `acabamento`, `bisel` (0,004) |
| `cilindro` | `raio` (0,2), `altura` (0,5), `raio_topo`, `acabamento` |
| `mesa` | `tam` [l, p, a] (1,4 × 0,7 × 0,75), `estilo` `4pes`/`painel`/`standing`, `tampo`, `pes`, `espessura` (0,025) |
| `cadeira` | `estilo` `escritorio` (cores `cor`, `cor2`, `cor_base`) ou `simples` (`acabamento`, `assento`, `altura_assento`) |
| `monitor` | `tela` [l, a] (0,6 × 0,34), `altura_base` (0,12), `curvo` (raio em m, ex. 1,0), `imagem`, `brilho`, `acabamento` |
| `notebook` | `tam` [l, p] (0,32 × 0,22), `abertura` (110°), `imagem`, `acabamento` |
| `teclado`, `mouse` | `cor` |
| `estante` | `tam` (0,8 × 0,3 × 1,8), `prateleiras` (4), `livros` (true), `semente` (muda os livros), `acabamento` |
| `armario` | `tam` (1,2 × 0,55 × 2,1), `portas` (2), `puxador`, `acabamento` |
| `sofa` | `tam` (2,0 × 0,9 × 0,82), `lugares` (3), `altura_assento`, `braco`, `pes`, `acabamento` |
| `cama` | `tam` [l, c] (1,38 × 1,88), `altura` (0,5), `roupa`, `travesseiro`, `cabeceira`, `acabamento` |
| `planta` | `altura` (1,2), `raio`, `raio_vaso`, `vaso`, `folhagem`, `semente` |
| `luminaria` | `estilo` `piso`/`mesa`/`pendente`, `altura`, `cupula`, `cor_luz`, `forca` (40), `acabamento` |
| `painel_led` | `tam` (0,19 × 0,165), `forca`, `cor_luz` (luz de vídeo/estúdio) |
| `quadro` | `tam` [l, a] (0,6 × 0,8), `imagem` ou `cor`, `moldura`, `moldura_largura` |
| `tv` | `tam` [l, a] (1,23 × 0,71), `imagem`, `brilho` |
| `prateleira` | `tam` (0,8 × 0,22 × 0,025), `suportes`, `suporte`, `acabamento` |
| `tapete` | `tam` [l, p] (2,0 × 1,4), `espessura`, `acabamento` (carpete) |
| `cortina` | `tam` [l, a] (1,6 × 2,4), `acabamento` |

- `luminaria` `pendente`: `pos` z = altura da cúpula; o fio sobe `altura` metros.
- Móvel que não está no catálogo: monte com `caixa` e `cilindro` (poltrona = caixa estofada + encosto; criado-mudo =
  caixa de madeira). Diga na entrega o que foi simplificado.

## luzes, sol e mundo

```json
"luzes": [
  {"tipo": "teto", "pos": [1.6, 1.8], "forca": 160, "tam": 0.5, "rebate": 0.3},
  {"tipo": "spot", "pos": [1.0, 3.0, 2.6], "alvo": [1.0, 3.3, 0.8], "forca": 80, "cone": 50},
  {"tipo": "area", "pos": [0.5, 1.0, 1.8], "alvo": [1.6, 3.2, 1.0], "forca": 60, "tam": [0.6, 0.4]},
  {"tipo": "ponto", "pos": [2.5, 3.0, 1.2], "forca": 30, "cor": "#ffd9a8"}
],
"sol": "auto",
"mundo": {"cor": "#2a2e33", "forca": 0.6},
"exposicao": 0.0
```

- `teto` = plafon/painel no forro (luz + a peça que brilha). `rebate` (0,3) = luz que volta do piso pro teto; 0 tira.
- Sem `luzes`, entra 1 luz de teto no centro.
- `"sol": "auto"` faz o sol entrar pela 1ª janela. Sol próprio: `{"tipo": "sol", "azimute": 200, "elevacao": 35, "forca": 3}`.
  `"sol": null` tira.
- `exposicao`: +0,5 clareia, -0,5 escurece a imagem inteira (como no celular).

## vistas

```json
"vistas": {
  "porta": {"cam": [0.9, 0.35, 1.6], "alvo": [1.8, 3.4, 1.0], "lente": 26, "foto": "fotos/porta.jpg", "rolagem": 0},
  "de_cima": {"cam": [1.6, 1.8, 6.0], "alvo": [1.6, 1.81, 0], "lente": 24, "res": [1080, 1080]}
}
```

- `cam` = onde está o celular; `alvo` = o ponto do centro da foto; `lente` = mm equivalente 35 mm (câmera principal
  do celular ~26; ultra-wide 0,5x: comece com 12 e acerte pela MISTURA, costuma fechar entre 11 e 12).
- Vista com `foto` sai na proporção da foto (é o que permite comparar). Sem foto: `res` [l, a] dá a proporção
  (padrão 1080 × 1350); `--largura` do `vistas.py` dá o tamanho.
- `rolagem` = foto torta (graus, positivo = anti-horário). O vídeo-passeio ignora a rolagem.
- A ordem das vistas no arquivo é a ordem padrão do vídeo-passeio (`passeio.py --ordem` muda).
- Vista de cima com teto: use `"teto": false` no ambiente numa cópia do cena.json, ou ponha a câmera abaixo do forro.
