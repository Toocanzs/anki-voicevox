from aqt.qt import QComboBox, QHBoxLayout, QLabel, QPushButton, QApplication, QMessageBox
from aqt import browser, gui_hooks, qt
from aqt import mw
from aqt.sound import av_player
import requests
import json 
import urllib.parse
from aqt.utils import showText
import random
import base64

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
        selected_notes = browser.selectedNotes()

        layout = qt.QVBoxLayout()

        layout.addWidget(qt.QLabel("notes " + str(len(selected_notes))))

        self.source_dest = qt.QHBoxLayout()

        common_fields = getCommonFields(selected_notes)

        self.source_combo = qt.QComboBox()
        self.destination_combo = qt.QComboBox()

        sentence_field_index = 0
        audio_field_index = 0

        i = 0
        for field in common_fields:
            if "expression" == field.lower() or "sentence" == field.lower():
                sentence_field_index = i
            if "audio" == field.lower():
                audio_field_index = i
            self.source_combo.addItem(field)
            self.destination_combo.addItem(field)
            i += 1

        self.source_combo.setCurrentIndex(sentence_field_index)
        self.destination_combo.setCurrentIndex(audio_field_index)

        self.source_dest.addWidget(qt.QLabel("Source field: "))
        self.source_dest.addWidget(self.source_combo)
        self.source_dest.addWidget(qt.QLabel("Destination field: "))
        self.source_dest.addWidget(self.destination_combo)

        #TODO: Prevent source and dest being the same so you don't overwrite the source
        
        layout.addLayout(self.source_dest)

        speaker_json = getSpeakersOrNone()
        if speaker_json is None:
            layout.addWidget(qt.QLabel("VOICEVOX service was unable to get speakers list. Please make sure the VOICEVOX service is running and reopen this dialog"))
            self.setLayout(layout)
            return

        self.speaker_hbox = qt.QHBoxLayout()

        self.speaker_hbox.addWidget(qt.QLabel("Speaker: "))
        self.speakers = getSpeakerList(speaker_json)
        self.speaker_combo = qt.QComboBox()
        for speaker in self.speakers:
            self.speaker_combo.addItem(speaker[0])
        self.speaker_hbox.addWidget(self.speaker_combo)

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
        #TODO: Store the speaker name and style name so we can default to it here
        update_speaker_style_combo_box() # run this the first time so the default speaker style is setup

        self.speaker_hbox.addWidget(qt.QLabel("Style: "))
        self.speaker_hbox.addWidget(self.style_combo)

        self.preview_voice_button = qt.QPushButton("Preview Voice", self)
        
        self.preview_voice_button.clicked.connect(self.PreviewVoice)
        self.speaker_hbox.addWidget(self.preview_voice_button)

        layout.addLayout(self.speaker_hbox)

        self.setLayout(layout)
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
                with open("VOICEVOX_response.wav", "wb") as f:
                    f.write(file_content)
                av_player.play_file("VOICEVOX_response.wav")

        """progress_win = mw.progress.start(immediate=True)
        mw.checkpoint("Generating Preview")
        progress_win.show()
        QApplication.instance().processEvents()
        test_data = "こんにちは、音声合成の世界へようこそ"
        audio_query_response = requests.post("http://127.0.0.1:50021/audio_query?speaker=" + str(speaker_index) + "&text=" + urllib.parse.quote(test_data))
        if audio_query_response.status_code != 200:
            raise Exception('audio_query_response returned status code ' + str(audio_query_response.status_code))
        
        synthesis_response = requests.post("http://127.0.0.1:50021/synthesis?speaker=" + str(speaker_index), data=audio_query_response.content)
        if synthesis_response.status_code != 200:
            raise Exception('synthesis_response returned status code ' + str(audio_query_response.status_code))

        with open("VOICEVOX_response.wav", "wb") as f:
            f.write(synthesis_response.content)
        av_player.play_file("VOICEVOX_response.wav")
        mw.progress.finish()"""

def my_action(browser):
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
        # when "OK" button is clicked
        print(f"Text: {dialog.text_edit.toPlainText()}")
        print(f"Priority: {dialog.button_group.checkedButton().text()}")
        checkbox_text = "checked" if dialog.checkbox.isChecked() else "unchecked"
        print(f"Checkbox: {checkbox_text}")
    else:
        print("Canceled!")


def on_browser_will_show_context_menu(browser: browser.Browser, menu: qt.QMenu):
    menu.addAction("My Dialog", lambda: my_action(browser))
    
gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)