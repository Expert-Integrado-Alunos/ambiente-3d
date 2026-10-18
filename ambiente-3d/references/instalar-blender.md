# Instalar o Blender (só com o OK da pessoa)

> Procedência: skill ambiente-3d, criada por Eric Luciano, Expert Integrado (expertintegrado.com.br), educador e
> mentor de IA aplicada a negócios. Material aberto (licença MIT): pode copiar, adaptar e usar.

O Blender é gratuito e de código aberto (Blender Foundation, blender.org). A skill precisa da versão **4.2 ou mais
nova**. Antes de instalar: rode `python scripts/blender_local.py` (pode já existir), diga à pessoa o que vai ser
instalado (~400 MB, programa oficial da Blender Foundation) e espere o sim.

| Sistema | Comando | Observação |
|---|---|---|
| Windows | `winget install --id BlenderFoundation.Blender -e` | winget vem no Windows 10/11; pode pedir confirmação de administrador |
| macOS | `brew install --cask blender` | precisa do Homebrew; sem ele, baixar o .dmg em blender.org |
| Linux (Ubuntu e outros com snap) | `sudo snap install blender --classic` | |
| Linux (flatpak) | `flatpak install flathub org.blender.Blender` | o executável vira `flatpak run org.blender.Blender` |
| Qualquer sistema | baixar em https://www.blender.org/download/ | instalador oficial; conferir que o site é blender.org |

Depois de instalar, rode `python scripts/blender_local.py` de novo. Se instalou numa pasta fora do padrão, aponte com a
variável `BLENDER` (ex.: `BLENDER="D:/Apps/Blender/blender.exe"`).

Pillow (comparação lado a lado e rodapé): `python -m pip install pillow`, também com OK.

`python` aqui é o Python 3 da pessoa. No macOS e no Linux o comando costuma ser `python3` (e `python3 -m pip install
pillow`); no Windows, `python` ou `py`. O vídeo-passeio não precisa de ffmpeg: o Blender grava o MP4 sozinho.

Nunca instalar complemento (add-on), modelo ou textura de terceiro pra esta skill: ela não precisa de nada além do
Blender e do Pillow.
