import time, json, re
from commons import SESSION

class DotDict(dict):
    def __getattr__(self, item):
        # Return None if the key is not present and no further access is attempted
        value = self.get(item, None)
        # If value is a dict, wrap it in a DotDict to allow further dot notation
        if isinstance(value, dict):
            return DotDict(value)
         # If value is a list, process each element
        elif isinstance(value, list):
            # Check if the list contains nested lists
            if any(isinstance(i, list) for i in value):
                raise ValueError("Nested lists detected. This is not supported.")
            
            # Iterate through each element and handle dictionaries within the list
            return [DotDict(v) if isinstance(v, dict) else v for v in value]
        # Return an empty DotDict for further chained access if value is None
        elif value is None:
            return DotDict()
        else:
            return value

def pretty_save_with_correct_data(big_data: dict, name: str):
    
    big_data = big_data if isinstance(big_data, DotDict) else DotDict(big_data)
    user_info = None

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
            'total_boards': big_data.board_count
        }

        def get_simple_pin_info(big_pin_data):
            return {
                'name': big_pin_data.name,
                'title': big_pin_data.title,
                'id': big_pin_data.id,
                'alt_text': big_pin_data.auto_alt_text,
                'created at': big_pin_data.created_at,
                'description': big_pin_data.description,
                'images': big_pin_data.images
            }
        
        def get_simple_board_info(big_board_info):
            info = {
                'name': big_board_info.name,
                'id': big_board_info.id,
                'url': big_board_info.url,
                'total_pins': big_board_info.pin_count,
                'created_at': big_board_info.created_at,
                'follower': big_board_info.follower_count,
                'cover': big_board_info.image_cover_hd_url,
            }
            if big_board_info.pins:
                simple_pins = []
                for pin in big_board_info.pins:
                    try:
                        simple_pins.append(get_simple_pin_info(pin))
                    except:
                        continue
                info['pins'] = simple_pins
            else:
                info['pins'] = []
            return info
        
        if big_data.created_pins:
            simple_created = []
            for created in big_data.created_pins:
                try:
                    simple_created.append(get_simple_pin_info(created))
                except:
                    continue
            user_info['created'] = simple_created
        else:
            user_info['created'] = []
        
        if big_data.boards:
            simple_board = []
            for board in big_data.boards:
                try:
                    simple_board.append(get_simple_board_info(board))
                except:
                    continue
            user_info['boards'] = simple_board
        else:
            user_info['boards'] = []
        
        user_info['scraped_at'] = int(time.time())
    except Exception as e:
        print(f'Unable to parse info: {e}')

    with open(name + ('.json' if not name.endswith('.json') else ''), 'w', errors='ignore', encoding='utf-8') as file:
        json.dump(user_info if user_info else big_data, file, indent=4, ensure_ascii=False)
        return True

def return_resource(response: dict):
    return DotDict(response).resource_response

def get_username(string: str):
    if re.match(r"""https?://[\d\w+]?pin.it/""", string):
        webpage = SESSION.get(string).text
        match = re.search(r"""https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"/]+)/(?P<board_name>[^"/]+)?(/?invite_code=[\w\d]+)""", webpage)
        if match:
            return match.group('username'), match.groupdict().get('board_name', '')
    match = re.match(r"""https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"/]+)/(?P<board_name>[^"/]+)?(/?invite_code=[\w\d]+)?""", string)
    if match:
        return match.group('username'), match.groupdict().get('board_url', '')
