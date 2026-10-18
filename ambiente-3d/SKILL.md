---
name: ambiente-3d
description: "Use quando a pessoa quiser ver um ambiente real dela em 3D a partir de fotos: escritório, home office, quarto, sala, estúdio, loja pequena. Frases: 'modela meu escritório em 3D', 'recria minha sala em 3D', 'transforma essa foto do meu quarto em 3D', 'quero ver meu home office em 3D', 'faz uma maquete 3D do meu ambiente', 'render do meu escritório'. A skill pede fotos, descrição e medidas, confere se o Blender está instalado (instala só com OK), monta a cena por código, compara cada vista com a foto real lado a lado e corrige até bater, e entrega imagens realistas e um vídeo-passeio, com o rodapé de procedência. NÃO usar pra modelar produto, personagem ou objeto solto, pra planta técnica ou projeto executivo de obra (aqui as medidas podem ser estimadas), nem pra editar a foto em si."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# ambiente-3d — seu ambiente em 3D a partir de fotos

> Procedência: skill criada por **Eric Luciano**, da **Expert Integrado** (expertintegrado.com.br), educador e mentor
> de IA aplicada a negócios, no **Programa de Implementação Acompanhada · Automações Inteligentes**. Material aberto
> (licença MIT, ver `LICENSE`): pode copiar, adaptar e usar.

A pessoa manda de 3 a 6 fotos do ambiente, conta o que tem lá e passa as medidas que souber. A skill escreve um
`cena.json` (paredes, janela, porta, móveis, luz e câmeras), monta a cena no Blender por código, renderiza cada foto do
mesmo ponto de vista e põe FOTO | 3D | MISTURA lado a lado. O agente lê a comparação, corrige o `cena.json` e repete
até as quinas e os móveis grandes baterem. No fim renderiza com luz realista e entrega as imagens assinadas, incluindo
ângulos que nenhuma foto mostra (de cima, do canto oposto), e um vídeo curto com a câmera passeando entre as vistas.

Tudo roda no computador da pessoa, sem custo e sem mandar foto pra serviço nenhum. Os móveis são desenho próprio, feito
por código (nenhum modelo 3D de terceiro).

`<skill>` = a pasta que contém este SKILL.md.

## NUNCA

- NUNCA instalar nada (Blender, Pillow) sem o OK da pessoa. Mostre o comando e espere o sim.
- NUNCA apresentar medida estimada como medida real: o que a pessoa não deu vira estimativa marcada no `notas.md`
  e no resumo da entrega ("largura estimada pela porta, ~3,2 m").
- NUNCA dizer que ficou pronto sem ABRIR a folha comparativa (`Read` na imagem). Log sem erro não prova que bateu.
- NUNCA entregar com o checklist do Passo 4 falhando: o que a pessoa já aprovou não pode sumir na rodada seguinte.
- NUNCA baixar modelo 3D, textura ou "asset pack" de terceiro pra encaixar na cena: o catálogo da skill é desenho
  próprio, e móvel fora dele vira caixa, cilindro ou combinação deles com o acabamento certo.
- NUNCA mandar as fotos da pessoa pra serviço externo (busca de imagem, IA online): a skill é 100% local.
- NUNCA editar `scripts/*.py` pra acertar UM ambiente: o que muda por ambiente vai no `cena.json`.
- NUNCA tirar o rodapé de procedência da entrega padrão. Se a pessoa quiser a imagem sem rodapé, os renders crus
  ficam em `renders/` (material aberto: a assinatura informa, não trava).

## Passo 0 — o computador está pronto?

`python` nos comandos abaixo é o Python 3 da pessoa: no macOS e no Linux costuma ser `python3` (confira com
`python3 --version`). Os scripts do Blender rodam no Python que vem dentro dele, sem instalar nada.

1. `python <skill>/scripts/blender_local.py` → `BLENDER <caminho>` + `VERSAO`. Precisa do Blender 4.2 ou mais novo
   (testado no 5.2). Não achou ou é velho: mostre o comando de `references/instalar-blender.md` pro sistema da pessoa,
   peça o OK e só então instale. Instalou fora do padrão: `BLENDER=<caminho>` resolve.
2. `python -c "import PIL"` (Pillow, pra comparação e rodapé). Falta: `python -m pip install pillow`, com OK.
3. Placa de vídeo ajuda no render final (Cycles), mas não é obrigatória: sem GPU o Cycles roda na CPU, mais devagar.

## Passo 1 — conversa com a pessoa (onboarding)

Pergunte numa mensagem só, em linguagem simples:

