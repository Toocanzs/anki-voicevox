from aqt import mw
from aqt.utils import showInfo, getText, askUser, QMessageBox
from .setting_config import SETTING_MAP


class PresetManager:
    """Manages the saving, loading, renaming, and deletion of VOICEVOX presets."""

    def __init__(self, dialog_instance, addon_name: str) -> None:
        """
        Initializes the manager with a reference to the main dialog instance.

        Args:
            dialog_instance: The MyDialog instance (must have all UI widgets).
            addon_name: The name of the addon for config access.
        """
        # Store a weak reference if possible, but a direct reference is fine for this context
        self.dialog = dialog_instance
        self.addon_name = addon_name
        self._is_loading_preset = False

        # Connect UI signals to methods
        self.dialog.save_preset_button.clicked.connect(self.save_preset)
        self.dialog.rename_preset_button.clicked.connect(self.rename_preset)
        self.dialog.delete_preset_button.clicked.connect(self.delete_preset)
        self.dialog.preset_combo.currentIndexChanged.connect(self.load_preset)

        # Initialize the combo box data
        self.load_preset_names()

        # Set initial button states immediately on initialization
        self._update_button_states()

    def _get_config(self) -> dict:
        """Helper to get the addon configuration."""
        return mw.addonManager.getConfig(self.addon_name)

    def _write_config(self, config: dict):
        """Helper to write the addon configuration."""
        mw.addonManager.writeConfig(self.addon_name, config)

    def _get_default_settings(self) -> dict:
        """Gathers default settings from the imported SETTING_MAP."""
        default_settings = {}
        for key, setting_config in SETTING_MAP.items():
            if setting_config.default_value is not None:
                default_settings[key] = setting_config.default_value
        return default_settings

    def _apply_settings_to_ui(self, settings: dict):
        """Applies a dictionary of settings to the dialog's UI widgets."""
        self._is_loading_preset = True  # Set flag to disable change signals

        for key, setting_config in SETTING_MAP.items():
            value = settings.get(key)
            if value is None:
                continue

            widget = getattr(self.dialog, setting_config.attr_name, None)
            if widget is None:
                continue

            set_value = value
            # Apply loader function if needed (e.g., "true" -> True)
            if setting_config.loader_func and isinstance(value, str):
                set_value = setting_config.loader_func(value)

            try:
                setter = getattr(widget, setting_config.setter_name)
                # Temporarily block signals for widgets that don't need update logic until later
                # NOTE: Only speaker_combo needs its signal to fire (for style update)
                if not setting_config.emit_signal_on_load:
                    widget.blockSignals(True)

                setter(set_value)

                if not setting_config.emit_signal_on_load:
                    widget.blockSignals(False)

            except Exception as e:
                print(f"Error applying setting {setting_config.attr_name}: {e}")

        # Manually trigger style update if speaker combo was set without signal
        # This is necessary because we blockSignals on the style combo in load_preset
        if settings.get("speaker_name"):
            self.dialog.update_speaker_style_combo_box()

        self._is_loading_preset = False  # Reset flag

    def _update_button_states(self):
        """
        Enables/disables management buttons based on the currently selected preset.
        """
        # currentData() returns the actual preset name or "" for the "---" item.
        current_preset_name = self.dialog.preset_combo.currentData()

        # Check if a valid, non-Default preset is selected.
        is_valid_user_preset = (current_preset_name != "") and (
            current_preset_name != "Default"
        )

        # Rename, and Delete buttons are only enabled for user-defined presets
        self.dialog.rename_preset_button.setEnabled(is_valid_user_preset)
        self.dialog.delete_preset_button.setEnabled(is_valid_user_preset)

    def load_preset_names(self, select_name: str = None):
        """Loads preset names into the combo box."""
        config = self._get_config()
        all_presets = config.get("presets", {})

        self.dialog.preset_combo.blockSignals(True)
        self.dialog.preset_combo.clear()

        # Item 0: "---" (No Preset Selected)
        self.dialog.preset_combo.addItem("---", "")

        # Add existing presets
        # Insert 'Default' as the first selectable name (after "---")
        names = sorted(
            [name for name in all_presets.keys() if name != "Default"], key=str.lower
        )
        names.insert(0, "Default")

        target_name = select_name or config.get("last_preset", "")
        index_to_select = 0

        for i, name in enumerate(names):
            # i+1 because index 0 is "---"
            self.dialog.preset_combo.addItem(name, name)
            if name == target_name:
                index_to_select = i + 1

        # Hide the "---" item from the list view
        internal_view = self.dialog.preset_combo.view()
        internal_view.setRowHidden(0, True)

        self.dialog.preset_combo.setCurrentIndex(index_to_select)

        # Update button states after setting the index
        self._update_button_states()

        self.dialog.preset_combo.blockSignals(False)

    def load_preset(self):
        """Loads the selected preset from config and applies it to the UI."""
        preset_name = self.dialog.preset_combo.currentData()
        if not preset_name:
            # "---" is selected, do nothing
            return

        config = self._get_config()
        all_presets = config.get("presets", {})

        # Ensure Default is available if needed
        if not ("Default" in all_presets):
            all_presets["Default"] = self._get_default_settings()

        preset_settings = all_presets.get(preset_name)

        if preset_settings:
            # Apply settings to the UI
            self._apply_settings_to_ui(preset_settings)

            # Update button states after loading is complete
            self._update_button_states()

            # Save the last loaded preset name
            config["last_preset"] = preset_name
            self._write_config(config)

    def save_preset(self):
        """Prompts for a name and saves current dialog settings as a preset."""

        # Use self.dialog.get_current_settings() to grab data
        current_preset_name = (
            self.dialog.preset_combo.currentData() or "New Preset Name"
        )

        preset_name, ok = getText(
            "Enter a name for the new preset:", default=current_preset_name
        )

        if not ok or not preset_name.strip():
            return

        preset_name = preset_name.strip()
        settings_to_save = self.dialog.get_current_settings()

        config = self._get_config()
        all_presets = config.get("presets", {})

        if preset_name == "Default":
            QMessageBox.warning(
                self.dialog,
                "Action Blocked",
                f"Cannot overwrite the 'Default' preset.\nPlease choose a different name.",
            )
            return

        if preset_name in all_presets:
            confirm = askUser(
                f"A preset named '{preset_name}' already exists.\nDo you want to overwrite it?",
                title="Overwrite Preset",
                defaultno=True,
            )
            if not confirm:
                return

        all_presets[preset_name] = settings_to_save
        config["presets"] = all_presets
        self._write_config(config)

        self.load_preset_names(select_name=preset_name)
        showInfo(f"Preset '{preset_name}' saved successfully!")

    def rename_preset(self):
        """Prompts for a new name and renames the current preset."""

        current_preset_name = self.dialog.preset_combo.currentData()
        # Checks and rename logic
        if not current_preset_name:
            showInfo("Please select a valid preset to rename.")
            return

        if current_preset_name == "Default":
            QMessageBox.warning(
                self.dialog,
                "Action Blocked",
                f"The 'Default' preset cannot be renamed.",
            )
            return

        new_preset_name, ok = getText(
            f"Rename preset '{current_preset_name}' to:", default=current_preset_name
        )
        # Validation and config update

        if not ok or not new_preset_name.strip():
            return

        new_preset_name = new_preset_name.strip()

        if new_preset_name == current_preset_name:
            showInfo("Preset name was not changed.")
            return

        config = self._get_config()
        all_presets = config.get("presets", {})

        if new_preset_name == "Default":
            QMessageBox.warning(
                self.dialog, "Action Blocked", "Cannot rename to 'Default'."
            )
            return

        if new_preset_name in all_presets:
            QMessageBox.warning(
                self.dialog,
                "Action Blocked",
                f"A preset named '{new_preset_name}' already exists.",
            )
            return

        settings_to_rename = all_presets.pop(current_preset_name)
        all_presets[new_preset_name] = settings_to_rename

        if config.get("last_preset") == current_preset_name:
            config["last_preset"] = new_preset_name

        config["presets"] = all_presets
        self._write_config(config)

        self.load_preset_names(select_name=new_preset_name)
        showInfo(f"Preset renamed to '{new_preset_name}' successfully!")

    def delete_preset(self):
        """Deletes the selected preset from config."""

        current_preset_name = self.dialog.preset_combo.currentData()

        if not current_preset_name:
            showInfo("Please select a preset to delete.")
            return

        if current_preset_name == "Default":
            QMessageBox.warning(
                self.dialog, "Action Blocked", "The 'Default' preset cannot be deleted."
            )
            return

        confirm = askUser(
            f"Are you sure you want to delete the preset '{current_preset_name}'?",
            title="Confirm Deletion",
            defaultno=True,
        )
        if not confirm:
            return

        old_index = self.dialog.preset_combo.currentIndex()

        config = self._get_config()
        all_presets = config.get("presets", {})

        if current_preset_name in all_presets:
            del all_presets[current_preset_name]
        else:
            showInfo(f"Preset '{current_preset_name}' not found.")
            return

        if config.get("last_preset") == current_preset_name:
            config["last_preset"] = ""

        config["presets"] = all_presets
        self._write_config(config)

        self.load_preset_names()

        # Select the closest item after deletion
        new_index = min(old_index, self.dialog.preset_combo.count() - 1)
        self.dialog.preset_combo.setCurrentIndex(new_index)
        self.load_preset()

        showInfo(f"Preset '{current_preset_name}' deleted successfully!")

    def clear_preset_selection(self):
        """Sets the preset combo box back to the '---' option."""
        if self._is_loading_preset:
            return

        current_data = self.dialog.preset_combo.currentData()
        if current_data:
            self.dialog.preset_combo.blockSignals(True)
            self.dialog.preset_combo.setCurrentIndex(0)
            self.dialog.preset_combo.blockSignals(False)

        # Update states even if no selection was cleared
        self._update_button_states()
