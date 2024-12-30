from aqt.qt import QComboBox, QHBoxLayout, QLabel, QPushButton, QApplication, QMessageBox, QSlider, QLineEdit, QToolButton, QIcon
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
import zipfile
import io
from . import ffmpeg
import traceback
import re, html
import json
import datetime

VOICEVOX_CONFIG_NAME = "VOICEVOX_CONFIG"

def getCommonFields(selected_notes):
    common_fields = set()

    first = True

    for note_id in selected_notes:
        note = mw.col.get_note(note_id)
        if note is None: 
            raise Exception(f"Note with id {note_id} is None.\nNotes: {','.join([mw.col.get_note(id) for id in selected_notes])}.\nPlease submit an issues with more information about what cards caused this at https://github.com/Toocanzs/anki-voicevox/issues/new")
        model = note.note_type()
        model_fields = set([f['name'] for f in model['flds']])
        if first:
            common_fields = model_fields # Take the first one as is and we will intersect it with the following ones
        else:
            common_fields = common_fields.intersection(model_fields) # Find the common fields by intersecting the set of all fields together
        first = False
    return common_fields
def getSpeakersOrNone():
    try:
        speakers_response = requests.get("http://127.0.0.1:50021/speakers", timeout=5)
        if speakers_response.status_code == 200:
            print(speakers_response.content)
            return json.loads(speakers_response.content)
    except:
        return None
    
def getSpeakerInfo(speaker_uuid):
    try:
        speakers_response = requests.get("http://127.0.0.1:50021/speaker_info?speaker_uuid=" + str(speaker_uuid), timeout=5)
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

def parse_filename_template(template: str, placeholders: dict) -> str:
    """
    Replaces placeholders of form {{...}} in the template with corresponding values.
    Example placeholders:
      {{uid}}, {{speaker}}, {{style}}, {{deck}}, {{deck-full}}, {{date}}, {{field:Foo}}
    """
    # For safety, let's keep a local copy
    result = template

    # Find all occurrences of {{xyz}}
    all_placeholders = re.findall(r"{{(.*?)}}", template)
    for ph in all_placeholders:
        # For field placeholders: "field:myFieldName"
        if ph.startswith("field:"):
            field_name = ph[len("field:"):]
            if field_name in placeholders.get("fields", {}):
                val = placeholders["fields"][field_name]
            else:
                val = ""  # If field not found, replace with empty
            result = result.replace(f"{{{{field:{field_name}}}}}", val)
        else:
            # Normal placeholders
            val = placeholders.get(ph, "")
            result = result.replace(f"{{{{{ph}}}}}", val)

    return result