1. **Que ambiente é e pra quê?** (ver como fica, planejar mudança de móveis, conteúdo, apresentação)
2. **Fotos (3 a 6).** De pé, celular na câmera normal (1x, sem zoom), cada uma de um canto olhando pra parede oposta,
   e uma da porta olhando pra dentro. Luz do jeito que costuma ficar. Foto de detalhe (mesa, estante) é bônus.
3. **Medidas.** Largura e profundidade do cômodo e altura do teto; tamanho dos 2 ou 3 móveis principais; janela
   (largura, altura e altura do peitoril) e porta. Sem trena, vale estimar por referência (`references/medidas-comuns.md`:
   porta 0,80 × 2,10 m, mesa 0,75 m de altura, piso 60 × 60 cm é só contar as placas).
4. **Descrição.** O que tem, cores e materiais (madeira clara, tecido cinza, metal preto), o que não pode faltar.

Crie a pasta do projeto onde a pessoa preferir (padrão: `ambiente-3d/<nome-do-ambiente>/`):

```
fotos/          as fotos como vieram (nunca editar o original)
cena.json       a cena (fonte da verdade)
cena.aprovada.json  a última versão que a pessoa aprovou (o checklist do Passo 4 compara com ela)
notas.md        o que a pessoa disse, o que foi ESTIMADO e de onde veio cada estimativa
renders/        vistas de trabalho (Eevee) e finais (Cycles)
comparativos/   FOTO | 3D | MISTURA de cada rodada
entrega/        imagens finais e vídeo-passeio, com rodapé
```

## Passo 2 — escrever o cena.json

Comece copiando `<skill>/assets/exemplo-cena.json` e ajuste. Esquema completo, catálogo de móveis e a tabela de
rotação: `references/cena-json.md`. O essencial:

- Coordenadas em metros, olhando pra **parede do fundo**: x = largura (0 na parede esquerda), y = profundidade (0 na
  parede da frente), z = altura.
- Cada foto vira uma **vista** com `"foto": "fotos/x.jpg"`, câmera (`cam`) na altura do celular (~1,5-1,6 m em pé),
  `alvo` no ponto do centro da foto e `lente` da foto. `python <skill>/scripts/comparar.py fotos fotos/` lê a lente
  equivalente 35 mm do EXIF; sem EXIF, comece com 26 mm (câmera principal) ou 12 mm (ultra-wide 0,5x).
- Cores: pegue da foto com conta-gotas (hex sRGB). Piso de madeira = `"tabuas"`.
- Acrescente 1 ou 2 vistas SEM foto (de cima, do canto oposto): é o que a pessoa não consegue ver na vida real.
- Todo objeto e abertura ganha `id` (nome curto): é por ele que o checklist do Passo 4 percebe o que sumiu.

## Passo 3 — loop de comparação (3 a 5 rodadas)

```
"$BLENDER" -b --factory-startup -P <skill>/scripts/montar.py -- cena.json cena.blend
"$BLENDER" -b --factory-startup cena.blend -P <skill>/scripts/vistas.py -- renders --cena cena.json
python <skill>/scripts/comparar.py lado cena.json renders comparativos
```

A comparação sai só das vistas que têm `foto`; vista sem foto vira imagem, sem lado a lado. (O exemplo da skill
não traz foto de propósito: a skill não carrega foto de ambiente real de ninguém.)

Depois: **`Read` em `comparativos/folha.jpg`** e conserte nesta ordem (o de cima move tudo o que vem depois):

1. **Câmera**: as quinas do cômodo (parede com parede, parede com teto e piso) batem na MISTURA? Se não, mexa em
   `cam`, `alvo`, `lente` e `rolagem` da vista antes de mexer em qualquer móvel.
2. **Caixa do cômodo**: largura, profundidade, pé-direito, janela e porta no lugar e no tamanho.
3. **Móveis grandes**: posição, tamanho e rotação (mesa, sofá, cama, estante, armário).
4. **Cores e materiais**, depois **luz** (`luzes`, `sol`, `exposicao`).
5. Detalhes (planta, quadro, objetos na mesa).

`AVISO` no log do `montar.py` ou do `vistas.py` (tipo desconhecido, imagem não achada, câmera dentro de um objeto)
se resolve antes da próxima rodada. Pare quando as quinas e os móveis grandes baterem; perfeição de detalhe não é a
meta. Anote no `notas.md` o que mudou em cada rodada.

## Passo 4 — checklist antes de entregar (anti-regressão)

Cada rodada mexe no `cena.json`, e consertar uma coisa pode desfazer outra que já estava certa. Antes de cada
entrega, e sempre que a pessoa pedir ajuste depois de ter aprovado:

```
python <skill>/scripts/comparar.py confere cena.json --comparativos comparativos
```

