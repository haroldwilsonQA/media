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
    sys.stderr.flush()
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


class PodcastListWidget(QListWidget):

    # -------------------------------------------------------------------------
    def __init__(self, parent=None):
        super().__init__()
        # self = QListWidget()

    # -------------------------------------------------------------------------
    def clear_podcast_list(self):
        """ Clear the podcast player list of all entries"""
        self.clear()

    # -------------------------------------------------------------------------
    def populate_list_items(self,
                            station_id         ,
                            api_version = "v1" ,
                            icon_height = 100  ,
                            icon_width  = 100  ):
        """ Given a station id,
            populate the podcast list with a podcast ID,
            podcast title and podcast image for each podcast in the list."""

        # Call out to the api and get a list podcast attributes
        podcast_attributes = api_utils.station_id_2_podcast_list(station_id)

        for item in podcast_attributes:

            # Create  new list item for the list widget
            list_item = QListWidgetItem(self)

            if api_version == "v1":

                # TODO: Make this a parallel call with QThread
                # Download the image for the podcast and add it to the list item
                podcast_image_file = podcast_player_utils.download_station_logo(item["attributes"]["image"])
                podcast_icon = QIcon(podcast_image_file)
                list_item.setIcon(podcast_icon)
                self.setIconSize(QSize(icon_width, icon_height))

                # Populate the podcastListWidget
                list_item.setText("Podcast ID: %s\n%s" % (str(item["id"]),
                                                          str(item["attributes"]["title"])))

            elif api_version == "v2":
                pass
            else:
                pass
