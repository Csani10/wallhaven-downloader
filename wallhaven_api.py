import requests
from datetime import datetime
from enum import Enum
import random
import string

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

    def __str__(self):
        return f"{bool_to_str(self.general)}{bool_to_str(self.anime)}{bool_to_str(self.people)}"

class WallhavenPurity:
    def __init__(self, sfw = True, sketchy = False, nsfw = False):
        self.sfw = sfw
        self.sketchy = sketchy
        self.nsfw = nsfw

    def __str__(self):
        return f"{bool_to_str(self.sfw)}{bool_to_str(self.sketchy)}{bool_to_str(self.nsfw)}"

class WallhavenSorting(Enum):
    DATE_ADDED = "date_added"
    RELEVANCE = "relevance"
    RANDOM = "random"
    VIEWS = "views"
    FAVOURITES = "favourites"
    TOPLIST = "toplist"

class WallhavenOrder(Enum):
    DESCENDING = "desc"
    ASCENDING = "asc"

class WallhavenSearchEntry:
    def __init__(self):
        self.id = ""
        self.url = ""
        self.short_url = ""
        self.views = 0
        self.favourites = 0
        self.source = ""
        self.purity = ""
        self.dimension_x = 0
        self.dimension_y = 0
        self.resolution = ""
        self.ratio = ""
        self.file_size = 0
        self.file_type = ""
        self.created_at = datetime.date()
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
        self.favourites = obj["favourites"]
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
            entry = WallhavenSearchEntry()
            entry.parse_from_json(data)
            self.entries.append(entry)

        self.current_page = obj["current_page"]
        self.last_page = obj["last_page"]
        self.per_page = obj["per_page"]
        self.total = obj["total"]
        self.query = obj["query"]
        self.seed = obj["seed"]

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
    def __init__(self, api_key = ""):
        self.use_api_key = len(api_key) > 0
        self.api_key = api_key
        self.seed = ""

    def gen_new_seed(self):
        self.seed = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    def search(self, 
               query, 
               categories = WallhavenCategories(), 
               purity = WallhavenPurity(), 
               sorting = WallhavenSorting.DATE_ADDED, 
               order = WallhavenSorting.DESCENDING, 
               toplist_range = "1M", 
               atleast = "1920x1080", 
               resolutions = [], 
               ratios = [], 
               colors = [], 
               page = "1"
               ):
        params = {
            "q": query,
            "categories": str(categories),
            "purity": str(purity),
            "sorting": sorting.value,
            "order": order.value,
            "toplist_range": toplist_range
        }
        
        if self.use_api_key:
            params["apikey"] = self.api_key
