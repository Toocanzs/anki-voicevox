from os.path import dirname, join, exists
import os
import stat
import requests
import json
from anki.utils import is_mac, is_win, is_lin
from aqt import mw
from anki.hooks import addHook
import zipfile
import subprocess

class FFmpegInstaller:
    def __init__(self):
        self.addonPath = dirname(__file__)
        self.can_convert = False

        self.ffmpeg_filename = "ffmpeg"
        if is_win:
            self.ffmpeg_filename += ".exe"

        self.full_ffmpeg_path = join(self.addonPath, self.ffmpeg_filename)

    def GetFFmpegIfNotExist(self):
        if exists(self.full_ffmpeg_path) or self.can_convert:
            self.can_convert = True
            return

        speakers_response = requests.get("https://ffbinaries.com/api/v1/version/6.1")
        download_url = None
        if speakers_response.status_code == 200:
            binaries_json = json.loads(speakers_response.content)
            if is_win:
                download_url = binaries_json['bin']['windows-64']['ffmpeg']
            elif is_lin:
                download_url = binaries_json['bin']['linux-64']['ffmpeg']
            elif is_mac:
                download_url = binaries_json['bin']['osx-64']['ffmpeg']
            else:
                return
        else:
            return
        
        try:
            temp_file_path = join(self.addonPath, "ffmpeg.zip")
            # Download zip
            with requests.get(download_url, stream=True) as ffmpeg_request:
                ffmpeg_request.raise_for_status()
                with open(temp_file_path, 'wb') as ffmpeg_file:
                    total_bytes = int(ffmpeg_request.headers['Content-Length'])
                    bytes_so_far = 0
                    for chunk in ffmpeg_request.iter_content(chunk_size=8192):
                        if chunk:
                            bytes_so_far += len(chunk)
                            ffmpeg_file.write(chunk)
            # Extract zip
            with zipfile.ZipFile(temp_file_path) as zf:
                zf.extractall(dirname(self.full_ffmpeg_path))
            if exists(self.full_ffmpeg_path):
                # Mark executable on platforms that need that
                if not is_win:
                    try:
                        st = os.stat(self.full_ffmpeg_path)
                        os.chmod(self.full_ffmpeg_path, st.st_mode | stat.S_IEXEC)
                    except:
                        print("Failed to mark ffmpeg as executable")
                os.remove(temp_file_path)
                self.can_convert = True
        except:
            print("FFmpeg failed")

ffmpegInstaller = FFmpegInstaller()

def ConvertWavToMp3(wav_data):
    if not ffmpegInstaller.can_convert:
        return None
    try:
        # If windows provide additional flags to subprocess.Popen
        if is_win:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # On MacOS, subprocess.STARTUPINFO() does not exist
            startupinfo = None
        
        process = subprocess.Popen([ffmpegInstaller.full_ffmpeg_path, '-y', '-nostats', '-hide_banner', '-i', 'pipe:', '-f', 'mp3', "-qscale:a", "3", '-'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE, startupinfo=startupinfo)
        output = process.communicate(input=wav_data)[0]
        return output
    except Exception as e:
        print("VoiceVox conversion error:", e)
        return None

addHook("profileLoaded", ffmpegInstaller.GetFFmpegIfNotExist)
