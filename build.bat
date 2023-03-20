del /f "VOICEVOX Audio Generator.ankiaddon"
if not exist "included_fonts" ( 
    mkdir "included_fonts"
)
pwsh -Command "& {Compress-Archive -LiteralPath included_fonts, __init__.py, config.json, config.md, manifest.json, README.md -DestinationPath VOICEVOX-Audio-Generator.zip -Force}"
rename VOICEVOX-Audio-Generator.zip "VOICEVOX Audio Generator.ankiaddon"