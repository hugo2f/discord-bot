import atexit
import json
import os
import subprocess
import sys
from collections import defaultdict

from constants import AUDIO_NAMES

# initialize audio volumes
VOLUMES_DIR = os.path.join('..', 'volumes.json')
DEFAULT_VOLUME = 0.4
volumes = None
volumes_changed = False

def set_volumes_changed():
    global volumes_changed
    volumes_changed = True

def fetch_newest_volumes():
    try:
        # Fetch the latest changes from the remote repository
        subprocess.run(["git", "fetch"], check=True)

        # Checkout only the latest version of volumes.json
        subprocess.run(["git", "checkout", "origin/main", "--", "../volumes.json"], check=True)

        print("Successfully fetched volumes.json")

    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch newest volumes: {e}")


def initialize_volumes():
    global volumes
    try:
        with open(VOLUMES_DIR, "r", encoding="utf-8") as f:
            volume_file_content = f.read()
            volumes = defaultdict(lambda: DEFAULT_VOLUME, json.loads(volume_file_content))
    except FileNotFoundError:
        print(f"'{VOLUMES_DIR}' not found")
        sys.exit()
    except json.JSONDecodeError:
        print(f"Error: Failed to parse '{VOLUMES_DIR}'. Ensure it contains valid JSON.")
        sys.exit()


@atexit.register
def update_volumes():
    global volumes_changed
    if not volumes or not volumes_changed:
        print('Volumes not changed, no need to push to GitHub')
        return

    # remove unnecessary entries in VOLUMES
    to_remove = []
    for audio, volume in volumes.items():
        if audio not in AUDIO_NAMES or volume == DEFAULT_VOLUME:
            to_remove.append(audio)
    for audio in to_remove:
        del volumes[audio]

    # Push to GitHub
    try:
        subprocess.run(["git", "add", "volumes.json"], check=True)
        subprocess.run(["git", "commit", "-m", "update volumes.json"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print('volumes.json pushed to GitHub')
    except subprocess.CalledProcessError as e:
        print(f'Failed to push volumes.json: {e}')


# Startup
fetch_newest_volumes()
initialize_volumes()