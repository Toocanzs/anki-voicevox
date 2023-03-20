from aqt.qt import QComboBox, QHBoxLayout, QLabel, QPushButton, QApplication, QMessageBox
from aqt import browser, gui_hooks, qt
from aqt import mw
from aqt.sound import av_player
import requests
import json 
import urllib.parse
from aqt.utils import showText
from os.path import join, exists, dirname
import random
import base64
import uuid
import re

from . import ffmpeg

VOICEVOX_CONFIG_NAME = "VOICEVOX_CONFIG"

def getCommonFields(selected_notes):
    common_fields = set()

    first = True

    for note_id in selected_notes:
        note = mw.col.getNote(note_id)
        model = note._model
        model_fields = set([f['name'] for f in model['flds']])
        if first:
            common_fields = model_fields # Take the first one as is and we will intersect it with the following ones
        else:
            common_fields = common_fields.intersection(model_fields) # Find the common fields by intersecting the set of all fields together
        first = False
    return common_fields
def getSpeakersOrNone():
    try:
        speakers_response = requests.get("http://127.0.0.1:50021/speakers")
        if speakers_response.status_code == 200:
            print(speakers_response.content)
            return json.loads(speakers_response.content)
    except:
        return None
    
def getSpeakerInfo(speaker_uuid):
    try:
        speakers_response = requests.get("http://127.0.0.1:50021/speaker_info?speaker_uuid=" + str(speaker_uuid))
        if speakers_response.status_code == 200:
            print(speakers_response.content)
            return json.loads(speakers_response.content)
    except:
        return None
    
def getSpeakerList(speaker_json):
    speakers = []
    for obj in speaker_json:
        styles = []
        for style in obj['styles']:
            styles.append( (style['name'], style['id']) )
        #speaker_info = getSpeakerInfo(obj['speaker_uuid'])
        speakers.append( (obj['name'], styles, obj['speaker_uuid']) )
    return speakers

def getSpeaker(speakers, speaker_combo, style_combo):
    speaker_name = speaker_combo.itemText(speaker_combo.currentIndex())
    speaker = next((x for x in speakers if x[0] == speaker_name), None)
    if speaker is None:
        raise Exception(f"Speaker '{speaker_name}' not found in getSpeaker")

    styles = speaker[1]
    style_name = style_combo.itemText(style_combo.currentIndex())
    style_info = next((x for x in styles if x[0] == style_name), None)

    if style_info is None:
        raise Exception(f"Style '{style_name}' not found in getSpeaker")
    
    speaker_id = style_info[1]
    return (speaker_id, speaker, style_info)

