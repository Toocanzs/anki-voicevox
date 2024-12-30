del /f "VOICEVOX Audio Generator.ankiaddon"
powershell -Command "& {Compress-Archive -LiteralPath __init__.py, ffmpeg.py, voicevox_gen.py, config.json, config.md, manifest.json, README.md -DestinationPath VOICEVOX-Audio-Generator.zip -Force}"
rename VOICEVOX-Audio-Generator.zip "VOICEVOX Audio Generator.ankiaddon"