import logging.config
import time, json, re, os, logging
from sys import exit
from .commons import SESSION, DOWNLOAD_PATH

class DotDict(dict):
    """
    A dictionary class with dot notation access and mode switching.
    """

    def __init__(self, *args, mode='scraping', **kwargs):
        super().__init__(*args, **kwargs)
        self._mode = mode
    
    def set_mode(self, mode: str):
        """
        Set the mode for the DotDict.
        :param mode: 'scraping' or 'saving'
        """
        if mode not in ('scraping', 'saving'):
            self.mode = 'saving'
        self._mode = mode

    def __getattr__(self, item):
        # Return None if the key is not present and no further access is attempted
        value = self.get(item, None)

        if isinstance(value, dict):
            # Check if the dictionary has no items and mode is 'saving'
            if not value and self._mode == 'saving':
                return None
            # Wrap nested dictionaries
            return DotDict(value, mode=self._mode)

        elif isinstance(value, list):
            # Process lists and handle nested dictionaries
            return [
                DotDict(v, mode=self._mode) if isinstance(v, dict) else v
                for v in value
            ]

        elif value is None:
            # Return an empty DotDict for further chained access
            return DotDict(mode=self._mode)

        return value

def pretty_save_with_correct_data(big_data: dict, name: str):
    # Initialize logging
    log_file = os.path.join(DOWNLOAD_PATH, 'scraping.log')
    logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    big_data = DotDict(big_data, mode='saving')
    user_info = None

    def log_and_continue(exception, message):
        logging.error(f"{message}: {exception}")
    
    try:
        user_info = {
            'id': big_data.id,
            'name': big_data.full_name,
            'username': big_data.username,
            'profile_cover': big_data.profile_cover,
            'external_links': big_data.website_url,
            'followers': big_data.follower_count,
            'following': big_data.following_count,
            'reach': big_data.reach,
            'views': big_data.profile_views,
            'instagram': big_data.instagram_data,
            'large_pfp': big_data.image_xlarge_url,
            'default': big_data.eligible_profile_tabs,
            'pfp': big_data.image_large_url,
            'about': big_data.about,
            'total_pins': big_data.pin_count,
            'total_created_pins': len(big_data.created),
            'total_boards': big_data.board_count,
            'created': [],
            'boards': []
        }

        def get_simple_pin_info(big_pin_data):
            def extract_videos():
                """Extract video information from pin data."""
                story_pin_data = big_pin_data.story_pin_data
                if not story_pin_data or story_pin_data.total_video_duration == 0:
                    logging.warning("Story pin data is invalid or has no duration.")
                    return big_data.get('videos', [])

                videos = []
                for page in story_pin_data.pages or []:
                    for block in page.blocks or []:
                        if block.block_type != 3:
                            logging.info("Skipping block with unsupported type.")
                            continue

                        for key, value in (block.video.video_list or {}).items():
                            value = DotDict(value)
                            logging.debug(f"Video key: {key}, URL: {value.url}")
                            videos.append({
                                'width': value.width,
                                'height': value.height,
                                'thumbnail': value.thumbnail,
                                'url': value.url,
                                'duration': story_pin_data.total_video_duration
                            })
                return videos

            try:
                videos = extract_videos()
                logging.info(f"Extracted {len(videos)} video(s) for pin [{big_pin_data.id}].")
                return {
                    'name': big_pin_data.name,
                    'title': big_pin_data.title,
                    'id': big_pin_data.id,
                    'alt_text': big_pin_data.auto_alt_text,
                    'created_at': big_pin_data.created_at,
                    'description': big_pin_data.description,
                    'images': big_pin_data.images,
                    'videos': videos,
                    'has_videos': bool(videos)
                }
            except Exception as e:
                log_and_continue(e, f"Failed to extract pin info for pin [{big_pin_data.id}]")
                return {}

        def get_simple_board_info(big_board_info):
            try:
                info = {
                    'name': big_board_info.name,
                    'id': big_board_info.id,
                    'url': big_board_info.url,
                    'total_pins': big_board_info.pin_count,
                    'created_at': big_board_info.created_at,
                    'follower': big_board_info.follower_count,
                    'cover': big_board_info.image_cover_hd_url,
                    'pins': []
                }

                for pin in big_board_info.pins or []:
                    try:
                        logging.debug(f"Extracting pin info for {pin.title}.")
                        info['pins'].append(get_simple_pin_info(pin))
                    except Exception as e:
                        log_and_continue(e, f"Failed to process pin [{pin.id}] in board [{big_board_info.name}]")
                return info
            except Exception as e:
                log_and_continue(e, f"Failed to process board [{big_board_info.name}]")
                return {}

        # Process created pins
        user_info['created'] = [get_simple_pin_info(pin) for pin in big_data.created_pins or []]
        logging.info(f"Processed {len(user_info['created'])} created pins.")

        # Process boards
        user_info['boards'] = [get_simple_board_info(board) for board in big_data.boards or []]
        logging.info(f"Processed {len(user_info['boards'])} boards.")

        user_info['scraped_at'] = int(time.time())
    except Exception as e:
        log_and_continue(e, "Failed to parse user info")
        return False

    # Save data to file
    output_file = name if name.endswith('.json') else f"{name}.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(user_info or big_data, file, indent=4, ensure_ascii=False)
        logging.info(f"Data saved successfully to {output_file}")
        return True
    except Exception as e:
        log_and_continue(e, "Failed to save data to file")
        return False

def return_resource(response: dict):
    return DotDict(response).resource_response

def get_username(string: str):

    if string == 'exit':
        exit(0)

    if re.match(r"""https?://[\d\w+]?pin.it/""", string):
        webpage = SESSION.get(string).text
        match = re.search(r"""https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"/]+)/(?P<board_name>[^"/]+)?(/?invite_code=[\w\d]+)""", webpage)
        if match:
            return match.group('username'), match.groupdict().get('board_name', '')
    match = re.match(r"""https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"/]+)/(?P<board_name>[^"/]+)?(/?invite_code=[\w\d]+)?""", string)
    if match:
        return match.group('username'), match.groupdict().get('board_url', '')
    
    return '', ''
