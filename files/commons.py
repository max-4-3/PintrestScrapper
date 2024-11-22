from requests import Session as RSession
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from fake_useragent import UserAgent

import os

BASE = 'https://jp.pinterest.com'
USER_RESOURCE = f'{BASE}/resource/UserResource/get/'
BOARD_RESOURCE = f'{BASE}/resource/BoardFeedResource/get/'
USER_PIN_RESOURCE = f'{BASE}/resource/UserActivityPinsResource/get/'
USER_BOARDS_RESOURCE = f'{BASE}/resource/BoardsResource/get/'

def create_session_with_retries(retries=3, backoff_factor=0.3, status_force_list=(500, 502, 503, 504)):
    """Creates a session with retries for failed downloads."""
    session = RSession()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_force_list,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    session.headers.update({'User-Agent': UserAgent().random, 'Referer': BASE, 'X-Pinterest-AppState': 'Active'})

    return session


SESSION = create_session_with_retries()
DOWNLOAD_PATH = os.path.join(os.path.split(os.path.split(__file__)[0])[0], 'Pintrest Scrapper') 
LOG_PATH = os.path.join(DOWNLOAD_PATH, 'Logs')
