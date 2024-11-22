import os
import logging
import uuid
import subprocess as sp
from .parser_methods import DotDict
from .util_methods import clear
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from .commons import DOWNLOAD_PATH, SESSION, LOG_PATH
import time
import re


class PinterestDownloader:
    def __init__(self):
        self.session = None
        self.root_path = None
        self.is_windows = os.name == 'nt'
        self.max_workers = 50

    def __download_file__(self, url: str, filename: str):
        try:
            with open(filename, 'wb') as file:
                content = self.session.get(url).content
                file.write(content)
                return len(content)
        except Exception as e:
            logging.error(f'Error Downlaoding a anoynomus file from \"{url}\" [name: {filename}]: {e.args} [{e.__class__.__name__}]')
            return 0
    
    def set_logger(self, username: str):
        logging.basicConfig(
            filename=os.path.join(LOG_PATH, username, username + "_downloads.log"),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )        

    @staticmethod
    def __get_title_or_id__(obj):
        return obj.title or obj.name or str(obj.id)

    def __download_m3u8__(self, m3u8_url: str, filename: str, filepath: str):
        # make noice filename
        filename = os.path.splitext(filename)[0]
 
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        
        random_filename = str(uuid.uuid4())  + '.mp4' # Use uuid for random unique filenames
        random_filepath = os.path.join(filepath, random_filename)

        # Downloads temp file
        def download(url: str, filename: str):
            cmd = [
                'ffmpeg',
                '-i', url,
                '-codec', 'copy',
                '-hide_banner', '-y', '-log_level', 'warning', '-f', 'mp4',
                filename
            ]
            output = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
            if output.returncode != 0:
                logging.error(f"FFmpeg error: {output.stderr}")
            return output.returncode == 0
        
        if not download(m3u8_url, random_filepath):
            logging.error(f"Download failed for {m3u8_url}.")
            if os.path.exists(random_filepath):
                try:
                    os.remove(random_filepath)
                except Exception as e:
                    logging.error(f'Unable to delete {random_filepath}: {e}')
            return 0
    
        try:
            original_filepath = os.path.join(filepath, self.__get_unique_name__(filepath, filename) + '.mp4')
            os.rename(random_filepath, original_filepath)
        except Exception as e:
            logging.error(f'Unable to rename {random_filepath}: {e}')
            return 0

        if os.path.exists(original_filepath):
            return os.path.getsize(original_filepath)
        else:
            return 0

    def __download_videos__(self, pin_data: dict, download_path: str):
        data = pin_data if isinstance(pin_data, DotDict) else DotDict(pin_data)

        for video in data.videos:
            if not video.get('url', '').endswith('.m3u8'):
                continue
            return self.__download_m3u8__(video.url, self.__get_title_or_id__(data) + '.mp4', download_path)

    def __download_images__(self, pin_data: str, download_path: str):
        data = pin_data if isinstance(pin_data, DotDict) else DotDict(pin_data)

        if not os.path.exists(download_path):
            os.makedirs(download_path)

        with open(os.path.join(download_path, self.__get_unique_name__( download_path, self.__get_title_or_id__(data)) + '.png'), 'wb') as file:
            content = self.session.get(data.images.orig.url).content
            file.write(content)
            return len(content)

    def download_profile(self, userinfo: dict):
        data = userinfo if isinstance(userinfo, DotDict) else DotDict(userinfo)
        total_size = 0

        def download_type(type: str, download_path: str, url: str):
            nonlocal total_size
            
            print(f'--------> Downloading {type} in {download_path}...')
            size = self.__download_file__(url, os.path.join(download_path, data.username + '_avatar.png'))
            total_size += size
            print(f'--------> Downloaded {type} in {download_path}! [{size/(1024):.2f}KB]')

        print(f"----$ Downloading {data.name if hasattr(data, 'name') else data.username} profile cover (banner/pfp)...")
        download_path = os.path.join(self.root_path, data.username)
        os.makedirs(download_path, exist_ok=True)
        if data.large_pfp:
            download_type('pfp', download_path, data.large_pfp)
        elif data.pfp:
            download_type('pfp', download_path, data.pfp)
        
        if data.profile_cover.images.originals.url:
            download_type('banner', download_path, data.profile_cover.images.originals.url)
        
        return total_size

    def download_pin(self, pin_data: dict, download_path: str, video: bool = False):
        
        pin = pin_data if isinstance(pin_data, DotDict) else DotDict(pin_data)
        pin_size = 0
        if not os.path.exists(download_path):
            os.makedirs(download_path)        

        print(f'\t|---> Downloading {self.__get_title_or_id__(pin)}...'.expandtabs(4), end='\n')

        if (not pin.videos) and (not pin.images):
            logging.error(f'{pin.title or pin.id} does not have any downloadable resource!')
        
        pin_size += self.__download_videos__(pin, download_path) if video else self.__download_images__(pin, download_path)
        
        print(f'\t|---> Downloaded {self.__get_title_or_id__(pin)}! [{pin_size/1024:.2f}KB]'.expandtabs(4), end='\n')
        return pin_size

    def download_board(self, board_data: dict):
        
        data = board_data if isinstance(board_data, DotDict) else DotDict(board_data)
        
        if not data.pins:
            raise ValueError(f"{self.__get_title_or_id__(data)} doesn't have any pins!")
        
        clear()

        download_path = os.path.join(self.root_path, self.__sanitize_filename__(self.__get_title_or_id__(data)) if self.is_windows else (self.__get_title_or_id__(data)))
        print(f'----$ Downloading {self.__get_title_or_id__(data)} in ./{os.path.split(download_path)[1]}')
        board_size = 0

        images, videos = [], []
        for pin in data.pins:
            if pin.videos:
                videos.append(pin)
            elif pin.images:
                images.append(pin)

        # First download images
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future = []

            for image in images:
                future.append(executor.submit(self.download_pin, image, download_path, False))
                
            # Ensure all pins are downloaded!
            for f in as_completed(future):
                board_size += f.result()

            time.sleep(2)
        
        # 2nd Download Videos
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future = []

            for video in videos:
                future.append(executor.submit(self.download_pin, video, download_path, True))
                
            # Ensure all pins are downloaded!
            for f in as_completed(future):
                board_size += f.result()

            time.sleep(2)

        time.sleep(1.3)

        return board_size

    def download(self, user_info: dict):

        if not isinstance(user_info, dict):
            return

        data = user_info if isinstance(user_info, DotDict) else DotDict(user_info)
        self.initialize(data)

        print(f'----# Downloading {data.name if hasattr(data, 'name') else data.username} in {self.root_path}')

        if (not data.created) and (not data.boards):
            raise ValueError(f"{data.name if hasattr(data, 'name') else data.username} doesn't have any pins and boards to download.")
        
        total_size = 0

        # Section 1: Download Created Pin -------------------------------------------------------------------------------------------
        fake_board = {
            'title': 'created',
            'id': 0,
            'pins': data.created
        }
        try:
            total_size += self.download_board(fake_board)
        except Exception as e:
            logging.error(f'[{self.__get_title_or_id__(fake_board)}] Unable to downlaod: {e.args} [{e.__class__.__name__}]')


        # Section 2: Download Boards -------------------------------------------------------------------------------------------------
        for board in data.boards:
            try:
                total_size += self.download_board(board)
                time.sleep(2)
            except Exception as e:
                logging.error(f'[{self.__get_title_or_id__(board)}] Unable to downlaod: {e.args} [{e.__class__.__name__}]')

        # Section 3: Download userinfo ------------------------------------------------------------------------------------------------
        total_size = sum(os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(self.root_path) for file in files if not file.endswith('.json'))

        print(f'----# Downloaded {data.name if hasattr(data, 'name') else data.username} in {self.root_path} [{total_size/(1024*1024):.2f}MB]')

    @staticmethod
    def __sanitize_filename__(filename: str, max_length: int = 60):

        if isinstance(filename, DotDict):
            filename = "EmptyFile"

        reserved_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        # Replace reserved characters with an underscore
        for char in reserved_chars:
            filename = filename.replace(char, '_')
        
        # Remove non-printable and special Unicode characters
        filename = re.sub(r'[^\w\s\.-]', '_', filename)
        
        # Strip any leading or trailing spaces or periods (invalid in Windows)
        filename = filename.strip(' .')

        # Ensure the filename isn't empty after sanitization
        filename = filename if filename else 'Empty_File_Name'
        
        # Truncate the filename if it exceeds the maximum allowed length
        if len(filename) > max_length:
            filename = filename[:max_length].strip(' .')

        return filename

    def __get_unique_name__(self, target_dir: str, filename: str):
        name = self.__sanitize_filename__(filename) if self.is_windows else name
        base_name, ext = os.path.splitext(name)
        counter = 1

        # Check for existing files and generate a unique name if needed
        while os.path.exists(os.path.join(target_dir, name + '.png')):
            name = f"{base_name}_{counter}"
            counter += 1

        return name + ext

    def initialize(self, userdata: dict):
        data = userdata if isinstance(userdata, DotDict) else DotDict(userdata)

        self.session = SESSION
        self.root_path = os.path.join(DOWNLOAD_PATH, data.username, 'downloads')
        self.set_logger(data.username)

        os.makedirs(self.root_path, exist_ok=True)

