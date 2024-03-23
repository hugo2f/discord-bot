from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import sys
from collections import defaultdict
import json
import atexit
import os




# initialize pydrive
google_auth = GoogleAuth()
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
    # remove unnecessary entries in VOLUMES
    to_remove = []
    for audio, volume in volumes.items():
        if not (os.path.exists(f'audios/{audio}.mp3')
                or os.path.exists(f'audios/{audio}.m4a')) \
                or volume == DEFAULT_VOLUME:
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
    msg_file.SetContentString(json.dumps(msg_counts, indent=4))
    msg_file.Upload()
    print('msg.json updated in Google Drive')
