#/usr/local/bin/python3

import sys
import os

# Some useful variables
VERSION    = "1.0.0"
FIRST      = 0
LAST       = -1
ME         = os.path.split(sys.argv[FIRST])[LAST]  # Name of this file
MY_PATH    = os.path.dirname(os.path.realpath(__file__))  # Path for this file
CACHE_PATH = os.path.join("/tmp")


# Third-part library imports
try:       
   import requests
except ModuleNotFoundError:
   sys.stderr.wite("ERROR -- Unable to import the 'vlc' library\n")
   sys.stderr.wite("         try: pip3 install requests --user\n")
   sys.stderr.flush()
   sys.exit(99)
   
# -----------------------------------------------------------------------------   
def config_2_dictionary(config_file_name):
    """ Reads a config file and returns a dictionary of key/value pairs from 
        the configuration file. If anything goes wrong then return an
        empty dictionary. Any errors are sent to standard error. """
    configurations = {}
    config_data    = ""
    delimeter      = ' '
    try:
        config_data = open(config_file_name, 'r').read()
        for line in config_data.split('\n'):
            line = line.strip()     # Clean up leading and trailing whitespace
            if len(line) < 1:
                pass                 # Skip blank lines
            elif line[FIRST] == '#':
                pass                 # Skip comment lines
            elif line.find(delimeter) == -1:
                pass                 # Skip mal-formed lines (lines without an equal sign character'=')
            else:
               line  = line.strip() # Clean up the whitespace
               key   = line.split(delimeter, 1)[FIRST].strip()
               value = line.split(delimeter, 1)[LAST].strip()
               configurations[key] = value
    except Exception as e:
        sys.stderr.write("ERROR -- Unable to read from configurations file %s\n" %(config_file_name))
        sys.stderr.write("%s\n" %str(e))
        sys.stderr.flush()
        configurations = {} # Trust no one. If there was a problem then flush the data
    finally:     
        return configurations     

    
def download_station_logo(url):
    """ Using the url provided, downlod the station logo image to the cache folder.
        If successful rhetun the name of hte downloaded file. If anything goes 
        wrong and empty string will be returned. """
        
    downloaded_file_name = ""
    
    try:
        downloaded_file_name = os.path.join(CACHE_PATH, url.split("/")[LAST] ) 
        response = "NO DATA" 
        response = requests.get(url)
        if response == "NO DATA":
           raise ValueError("No data from %s" %url)
        else:   
            if response.status_code == 200:
                with open(downloaded_file_name, 'wb') as f:
                    f.write(response.content)
        if os.path.isfile(downloaded_file_name):
            pass
        else:
           raise ValueError("Unable to write image file %s" %downloaded_file_name)

    except Exception as e:
        sys.stderr.write("ERROR -- Unable to download and save image from %s" %url)
        sys.stderr.write("---------------------\n%s\n---------------------\n" %str(e))
        sys.stderr.flush()
        downloaded_file_name = ""

    finally:
        return downloaded_file_name
    
    
    
        
# =============================================================================    
# Unit tests, because Jon asked and he is right    
def test_bad_config_file_name():
   assert len(config_2_dictionary("bad_file_name")) == 0

def test_known_good_file():
   assert len(config_2_dictionary(   os.path.join(MY_PATH, "../config/podcast_player.conf")    )) > 2
    
def test_background_color():
   assert config_2_dictionary(     os.path.join(MY_PATH, "../config/podcast_player.conf")   )["bg_color"] == "1F055E"
