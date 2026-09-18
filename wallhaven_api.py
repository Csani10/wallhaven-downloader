import requests
from datetime import datetime
from enum import Enum
import shutil
import random
import string
from urllib.parse import urlparse
from pathlib import Path

BASE_URL = "https://wallhaven.cc/api/v1/"
SEARCH_ENDPOINT = BASE_URL + "search/"
WALLPAPER_ENDPOINT = BASE_URL + "w/"
TAG_ENDPOINT = BASE_URL + "tag/"
COLLECTIONS_ENDPOINT = BASE_URL + "collections/"
SETTINGS_ENDPOINT = BASE_URL + "settings/"

def bool_to_str(value: bool):
    return "1" if value else "0"

class WallhavenCategories:
    def __init__(self, general = True, anime = True, people = True):
        self.general = general
        self.anime = anime
        self.people = people

    def as_list(self):
        return ["General", "Anime", "People"]

    def selected_as_list(self):
        result = []
        if self.general: result.append("General")
        if self.anime: result.append("Anime")
        if self.people: result.append("People")

        return result

    def __str__(self):
        return f"{bool_to_str(self.general)}{bool_to_str(self.anime)}{bool_to_str(self.people)}"

class WallhavenPurity:
    def __init__(self, sfw = True, sketchy = False, nsfw = False):
        self.sfw = sfw
        self.sketchy = sketchy
        self.nsfw = nsfw

    def as_list(self):
        return ["SFW", "Sketchy", "NSFW"]

    def selected_as_list(self):
        result = []
        if self.sfw: result.append("SFW")
        if self.sketchy: result.append("Sketchy")
        if self.nsfw: result.append("NSFW")

        return result

    def __str__(self):
        return f"{bool_to_str(self.sfw)}{bool_to_str(self.sketchy)}{bool_to_str(self.nsfw)}"

class WallhavenSorting(Enum):
    RELEVANCE = "relevance"
    RANDOM = "random"
    DATE_ADDED = "date_added"
    VIEWS = "views"
    FAVOURITES = "favourites"
    TOPLIST = "toplist"
    HOT = "hot"

    def str_to_idx(self, value):
        match value:
            case "relevance":
                return 0
            case "random":
                return 1
            case "date_added":
                return 2
            case "views":
                return 3
            case "favourites":
                return 4
            case "toplist":
                return 5
            case "hot":
                return 6

        return -1