class MyDialog(qt.QDialog):
    def __init__(self, browser, parent=None) -> None:
        super().__init__(parent)
        self.selected_notes = browser.selectedNotes()

        config = mw.addonManager.getConfig(__name__)

        layout = qt.QVBoxLayout()

        layout.addWidget(qt.QLabel("Selected notes: " + str(len(self.selected_notes))))

        self.grid_layout = qt.QGridLayout()

        common_fields = getCommonFields(self.selected_notes)

        if len(common_fields) < 1:
            QMessageBox.critical(mw, "Error", f"The chosen notes share no fields in common. Make sure you're not selecting two different note types")
        elif len(common_fields) == 1:
            QMessageBox.critical(mw, "Error", f"The chosen notes only share a single field in common '{list(common_fields)[0]}'. This would leave no field to put the generated audio without overwriting the sentence data")

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


        source_label = qt.QLabel("Source field: ")
        source_tooltip = "The field to read from. For example if your sentence is in the field 'Expression' you want to choose 'Expression' as the source field to read from"
        source_label.setToolTip(source_tooltip)
        
        destination_label = qt.QLabel("Destination field: ")
        destination_tooltip = "The field to write the audio to. Typically you want to choose a field like 'Audio' or 'Audio on Front' or wherever you want the audio placed on your card."
        destination_label.setToolTip(destination_tooltip)

        self.source_combo.setToolTip(source_tooltip)
        self.destination_combo.setToolTip(destination_tooltip)

        self.grid_layout.addWidget(source_label, 0, 0)
        self.grid_layout.addWidget(self.source_combo, 0, 1)
        self.grid_layout.addWidget(destination_label, 0, 2)
        self.grid_layout.addWidget(self.destination_combo, 0, 3)

        # TODO: Does anyone actually want to not ignore stuff in brackets? The checkbox is here if we need it but I don't think anyone wants brackets to be read
        self.ignore_brackets_checkbox = qt.QCheckBox("Ignore stuff in brackets [...]")
        self.ignore_brackets_checkbox.setToolTip("Ignores things between brackets. Usually Japanese cards have pitch accent and reading info in brackets. Leave this checked unless you really know what you're doing")
        self.ignore_brackets_checkbox.setChecked(True)
        # self.grid_layout.addWidget(self.ignore_brackets_checkbox, 0, 4)

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

        # Keep track of the current note index for previewing actual content
        self.preview_note_index = 0
        def resetPreviewIndex(*args):
            self.preview_note_index = 0

        def voiceValueChanged(*args):
            resetPreviewIndex(*args)

        # Connect the voice value changed signals
        self.speaker_combo.currentIndexChanged.connect(voiceValueChanged)
        self.style_combo.currentIndexChanged.connect(voiceValueChanged)
        self.source_combo.currentIndexChanged.connect(voiceValueChanged)

        preview_layout = qt.QHBoxLayout()
        label = QLabel("Preview Voice")
        preview_layout.addWidget(label)

        self.preview_voice_button_sample = qt.QPushButton("🎲", self)
        self.preview_voice_button_sample.setToolTip("Preview a random sample sentence")
        self.preview_voice_button_sample.clicked.connect(self.PreviewVoiceSample)
        preview_layout.addWidget(self.preview_voice_button_sample)

        self.preview_voice_button_actual = qt.QPushButton("🗂️", self)
        self.preview_voice_button_actual.setToolTip("Preview the source field\n\nRepeated clicks cycle through each note.")
        self.preview_voice_button_actual.clicked.connect(self.PreviewVoiceActual)
        preview_layout.addWidget(self.preview_voice_button_actual)

        self.grid_layout.addLayout(preview_layout, 1, 4)

        self.append_audio =  qt.QCheckBox("Append Audio")
        append_audio_checked = config.get('append_audio') or "false"
        self.append_audio.setChecked(True if append_audio_checked == "true" else False)
        self.grid_layout.addWidget(self.append_audio, 2, 0)

        self.use_opus =  qt.QCheckBox("Use opus instead of mp3")
        use_opus_checked = config.get('use_opus') or "false"
        self.use_opus.setChecked(True if use_opus_checked == "true" else False)
        self.grid_layout.addWidget(self.use_opus, 2, 1)

        # Filename template
        self.grid_layout.addWidget(qt.QLabel("Filename: "), 3, 0)
        
        self.filename_template_edit = QLineEdit()
        default_template = config.get('filename_template') or "VOICEVOX_{{speaker}}_{{style}}_{{uid}}"
        self.filename_template_edit.setText(default_template)
        self.filename_template_edit.setToolTip(
            "Use placeholders like {{uid}}, {{speaker}}, {{style}}, {{deck}}, {{deck-full}}, {{date}}, or {{field:<fieldName>}}.\n"
            "Example: VOICEVOX_{{speaker}}_{{style}}_{{field:Card ID}}.mp3\n"
            "If you omit {{uid}}, files may clash unless other placeholders ensure uniqueness."
        )
        
        self.grid_layout.addWidget(self.filename_template_edit, 3, 1, 1, 3)
        
        # "?" Button for help
        self.help_button = QToolButton()
        self.help_button.setText("?")
        self.help_button.setToolTip(
            "Possible placeholders:\n"
            "  {{uid}} - random unique identifier\n"
            "  {{speaker}} - speaker name\n"
            "  {{style}} - speaking style\n"
            "  {{deck}} - card deck name\n"
            "  {{deck-full}} - full card deck name, including parent deck hierarchy\n"
            "  {{date}} - current date in ISO format\n"
            "  {{field:<fieldName>}} - replaces with note field content\n\n"
            "Example: VOICEVOX_{{speaker}}_{{style}}_{{field:ID}}_{{uid}}"
        )
        self.grid_layout.addWidget(self.help_button, 3, 4)

        # Warning icon if {{uid}} is missing
        self.uid_warning_label = QLabel()
        self.uid_warning_label.setToolTip("Warning: Without {{uid}}, you might get file name collisions. Each generated audio must have a globally unique name.")
        # Use some built-in icon or text: exclamation triangle
        self.uid_warning_label.setPixmap(self.style().standardIcon(qt.QStyle.StandardPixmap.SP_MessageBoxWarning).pixmap(16,16))
        self.uid_warning_label.setVisible(False)
        self.grid_layout.addWidget(self.uid_warning_label, 3, 5)

        # Red border if invalid placeholders
        def validate_template():
            t = self.filename_template_edit.text()
            # If we find placeholders not recognized: we won't parse them now with a big logic,
            # but let's warn if we see something that doesn't match recognized patterns.
            # For simplicity, only check for missing 'uid' for now, or obviously invalid placeholders.
            has_uid = "{{uid}}" in t
            self.uid_warning_label.setVisible(not has_uid)

            # Check for well-formed placeholders (all must be either "uid", "speaker", "style", "deck", "date", or "field:")
            # We'll just do a quick check: anything that doesn't start with field: or match known placeholders is suspect.
            # This is a mild approach; you can expand if needed.
            found_placeholders = re.findall(r"{{(.*?)}}", t)
            invalids = []
            for ph in found_placeholders:
                if ph not in ["uid", "speaker", "style", "deck", "deck-full", "date"] and not ph.startswith("field:"):
                    invalids.append(ph)
                elif ph.startswith("field:"):
                    field_name = ph[len("field:"):].strip()
                    if field_name not in common_fields:
                        invalids.append(ph)
            
            if invalids:
                self.filename_template_edit.setStyleSheet("border: 1px solid red;")
                self.filename_template_edit.setToolTip(
                    f"Invalid placeholder(s) detected: {', '.join(invalids)}\n"
                    "Valid placeholders: uid, speaker, style, deck, deck-full, date, field:<fieldName>"
                )
            else:
                self.filename_template_edit.setStyleSheet("")
                self.filename_template_edit.setToolTip(
                    "Use placeholders like {{uid}}, {{speaker}}, {{style}}, {{deck}}, {{deck-full}}, {{date}}, or {{field:<fieldName>}}."
                )

        self.filename_template_edit.textChanged.connect(validate_template)
        validate_template()

        self.cancel_button = qt.QPushButton("Cancel")
        self.generate_button = qt.QPushButton("Generate Audio")
        
        self.cancel_button.clicked.connect(self.reject)
        self.generate_button.clicked.connect(self.pre_accept)
        
        self.grid_layout.addWidget(self.cancel_button, 4, 0, 1, 2)
        self.grid_layout.addWidget(self.generate_button, 4, 3, 1, 2)
        
        def update_slider(slider, label, config_name, slider_desc):
            def update_this_slider(value):
                label.setText(f'{slider_desc} {slider.value() / 100}')
                config[config_name] = slider.value()
                mw.addonManager.writeConfig(__name__, config)
            return update_this_slider
        
        volume_slider = QSlider(qt.Qt.Orientation.Horizontal)
        volume_slider.setMinimum(0)
        volume_slider.setMaximum(200)
        volume_slider.setValue(config.get('volume_slider_value') or 100)
        
        volume_label = QLabel(f'Volume scale {volume_slider.value() / 100}')
        
        volume_slider.valueChanged.connect(update_slider(volume_slider, volume_label, 'volume_slider_value', 'Volume scale'))
        volume_slider.valueChanged.connect(voiceValueChanged)

        self.grid_layout.addWidget(volume_label, 5, 0, 1, 2)
        self.grid_layout.addWidget(volume_slider, 5, 3, 1, 2)
        
        pitch_slider = QSlider(qt.Qt.Orientation.Horizontal)
        pitch_slider.setMinimum(-15)
        pitch_slider.setMaximum(15)
        pitch_slider.setValue(config.get('pitch_slider_value') or 0)
        
        pitch_label = QLabel(f'Pitch scale {pitch_slider.value() / 100}')
        
        pitch_slider.valueChanged.connect(update_slider(pitch_slider, pitch_label, 'pitch_slider_value', 'Pitch scale'))
        pitch_slider.valueChanged.connect(voiceValueChanged)

        self.grid_layout.addWidget(pitch_label, 6, 0, 1, 2)
        self.grid_layout.addWidget(pitch_slider, 6, 3, 1, 2)
        
        speed_slider = QSlider(qt.Qt.Orientation.Horizontal)
        speed_slider.setMinimum(50)
        speed_slider.setMaximum(200)
        speed_slider.setValue(config.get('speed_slider_value') or 100)
        
        speed_label = QLabel(f'Speed scale {speed_slider.value() / 100}')
        
        speed_slider.valueChanged.connect(update_slider(speed_slider, speed_label, 'speed_slider_value', 'Speed scale'))
        speed_slider.valueChanged.connect(voiceValueChanged)

        self.grid_layout.addWidget(speed_label, 7, 0, 1, 2)
        self.grid_layout.addWidget(speed_slider, 7, 3, 1, 2)

        # Intonation slider
        intonation_slider = QSlider(qt.Qt.Orientation.Horizontal)
        intonation_slider.setMinimum(1)
        intonation_slider.setMaximum(200)
        intonation_slider.setValue(config.get('intonation_slider_value') or 100)
        
        intonation_label = QLabel(f'Intonation scale {intonation_slider.value() / 100}')
        
        intonation_slider.valueChanged.connect(update_slider(intonation_slider, intonation_label, 'intonation_slider_value', 'Intonation scale'))
        intonation_slider.valueChanged.connect(voiceValueChanged)

        self.grid_layout.addWidget(intonation_label, 8, 0, 1, 2)
        self.grid_layout.addWidget(intonation_slider, 8, 3, 1, 2)

        # Initial silence slider
        initial_silence_slider = QSlider(qt.Qt.Orientation.Horizontal)
        initial_silence_slider.setMinimum(0)
        initial_silence_slider.setMaximum(150)
        initial_silence_slider.setValue(config.get('initial_silence_slider_value') or 10)

        initial_silence_label = QLabel(f'Initial silence scale {initial_silence_slider.value() / 100}')

        initial_silence_slider.valueChanged.connect(update_slider(initial_silence_slider, initial_silence_label, 'initial_silence_slider_value', 'Initial silence scale'))
        initial_silence_slider.valueChanged.connect(voiceValueChanged)

        self.grid_layout.addWidget(initial_silence_label, 9, 0, 1, 2)
        self.grid_layout.addWidget(initial_silence_slider, 9, 3, 1, 2)

        # Final silence slider
        final_silence_slider = QSlider(qt.Qt.Orientation.Horizontal)
        final_silence_slider.setMinimum(0)
        final_silence_slider.setMaximum(150)
        final_silence_slider.setValue(config.get('final_silence_slider_value') or 10)

        final_silence_label = QLabel(f'Final silence length {final_silence_slider.value() / 100}')

        final_silence_slider.valueChanged.connect(update_slider(final_silence_slider, final_silence_label, 'final_silence_slider_value', 'Final silence scale'))
        final_silence_slider.valueChanged.connect(voiceValueChanged)

        self.grid_layout.addWidget(final_silence_label, 10, 0, 1, 2)
        self.grid_layout.addWidget(final_silence_slider, 10, 3, 1, 2)
        
        layout.addLayout(self.grid_layout)

        self.setLayout(layout)
    def pre_accept(self):
        if self.source_combo.currentIndex() == self.destination_combo.currentIndex():
            source_text = self.source_combo.itemText(self.source_combo.currentIndex())
            destination_text = self.destination_combo.itemText(self.destination_combo.currentIndex())
            QMessageBox.critical(mw, "Error", f"The chosen source field '{source_text}' is the same as the destination field '{destination_text}'.\nThis would overwrite the field you're reading from.\n\nTypically you want to read from a field like 'sentence' and output to 'audio', but in this case you're trying to read from 'sentence' and write to 'sentence' which cause your sentence to be overwritten")
        else:
            self.accept()

    def getNoteTextAndSpeaker(self, note_id):
        (speaker_index, speaker, style_info) = getSpeaker(self.speakers, self.speaker_combo, self.style_combo)
        source_field = self.source_combo.itemText(self.source_combo.currentIndex())
        note = mw.col.get_note(note_id)
        note_text = note[source_field]

        # Remove html tags https://stackoverflow.com/a/19730306
        tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
        entity_re = re.compile(r'(&[^;]+;)')

        note_text = entity_re.sub('', note_text)
        note_text = tag_re.sub('', note_text)

        # Remove stuff between brackets. Usually japanese cards have pitch accent and reading info in brackets like 「 タイトル[;a,h] を 聞[き,きく;h]いた わけ[;a] じゃ ない[;a] ！」
        if self.ignore_brackets_checkbox.isChecked():
            note_text = re.sub("\[.*?\]", "", note_text)
        note_text = re.sub(" ", "", note_text) # there's a lot of spaces for whatever reason which throws off the voice gen so we remove all spaces (japanese doesn't care about them anyway)
        
        return (note_text, speaker_index)

    def PreviewVoiceSample(self):
        (speaker_index, speaker, style_info) = getSpeaker(self.speakers, self.speaker_combo, self.style_combo)
        if speaker_index is None:
            raise Exception('getSpeaker returned None in PreviewVoiceSample')
            
        preview_sentences = ["こんにちは、これはテスト文章です。", "ＤＶＤの再生ボタンを押して、書斎に向かった。", "さてと 、 ご馳走様でした", "真似しないでくれる？", "な 、 なんだよ ？　 テンション高いな"]
            
        tup = (random.choice(preview_sentences), speaker_index)
        result = GenerateAudioQuery(tup, mw.addonManager.getConfig(__name__))
        contents = SynthesizeAudio(result, speaker_index)
        
        addon_path = dirname(__file__)
        preivew_path = join(addon_path, "VOICEVOX_preview.wav")
        with open(preivew_path, "wb") as f:
            f.write(contents)
        av_player.play_file(preivew_path)

    def PreviewVoiceActual(self):
        if not self.selected_notes:
            return
        (speaker_index, speaker, style_info) = getSpeaker(self.speakers, self.speaker_combo, self.style_combo)
        if speaker_index is None:
            raise Exception('getSpeaker returned None in PreviewVoiceActual')

        # If we've gone past the last note, restart from 0
        if self.preview_note_index >= len(self.selected_notes):
            self.preview_note_index = 0

        note_id = self.selected_notes[self.preview_note_index]
        config = mw.addonManager.getConfig(__name__)
        tup = self.getNoteTextAndSpeaker(note_id)

        result = GenerateAudioQuery(tup, config)
        contents = SynthesizeAudio(result, speaker_index)

        addon_path = dirname(__file__)
        preview_path = join(addon_path, "VOICEVOX_preview.wav")
        with open(preview_path, "wb") as f:
            f.write(contents)
        av_player.play_file(preview_path)

        self.preview_note_index += 1

