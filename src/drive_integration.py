from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import sys
from collections import defaultdict
import json
import atexit
import os
from constants import CURRENT_DIR, AUDIO_NAMES

# initialize pydrive
credentials_path = os.path.join(CURRENT_DIR, '..', 'credentials.json')
settings_path = os.path.join(CURRENT_DIR, '..', 'settings.yaml')

google_auth = GoogleAuth(settings_file=settings_path)
google_auth.LoadCredentialsFile(credentials_path)
drive = GoogleDrive(google_auth)

# initialize msg_counts
file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
msg_file = None
for file in file_list:
    if file['title'] == 'msg.json':
        msg_file = file
        break

msg_counts = None
if msg_file:
    msg_file_content = msg_file.GetContentString()
    msg_counts = defaultdict(int, json.loads(msg_file_content))
    print('Current msg.json:', msg_counts)
else:
    print("'msg.json' not found")
    sys.exit()

# initialize audio volumes
volume_file = None
for file in file_list:
    if file['title'] == 'volumes.json':
        volume_file = file
        break

volumes = None
if volume_file:
    DEFAULT_VOLUME = 0.4
    volume_file_content = volume_file.GetContentString()
    volumes = defaultdict(lambda: DEFAULT_VOLUME, json.loads(volume_file_content))
else:
    print("'volumes.json' not found")
    sys.exit()

@atexit.register
def update_volumes():
    global volumes_changed
    if not volumes_changed:
        print('volumes not changed')
        return

    # remove unnecessary entries in VOLUMES
    to_remove = []
    for audio, volume in volumes.items():
        if audio not in AUDIO_NAMES or volume == DEFAULT_VOLUME:
            to_remove.append(audio)
    for audio in to_remove:
        del volumes[audio]

    volume_file.SetContentString(json.dumps(volumes, indent=4))
    volume_file.Upload()
    print('volume.json updated in Google Drive')


@atexit.register
def update_msg_counts():
    """
    Updates the msg.json file when the bot is exited.
    """
    global msg_counts_changed
    if not msg_counts_changed:
        print('msg_counts not changed')
        return
    msg_file.SetContentString(json.dumps(msg_counts, indent=4))
    msg_file.Upload()
    print('msg.json updated in Google Drive')

volumes_changed = False
msg_counts_changed = False


def set_volumes_changed():
    global volumes_changed
    volumes_changed = True


def set_msgs_counts_changed():
    global msg_counts_changed
    msg_counts_changed = True
