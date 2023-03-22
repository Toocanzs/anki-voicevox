# VOICEVOX Audio Generator for Anki
Generate high quality Japanese audio for your Anki cards using the VOICEVOX speech synthesis software

Showoff and setup guide video: https://youtu.be/-V3pnCuEIxw

Download VOICEVOX: https://voicevox.hiroshiba.jp/

Download from AnkiWeb: https://ankiweb.net/shared/info/366960193

# What does this do?
This is a text to speech addon for Anki that makes use of the VOICEVOX speech synthesis engine to generate audio for Japanese Anki cards.

# Setup
IMPORTANT: This addon requires that the VOICEVOX engine service is running in order to generate audio.
To setup VOICEVOX for this addon, follow these steps: 
1. You can download VOICEVOX from here: https://voicevox.hiroshiba.jp/
    * I prefer the zip package, but you can use the installer if you like
    * Note that it's about 1gb in size. This is a machine learning model so it's quite large

2. Download the addon from AnkiWeb: https://ankiweb.net/shared/info/366960193
3. Navigate to your VOICEVOX install and find `run.exe`. `run.exe` will launch the VOICEVOX engine and allow Anki to communicate with it.
    * You must keep `run.exe` running to generate audio in Anki

4. Open the Anki card browser and right click on any card and select "Generate VOICEVOX Audio" from the dropdown
    * You can drag and select multiple cards to generate audio for many cards at once. Note that if you select two different types of cards only the fields that they have in common will appear in the source/destination dropdown.

5. Select the source and destination fields for generating audio
    * Source refers to which field the addon should read from to generate audio. For example you usually want to read from the `Sentence` field or similar.
    * Destination refers to the field that the addon should output the audio to. Fields like `Audio` or `Audio On Front`. Whatever field you want the audio to be placed in. NOTE: This will overwrite the contents of this field, so don't select any field you don't want overwritten with audio

6. Select a speaker and a style from the dropdown. You can preview the voices by selecting "Preview Voice"

7. Click "Generate Audio" and wait for the audio to be generated
    * Note that the time it takes to generate audio can vary based on your hardware. VOICEVOX works whether you run it on a dedicated GPU or just a CPU, but running it on the CPU will be much slower.

# Building
* Windows
    * Building the .ankiaddon can be done on by running `build.bat`
    * NOTE: requires powershell 7 ( run `winget upgrade Microsoft.PowerShell` to get powershell 7)
* Linux
    * On Linux there currently isn't a one click build setup, but all that needs to be done is to zip everything except for `meta.json`(it may not exist) into a `.zip` file, and then rename to a `.ankiaddon` file