def GenerateAudioQuery(text_and_speaker_index_tuple, config):
    try:
        text = text_and_speaker_index_tuple[0]
        speaker_index = text_and_speaker_index_tuple[1]
        audio_query_response = requests.post("http://127.0.0.1:50021/audio_query?speaker=" + str(speaker_index) + "&text=" + urllib.parse.quote(text, safe=''))
        if audio_query_response.status_code != 200:
            raise Exception(f"Unable to generate audio for the following text: `{text}`. Response code was {audio_query_response.status_code}\nResponse:{audio_query_response.text}")
            
        result = audio_query_response.text
        j = json.loads(result)
        if config.get('speed_slider_value'):
            j['speedScale'] = config.get('speed_slider_value') / 100;
        if config.get('volume_slider_value'):
            j['volumeScale'] = config.get('volume_slider_value') / 100;
        if config.get('pitch_slider_value'):
            j['pitchScale'] = config.get('pitch_slider_value') / 100;
        if config.get('intonation_slider_value'):
            j['intonationScale'] = config.get('intonation_slider_value') / 100;
        if config.get('initial_silence_slider_value'):
            j['prePhonemeLength'] = config.get('initial_silence_slider_value') / 100;
        if config.get('final_silence_slider_value'):
            j['postPhonemeLength'] = config.get('final_silence_slider_value') / 100;
        result = json.dumps(j, ensure_ascii=False).encode('utf8')
        return result
    except Exception as e:
        raise Exception(f"Unable to generate audio for the following text: `{text}`.\nResponse: {audio_query_response.text if audio_query_response is not None else 'None'}\n{traceback.format_exc()}")

