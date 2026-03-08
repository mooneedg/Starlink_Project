from dotenv import load_dotenv
import requests
import os


# Load the variables from .env
load_dotenv()

class SpaceTrackClient:
    '''
        HTTP client for interacting with Space-Track.org 

        This file will retrieve only the raw data .
    '''

    LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
    TLE_LATEST_URL = (
       "https://www.space-track.org/basicspacedata/query/class/gp/decay_date/null-val/epoch/%3Enow-30/orderby/norad_cat_id/format/3le"
    )




    def __init__(self, username: str, password: str):
        # Its going to initialize the connection to Space-Track Client (which requires credentials)
        if not username or not password:
            raise ValueError("Space-Track Username and Password must be provided")
        
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self) -> None:
        # Establish session to Space-Track (using cookies)
        
        response = self.session.post(
            self.LOGIN_URL,
            data = {"identity": self.username, "password": self.password}
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Space-Track login failed with HTTP {response.status_code}"
                )
        # Space-Track returns an empty body (or a literal quotation mark) for sucesssful login attempt
        # a non-empty body indicates an error message
        if response.text.strip() and response.text.strip() != '""' :
            raise RuntimeError(
                f"Space-Track login failed: {response.text.strip()}"
            )
        
    def get_latest_tles(self) -> str:
        # Dowloads and returns a string of RAW TLES text

        response = self.session.get(self.TLE_LATEST_URL)

        if response.status_code != 200:
            raise RuntimeError(
                f"TLE download fail with HTTP: {response.status_code}"
            )

        # If response.text is empty throw RuntimeError
        if not response.text or not response.text.strip():    
            raise RuntimeError("Recieved empty TLE data from Space-Track")
        
        return response.text
        