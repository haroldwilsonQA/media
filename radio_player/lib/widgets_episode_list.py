#/usr/local/bin/python3

import sys
import os
import json

VERSION       = "1.0.0"
DEBUG         = True
VERBOSE       = True
FIRST         = 0
LAST          = -1
ME            = os.path.split(sys.argv[FIRST])[LAST]  # Name of this file
MY_PATH       = os.path.dirname(os.path.realpath(__file__))  # Path for this file
CONFIG_PATH   = os.path.join(MY_PATH, "../config")
CONFIG_FILE   = os.path.join(CONFIG_PATH, "podcast_player.conf")
LIBRARY_PATH  = MY_PATH

# import third-party libraries
try:
    from PyQt5.QtWidgets import (QListWidget, QListWidgetItem)
    from PyQt5.QtGui import (QPixmap, QFont, QIcon)
    from PyQt5.QtCore import (Qt, pyqtSignal, QSize)


except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'PyQt5' library\n")
    sys.stderr.write("         try: pip3 install pyqt5 --user\n")
    sys.stderr.flush
    sys.exit(99)

# import custom libraries
sys.path.append(LIBRARY_PATH)
try:
    import podcast_player_utils
except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'podcast_player_utils' library\n")
    sys.stderr.write("         try: git pull\n")
    sys.stderr.flush()
    sys.exit(98)

try:
    import api_utils
except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'api_utils' library\n")
    sys.stderr.write("         try: git pull\n")
    sys.stderr.flush()
    sys.exit(98)


class EpisodesListWidget(QListWidget):

    # -------------------------------------------------------------------------
    def __init__(self, parent=None):
        super().__init__()
        # self = QListWidget()

    # -------------------------------------------------------------------------
    def clear_episodes_list(self):
        """ Clear the Episodes list of all entries"""
        self.clear()
    # -------------------------------------------------------------------------
    def populate_list_items(self               ,
                            podcast_id         ,
                            api_version = "v1" ,
                            icon_height = 100  ,
                            icon_width  = 100  ):
        """ Given a podcast_id ,
            populate the episodes list with an Episode ID,
            Episode Title, Episode Published Date, Duration, and podcast image."""

        # Start with a clean list
        self.clear_episodes_list()

        # We use the same image for every episode in the list so we really only
        # need to download the one image and use it for every list item
        # TODO: Come up with a cool caching mechanism for this and all image downloads

        if api_version == "v1":
            episode_image_url = api_utils.podcast_id_2_image_url(podcast_id, api_version="v1")
        elif api_version == "v2":
            episode_image_url = api_utils.podcast_id_2_image_url(podcast_id, api_version="v2")
        else:
            pass

        # Download the image file to be used for all episodes in the list
        episode_image_file = podcast_player_utils.download_station_logo(episode_image_url)

        # Call out to the api and get a list episode attributes
        episode_attributes = api_utils.podcast_id_2_episodes(podcast_id)

        for item in episode_attributes:

            # Create new list item for the list widget
            list_item = QListWidgetItem(self)

            # Add episode data to the newly created list item
            if api_version == "v1":

                # TODO: Make this a parallel call with QThread
                # Download the image for the podcast and add it to the list item
                episode_icon = QIcon(episode_image_file)
                list_item.setIcon(episode_icon)
                self.setIconSize(QSize(icon_width, icon_height))

                # Populate the podcastListWidget
                # Populate the podcastListWidget
                list_item.setText("Episode ID: %s\n%s\n%s\n%s" % (str(item["id"])                            ,
                                                                  str(item["attributes"]["title"])           ,
                                                                  str(item["attributes"]["published_date"])  ,
                                                                  str(item["attributes"]["duration_seconds"])))

            elif api_version == "v2":
                pass
            else:
                pass
