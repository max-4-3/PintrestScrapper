from files.http_methods import get_user, get_created_pins, get_all_boards
from files.parser_methods import get_username, pretty_save_with_correct_data
from files.util_methods import clear
from files.commons import DOWNLOAD_PATH

import os


def main():

    while True:

        try:

            clear()

            userinput = input('\t----+ Enter url: '.expandtabs(4))
            if not userinput:
                continue
            
            username, boardname = get_username(userinput)
            if not username:
                continue

            userinfo = get_user(username)
            created_pins, boards = [], []

            clear()

            try:
                created_pins = get_created_pins(userinfo)
            except Exception as e:
                print(f'[{e.__class__.__name__}] Error Retriving Created Pins: {e}')
                input('# Press enter to continue...')

            clear()


            try:
                boards = get_all_boards(userinfo)
            except Exception as e:
                print(f'[{e.__class__.__name__}] Error Retriving Boards: {e}')
                input('# Press enter to continue...')

            clear()

            massive_dict = {key: value for key, value in userinfo.items()}
            massive_dict['created_pins'] = created_pins
            massive_dict['boards'] = boards

            download_dir = os.path.join(DOWNLOAD_PATH, userinfo.username)
            os.makedirs(download_dir, exist_ok=True)

            pretty_save_with_correct_data(massive_dict, os.path.join(download_dir, userinfo.username + '.json'))
            print(f'\t----+ Info saved in: {os.path.join(os.path.abspath(os.getcwd()), userinfo.username+'.json')}'.expandtabs(4))
            
            if input('\t--------> Do you want to scrap another user?: '.expandtabs(4)).strip().lower() in ['yes', 'y']:
                continue
            break
        
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    main()