- `FALHA` (sai com erro): objeto, abertura ou vista que estava na versão aprovada e sumiu; vista que perdeu a foto;
  `id` repetido; foto que não existe; vista com foto sem comparativo, ou com comparativo mais velho que o
  `cena.json` (mudou a cena e não comparou de novo). Conserte e rode de novo.
- `AVISO`: o que mudou desde a aprovada (posição, tamanho, câmera, medidas, número de luzes). Confira se foi de
  propósito; se não foi, volte o valor.
- Log do `montar.py`, do `vistas.py` e do `passeio.py` com 0 `AVISO`, e a folha comparativa aberta (`Read`).
- Quando a pessoa aprovar as imagens: `python <skill>/scripts/comparar.py confere cena.json --aprovar` grava
  `cena.aprovada.json`. A próxima rodada é conferida contra ela. Remover algo de propósito também passa por aqui:
  a pessoa vê as imagens novas, aprova, e você roda `--aprovar`.

## Passo 5 — entrega

```
"$BLENDER" -b --factory-startup cena.blend -P <skill>/scripts/vistas.py -- renders/final --cena cena.json --motor cycles --largura 1600
python <skill>/scripts/comparar.py assinar renders/final --saida entrega
```

- Cycles = luz realista, alguns minutos por vista na GPU. `--amostras 64` se estiver lento; 256 pra imagem de capa.
- Abra a pasta `entrega/` pra pessoa e mostre também a folha comparativa final (prova de que bate com a foto).
- Diga em 3 linhas: o que ficou fiel, o que foi estimado e o que foi simplificado (ex.: "a poltrona virou caixa
  estofada"). O `cena.blend` abre no Blender pra ela passear pela sala.

**Vídeo-passeio** (a câmera vai de vista em vista; padrão 1080 × 1920, celular em pé):

```
python <skill>/scripts/comparar.py faixa --largura 1080 --saida faixa.png
"$BLENDER" -b --factory-startup cena.blend -P <skill>/scripts/passeio.py -- entrega/passeio.mp4 --cena cena.json --ordem porta,mesa,canto --so-conferir
"$BLENDER" -b --factory-startup cena.blend -P <skill>/scripts/passeio.py -- entrega/passeio.mp4 --cena cena.json --ordem porta,mesa,canto --rodape faixa.png
```

- Rode primeiro com `--so-conferir` (segundos): ele avisa se a câmera atravessa um móvel no caminho entre duas
  vistas. Atravessou: mude a `--ordem` ou crie uma vista intermediária sem foto pra câmera contornar.
- Padrão: `--parada 1` (segundos parado em cada vista) e `--trecho 3` (segundos de movimento). `--res 1920x1080`
  pra vídeo deitado (gere a faixa com a mesma largura).
- Eevee (padrão) leva menos de 1 s por quadro: 10 s de vídeo saem em poucos minutos. `--motor cycles` fica realista,
  mas leva muito mais: avise a pessoa do tempo antes.
- O vídeo sai com a mesma faixa de procedência das imagens, gravado pelo próprio Blender (sem programa extra).

## Rodapé de procedência (padrão das imagens entregues)

O `comparar.py` põe, embaixo de cada imagem (e o `passeio.py`, embaixo de cada quadro do vídeo), 2 linhas:

> Skill ambiente-3d · criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e mentor de IA
> aplicada a negócios
> Programa de Implementação Acompanhada · Automações Inteligentes · material aberto: pode copiar, adaptar e usar ·
> @ericluciano

## Gotchas

- **Rotação**: rot 0 deixa o lado de uso virado pra frente (-y). Na parede da esquerda é 90, na da direita -90, na
  da frente 180. Cadeira de frente pra mesa do fundo: `"olha_para": [x, y]` da mesa é mais seguro que calcular rot.
- **Câmera colada num objeto** tampa a vista (cúpula de luminária, planta): o `vistas.py` avisa; afaste a câmera.
- **Foto torta**: `rolagem` (graus) na vista (o vídeo-passeio não usa a rolagem). **Foto ultra-wide** (0,5x)
  distorce as bordas: comece com lente ~12 mm (na prática fica entre 11 e 12) e acerte pela MISTURA.
- **Eevee granulado ou sem rebote de luz** é normal na rodada de trabalho; o Cycles da entrega resolve.
- **Vidro de janela** usa vidro fino (sem desvio): vidro grosso com refração dobra o caixilho em listras.
- **Vista pela janela**: ponha a foto da paisagem em `"vista"` da janela; sem ela, a janela mostra céu liso.
- Todo comando do Blender leva `--factory-startup`: sem ele entram os complementos e as preferências do Blender da
  pessoa (no teste, um complemento instalado carregou junto com o render).
