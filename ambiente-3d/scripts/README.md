# scripts da skill ambiente-3d

Ordem de uso: `blender_local.py` (acha o Blender) → `montar.py` (cena.json → cena.blend) → `vistas.py` (renderiza as
vistas) → `comparar.py` (`fotos` lê a lente do EXIF, `lado` faz FOTO | 3D | MISTURA, `confere` é o checklist
anti-regressão contra a versão aprovada, `assinar` põe o rodapé, `faixa` gera o rodapé pro vídeo) → `passeio.py`
(vídeo com a câmera indo de vista em vista, rodapé embaixo).

`pecas.py` (peças base: caixa, cilindro, cadeira de escritório, teclado, mouse, caixas de colisão) e
`teclado_layout.py` + `gera_tex_teclado.py` (as teclas e a textura `assets/tex/teclado.png`) são bibliotecas usadas
pelo `montar.py`, `vistas.py` e `passeio.py`.
Os scripts do Blender rodam dentro dele (`blender -b --factory-startup [cena.blend] -P <script> -- <args>`);
`comparar.py` e `blender_local.py` são Python 3 comum (`python3` no macOS/Linux). Detalhe de cada um no cabeçalho do
arquivo.
