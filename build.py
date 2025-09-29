import json
from setting_config import SETTING_MAP
from zipfile import ZipFile, ZIP_DEFLATED
import os

# --- Configuration ---

# The name of the final Anki addon file.
ADDON_NAME = "VOICEVOX Audio Generator.ankiaddon"

CONFIG_FILE = "config.json"

# List of files and directories to be included in the archive.
# If a folder is listed, its entire contents will be added recursively.
ADDON_ENTRIES = [
    "__init__.py",
    "ffmpeg.py",
    "voicevox_gen.py",
    "setting_config.py",
    "preset_manager.py",
    CONFIG_FILE,
    "config.md",
    "manifest.json",
    "README.md",
]

# List of patterns to ignore (case-insensitive check for folder/file names).
IGNORED_PATTERNS = [
    # Folders/Paths to ignore
    "__pycache__",
    ".git",
    ".vscode",
    # Files to ignore
    "build.py",  # Ignore the script itself
    "build.bat",
]


def dump_config(file_name: str) -> None:
    """Generates the default config.json file based on SETTING_MAP and writes it to disk."""
    config = {"presets": {}}
    default_preseet = {}

    for name, row in SETTING_MAP.items():
        value = row.default_value
        func = row.saver_func

        if value is None:
            continue
        if func:
            value = func(value)

        default_preseet[name] = value

    config["presets"]["Default"] = default_preseet

    # Write the formatted JSON to the specified file
    with open(file_name, "w") as f:
        # Using indent=4 makes the generated JSON human-readable
        f.write(json.dumps(config, indent=4))


def create_anki_addon_archive(addon_name: str, entries: list[str]) -> None:
    """
    Creates the Anki addon archive file, supporting files and recursive folders,
    while respecting the IGNORED_PATTERNS list.

    :param addon_name: The name of the resulting zip file.
    :param entries: A list of file or folder paths to include in the archive.
    """
    print(f"Starting to create archive: {addon_name}")

    try:
        # Use 'w' mode to overwrite any existing file. compresslevel=9 for max compression.
        with ZipFile(addon_name, "w", ZIP_DEFLATED, compresslevel=9) as zf:
            for entry in entries:
                if not os.path.exists(entry):
                    print(f"  ! Warning: Entry not found and skipped: {entry}")
                    continue

                # Check if the top-level entry itself should be ignored
                if any(p in entry.lower() for p in IGNORED_PATTERNS):
                    print(f"  - Ignored Entry: {entry}")
                    continue

                if os.path.isfile(entry):
                    # For files, write directly to the root of the archive
                    zf.write(entry, entry)
                    print(f"  + Added File: {entry}")

                elif os.path.isdir(entry):
                    print(f"  + Adding Folder: {entry}/...")

                    # Recursively walk the directory
                    for foldername, _, filenames in os.walk(entry):
                        # Check if the folder path contains any ignored pattern
                        if any(p in foldername.lower() for p in IGNORED_PATTERNS):
                            print(f"  - Ignored Folder: {foldername}")
                            continue

                        for filename in filenames:
                            # Check if the file name itself should be ignored
                            if any(p in filename.lower() for p in IGNORED_PATTERNS):
                                continue

                            # Construct full local path
                            filepath = os.path.join(foldername, filename)
                            # The name inside the zip archive (preserves relative path)
                            arcname = filepath

                            zf.write(filepath, arcname)
                            print(f"  > Added: {arcname}")

                else:
                    print(f"  ! Warning: Unknown entry type skipped: {entry}")

        print(f"\nSuccessfully created/updated the addon: {addon_name}")

    except Exception as e:
        print(f"An unexpected error occurred during zipping: {e}")


if __name__ == "__main__":
    # Ensure config.json is generated/updated
    dump_config(CONFIG_FILE)

    # Execute the packaging process
    create_anki_addon_archive(ADDON_NAME, ADDON_ENTRIES)
