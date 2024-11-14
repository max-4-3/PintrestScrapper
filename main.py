from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import json, requests, time, os, re
from fake_useragent import UserAgent

class PintrestScrapper:

    def __init__(self, username: str, mode: str) -> None:
        self.username = username
        self.mode = mode if mode else 'created'
        self.user_id = None
        self.basic_info = {}
        self.headers = {}
        self.is_fully_scraped = False
        self.save_path = os.path.join(os.path.split(__file__)[0], self.__class__.__name__, self.username)
        self.base_url = 'https://in.pinterest.com/resource/UserResource/get'

        os.makedirs(self.save_path, exist_ok=True)
        self.make_headers()
        self.early()

    def early(self):
        if not os.path.exists(self.save_path):
            return
        for file in os.listdir(self.save_path):
            if self.username not in file:
                continue

            if input('File Already Exist.\nDo You wanna load from that file? (y/n):').lower() in ['no', 'n']:
                break
            
            self.is_fully_scraped = True

            self.basic_info = json.load(open(os.path.join(self.save_path, file), 'r', errors='ignore', encoding='utf-8'))

    def make_headers(self):
        self.headers = {
            'User-Agent': UserAgent().random
        }
    
    def make_url(self, bookmark: str | None, long: bool = False) -> str:
        if long:
            url = """https://in.pinterest.com/resource/UserActivityPinsResource/get/?source_url=/navu__edition_/_created/&data={\"options\":{\"exclude_add_pin_rep\":true,\"field_set_key\":\"grid_item\",\"is_own_profile_pins\":false,\"redux_normalize_feed\":true,\"user_id\":\"1069182905193870202\",\"username\":\"navu__edition_\"},\"context\":{}}&_=1731394021059"""
        else:
            url = """https://in.pinterest.com/resource/UserResource/get/?source_url=/navu__edition_/_created/&data={%22options%22:{%22username%22:%22navu__edition_%22},%22context%22:{}}&_=182918291821"""

        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        params['data'] = json.loads(params['data'][0])

        if bookmark and long:
            params['data']['options']['bookmarks'] = [bookmark]

        # Modify the data in a way that exactly matches the original code
        params['source_url'] = f'/{self.username}/{"_created" if not self.mode else self.mode if self.mode.startswith("_") else "_" + self.mode}/'
        params['_'] = str(int(time.time()))
        params['data']['options']['username'] = self.username

        if long:
            params['data']['options']['user_id'] = str(self.user_id)

        # JSON stringify only the data and the source URL as in the original
        params['source_url'] = json.dumps(params['source_url'])
        params['_'] = json.dumps(params['_'])
        params['data'] = json.dumps(params['data'])

        new_query = urlencode(params, doseq=True)
        new_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", new_query, ""))

        return new_url
    
    def delete_dir(self):
        import shutil
        shutil.rmtree(self.save_path, ignore_errors=True)

    def __response_validation(self, url: str):
        response = requests.get(url, headers=self.headers)

        match response.status_code:
            case 200:
                pass
            case 404:
                self.delete_dir()
                raise ValueError(f'Unknowm User: {self.username}')
            case 409:
                raise Exception(f"You are being rate limited, try using vpn/proxies...")
            case _:
                raise Exception(f"[Pinterest] Error: {response.text} ({response.status_code})")

        try:
            return response.json()  # This should return a dictionary
        except json.JSONDecodeError as e:
            print(f"Unable to parse JSON from response: {e}")
            raise e

    def __get_basic_info(self):

        if self.basic_info != {}:
            return self.basic_info

        url = self.make_url(None, long=False)
        response = self.__response_validation(url)

        resource = response.get('resource_response', {})

        resource_data = resource.get('data', {})
        if not resource_data:
            raise Exception('No Data!')
        
        data = {
            "name": resource_data.get('full_name', resource_data.get("first_name", "") + resource_data.get("last_name", "")),
            "username": resource_data.get('username', ''),
            "user_id": int(resource_data.get('id', '0')),
            "pfp": resource_data.get('image_xlarge_url'),
            "following": resource_data.get('following_count', 0),
            "followers": resource_data.get('follower_count'),
            "boards": resource_data.get('board_count'),
            "bio": resource_data.get('about', ''),
            "views": resource_data.get('profile_views', 0),
            "profile_tabs": resource_data.get('eligible_profile_tabs'),
            "verified": resource_data.get('is_verified_merchant', False),
            "total": resource_data.get('pin_count', 0)
        }

        # Extras
        partner = resource_data.get('partner')
        ig_data = resource_data.get('instagram_data')
        pfp = resource_data.get('profile_cover')
        bookmark = resource.get('bookmark')

        # Adds
        if partner:
            data['phone'] = partner.get('contact_phone', 0)
            data['email'] = partner.get('contact_email', '')

        if ig_data:
            data['instagram'] = ig_data
        
        if pfp:
            images = pfp.get('images')
            if images:
                data['banner'] = images.get('originals', {}).get('url', '')
        
        if bookmark:
            data['bookmark'] = bookmark

        self.basic_info = data
        self.user_id = data.get('user_id')
        self.username = data.get('username')

        return data

    def __get_full_info(self):

        if not self.basic_info:
            self.__get_basic_info()

        if 'images' in self.basic_info.keys():
            return self.basic_info

        def scrap_one_page(url: str):
            response = self.__response_validation(url)

            if not isinstance(response, dict):
                raise TypeError("Expected response to be a dictionary, got something else.")

            resource = response.get('resource_response', {})
            resource_data = resource.get('data', [])

            if not resource_data:
                raise StopIteration('No More Images!')
            
            return resource.get('bookmark'), [{
                'title': info.get('title') if info.get('title') not in ['', ' ', None] else info.get('id') if info.get('description') in ['', ' ', None] else info.get('description'),
                'description': info.get('description'),
                'id': int(info.get('id')),
                'comment_count': info.get('comment_count'),
                'created_at': info.get('created_at'),
                'image': not info.get('is_video'),
                'sig': info.get('image_signature'),
                'urls': info.get('images')
            } for info in resource_data if info]

        total_pins = self.basic_info.get('total')
        bookmark_i = self.basic_info.get('bookmark')
        url = self.make_url(bookmark_i, long=True)
        bookmark_c = bookmark_i

        massive_dict = {key: value for key, value in self.basic_info.items()}
        images = []
        idx = 0

        while True:
            try:
                bookmark, new_images = scrap_one_page(url)
                if not bookmark or bookmark == bookmark_c:
                    break

                images.extend(new_images)
                bookmark_c = bookmark
                url = self.make_url(bookmark_c, long=True)

                idx += 1
                print(f"[{idx}] {len(new_images)} images added! [{len(images)}/{total_pins}]")

                time.sleep(2)
            except (StopIteration, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"Unable to fetch data: {e}")
                time.sleep(4)

        massive_dict['images'] = images
        massive_dict['total_image_scrapted'] = len(images)

        self.is_fully_scraped = True

        print(f"Data Scraped!")

        return massive_dict

    def get(self, type: str):

        match type.lower():
            case 'basic':
                return self.__get_basic_info()
            case 'full':
                return self.__get_full_info()
            case _:
                raise ValueError(f"{type} Not Supported!")

    def save_info(self, data: dict):
        try:
            save_path = os.path.join(self.save_path, self.username + '.json')

            with open(save_path, 'w', errors='ignore', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f'Unable to save info: {e}')
            return False

    def download_file(self, url, filepath) -> int:
        with open(filepath, 'wb') as file:
            data = requests.get(url)
            data.raise_for_status()
            file.write(data.content)
            return len(data.content)

    def sanitize_file_name(self, filename):
        # Replace reserved characters with an underscore
        reserved_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in reserved_chars:
            filename = filename.replace(char, '_')
        filename = filename.strip()
        return filename if filename else 'Empty_File_Name'

    def download(self, data: dict):
        images = data.get('images')
        total_images = data.get('total_image_scrapted', data.get('total', 0))

        if not images:
            raise ValueError('Images Missing!')

        download_dir = os.path.join(self.save_path, 'downloads') if not self.mode else os.path.join(self.save_path, 'downloads', self.mode)
        download_dir_user = os.path.join(download_dir if not self.mode else os.path.join(self.save_path, 'downloads'), 'user')
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(download_dir_user, exist_ok=True)

        print(f"Saving Data...")
        self.save_info(data)
        print(f"Data Saved!")

        def get_unique_file_name(dir, name: str):

            # Sanitize the original name
            name = self.sanitize_file_name(name)
            base_name, ext = os.path.splitext(name)
            counter = 1

            # Check for existing files and generate a unique name if needed
            while os.path.exists(os.path.join(dir, name + '.png')):
                name = f"{base_name}_{counter}"
                counter += 1

            return name

        if data.get('pfp'):
            print(f"Downloading pfp in {download_dir_user}")
            p = self.download_file(
                data.get('pfp'),
                os.path.join(download_dir_user, self.sanitize_file_name(data.get('name'))) + '_avatar_' + '.png'
            )
            print(f"Downloaded pfp in {download_dir_user} [{p/1024:.2f}KB]")
        
        if data.get('banner'):
            print(f"Downloading banner in {download_dir_user}")
            p = self.download_file(
                data.get('banner'),
                os.path.join(download_dir_user, self.sanitize_file_name(data.get('name'))) + '_banner_' + '.png'
            )
            print(f"Downloaded banner in {download_dir_user} [{p/1024:.2f}KB]")

        print("Downloading images in: " + str(download_dir))
        total = 0
        for idx, image in enumerate(images, start=1):
            title = image.get('title') or f"image_{idx}"
            print(f"[{idx}/{total_images}] ({title}) Downloading...", end='\r')

            try:
                file_path = os.path.join(download_dir, get_unique_file_name(download_dir, title) + '.png')
                url = image.get('urls').get('orig').get('url')

                downlaod_size = self.download_file(url, file_path)

                print(f"[{idx}/{total_images}] ({title}) Downloaded! [{(downlaod_size) / 1024:.2f}KB]", end='\n')
                total += downlaod_size

            except Exception as e:
                print(f"[{idx}/{total_images}] ({title}) Unable to download: {e}", end='\n')

        print(f"All images downloaded in: {download_dir}\nTotal: {total / 1024:.2f}KB\nFiles: {len(images)}")

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_from_url(url: str):
    pattern = re.compile(r"""<meta[^>]*content="(?P<url>https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"]+)[^"]+)"[^>]*property=["\']og:url["\'][^>]*>""")
    return pattern.search(requests.get(url).text).group('username'), ''

def url_check(string: str):
    
    if re.match(r'''https?://[\d\w+]pin\.it''', string):
        return get_from_url(string)
    
    u = re.match(r"""https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"/]+)/(?P<mode>[^"/]+)""", string)
    if u:
        return u.group('username'), u.group('mode')
    
    k = re.match(r"""https?://(?:[a-zA-Z0-9-]+\.)?pinterest\.com/(?P<username>[^"/]+)""", string)
    if k:
        return k.group('username'), ''

    raise ValueError(string + 'is not a valid url\nEnter username Manually!')

if __name__ == "__main__":
    while True:
        clear()
        try:
            username = input('Enter a username: ').strip()

            pattern = re.compile(r"""https?://\.pinterest\.com/([^/]+)/""", re.IGNORECASE)

            if username.startswith(('https://', 'http://')):
                username, mode = url_check(username)

            s = PintrestScrapper(username, mode=mode)
            print(f'Downloading \'{mode if mode else "created"}\' board from \'{username}\' user')
            s.download(s.get('full'))

            input("Press Enter to continue...")
            del s
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error Running Script: {e}")
            input("Press Enter to continue...")
