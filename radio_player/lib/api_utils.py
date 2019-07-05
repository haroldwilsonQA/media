#/usr/local/bin/python3

import sys
import os
import json


VERSION       = "1.0.0"
DEBUG         = False
VERBOSE       = False
FIRST         = 0
LAST          = -1
ME            = os.path.split(sys.argv[FIRST])[LAST]  # Name of this file
MY_PATH       = os.path.dirname(os.path.realpath(__file__))  # Path for this file
CONFIG_PATH   = os.path.join(MY_PATH, "../config")
CONFIG_FILE   = os.path.join(CONFIG_PATH, "podcast_player.conf")
LIBRARY_PATH  = MY_PATH
PRODUCTION    = "production"
STAGING       = "staging"
DEVELOPMENT   = "development"
CONFIG_PATH   = os.path.join(MY_PATH, "../config")

api_base_urls = {PRODUCTION  : "" ,
                 STAGING     : "" ,
                 DEVELOPMENT : "" }

# import custom libs
sys.path.append(LIBRARY_PATH)
try:
    import podcast_player_utils
except:
    sys.stderr.wite("ERROR -- Unable to import the 'podcast_player_utils' library\n")
    sys.stderr.wite("         try: git pull\n")
    sys.stderr.flush()
    sys.exit(98)

# Third-part library imports
try:
   import requests
except:
   sys.stderr.wite("ERROR -- Unable to import the 'vlc' library\n")
   sys.stderr.wite("         try: pip3 install requests --user\n")
   sys.stderr.flush()
   sys.exit(99)

# read configs 
CONFIGS =  podcast_player_utils.config_2_dictionary(CONFIG_FILE)

api_url_single_station =  CONFIGS["api_base_url"] + "/" + CONFIGS["api_version"] + "/" + "stations/"

# assign base urls from config file
api_base_urls[PRODUCTION]  = CONFIGS["prod_base_url"]
api_base_urls[STAGING]     = CONFIGS["stg_base_url"]
api_base_urls[DEVELOPMENT] = CONFIGS["dev_base_url"]

# Get the v2 api auth token from the config file
# and use it to define a header dictionary for
# v2 requests.get() calls
v2_api_auth_token = CONFIGS["v2_api_auth_token"]
api_header = {"Authorization": v2_api_auth_token}


# ----------------------------------------------------------------------------- get_station_ids()
def get_station_ids(api_version="v1", environment=STAGING):
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
            r = requests.get(api_call_url)
            if r == "NO DATA":
                raise ValueError("No data from %s" %api_call_url)
            else:
                if r.status_code == requests.codes.ok:
                    response = r.text
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
        sys.stderr.write("ERROR -- Unalbe to obtain information for stations\n")
        sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
        station_data = {}
    finally:
        return station_data


# ----------------------------------------------------------------------------- get_station_attributes()
def get_station_attributes(station_id, api_version="v1", environment=STAGING):
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
            r = requests.get(api_call_url)
            if r == "NO DATA":
                raise ValueError("No data from %s" % api_call_url)
            else:
                if r.status_code == requests.codes.ok:
                    response = r.text
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
def station_id_2_podcast_list(station_id, api_version="v1", environment=STAGING):
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
            r = requests.get(api_call_url)
            if r == "NO DATA":
                raise ValueError("No data from %s" % api_call_url)
            else:
                if r.status_code == requests.codes.ok:
                    response = r.text
                    python_data = json.loads(response)
                    podcast_list = python_data["data"]
                else:
                    raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

        if api_version == "v2":
            # V2 calls use a special header and reutrn data differently
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


# -----------------------------------------------------------------------------
def podcast_id_2_episodes(podcast_id, environment=STAGING, api_version="v1"):
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
            r = requests.get(api_call_url)
            if r == "NO DATA":
                raise ValueError("No data from %s" % api_call_url)
            else:
                if r.status_code == requests.codes.ok:
                    response = r.text
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
        sys.stderr.write("ERROR -- Unalbe to obtain episodes for podcast_id %s\n" % podcast_id)
        sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
        episodes = []
    finally:
        return episodes


# -----------------------------------------------------------------------------
def podcast_id_2_image_url(podcast_id, api_version="v1", environment=STAGING):
    """ Given a podcast ID return the url to later download an image for
        the podcast. If anything goes wrong return an empty string. """
    image_url = ""
    r = "NO DATA"
    podcast_id = str(podcast_id)

    try:
        # Call out to the the API using the correct environment base url
        # and the correct api version string

        if api_version == "v1":

            base_url = api_base_urls[environment]
            api_call_url = "%s/%s/podcasts?filter[station_id]=%s&page[size]=100" % (base_url, api_version, podcast_id)
            r = "NO DATA"
            r = requests.get(api_call_url)
            if r == "NO DATA":
                raise ValueError("No data from %s" % api_call_url)
            else:
                if r.status_code == requests.codes.ok:
                    response = r.text
                    python_data = json.loads(response)
                    episodes = python_data["data"]
                else:
                    raise ValueError("Bad Response (%d) from %s " % (r.status_code, api_call_url))

        if api_version == "v2":
            # V2 calls use a special header and reutrn data differently
            # than v1 calls.
            pass

            # *** ********************************************************** ***
            # *** PODCAST FILTER BY PODCAST ID NOT YET IMPLEMENTED IN V2 API ***
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
        sys.stderr.write("ERROR -- Unable to obtain information for stations\n")
        sys.stderr.write("---------------------\n%s\n---------------------\n" % str(e))
        sys.stderr.flush()
        image_url = ""
    finally:
        return image_url




# =============================================================================
# Unit tests, because Jon asked and he is right  
# To execute units test try:
#     $HOME/Library/Python/3.7/bin/pytest ./api_utils.py

def test_get_station_ids_count():
    assert len(get_station_ids()) > 300

def test_get_station_ids_type():
    assert type(get_station_ids()) == type({})

