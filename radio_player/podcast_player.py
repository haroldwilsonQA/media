#!/usr/local/bin/python3

# RADIO.COM	Podcast and Station Player for QA to use to validate API info and
# streaming performance.
#
# Special notes:
#    1.) Requires Python 3 ,PyQt5, Requests and VLC libraries
#    2.) Return codes:
#          99 --> Unable to import third party libraries
#          98 --> Unable to import custom libraries

# H. Wilson, April 2019

# Standard Library imports
import sys
import time
import os
import json
import pprint
from threading import (Thread)

# Dictionary of variables
VERSION        = "1.4.0"
VERBOSE        = False
DEBUG          = False
FIRST          = 0
LAST           = -1
ME             = os.path.split(sys.argv[FIRST])[LAST]  # Name of this file
MY_PATH        = os.path.dirname(os.path.realpath(__file__))  # Path for this file
RESOURCE_PATH  = os.path.join(MY_PATH, "./res")
LIBRARY_PATH   = os.path.join(MY_PATH, "./lib")
CONFIG_PATH    = os.path.join(MY_PATH, "./config")
CACHE_PATH     = os.path.join("/tmp")
CONFIG_FILE    = os.path.join(CONFIG_PATH, "podcast_player.conf")
THREAD_MONITOR = []
PRODUCTION     = "production"
STAGING        = "staging"
DEVELOPMENT    = "development"


# Third party library imports
try:
    import vlc
except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'vlc' library\n")
    sys.stderr.write("         try: pip3 install python-vlc --user\n")
    sys.stderr.flush()
    sys.exit(99)

try:
    import requests
except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'requests' library\n")
    sys.stderr.write("         try: pip3 install requests --user\n")
    sys.stderr.flush()
    sys.exit(99)

try:
    from PyQt5.QtWidgets import (QApplication, QWidget)
    from PyQt5.QtWidgets import (QGridLayout, QVBoxLayout, QHBoxLayout, QBoxLayout)
    from PyQt5.QtWidgets import (QLabel, QComboBox, QTabWidget, QTextEdit, QLineEdit)
    from PyQt5.QtWidgets import (QSlider, QDial, QScrollBar, QListWidget, QListWidgetItem)
    from PyQt5.QtGui import (QPixmap, QFont, QIcon)
    from PyQt5.QtCore import (Qt, pyqtSignal, QSize)

except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'PyQt5' library\n")
    sys.stderr.write("         try: pip3 install pyqt5 --user\n")
    sys.stderr.flush()
    sys.exit(99)

# Custom library imports
sys.path.append(LIBRARY_PATH)
try:
    import podcast_player_utils
except ModuleNotFoundError:
    sys.stderr.write("ERROR -- Unable to import the 'podcast_player_utils' library\n")
    sys.stderr.write("         try: git pull\n")
    sys.stderr.flush()
    sys.exit(98)

# Read configurations from the configuration file
CONFIGS = podcast_player_utils.config_2_dictionary(CONFIG_FILE)

# Assign base urls for different environments from config file
CONFIG_PATH   = os.path.join(MY_PATH, "../config")
api_base_urls = {}
api_base_urls[PRODUCTION]  = CONFIGS["prod_base_url"]
api_base_urls[STAGING]     = CONFIGS["stg_base_url"]
api_base_urls[DEVELOPMENT] = CONFIGS["dev_base_url"]

# Get the v2 api auth token from the config file
# and use it to define a header dictionary for
# v2 requests.get() calls
v2_api_auth_token = CONFIGS["v2_api_auth_token"]
api_header = {"Authorization": v2_api_auth_token}


# This is total BS! I have to make QLabel clickable with my bare hands
class ExtendedQLabel(QLabel):
    """ Extends the QLable object to make it clickable, Grrrr! """

    def __init(self, parent):
        super().__init__(parent)

    clicked = pyqtSignal()
    rightClicked = pyqtSignal()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            self.clicked.emit()

