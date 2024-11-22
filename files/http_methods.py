from .commons import SESSION, USER_BOARDS_RESOURCE, USER_PIN_RESOURCE, USER_RESOURCE, BOARD_RESOURCE
from .parser_methods import DotDict, return_resource
from .util_methods import clear
from urllib.parse import urlencode

import json, time, random

def get_user(user_name: str):

    print(f"----# Fetching user data for: {user_name}...")  # Add start message
    params={
        'source_url': f'/{user_name}/',
        'data': json.dumps({'options': {'username': user_name}, 'context': {}}),
        '_': int(time.time())
    }
    data = return_resource(f'{USER_RESOURCE}?{urlencode(params, doseq=True)}')
    print(f"----# User data for {user_name} successfully fetched!")  # Success message
    return data.data

def get_created_pins(user_info: DotDict):
    print(f"----# Scraping created pins for user: {user_info.username}...")
    bookmark = None
    pins = []
    scraped, count = 0, 1

    while True:
        try:
            params={
                'source_url': f'/{user_info.username}/_created',
                'data': json.dumps({
                    'options': {
                        'exclude_add_pin_rep': True,
                        'field_set_key': 'grid_item',
                        'user_id': str(user_info.id) if not isinstance(user_info.id, str) else user_info.id,
                        'username': user_info.username,
                        'bookmarks': [bookmark]
                    },
                    'context': {}
                }),
                '_': int(time.time())
            }

            data = return_resource(
                f"{USER_PIN_RESOURCE}?{urlencode(params, doseq=True)}"
            )

            if not data:
                print("\nRecieved Null Data, Continuing...") 
                continue

            pins.extend(data.data)
            scraped += len(data.data)
            print(f'--------> {count}. {scraped} pins scraped out of {user_info.pin_count} total pins...')  # Progress info

            bookmark_n = data.bookmark
            if not bookmark_n or bookmark_n == bookmark:
                break
            bookmark = bookmark_n
            count += 1
            time.sleep(1 + random.random())

        except KeyboardInterrupt:
            print("\n----$ Scraping interrupted. Saving current data...")  # Graceful exit message
            break

    print(f"\n----# Completed scraping {scraped} created pins for {user_info.username}.")
    return pins

def get_all_boards(userinfo: DotDict):
    print(f"----# Scraping boards for user: {userinfo.username}...")

    def get_boards_without_pins():
        bookmark = None
        count, scraped = 1, 0

        boards = []
        while True:
            try:
                params={
                    'source_url': f'/{userinfo.username}/',
                    'data': json.dumps({
                        "options": {
                        "field_set_key": "profile_grid_item",
                        "filter_stories": False,
                        "sort": "last_pinned_to",
                        "username": userinfo.username
                        },
                        'context': {}
                    }),
                    '_': int(time.time())
                }

                resource = return_resource(
                    f'{USER_BOARDS_RESOURCE}?{urlencode(params, doseq=True)}'
                )
                
                if not resource:
                    print("\nRecieved Null Data, Continuing...") 
                    continue

                for board in resource.data:
                    if board.type != 'board':
                        continue
                    boards.append(board)

                scraped += len(boards)
                print(f'{count}. {scraped} boards scraped (without pins)... [{userinfo.board_count} boards total]')
                bookmark_current = resource.bookmark
                if not bookmark_current or bookmark_current == bookmark:
                    break
                bookmark = bookmark_current
                count += 1
                time.sleep(1 + random.random())

            except KeyboardInterrupt:
                print("\nScraping interrupted. Saving current data...")  # Graceful exit message
                break
        
        return boards
    
    def get_board_with_pins(board: DotDict):
        bookmark = None
        scraped, count = 0, 1

        orig_board = {key: value for key, value in board.items()}
        pins = []
        while True:
            try:

                params={
                    'source_url': board.url,
                    'data': json.dumps({
                        'options': {
                            'board_id': str(board.id),
                            'board_url': board.url,
                            'sort': 'default',
                            'page_size': 25,
                            'currentFilter': -1,
                            'filter_stories': False,
                            'bookmarks': [bookmark]
                        },
                        'context': {}
                    }),
                    '_': int(time.time())
                }

                resource = return_resource(
                    f"{BOARD_RESOURCE}?{urlencode(params, doseq=True)}"
                )

                if not resource:
                    print("\t|--------> Recieved Null Data!".expandtabs(4)) 
                    break

                pins.extend(resource.data)
                scraped += len(resource.data)
                print(f'\t|--------> {count}. {scraped} pins scraped out of {board.pin_count} pins.'.expandtabs(4))  # Progress info

                count += 1
                new_bookmark = resource.bookmark
                if not new_bookmark or new_bookmark == bookmark:
                    print(f"\t|--------> Completed scraping board: {board.name} with {scraped} pins.".expandtabs(4))  # Completed message
                    break
                bookmark = new_bookmark
                time.sleep(1 + random.random())
            except KeyboardInterrupt:
                print("\t|--------> Scraping interrupted. Saving current data...".expandtabs(4))
                break
        orig_board['pins'] = pins
        return orig_board

    boards = get_boards_without_pins()
    clear()
    new_boards = []
    try:
        for idx, board in enumerate(boards):
            if board.type != "board":
                continue
            front_char = '+' if idx != len(boards) else "-"
            print(f'\t{front_char}----$ Adding pins to board "{board.name}"...'.expandtabs(4))
            new_board = get_board_with_pins(board)
            if new_board:
                new_boards.append(new_board)
            new_boards.append(new_board)
            print(f'\t{front_char}----$ Added pins to board "{board.name}"!'.expandtabs(4), end='\n'*2)
            time.sleep(1 + random.random())
    except KeyboardInterrupt:
        print("\nScraping interrupted. Saving current progress...")

        bs = []
        for board1, board2 in zip(new_boards, boards):
            if board1 and board1.get('id') == board2.get('id'):
                bs.append(board1)

        print(f"Partial progress saved. {len(bs)} boards have been processed.")

    print(f"----# Completed scraping {len(new_boards)} boards with pins.")
    return new_boards