def SynthesizeAudio(audio_query_json, speaker_index):
    synthesis_response = requests.post("http://127.0.0.1:50021/synthesis?speaker=" + str(speaker_index), data=audio_query_json)
    if synthesis_response.status_code != 200:
        return None
    return synthesis_response.content

def MultiSynthesizeAudio(audio_queries, speaker_index): # NOTE: This returns a zip
    for q in audio_queries:
        if q is None:
            raise Exception("MultiSynthesizeAudio recieved an audio query that was None")
    # Create json array of queries
    combined = b"[" + b','.join(audio_queries) + b"]"

    synthesis_response = requests.post("http://127.0.0.1:50021/multi_synthesis?speaker=" + str(speaker_index), data=combined)
    if synthesis_response.status_code != 200:
        return None
    return synthesis_response.content 

def DivideIntoChunks(array, n):
    # looping till length l
    for i in range(0, len(array), n):
        yield array[i:i + n]

def onVoicevoxOptionSelected(browser):
    voicevox_exists = False
    try:
        response = requests.get("http://127.0.0.1:50021/version", timeout=5)
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
        user_template = dialog.filename_template_edit.text()

        # Save previously used stuff
        config = mw.addonManager.getConfig(__name__)
        config['last_source_field'] = source_field
        config['last_destination_field'] = destination_field
        config['last_speaker_name'] = speaker_combo_text
        config['last_style_name'] = style_combo_text
        config['append_audio'] = "true" if dialog.append_audio.isChecked() else "false"
        config['use_opus'] = "true" if dialog.use_opus.isChecked() else "false"
        config['filename_template'] = user_template

        mw.addonManager.writeConfig(__name__, config)

        progress_window = qt.QWidget(None)
        progress_window.setWindowTitle("Generating VOICEVOX Audio")
        progress_window.setFixedSize(400, 80)

        progress_text = qt.QLabel("Generating Audio...")

        progress_bar = qt.QProgressBar(progress_window)

        progress_layout = qt.QVBoxLayout()
        progress_layout.addWidget(progress_text)
        progress_layout.addWidget(progress_bar)

        progress_window.setLayout(progress_layout)

        progress_window.show()
        progress_window.setFocus()

        def updateProgress(notes_so_far, total_notes, bottom_text = ''):
            progress_text.setText(f"Generating Audio {notes_so_far}/{total_notes}\n{bottom_text}")
            progress_bar.setMaximum(total_notes)
            progress_bar.setValue(notes_so_far)
            mw.app.processEvents()
        def sanitize_filename(filename: str, replacement: str = "_") -> str:
            # Replace problematic characters with a replacement character
            sanitized = re.sub(r'[<>:"/\\|?*]', replacement, filename)
            # Strip leading and trailing whitespaces and dots (Windows hates these)
            sanitized = sanitized.strip().strip(".")
            # Limit filename length to something reasonable (255 is typical for most filesystems)
            return sanitized[:255]

        # We split the work into chunks so we can pass a bunch of audio queries to the synthesizer instead of doing them one at time, but we don't want to do all of them at once so chunks make the most sense
        CHUNK_SIZE = 4
        note_chunks = DivideIntoChunks(dialog.selected_notes, CHUNK_SIZE)
        notes_so_far = 0
        total_notes = len(dialog.selected_notes)
        updateProgress(notes_so_far, total_notes)

        # Pre-cache user template for performance
        filename_template = config.get("filename_template", "VOICEVOX_{{speaker}}_{{style}}_{{uid}}")

        for note_chunk in note_chunks:
            note_text_and_speakers = map(dialog.getNoteTextAndSpeaker, note_chunk)
            updateProgress(notes_so_far, total_notes, f"Audio Query: {0}/{len(note_chunk)}")
            query_count = 0
            def GenerateQueryAndUpdateProgress(x, query_count):
                updateProgress(notes_so_far, total_notes, f"Audio Query: {query_count}/{len(note_chunk)}")
                query_count+=1
                return GenerateAudioQuery(x, config)

            audio_queries = list(map(lambda note: GenerateQueryAndUpdateProgress(note, query_count), note_text_and_speakers))
            media_dir = mw.col.media.dir()
            updateProgress(notes_so_far, total_notes, f"Synthesizing Audio {notes_so_far} to {min(notes_so_far+CHUNK_SIZE, total_notes)}")
            zip_bytes = MultiSynthesizeAudio(audio_queries, speaker_index)

            # MultiSynthesis returns zip bytes with ZIP_STORED
            zip_counter = 0
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r", zipfile.ZIP_STORED) as wavs_zip:
                for name in wavs_zip.namelist():
                    updateProgress(notes_so_far, total_notes, f"Converting Audio: {zip_counter}/{len(note_chunk)}")
                    zip_counter+=1
                    audio_data = wavs_zip.read(name)
                    chunk_note_index = int(name.replace('.wav', '')) - 1 # Starts at 001.wav, this converts to 0 index
                    note_id = note_chunk[chunk_note_index]
                    
                    audio_extension = "wav"

                    new_audio_format = "opus" if config['use_opus'] == "true" else "mp3"
                    new_audio_data = ffmpeg.ConvertWav(audio_data, new_audio_format)
                    if new_audio_data != None:
                        audio_data = new_audio_data
                        audio_extension = new_audio_format

                    # Build placeholders
                    note_obj = mw.col.get_note(note_id)
                    fields_map = {f: note_obj[f] for f in note_obj.keys()}
                    cards_of_note = note_obj.cards()
                    if cards_of_note:
                        deck_id = cards_of_note[0].did
                        deck_name = mw.col.decks.name(deck_id)
                    else:
                        deck_name = "UnknownDeck"

                    placeholders = {
                        "uid": str(uuid.uuid4()),
                        "speaker": speaker_combo_text,
                        "style": style_combo_text,
                        "deck": deck_name.split("::")[-1],
                        "deck-full": deck_name,
                        "date": datetime.datetime.now().date().isoformat(),
                        "fields": fields_map
                    }

                    raw_filename = parse_filename_template(filename_template, placeholders)
                    raw_filename = sanitize_filename(raw_filename)
                    # We'll add the final extension here
                    filename = f"{raw_filename}.{audio_extension}"

                    audio_full_path = join(media_dir, filename)

                    with open(audio_full_path, "wb") as f:
                        f.write(audio_data)

                    audio_field_text = f"[sound:{filename}]"
                    note = mw.col.get_note(note_id)
                    if config['append_audio'] == "true":
                        note[destination_field] += audio_field_text
                    else:
                        note[destination_field] = audio_field_text
                    mw.col.update_note(note)
                    mw.app.processEvents()
                    notes_so_far += 1
        mw.progress.finish()
        mw.reset() # reset mw so our changes are applied
    else:
        print("Canceled!")
