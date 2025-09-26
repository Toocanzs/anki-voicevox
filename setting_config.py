from dataclasses import dataclass
from typing import Union

@dataclass
class SettingConfig:
    """Configuration metadata for each setting in MyDialog.SETTING_MAP."""

    attr_name: str  # Widget attribute name (e.g., "volume_slider")
    getter_name: str  # Method to read value (e.g., "value")
    setter_name: str  # Method to write value (e.g., "setValue")

    # Optional conversion functions, default to None (direct use)
    loader_func: callable = (
        None  # Function for type conversion during loading (str -> bool/int/etc.)
    )
    saver_func: callable = (
        None  # Function for type conversion during saving (bool/int/etc. -> str/primitive)
    )

    # Default value for the setting
    # Use None for settings that must be dynamically determined
    default_value: Union[str, bool, int, float, None] = None

    # Whether to emit the signal after setting the value on load (used for speaker_combo)
    emit_signal_on_load: bool = False

    # We add a way to group fields visually (optional, but helpful for big maps)
    group: str = "General"


def bool_to_str(value: bool) -> str:
    """Converts boolean check state to config string 'true' or 'false'."""
    return "true" if value else "false"


def str_to_bool(value: str) -> bool:
    """Converts config string 'true' or 'false' to boolean check state."""
    return value.lower() == "true"


# Define the mapping of config keys to UI widget attributes and their getter/setter methods
# We use the dataclsss SettingConfig for clarity
SETTING_MAP = {
    # Text and Combo Boxes (most fields use default None for conversion)
    "source_field": SettingConfig(
        "source_combo", "currentText", "setCurrentText", group="Fields"
    ),
    "destination_field": SettingConfig(
        "destination_combo", "currentText", "setCurrentText", group="Fields"
    ),
    "filename_template": SettingConfig(
        "filename_template_edit",
        "text",
        "setText",
        default_value="VOICEVOX_{{speaker}}_{{style}}_{{uid}}",
        group="General",
    ),
    # Speaker/Style: Needs emit_signal_on_load=True to update styles combo
    "speaker_name": SettingConfig(
        "speaker_combo",
        "currentText",
        "setCurrentText",
        default_value="四国めたん",
        emit_signal_on_load=True,
        group="Voice",
    ),
    "style_name": SettingConfig(
        "style_combo",
        "currentText",
        "setCurrentText",
        default_value="ノーマル",
        group="Voice",
    ),
    # Boolean Checkboxes: Needs both loader_func and saver_func
    "append_audio": SettingConfig(
        "append_audio",
        "isChecked",
        "setChecked",
        loader_func=str_to_bool,
        saver_func=bool_to_str,
        default_value=False,
        group="File Options",
    ),
    "use_opus": SettingConfig(
        "use_opus",
        "isChecked",
        "setChecked",
        loader_func=str_to_bool,
        saver_func=bool_to_str,
        default_value=False,
        group="File Options",
    ),
    # Sliders: All use default settings
    "volume_slider_value": SettingConfig(
        "volume_slider", "value", "setValue", default_value=100, group="Sliders"
    ),
    "pitch_slider_value": SettingConfig(
        "pitch_slider", "value", "setValue", default_value=0, group="Sliders"
    ),
    "speed_slider_value": SettingConfig(
        "speed_slider", "value", "setValue", default_value=100, group="Sliders"
    ),
    "intonation_slider_value": SettingConfig(
        "intonation_slider", "value", "setValue", default_value=100, group="Sliders"
    ),
    "initial_silence_slider_value": SettingConfig(
        "initial_silence_slider", "value", "setValue", default_value=10, group="Sliders"
    ),
    "final_silence_slider_value": SettingConfig(
        "final_silence_slider", "value", "setValue", default_value=10, group="Sliders"
    ),
}