class MyDialog(qt.QDialog):
    def __init__(self, browser, parent=None) -> None:
        super().__init__(parent)
        self.selected_notes = browser.selectedNotes()

        config = mw.addonManager.getConfig(__name__)

        layout = qt.QVBoxLayout()

        layout.addWidget(qt.QLabel("Selected notes: " + str(len(self.selected_notes))))

        self.grid_layout = qt.QGridLayout()

        common_fields = getCommonFields(self.selected_notes)

        self.source_combo = qt.QComboBox()
        self.destination_combo = qt.QComboBox()

        last_source_field = config.get('last_source_field') or None
        last_destination_field = config.get('last_destination_field') or None
        source_field_index = 0
        destination_field_index = 0
        i = 0
        for field in common_fields:
            if last_source_field is None:
                if "expression" == field.lower() or "sentence" == field.lower():
                    source_field_index = i
            elif field == last_source_field:
                    source_field_index = i
            
            if last_destination_field is None:
                if "audio" == field.lower():
                    destination_field_index = i
            elif field == last_destination_field:
                destination_field_index = i
            self.source_combo.addItem(field)
            self.destination_combo.addItem(field)
            i += 1

        self.source_combo.setCurrentIndex(source_field_index)
        self.destination_combo.setCurrentIndex(destination_field_index)

        self.grid_layout.addWidget(qt.QLabel("Source field: "), 0, 0)
        self.grid_layout.addWidget(self.source_combo, 0, 1)
        self.grid_layout.addWidget(qt.QLabel("Destination field: "), 0, 2)
        self.grid_layout.addWidget(self.destination_combo, 0, 3)
        self.ignore_brackets_checkbox = qt.QCheckBox("Ignore stuff in brackets [...]")
        self.ignore_brackets_checkbox.setCheckState(True)

        #TODO: Prevent source and dest being the same so you don't overwrite the source
        
        speaker_json = getSpeakersOrNone()
        if speaker_json is None:
            layout.addWidget(qt.QLabel("VOICEVOX service was unable to get speakers list. Please make sure the VOICEVOX service is running and reopen this dialog"))
            self.setLayout(layout)
            return

        self.grid_layout.addWidget(qt.QLabel("Speaker: "), 1, 0)
        self.speakers = getSpeakerList(speaker_json)
        self.speaker_combo = qt.QComboBox()
        for speaker in self.speakers:
            self.speaker_combo.addItem(speaker[0])
        self.grid_layout.addWidget(self.speaker_combo, 1, 1)

        self.style_combo = qt.QComboBox()

        def update_speaker_style_combo_box():
            speaker_name = self.speaker_combo.itemText(self.speaker_combo.currentIndex())
            speaker = next((x for x in self.speakers if x[0] == speaker_name), None) # grab the first speaker with this name
            if speaker is None:
                print("Speaker not found in update_speaker_style_combo_box")
                return
            self.style_combo.clear()
            for style in speaker[1]:
                self.style_combo.addItem(style[0])

        self.speaker_combo.currentIndexChanged.connect(update_speaker_style_combo_box)
        update_speaker_style_combo_box() # run this the first time so the default speaker style is setup

        last_speaker_name = config.get('last_speaker_name') or None
        last_style_name = config.get('last_style_name') or None

        # find the speaker/style from the previously saved config data and pick it from the dropdown
        speaker_combo_index = 0
        i = 0
        for speaker_item in [self.speaker_combo.itemText(i) for i in range(self.speaker_combo.count())]:
            if speaker_item == last_speaker_name:
                speaker_combo_index = i
                break
            i += 1

        style_combo_index = 0
        i = 0
        for style_item in [self.style_combo.itemText(i) for i in range(self.style_combo.count())]:
            if style_item == last_style_name:
                style_combo_index = i
                break
                i += 1

        self.speaker_combo.setCurrentIndex(speaker_combo_index)
        self.style_combo.setCurrentIndex(style_combo_index) # NOTE: The previous style should probably be stored as a tuple with the speaker, but this is good enough. IE. Person A style X is not the same as Person B style X

        self.grid_layout.addWidget(qt.QLabel("Style: "), 1, 2)
        self.grid_layout.addWidget(self.style_combo, 1, 3)

        self.preview_voice_button = qt.QPushButton("Preview Voice", self)
        
        self.preview_voice_button.clicked.connect(self.PreviewVoice)
        self.grid_layout.addWidget(self.preview_voice_button, 1, 4)

        self.button_box = qt.QDialogButtonBox()
        self.button_box.addButton("Cancel", qt.QDialogButtonBox.RejectRole)
        self.button_box.addButton("Generate Audio", qt.QDialogButtonBox.AcceptRole)

        self.button_box.accepted.connect(self.pre_accept)
        self.button_box.rejected.connect(self.reject)

        self.grid_layout.addWidget(self.button_box, 2, 0, 1, 5)
        
        layout.addLayout(self.grid_layout)

        self.setLayout(layout)
    def pre_accept(self):
        if self.source_combo.currentIndex() == self.destination_combo.currentIndex():
            source_text = self.source_combo.itemText(self.source_combo.currentIndex())
            destination_text = self.destination_combo.itemText(self.destination_combo.currentIndex())
            QMessageBox.critical(mw, "Error", f"The chosen source field '{source_text}' is the same as the destination field '{destination_text}'.\nThis would overwrite the field you're reading from.\n\nTypically you want to read from a field like 'sentence' and output to 'audio', but in this case you're trying to read from 'sentence' and write to 'sentence' which cause your sentence to be overwritten")
        else:
            self.accept()
    def PreviewVoice(self):
        (speaker_index, speaker, style_info) = getSpeaker(self.speakers, self.speaker_combo, self.style_combo)
        if speaker_index is None:
            raise Exception('getSpeaker returned None in PreviewVoice')
        
        speaker_uuid = speaker[2]
        speaker_info = getSpeakerInfo(speaker_uuid)
        if speaker_info is not None:
            voice_samples = None
            style_infos = speaker_info['style_infos']
            for style_info in style_infos:
                if style_info['id'] == speaker_index:
                    voice_samples = list(style_info['voice_samples'])
                    break
            if voice_samples is not None:
                voice_base64 = random.choice(voice_samples)
                file_content = base64.b64decode(voice_base64)
                with open("VOICEVOX_preview.wav", "wb") as f:
                    f.write(file_content)
                av_player.play_file("VOICEVOX_preview.wav")
        else:
            QMessageBox.critical(mw, "Error", f"Unable to get speaker info for speaker {speaker_uuid}. Check that VOICEVOX is running")