# MAIN WINDOW CLASS ===========================================================
class mainWindow(QWidget):

    # -------------------------------------------------------------------------
    def __init__(self):
        """ Constructor for the main window of the appilication """

        # ---
        super().__init__()

        self.environment_list          = ["development", "staging", "production"]
        self.api_version_list          = ["v1", "v2"]
        self.environment               = ""
        self.api_version               = ""
        self.selected_station_id       = 0
        self.selected_station_callsign = ""
        self.list_of_podcasts          = []
        self.selected_podcast_id       = 0
        self.list_of_episodes          = []
        self.selected_episode_id       = 0
        self.player_states             = ["Not Ready", "Media Ready", "Playing"]
        self.station_player_state      = self.player_states[0]
        self.episode_player_state      = self.player_states[0]
        self.station_ids               = {}

        # --- Define the logo for the application
        #
        self.logo = QLabel()
        pixmap = QPixmap(os.path.join(RESOURCE_PATH, CONFIGS["logo"]))
        self.logo.setPixmap(pixmap)

        # --- Define the selectors for Environment, API Version and Station
        #     and their associated labels
        self.station_selector     = QComboBox()
        self.api_version_selector = QComboBox()
        self.environment_selector = QComboBox()
        self.station_selector_label     = QLabel("Select\nStation\nCallsign")
        self.api_version_selector_label = QLabel("API Version")
        self.environment_selector_label = QLabel("Environment")

        # --- Define the Comm Log text area


        # --- Define the station logo widget and associated callsign label
        self.station_logo_image = QLabel()
        pixmap = QPixmap(os.path.join(RESOURCE_PATH, "no_image.jpg"))
        pixmap_resized = pixmap.scaled(200, 200, Qt.KeepAspectRatio)
        self.station_logo_image.setPixmap(pixmap_resized)
        self.staton_callsign_label = QLabel("No Station Selected")


        # --- Define the station List Widget
        self.station_details_labels = []
        self.station_details_values = []

        # --- Define the Podcast List Widget
        self.PodcastListWidget = QListWidget()
        self.PodcastListWidget.setSelectionMode(1) # 1 = SingleSelection, 2 = MultiSelection
        self.podcast_details_labels = []
        self.podcast_details_values = []

        # --- Define the Episodes List Widget
        self.EpisodesListWidget = QListWidget()
        self.EpisodesListWidget.setSelectionMode(1) # 1 = SingleSelection, 2 = MultiSelection
        self.episode_details_labels = []
        self.episode_details_values = []

        # --- Define the Communication Log text area
        self.commLogTextArea = QTextEdit()
        self.commLogTextArea.setFont(QFont('SansSerif', 10))

        # --------------------------------------------------------------------- ------------ TAB AREA
        # --- Define the Tab Area of the window
        self.tabArea = QTabWidget()
        self.tabArea.setFont(QFont('SansSerif', 22, QFont.Bold))
        self.station_tab  = QWidget()
        self.podcasts_tab = QWidget()
        self.episodes_tab = QWidget()
        self.commLog_tab  = QWidget()
        # Add individual tabs to the tabs area
        self.tabArea.addTab(self.station_tab,  "Station")
        self.tabArea.addTab(self.podcasts_tab, "Podcasts")
        self.tabArea.addTab(self.episodes_tab, "Episodes")
        self.tabArea.addTab(self.commLog_tab,  "Comm Log")
        # Define the size and shape of the tabs
        self.tabArea.resize(300, 200)
        self.tabArea.setTabShape(8)

        # --- Define the station player widget
        self.StationPlayer = vlc.MediaPlayer()
        self.station_player_label  = QLabel("Media Not Loaded")
        self.station_player_button = ExtendedQLabel()  # Because QLabel is not clickable
        self.station_player_state  = self.player_states[0] # Not Ready

        # --- Define the episode player widget
        self.EpisodePlayer = vlc.MediaPlayer()
        self.episode_player_label  = QLabel("Media Not Loaded")
        self.episode_player_button = ExtendedQLabel()  # Because QLabel is not clickable
        self.episode_player_state  = self.player_states[0] # Not Ready

        # --------------------------------------------------------------------- ------------ STATIONS TAB
        # --- Add widgets to the Stations tab
        self.station_tab.layout = QGridLayout(self)
        self.station_tab.layout.addWidget(self.staton_callsign_label, 0, 0, 1, 1)
        self.station_tab.layout.addWidget(self.station_logo_image,    1, 0, 1, 3)
        self.station_tab.layout.addWidget(self.station_player_label,  1, 3, 1, 1)
        self.station_tab.layout.addWidget(self.station_player_button, 1, 4, 1, 1)
        # Get a realtime list of station attributes for the station detail labels
        # All stations return the same attributes with different values so we just
        # pick a station more or less at random to get a list of attributes
        station_attributes = self.get_station_attributes(3)

                                                              # api_version=self.api_version_selector.currentText(),
                                                              # environment=self.environment_selector.currentText())
        if len(station_attributes) < 60:
            sys.exit(1)

        for item in station_attributes.keys():
            station_detail_label = QLabel(item)
            station_detail_label.setAlignment(Qt.AlignRight)
            self.station_details_labels.append(station_detail_label)

        # TODO: Change this to one nested loop
        row = 2
        counter = 0
        for item in self.station_details_labels[0:18]:
            self.station_tab.layout.addWidget(item, row, 0, 1, 1)
            self.station_details_values.append(QLineEdit())
            self.station_tab.layout.addWidget(self.station_details_values[counter], row, 1, 1, 1)
            row += 1
            counter += 1

        row = 2
        for item in self.station_details_labels[18:36]:
            self.station_tab.layout.addWidget(item, row, 3, 1, 1)
            self.station_details_values.append(QLineEdit())
            self.station_tab.layout.addWidget(self.station_details_values[counter], row, 4, 1, 1)
            row += 1
            counter += 1

        row = 2
        for item in self.station_details_labels[36:54]:
            self.station_tab.layout.addWidget(item, row, 6, 1, 1)
            self.station_details_values.append(QLineEdit())
            self.station_tab.layout.addWidget(self.station_details_values[counter], row, 7, 1, 1)
            row += 1
            counter += 1

        # --- Set the layout for the stations tab area
        self.station_tab.setLayout(self.station_tab.layout)
        # ---------------------------------------------------------------------

        # --------------------------------------------------------------------- ------------ PODCAST TAB
        # --- Add widgets to the Podcasts tab
        # --- Specify a grid layout for the tab
        self.podcasts_tab.layout = QGridLayout(self)

        # --- Place the Podcast List Widget in the grid
        self.podcasts_tab.layout.addWidget(self.PodcastListWidget, 0, 0, 15, 1)

        # --- Get a list of realtime podcast attributes from the api to use for
        #     creating the labels for the podcast details. As all podcasts have the
        #     same attributes we select a station more or less at random and
        #     get the attributes from the first podcasts of that stations
        self.podcast_attributes = self.station_id_2_podcast_list(1157)[0]["attributes"]

        # --- Create a list of both Labels and Text boxes for the podcast details
        for item in self.podcast_attributes:
            podcast_label = QLabel(str(item))
            podcast_label.setAlignment(Qt.AlignRight)
            self.podcast_details_labels.append(podcast_label)
            lineEdit = QLineEdit()
            font = lineEdit.font()
            font.setPointSize(10)  # set Font size
            lineEdit.setFont(font)
            self.podcast_details_values.append(lineEdit)

        # --- Add the Labels to the grid for the podcast tab
        row = 1
        labelColumn = 3
        for item in self.podcast_details_labels:
            self.podcasts_tab.layout.addWidget(item, row, labelColumn, 1, 1)
            row += 1

        # --- Add the text boxes to the grid for the podcast tab
        row = 1
        textDetailsColumn = 4
        for item in self.podcast_details_values:
            self.podcasts_tab.layout.addWidget(item, row, textDetailsColumn, 1, 1)
            row += 1

        # --- Set the layout for the podcasts tab area
        self.podcasts_tab.setLayout(self.podcasts_tab.layout)
        # ---------------------------------------------------------------------

        # --------------------------------------------------------------------- ------------ EPISODE TAB
        # --- Add widgets to the Episodes tab
        # --- Specify a grid layout for the tab
        self.episodes_tab.layout = QGridLayout(self)

        # --- Place the Podcast List Widget in the grid
        self.episodes_tab.layout.addWidget(self.EpisodesListWidget, 0, 0, 15, 1)

        # --- Get a list of realtime episode attributes from the api to use for
        #     creating the labels for the episode details. As all episodes have the
        #     same attributes we select a podcast more or less at random and
        #     get the attributes from the first episode of that podcast
        self.episodes_attributes = self.podcast_id_2_episodes(22334)[0]["attributes"]

        # --- Create a list of both Labels and Text boxes for the Episode details
        for item in self.episodes_attributes:
            episode_label = QLabel(item)
            episode_label.setAlignment(Qt.AlignRight)
            self.episode_details_labels.append(episode_label)
            lineEdit = QLineEdit()
            font = lineEdit.font()
            font.setPointSize(10)  # set Font size
            lineEdit.setFont(font)
            self.episode_details_values.append(lineEdit)

        # --- Add the Labels to the grid for the episodes tab
        row = 1
        labelColumn = 3
        for item in self.episode_details_labels:
            self.episodes_tab.layout.addWidget(item, row, labelColumn, 1, 1)
            row += 1

        # --- Add the text boxes to the grid for the episodes tab
        row = 1
        textDetailsColumn = 4
        for item in self.episode_details_values:
            self.episodes_tab.layout.addWidget(item, row, textDetailsColumn, 1, 1)
            row += 1

        # --- Place the episode player in the grid and set the initial state
        self.episodes_tab.layout.addWidget(self.episode_player_label, row, 4, 1, 1)
        self.episodes_tab.layout.addWidget(self.episode_player_button, row + 1, 4, 1, 1)

        # --- Set the layout for the episodes tab area
        self.episodes_tab.setLayout(self.episodes_tab.layout)
        # ---------------------------------------------------------------------

        # --------------------------------------------------------------------- ------------ COMM LOG TAB
        # --- Add widgets to the Comm Log tab
        # --- Specify a Vertical Box layout for the tab
        self.commLog_tab.layout = QVBoxLayout(self)

        self.commLog_tab.layout.addWidget(self.commLogTextArea)

        # define the font for the self.commLogTextArea widget


        # --- Set the Layout for the Comm Log tab area
        self.commLog_tab.setLayout(self.commLog_tab.layout)
        # ---------------------------------------------------------------------

        # --------------------------------------------------------------------- ------------ MAIN WINDOW
        # --- Add widgets to the main window
        # --- Define a grid layout for this (the main window) window
        self.grid_layout = QGridLayout()

        # --- Add the radio.com logo and selectors for api version, environment, and station
        #     to the main window
        self.grid_layout.addWidget(self.logo,                       0,  0, 1, 1)
        self.grid_layout.addWidget(QLabel("   "),                   0,  2, 1, 1)
        self.grid_layout.addWidget(self.environment_selector_label, 0,  3, 1, 1)
        self.grid_layout.addWidget(self.environment_selector,       0,  4, 1, 1)
        self.grid_layout.addWidget(QLabel("   "),                   0,  5, 1, 1)
        self.grid_layout.addWidget(self.api_version_selector_label, 0,  6, 1, 1)
        self.grid_layout.addWidget(self.api_version_selector,       0,  7, 1, 1)
        self.grid_layout.addWidget(QLabel("   "),                   0,  8, 1, 1)
        self.grid_layout.addWidget(self.station_selector_label,     0,  9, 1, 1)
        self.grid_layout.addWidget(self.station_selector,           0, 10, 1, 1)
        self.grid_layout.addWidget(QLabel("   "),                   0, 11, 1, 1)

        # --- Populate the selectors, Also as a nice side effect
        #     populate the self.station_ids dictionary
        self.environment_selector.addItems(self.environment_list)
        self.environment_selector.setCurrentText(self.environment_list[1]) # Staging
        self.api_version_selector.addItems(self.api_version_list)
        self.api_version_selector.setCurrentText(self.api_version_list[0]) # v1
        self.station_ids = self.get_station_ids()


        callsigns = list(self.station_ids.keys())
        callsigns.sort()
        callsigns[0:0] = [""] # Add an empty entry to the beginning of the list
        self.station_selector.addItems(callsigns)
        self.station_selector.setCurrentIndex(0) # Empty selection

        # --- Place the tab area in the main window grid
        self.grid_layout.addWidget(self.tabArea, 1, 0, 1, 11)

        # --- Set the initial Window position and size
        self.setGeometry(300, 300, 1100, 1000)

        # --- Set the initial background color for the main window
        # TODO: Find a better way of doing this
        self.setObjectName('MainWidget')
        self.setStyleSheet("""#MainWidget {
                                             background-color: #%s;
                                          }.QLabel 
                                          {
                                             color: #%s;
                                          }""" % (CONFIGS["bg_color"], CONFIGS["fg_color"]))

        # --- set the main window title
        self.setWindowTitle('QA Podcast Player')

        # --- Set the layout for the main window
        self.setLayout(self.grid_layout)
        # ---------------------------------------------------------------------

        # --------------------------------------------------------------------- ------------ CONNECTIONS
        # --- Connect the stations_selector change item to the populate
        self.station_selector.activated.connect(self.populate_station_details)
        self.PodcastListWidget.currentItemChanged.connect(self.podcast_selected)
        self.EpisodesListWidget.currentItemChanged.connect(self.episode_selected)
        self.station_player_button.clicked.connect(self.station_player_controller)
        self.episode_player_button.clicked.connect(self.episode_player_controller)



    # ------------------------------------------------------------------------- ----- populate_station_details()
    def populate_station_details(self):
        """ Using the station id populate the station details
            tab with ... well ... station details """

        # --- First we need to check to see if the station player is playing
        #     audio and if it is then we need to stop that audio
        if self.station_player_state == self.player_states[2]: self.station_player_controller()


        # --- Call out to the api and get the station attributes for the selected station
        result = self.get_station_attributes(self.station_ids[self.station_selector.currentText()],
                                                  api_version=self.api_version_selector.currentText(),
                                                  environment=self.environment_selector.currentText())

        if len(result) == 0: return # If we got nothing back from get_statoion_attributes() then quit

        stream_url = result["station_stream"][FIRST]["url"]

        # --- set the station_id and callsign for the selected station
        self.selected_station_id = result["id"]
        self.selected_station_callsign = result["callsign"]

        # --- Populate the station details text boxes
        station_attributes = list(result.values())
        # TODO: find a cool "index into a list with anther list"" solution
        counter = 0
        for item in station_attributes[0:len(self.station_details_values)]:
            font = self.station_details_values[counter].font()
            font.setPointSize(11)
            font.setBold(True)
            self.station_details_values[counter].setFont(font)
            self.station_details_values[counter].setText(str(item))
            self.station_details_values[counter].setCursorPosition(0)
            counter += 1


        # Download and show the image and set the image in the station tab
        station_logo_filename = podcast_player_utils.download_station_logo(result["square_logo_small"])
        if os.path.isfile(station_logo_filename):
            pixmap = QPixmap(station_logo_filename)
            pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            self.station_logo_image.setPixmap(pixmap_resized)
            self.staton_callsign_label.setText("%s %s" %(result["name"], result["callsign"]))
        else:
            # TODO: Message box to tell user no image available for this station
            pass

        # Show and load the station player
        pixmap = QPixmap(os.path.join(RESOURCE_PATH, "play.png"))
        pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
        self.station_player_button.setPixmap(pixmap_resized)
        self.StationPlayer = vlc.MediaPlayer(stream_url)
        self.station_player_state = self.player_states[1]  # Media ready
        self.station_player_label.setText(self.station_player_state)

        # --- Now we can populate the podcasts tab with all
        #     of the podcasts for this station
        self.populate_podcasts()



    # -------------------------------------------------------------------------
    def station_player_controller(self):
        """ Control the Station Media Player and associated widgets
            The function is implemented as a simple toggle:
               If the player is playing we stop it and if it is not
               playing The we start playing """
        if self.station_player_state == self.player_states[0]:
           pass

        elif self.station_player_state == self.player_states[1]:

            if self.episode_player_state == self.player_states[2]: self.episode_player_controller()
            self.StationPlayer.play()
            pixmap = QPixmap(os.path.join(RESOURCE_PATH, "pause.png"))
            pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            self.station_player_button.setPixmap(pixmap_resized)
            self.station_player_state = self.player_states[2]
            self.station_player_label.setText(self.player_states[2])
        elif self.station_player_state == self.player_states[2]:

            self.StationPlayer.stop()
            pixmap = QPixmap(os.path.join(RESOURCE_PATH, "play.png"))
            pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            self.station_player_button.setPixmap(pixmap_resized)
            self.station_player_state = self.player_states[1]
            self.station_player_label.setText(self.player_states[1])
        else:
            pass

    # ------------------------------------------------------------------------- episode_player_controller()
    def episode_player_controller(self):
        """ Control the Episode Media Player and associated widgets
            The function is implemented as a simple toggle:
               If the player is playing we stop it and if it is not
               playing The we start playing.
            In later versions of this program the Episode player will 
            be a different type than that of the Station player, so
            we are using a separate controller for now.  """
        if self.episode_player_state == self.player_states[0]:
            pass

        elif self.episode_player_state == self.player_states[1]:

            if self.station_player_state == self.player_states[2]: self.station_player_controller()
            self.EpisodePlayer.play()
            pixmap = QPixmap(os.path.join(RESOURCE_PATH, "pause.png"))
            pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            self.episode_player_button.setPixmap(pixmap_resized)
            self.episode_player_state = self.player_states[2]
            self.episode_player_label.setText(self.player_states[2])

        elif self.episode_player_state == self.player_states[2]:

            self.EpisodePlayer.stop()
            pixmap = QPixmap(os.path.join(RESOURCE_PATH, "play.png"))
            pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            self.episode_player_button.setPixmap(pixmap_resized)
            self.episode_player_state = self.player_states[1]
            self.episode_player_label.setText(self.player_states[1])
        else:

            pass

    # ------------------------------------------------------------------------- THREAD insert_podcast_list_item()
    def insert_podcast_list_item(self              ,
                                 podcast_id        ,
                                 podcast_image_url ,
                                 podcast_title     ,
                                 thread_number     ):
        """ This is the function that is executed as a thread.
            Take extra care to hanle andy exceptions a python hates
            unhandled exceptions in thread"""
        global  THREAD_MONITOR
        THREAD_MONITOR[thread_number] = 1
        try:
            # --- Download the image for this podcast
            podcast_image_file = podcast_player_utils.download_station_logo(podcast_image_url)

            # --- Be sure we got an image, if not then use the "image
            #     not available" image
            if len(podcast_image_file) == 0:
                podcast_icon = QIcon(os.path.join(RESOURCE_PATH, "no_image.jpg"))
            else:
                podcast_icon = QIcon(podcast_image_file)

            # --- Create the list item as a native object
            #     To the PodcastListWidget
            list_item = QListWidgetItem(self.PodcastListWidget)

            # --- Populate the item test and icon/image
            list_item.setText("Podcast ID: %s\n%s" % (str(podcast_id)    ,
                                                      str(podcast_title) ) )
            list_item.setIcon(podcast_icon)

        except Exception as e:
            pass
        finally:
            THREAD_MONITOR[thread_number] = 0

    # ------------------------------------------------------------------------- populate_podcasts()
    def populate_podcasts(self):
        """ use multi-threading to populate the podcast list """

        # --- Clear out any existing podcast and or episode values
        self.PodcastListWidget.clear()
        for text_box in self.podcast_details_values: text_box.setText("")
        self.EpisodesListWidget.clear()
        for text_box in self.episode_details_values: text_box.setText("")

        # --- Stop playing any media players
        if self.station_player_state == self.player_states[2]: self.station_player_controller()
        if self.episode_player_state == self.player_states[2]: self.episode_player_controller()

        # --- Get a list of podcasts for the selected station from the api
        self.list_of_podcasts = self.station_id_2_podcast_list(self.selected_station_id)

        # --- If there are now podcasts for a given station then we are outta here
        if len(self.list_of_podcasts) == 0: return

        # ---  Add a list item to the PodcastListWidget for each item
        #      in the list of podcasts (multi-threaded solution)
        number_of_podcasts =  len(self.list_of_podcasts)

        # --- initialize the thread monitor
        for i in range(number_of_podcasts): THREAD_MONITOR.append(0)

        if number_of_podcasts > 0:

            # --- Run the threads to populate the podcast list items
            counter = 0
            for item in self.list_of_podcasts:

                id        = item["id"]
                image_url = item["attributes"]["image"]
                title     = item["attributes"]["title"]
                # --- Call a thread
                t = Thread(target=self.insert_podcast_list_item,
                           args=(id, image_url, title, counter,))
                t.start()
                counter += 1

            # --- Wait for all threads to finish
            while sum(THREAD_MONITOR) > 0: pass

            # --- A little clean up on the image size
            self.PodcastListWidget.setIconSize(QSize(100, 100))
            self.PodcastListWidget.setWordWrap(True)

            # --- Sort teh PodcastListWidget items by ... tbd
            # TODO: sort the PodcastListWidget items
            self.PodcastListWidget.sortItems()

            # --- Set the index to the top of the PodcastListWidget
            self.PodcastListWidget.setCurrentRow(0)

            # --- Populate the text details
            self.podcast_selected()

        else:
            # TODO: Add a message box to let the user know that there were no
            #       Podcasts for the selected station
            pass

    # ------------------------------------------------------------------------- podcast_selected()
    def podcast_selected(self):
        """ Populate the podcast text details with the details
            from the selected podcast. This function is executed
            when a podcast is selected from the PodcastListWidget

        """

        if self.episode_player_state == self.player_states[2]: self.episode_player_controller()

        # --- Just in case no PodcastListWidget items have been added yet
        #     or the item added has no text yet ...
        if self.PodcastListWidget.count() == 0: return
        try: selected_podcast_id = self.PodcastListWidget.currentItem().text()
        except AttributeError: return

        # --- Clean out any old entries that might be laying around
        for text_box in self.podcast_details_values: text_box.setText("")

        selected_podcast_id = selected_podcast_id.split("\n")[FIRST]
        selected_podcast_id = selected_podcast_id.split(":")[LAST]
        selected_podcast_id = selected_podcast_id.strip()

        for item in self.list_of_podcasts:
            if str(item["id"]) == selected_podcast_id:
                podcast_values = list(item["attributes"].values())
                index = 0
                for podcast_value_text in self.podcast_details_values:
                    podcast_value_text.setText(str(podcast_values[index]))
                    podcast_value_text.setCursorPosition(0)
                    index += 1
                break  # No need to look ay further
            else:
                pass

        # --- Populate the Episodes tab
        self.populate_episodes(selected_podcast_id)
        self.EpisodesListWidget.setIconSize(QSize(100, 100))



    # ------------------------------------------------------------------------- populate_episodes()
    def populate_episodes(self,  selected_podcast_id):
        """ Using the current podcast ID populate the Episodes LIst widget
            with all of the episodes for the selected podcast."""


        # --- start with a clean list of episodes
        self.EpisodesListWidget.clear()

        # --- Get a list of episodes using the podcast id from the api
        self.list_of_episodes = self.podcast_id_2_episodes(selected_podcast_id)

        # --- Check to see if the list of episodes returned from the API is
        #     empty, if so the we are outta here.
        if len(self.list_of_episodes) == 0:
            # TODO: Maybe add a message box to indicate that no episodes
            #       were available for the selected podcast
            return

        for episode in self.list_of_episodes:

            # --- Use the icon from the selected podcast for all episodes
            episode_icon = self.PodcastListWidget.currentItem().icon()

            # --- Create the list item as a native object
            #     To the EpisodesListWidget
            list_item = QListWidgetItem(self.EpisodesListWidget)

            # --- Populate the item test and icon/image
            list_item.setText("Episode ID: %s\n%s\nPublished: %s" % (str(episode["id"]),
                                                                     str(episode["attributes"]["title"]),
                                                                     str(episode["attributes"]["published_date"]) ))
            list_item.setIcon(episode_icon)

        # --- Populate the text detail values for the selected episode

    # ------------------------------------------------------------------------- episode_selected()
    def episode_selected(self):
        """ Populate the episode text details with the details
            from the selected episode. This function is executed
               when an episode is selected from the EpisodesListWidget
        """

        # =-- If an Episode is playing then stop that player
        if self.episode_player_state == self.player_states[2]: self.episode_player_controller()

        # --- Just in case no EpiosdesListWidget items have been added yet
        #     or the item added has no text yet ...
        if self.EpisodesListWidget.count() == 0: return
        try:
            selected_episode_id = self.EpisodesListWidget.currentItem().text()
        except AttributeError:
            return

        # --- Clean up any old entries that might be here
        for text_box in self.episode_details_values: text_box.setText("")

        selected_episode_id = selected_episode_id.split("\n")[FIRST]
        selected_episode_id = selected_episode_id.split(":")[LAST]
        selected_episode_id = selected_episode_id.strip()

        for item in self.list_of_episodes:
            if str(item["id"]) == selected_episode_id:
                episode_values = list(item["attributes"].values())
                index = 0
                episode_stream_url = item["attributes"]["audio_url"]
                for episode_value_text in self.episode_details_values:
                    episode_value_text.setText(str(episode_values[index]))
                    episode_value_text.setCursorPosition(0)
                    index += 1
                break  # No need to look ay further
            else:
                pass

        self.EpisodesListWidget.setWordWrap(True)

        # --- Insert the Episode player widget

        pixmap = QPixmap(os.path.join(RESOURCE_PATH, "play.png"))
        pixmap_resized = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
        self.episode_player_button.setPixmap(pixmap_resized)
        self.EpisodePlayer = vlc.MediaPlayer(episode_stream_url)
        self.episode_player_state = self.player_states[1]  # Media ready
        self.episode_player_label.setText(self.episode_player_state)



    # ----------------------------------------------------------------------------- get_station_ids()
    def get_station_ids(self, api_version="v1", environment=STAGING):
        """ Returns a dictionary of callsigns --> station_ids. If anything goes
            wrong then return an empty dictionary. """
        station_data = {}
        try:

            # Call out hte the API using the correct environment base url
            # and the correct api version string

            if api_version == "v1":

                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/stations?page[size]=400" %(base_url, api_version)
                r = "NO DATA"
                self.commLogTextArea.append("Calling: %s\n----------------\n" %api_call_url)
                r = requests.get(api_call_url)
                if r == "NO DATA":
                    raise ValueError("No data from %s" %api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        self.commLogTextArea.append("Response:\n%s\n----------------\n" %response)

                        python_data = json.loads(response)
                        for item in python_data["data"]:
                            station_data[item["attributes"]["callsign"]] = item["attributes"]["id"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " %(r.status_code, api_call_url))

            if api_version == "v2":
                # V2 calls use a special header and reutrn data differently
                # than v1 calls.

                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/stations" % (base_url, api_version)
                r = "NO DATA"
                r = requests.get(api_call_url,headers=api_header)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        python_data = json.loads(response)
                        for item in python_data["stations"]:
                            station_data[item["callsign"]] = item["id"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

            else:
                pass

        except Exception as e:
            sys.stderr.write("ERROR -- Unable to obtain information for stations\n")
            sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
            station_data = {}
        finally:
            return station_data

    # ----------------------------------------------------------------------------- get_station_attributes()
    def get_station_attributes(self, station_id, api_version="v1", environment=STAGING):
        """ Given a station ID return a dictionary of key-value pairs where each
            each key-value pair is a station attribute. If anything goes wrong
            return a empty dictionary. """

        station_id = str(station_id)
        station_attributes = {}
        try:

            # Call out to the the API using the correct environment base url
            # and the correct api version string

            if api_version == "v1":

                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/stations/%s" % (base_url, api_version, station_id)
                r = "NO DATA"
                self.commLogTextArea.setText("Calling: %s\n----------------\n" %api_call_url)
                r = requests.get(api_call_url)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        self.commLogTextArea.append("Response:\n%s\n----------------\n" % response)
                        python_data = json.loads(response)
                        station_attributes =  python_data["data"]["attributes"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

            if api_version == "v2":
                # V2 calls use a special header and reutrn data differently
                # than v1 calls.

                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/stations/%s" % (base_url, api_version, station_id)
                r = "NO DATA"
                r = requests.get(api_call_url, headers=api_header)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        python_data = json.loads(response)
                        station_attributes = python_data["station"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

            else:
                pass

        except Exception as e:
            sys.stderr.write("ERROR -- Unable to obtain information for station %s\n" %station_id)
            sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
            station_attributes = {}
        finally:
            return station_attributes

    # ----------------------------------------------------------------------------- station_id_2_podcast_list()
    def station_id_2_podcast_list(self, station_id, api_version="v1", environment=STAGING):
        """ Given a station ID return a list of podcasts for that station. If
            anything goes wrong return an empty list.  """
        podcast_list = []
        station_id = str(station_id)
        r = "NO DATA"
        try:

            # Call out to the the API using the correct environment base url
            # and the correct api version string

            if api_version == "v1":

                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/podcasts?filter[station_id]=%s&page[size]=100" % (base_url, api_version, station_id)
                r = "NO DATA"
                self.commLogTextArea.append("Calling: %s\n----------------\n" % api_call_url)
                r = requests.get(api_call_url)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        self.commLogTextArea.append("Response:\n%s\n----------------\n" % response)
                        python_data = json.loads(response)
                        podcast_list = python_data["data"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

            if api_version == "v2":
                # V2 calls use a special header and return data differently
                # than v1 calls.
                pass

                # *** ********************************************************** ***
                # *** PODCAST FILTER BY STATION ID NOT YET IMPLEMENTED IN V2 API ***
                # *** ********************************************************** ***

                """  
                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/podcasts?filter[station_id]=%s&page[size]=100" % (base_url, api_version, station_id)
                r = "NO DATA"
                r = requests.get(api_call_url, headers=api_header)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        python_data = json.loads(response)
                        station_attributes = python_data["station"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))
                """

            else:
                pass

        except Exception as e:
            sys.stderr.write("ERROR -- Unable to obtain podcast information\n")
            sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
            podcast_list = []
        finally:
            return podcast_list

    # ----------------------------------------------------------------------------- podcast_id_2_episodes()
    def podcast_id_2_episodes(self, podcast_id, environment=STAGING, api_version="v1"):
        """ Given a podcast id as eitehr an int or a string, return a list of episodes for
            that podcast where each item in the list is a set of attributes for a particular
            episode. If anything goes wrong, return an empty list.  """

        #  Example API call
        # http://originapi-stg.radio.com/v1/episodes?filter%5Bpodcast_id%5D=22334&page%5Bsize%5D=100&page%5Bnumber%5D=1

        episodes = []
        r = "NO DATA"
        podcast_id = str(podcast_id)

        try:

            # Call out to the the API using the correct environment base url
            # and the correct api version string

            if api_version == "v1":

                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/episodes?filter[podcast_id]=%s&page[size]=100" % (base_url, api_version, podcast_id)
                r = "NO DATA"
                self.commLogTextArea.append("Calling: %s\n----------------\n" % api_call_url)
                r = requests.get(api_call_url)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        self.commLogTextArea.append("Response:\n%s\n----------------\n" % response)
                        python_data = json.loads(response)
                        episodes = python_data["data"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

            if api_version == "v2":
                # V2 calls use a special header and reutrn data differently
                # than v1 calls.
                pass

                # *** ********************************************************** ***
                # *** EPISODES FILTER BY PODCAST ID NOT YET IMPLEMENTED IN V2 API ***
                # *** ********************************************************** ***

                """  
                base_url = api_base_urls[environment]
                api_call_url = "%s/%s/podcasts?filter[station_id]=%s&page[size]=100" % (base_url, api_version, station_id)
                r = "NO DATA"
                r = requests.get(api_call_url, headers=api_header)
                if r == "NO DATA":
                    raise ValueError("No data from %s" % api_call_url)
                else:
                    if r.status_code == requests.codes.ok:
                        response = r.text
                        python_data = json.loads(response)
                        station_attributes = python_data["station"]
                    else:
                        raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))
                """

            else:
                pass

        except Exception as e:
            sys.stderr.write("ERROR -- Unable to obtain episodes for podcast_id %s\n" % podcast_id)
            sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
            episodes = []
        finally:
            return episodes


# === MAIN ====================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    windowMain = mainWindow()
    windowMain.show()
    sys.exit(app.exec_())
