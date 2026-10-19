> **Publicado pela Expert Integrado — versão 2026-10-19-3fab513.** Cópia pública de `ambiente-3d`, gerada automaticamente a partir da fonte interna (sem histórico) pelo robô publicador. Issues e pull requests aqui não são acompanhados; contato em expertintegrado.com.br.

# ambiente-3d — seu ambiente em 3D a partir de fotos

Skill para o Claude Code: você manda de 3 a 6 fotos de um ambiente (escritório, quarto, sala), conta o que tem lá e
passa as medidas que souber. O agente monta a cena no Blender por código, compara cada vista com a foto real lado a
lado, corrige até bater e entrega imagens realistas, inclusive de ângulos que nenhuma foto mostra, e um vídeo curto
com a câmera passeando pelo ambiente.

Roda inteira no seu computador, sem custo e sem mandar foto pra serviço nenhum. Os móveis são desenho próprio, feito
por código (sem modelo 3D de terceiro).

> Criada por **Eric Luciano**, da **Expert Integrado** (expertintegrado.com.br), educador e mentor de IA aplicada a
> negócios, no **Programa de Implementação Acompanhada · Automações Inteligentes**. Material aberto (licença MIT):
> pode copiar, adaptar e usar.

## Como instalar

1. Baixe este repositório: `git clone https://github.com/Expert-Integrado-Alunos/ambiente-3d` (ou, no GitHub,
   *Code > Download ZIP*).
2. Copie a pasta `ambiente-3d/` de dentro dele para `~/.claude/skills/` (Windows: `C:\Users\<você>\.claude\skills\`).
3. Abra o Claude Code e peça: *"modela meu escritório em 3D"*. A skill confere se o Blender (4.2+) e o Pillow estão
   instalados e, se faltar, pede seu OK antes de instalar.

## O que tem aqui

- `ambiente-3d/SKILL.md` — o passo a passo que o agente segue (conversa, montagem, loop de comparação, checklist
  anti-regressão, entrega).
- `ambiente-3d/scripts/` — montar a cena, renderizar vistas, comparar com a foto, conferir o que mudou desde a última
  aprovação, assinar a entrega e gravar o vídeo-passeio.
- `ambiente-3d/references/` — formato do `cena.json`, como instalar o Blender, medidas comuns pra estimar.
- `ambiente-3d/assets/exemplo-cena.json` — um escritório de exemplo pronto pra testar.

## Teste rápido (sem fotos)

```
blender -b --factory-startup -P ambiente-3d/scripts/montar.py -- ambiente-3d/assets/exemplo-cena.json teste/cena.blend
blender -b --factory-startup teste/cena.blend -P ambiente-3d/scripts/vistas.py -- teste/renders --cena ambiente-3d/assets/exemplo-cena.json
python ambiente-3d/scripts/comparar.py faixa --largura 1080 --saida teste/faixa.png
blender -b --factory-startup teste/cena.blend -P ambiente-3d/scripts/passeio.py -- teste/passeio.mp4 --cena ambiente-3d/assets/exemplo-cena.json --rodape teste/faixa.png
```

No macOS e no Linux, `python3` no lugar de `python`. O exemplo não traz foto (a skill não carrega foto de ambiente real
de ninguém), então ele gera as vistas e o vídeo, mas não a comparação lado a lado: essa aparece quando você põe as suas
fotos nas vistas (`"foto": "fotos/sua-foto.jpg"`).