def GenerateAudio(text, speaker_index):
    #TODO: /multi_synthesis. Returns a zip. File names start at 0001.wav and continue up https://stackoverflow.com/a/10909016
    # zipfile.read() and pass to mp3 converter. Probably don't need to multithread the creation but could multithread conversion maybe

    audio_query_response = requests.post("http://127.0.0.1:50021/audio_query?speaker=" + str(speaker_index) + "&text=" + urllib.parse.quote(text))
    if audio_query_response.status_code != 200:
        raise Exception('audio_query_response returned status code ' + str(audio_query_response.status_code) + ". Check that VOICEVOX is running")
    
    synthesis_response = requests.post("http://127.0.0.1:50021/synthesis?speaker=" + str(speaker_index), data=audio_query_response.content)
    if synthesis_response.status_code != 200:
        raise Exception('synthesis_response returned status code ' + str(audio_query_response.status_code) + ". Check that VOICEVOX is running")
    return synthesis_response.content

def onVoicevoxOptionSelected(browser):
    voicevox_exists = False
    try:
        response = requests.get("http://127.0.0.1:50021/version")
        if response.status_code == 200:
            print(f"version: {response.content}")
            voicevox_exists = True
    except:
        print("Request timed out!")

    if not voicevox_exists:
        QMessageBox.critical(mw, "Error", f"VOICEVOX service is not running. Navigate to your VOICEVOX install and run 'run.exe'. You can download VOICEVOX from https://voicevox.hiroshiba.jp/ if you do not have it installed")
        return

    dialog = MyDialog(browser)
    if dialog.exec():
        (speaker_index, speaker, style_info) = getSpeaker(dialog.speakers, dialog.speaker_combo, dialog.style_combo)
        if speaker_index is None:
            raise Exception('getSpeaker returned None in my_action')
        
        source_field = dialog.source_combo.itemText(dialog.source_combo.currentIndex())
        destination_field = dialog.destination_combo.itemText(dialog.destination_combo.currentIndex())

        speaker_combo_text = dialog.speaker_combo.itemText(dialog.speaker_combo.currentIndex())
        style_combo_text = dialog.style_combo.itemText(dialog.style_combo.currentIndex())

        # Save previously used stuff
        config = mw.addonManager.getConfig(__name__)
        config['last_source_field'] = source_field
        config['last_destination_field'] = destination_field
        config['last_speaker_name'] = speaker_combo_text
        config['last_style_name'] = style_combo_text
        mw.addonManager.writeConfig(__name__, config)

        progress_win = mw.progress.start(immediate=True, label="Generating Audio...")
        progress_win.show()
        mw.app.processEvents() #TODO: remove
        notes_so_far = 0
        for note_id in dialog.selected_notes:
            mw.progress.update(value=notes_so_far, max=len(dialog.selected_notes))
            notes_so_far += 1
            note = mw.col.getNote(note_id)

            # Remove stuff between brackets. Usually japanese cards have pitch accent and reading info in brackets like 「 タイトル[;a,h] を 聞[き,きく;h]いた わけ[;a] じゃ ない[;a] ！」
            note_text = note[source_field]
            if dialog.ignore_brackets_checkbox.isChecked():
                note_text = re.sub("\[.*?\]", "", note_text)
            note_text = re.sub(" ", "", note_text) # there's a lot of spaces for whatever reason which throws off the voice gen so we remove all spaces (japanese doesn't care about them anyway)
            media_dir = mw.col.media.dir()

            audio_data = GenerateAudio(note_text, speaker_index)
            audio_extension = "wav"

            new_audio_data = ffmpeg.ConvertWavToMp3(audio_data)
            if new_audio_data != None:
                audio_data = new_audio_data
                audio_extension = "mp3"

            file_id = str(uuid.uuid4())
            filename = f"VOICEVOX_{file_id}.{audio_extension}"
            audio_full_path = join(media_dir, filename)

            with open(audio_full_path, "wb") as f:
                f.write(audio_data)
            
            audio_field_text = f"[sound:{filename}]"
            note[destination_field] = audio_field_text
            note.flush()
            mw.app.processEvents() #TODO: REMOVE
        mw.progress.finish()
        mw.reset() # reset mw so our changes are applied
    else:
        print("Canceled!")