class WallhavenOrder(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

    def str_to_idx(self, value):
        match value:
            case "asc":
                return 0
            case "desc":
                return 1

        return -1

class WallhavenResolutionSearchType(Enum):
    ATLEAST = 0
    EXACT = 1
    ALL = 2

class WallhavenTag:
    def __init__(self):
        self.id = 0
        self.name = ""
        self.alias = ""
        self.category_id = ""
        self.category = ""
        self.purity = ""
        self.created_at = None

    def parse_from_json(self, obj):
        self.id = obj["id"]
        self.name = obj["name"]
        self.alias = obj["alias"]
        self.category_id = obj["category_id"]
        self.category = obj["category"]
        self.purity = obj["purity"]
        self.created_at = datetime.strptime(obj["created_at"], "%Y-%m-%d %H:%M:%S")

class WallhavenEntry:
    def __init__(self):
        self.id = ""
        self.url = ""
        self.short_url = ""
        self.views = 0
        self.favorites = 0
        self.source = ""
        self.purity = ""
        self.dimension_x = 0
        self.dimension_y = 0
        self.resolution = ""
        self.ratio = ""
        self.file_size = 0
        self.file_type = ""
        self.created_at = None 
        self.colors = []
        self.path = ""
        self.thumb_large = ""
        self.thumb_original = ""
        self.thumb_small = ""

    def parse_from_json(self, obj):
        self.id = obj["id"]
        self.url = obj["url"]
        self.short_url = obj["short_url"]
        self.views = obj["views"]
        self.favorites = obj["favorites"]
        self.source = obj["source"]
        self.purity = obj["purity"]
        self.dimension_x = obj["dimension_x"]
        self.dimension_y = obj["dimension_y"]
        self.resolution = obj["resolution"]
        self.ratio = obj["ratio"]
        self.file_size = obj["file_size"]
        self.file_type = obj["file_type"]
        self.created_at = datetime.strptime(obj["created_at"], "%Y-%m-%d %H:%M:%S")
        self.colors = obj["colors"]
        self.path = obj["path"]
        self.thumb_large = obj["thumbs"]["large"]
        self.thumb_original = obj["thumbs"]["original"]
        self.thumb_small = obj["thumbs"]["small"]

    def download_to_folder(self, path: Path):
        req = requests.get(self.path)
        
        name = Path(urlparse(self.path).path).name

        with open(str(path / Path(name)), "wb") as f:
            f.write(req.content)

        return path / Path(name)

    def download_thumb_small(self, path: Path):
        req = requests.get(self.thumb_small)

        name = Path(urlparse(self.path).path).name

        with open(str(path / Path(name)), "wb") as f:
            f.write(req.content)

        return path / Path(name)

    def download_thumb_original(self, path: Path):
            req = requests.get(self.thumb_original)
    
            name = Path(urlparse(self.path).path).name
    
            with open(str(path / Path(name)), "wb") as f:
                f.write(req.content)
    
            return path / Path(name)

class WallhavenUploader:
    def __init__(self):
        self.username = ""
        self.group = ""
        self.avatar200px = ""
        self.avatar128px = ""
        self.avatar32px = ""
        self.avatar20px = ""

    def parse_from_json(self, obj):
        self.username = obj["username"]
        self.group = obj["group"]
        avatar = obj["avatar"]
        self.avatar200px = avatar["200px"]
        self.avatar128px = avatar["128px"]
        self.avatar32px = avatar["32px"]
        self.avatar20px = avatar["20px"]

class WallhavenWallpaperInfo(WallhavenEntry):
    def __init__(self):
        super().__init__()

        self.uploader = WallhavenUploader()
        self.tags = []
    
    def parse_from_json(self, obj):
        super().parse_from_json(obj)

        self.uploader.parse_from_json(obj["uploader"])
        for t in obj["tags"]:
            tag = WallhavenTag()
            tag.parse_from_json(t)
            self.tags.append(tag)

class WallhavenSearchResult:
    def __init__(self):
        self.entries = []
        self.current_page = 0
        self.last_page = 0
        self.per_page = 0
        self.total = 0
        self.query = ""
        self.seed = ""

    def parse_from_json(self, obj):
        for data in obj["data"]:
            entry = WallhavenEntry()
            entry.parse_from_json(data)
            self.entries.append(entry)
        
        meta = obj["meta"]

        self.current_page = meta["current_page"]
        self.last_page = meta["last_page"]
        self.per_page = meta["per_page"]
        self.total = meta["total"]
        self.query = meta["query"]
        self.seed = meta["seed"]

    def download_thumbs_small(self, path: Path):
        if path.exists():
            shutil.rmtree(str(path.absolute()))

        path.mkdir()

        for entry in self.entries:
            entry.download_thumb_small(path)

class WallhavenSearchFilters:
    def __init__(self,
        categories = WallhavenCategories(), 
        purity = WallhavenPurity(), 
        sorting = WallhavenSorting.DATE_ADDED, 
        order = WallhavenOrder.DESCENDING, 
        toplist_range = "1d",
        resolution_search_type = WallhavenResolutionSearchType.ALL, 
        atleast = "", 
        resolutions = [], 
        ratios = [], 
        colors = [], 
        page = 1
    ):
        self.categories = categories
        self.purity = purity
        self.sorting = sorting
        self.order = order
        self.toplist_range = toplist_range
        self.resolution_search_type = resolution_search_type
        self.atleast = atleast
        self.resolutions = resolutions
        self.ratios = ratios
        self.colors = colors
        self.page = page

TOP_RANGE = [
    "1d",
    "3d",
    "1w",
    "1M",
    "3M",
    "6M",
    "1y"
]

ALLOWED_COLORS = [
    "660000",
    "990000",
    "cc0000",
    "cc3333",
    "ea4c88",
    "993399",
    "663399",
    "333399",
    "0066cc",
    "0099cc",
    "66cccc",
    "77cc33",
    "669900",
    "336600",
    "666600",
    "999900",
    "cccc33",
    "ffff00",
    "ffcc33",
    "ff9900",
    "ff6600",
    "cc6633",
    "996633",
    "663300",
    "000000",
    "999999",
    "cccccc",
    "ffffff",
    "424153",
    ""
]

PRESET_RESOLUTIONS = [
    "2560x1080",
    "1280x720",
    "1280x800",
    "1280x960",
    "1280x1024",
    "3440x1440",
    "1600x900",
    "1600x1000",
    "1600x1200",
    "1600x1280",
    "3840x1600",
    "1920x1080",
    "1920x1200",
    "1920x1440",
    "1920x1536",
    "2560x1440",
    "2560x1600",
    "2560x1920",
    "2560x2048",
    "3840x2160",
    "3840x2400",
    "3840x2880",
    "3840x3072"
]

ASPECT_RATIOS = [
    "landscape",
    "portrait",
    "16x9",
    "21x9",
    "9x16",
    "1x1",
    "16x10",
    "32x9",
    "10x16",
    "3x2",
    "48x9",
    "9x18",
    "4x3",
    "5x4"
]

class WallhavenAPI:
    def __init__(self, api_key = "", download_path = Path.home()):
        self.use_api_key = len(api_key) > 0
        self.api_key = api_key
        self.seed = ""

        self.temp_path = Path("/tmp/wallhaven-downloader/")
        self.temp_path.mkdir(exist_ok=True)

        self.thumbs_path = self.temp_path / Path("thumbs")
        self.thumbs_path.mkdir(exist_ok=True)

        self.download_path = download_path

    def gen_new_seed(self):
        self.seed = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    def search(self, query, filters = WallhavenSearchFilters()):
        params = {
            "q": query,
            "categories": str(filters.categories),
            "purity": str(filters.purity),
            "sorting": filters.sorting.value,
            "order": filters.order.value,
            "toplist_range": filters.toplist_range,
        }
        
        if self.use_api_key:
            params["apikey"] = self.api_key

        if filters.resolution_search_type == WallhavenResolutionSearchType.ATLEAST:
            params["atleast"] = filters.atleast
        elif filters.resolution_search_type == WallhavenResolutionSearchType.EXACT:
            params["resolutions"] = ",".join(filters.resolutions)

        if filters.ratios:
            params["ratios"] = ",".join(filters.ratios)

        if filters.colors:
            params["colors"] = ",".join(filters.colors)

        params["page"] = filters.page

        request = requests.get(SEARCH_ENDPOINT, params=params)
        
        if request.status_code != 200:
            return None
        
        result = WallhavenSearchResult()
        result.parse_from_json(request.json())
        return result

    def get_wallpaper_info(self, id):
        params = {}
        if self.use_api_key:
            params["apikey"] = self.api_key

        request = requests.get(f"{WALLPAPER_ENDPOINT}{id}", params=params)

        if request.status_code != 200:
            return None
        
        info = WallhavenWallpaperInfo()
        info.parse_from_json(request.json()["data"])
        return info
