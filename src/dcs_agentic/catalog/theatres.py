"""Theatre alias map + airport lookup + structured metadata.

Each theatre has a TheatreInfo dataclass carrying coordinate bounds,
default bullseye positions, and notable airport lists — sourced from
the pydcs terrain definitions at .venv/Lib/site-packages/dcs/terrain/.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

from dcs.terrain import (
    Caucasus,
    Falklands,
    MarianaIslands,
    Nevada,
    Normandy,
    PersianGulf,
    Syria,
    TheChannel,
)
from dcs.terrain.terrain import Terrain

from ..schemas import Position


# ─── BoundingBox ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundingBox:
    """Coordinate bounds for a theatre, in pydcs projected meters.

    left = minimum x (west)
    right = maximum x (east)
    bottom = minimum y (south)
    top = maximum y (north)

    Caucasus example: x ∈ [-600k, 380k], y ∈ [-560k, 1130k]
    """
    left: float
    bottom: float
    right: float
    top: float

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        """True if (x, y) is within bounds, with optional margin."""
        return (
            (self.left - margin) <= x <= (self.right + margin)
            and (self.bottom - margin) <= y <= (self.top + margin)
        )


# ─── TheatreInfo ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TheatreInfo:
    """Structured metadata for a DCS theatre/map.

    Attributes:
        name:              Canonical name (e.g. "Caucasus")
        pydcs_class:       The pydcs Terrain subclass
        bounds:            Projected coordinate bounding box
        default_bullseye:  Logical centre point, used as default bullseye
        notable_airports:  Tuple of major airport names mission designers use
        all_airports:      Full tuple of airport names known to pydcs
        notes:             Additional context
    """
    name: str
    pydcs_class: Type[Terrain]
    bounds: BoundingBox
    default_bullseye: Position = field(default_factory=lambda: Position(x=0, y=0))
    notable_airports: Tuple[str, ...] = field(default_factory=tuple)
    all_airports: Tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


# ─── Theatre catalog ────────────────────────────────────────────────────────

CAUCASUS = TheatreInfo(
    name="Caucasus",
    pydcs_class=Caucasus,
    bounds=BoundingBox(left=-600000, bottom=-560000, right=380000, top=1130000),
    default_bullseye=Position(x=-110000, y=285000),
    notable_airports=(
        "Anapa-Vityazevo",
        "Batumi",
        "Gelendzhik",
        "Krasnodar-Center",
        "Krasnodar-Pashkovsky",
        "Kutaisi",
        "Maykop-Khanskaya",
        "Mineralnye Vody",
        "Mozdok",
        "Nalchik",
        "Novorossiysk",
        "Senaki-Kolkhi",
        "Sochi-Adler",
        "Soganlug",
        "Sukhumi-Babushara",
        "Tbilisi-Lochini",
        "Vaziani",
        "Kobuleti",
        "Gudauta",
        "Krymsk",
        "Beslan",
    ),
    all_airports=(
        "Anapa-Vityazevo", "Batumi", "Beslan", "Gelendzhik", "Gudauta",
        "Kobuleti", "Krasnodar-Center", "Krasnodar-Pashkovsky", "Krymsk",
        "Kutaisi", "Maykop-Khanskaya", "Mineralnye Vody", "Mozdok",
        "Nalchik", "Novorossiysk", "Senaki-Kolkhi", "Sochi-Adler",
        "Soganlug", "Sukhumi-Babushara", "Tbilisi-Lochini", "Vaziani",
    ),
    notes="Black Sea region. Most popular DCS theatre. Blue: Batumi/Kutaisi, Red: Sochi/Krasnodar/Mozdok.",
)

PERSIAN_GULF = TheatreInfo(
    name="PersianGulf",
    pydcs_class=PersianGulf,
    bounds=BoundingBox(left=-218768, bottom=-392081, right=197357, top=333129),
    default_bullseye=Position(x=-10705, y=-29476),
    notable_airports=(
        "Abu Dhabi Intl",
        "Al Ain Intl",
        "Al Bateen",
        "Al Dhafra AFB",
        "Al Maktoum Intl",
        "Al Minhad AFB",
        "Bandar Abbas Intl",
        "Dubai Intl",
        "Fujairah Intl",
        "Kerman",
        "Kish Intl",
        "Lar",
        "Liwa AFB",
        "Qeshm Island",
        "Ras Al Khaimah Intl",
        "Sharjah Intl",
        "Shiraz Intl",
    ),
    all_airports=(
        "Abu Dhabi Intl", "Abu Musa Island", "Al Ain Intl", "Al Bateen",
        "Al Dhafra AFB", "Al Maktoum Intl", "Al Minhad AFB",
        "Bandar Abbas Intl", "Bandar Lengeh", "Bandar-e-Jask",
        "Dubai Intl", "Fujairah Intl", "Havadarya", "Jiroft", "Kerman",
        "Khasab", "Kish Intl", "Lar", "Lavan Island", "Liwa AFB",
        "Qeshm Island", "Ras Al Khaimah Intl", "Sas Al Nakheel",
        "Sharjah Intl", "Shiraz Intl", "Sir Abu Nuayr", "Sirri Island",
        "Tunb Island AFB", "Tunb Kochak",
    ),
    notes="Strait of Hormuz. Blue: UAE bases, Red: Iranian bases.",
)

SYRIA_THEATRE = TheatreInfo(
    name="Syria",
    pydcs_class=Syria,
    bounds=BoundingBox(left=-320000, bottom=-579986, right=300000, top=579998),
    default_bullseye=Position(x=-10000, y=0),
    notable_airports=(
        "Aleppo",
        "Bassel Al-Assad",
        "Beirut-Rafic Hariri",
        "Damascus",
        "Deir ez-Zor",
        "Hama",
        "Hatay",
        "Incirlik",
        "King Hussein Air College",
        "Kuweires",
        "Larnaca",
        "Mezzeh",
        "Palmyra",
        "Ramat David",
        "Shayrat",
        "Tabqa",
        "Taftanaz",
        "Tiyas",
        "Akrotiri",
        "Adana Sakirpasa",
    ),
    all_airports=(
        "Abu al-Duhur", "Adana Sakirpasa", "Al Qusayr", "Al-Dumayr",
        "Aleppo", "An Nasiriyah", "At Tanf", "Bassel Al-Assad",
        "Beirut-Rafic Hariri", "Damascus", "Deir ez-Zor",
        "Gaziantep", "H3", "H4", "Hama", "Hatay", "Incirlik",
        "Kharab Ishk", "King Hussein Air College", "Kiryat Shmona",
        "Kuweires", "Larnaca", "Marj as Sultan North",
        "Marj as Sultan South", "Megiddo", "Mezzeh", "Palmyra",
        "Paphos", "Ramat David", "Rosh Pina", "Ruwayshid",
        "Sanliurfa", "Sayqal", "Shayrat", "Tabqa", "Taftanaz",
        "Tiyas",
    ),
    notes="Eastern Mediterranean. Large theatre spanning Syria/Lebanon/Israel/Cyprus/southern Turkey.",
)

NEVADA = TheatreInfo(
    name="Nevada",
    pydcs_class=Nevada,
    bounds=BoundingBox(left=-497177, bottom=-329334, right=-166934, top=209836),
    default_bullseye=Position(x=-332055, y=-59749),
    notable_airports=(
        "Creech",
        "Groom Lake",
        "Henderson Executive",
        "McCarran International",
        "Nellis",
        "North Las Vegas",
        "Tonopah",
        "Tonopah Test Range",
    ),
    all_airports=(
        "Beatty", "Boulder City", "Creech", "Echo Bay",
        "Groom Lake", "Henderson Executive", "Jean",
        "Laughlin", "Lincoln County", "McCarran International",
        "Mesquite", "Mina", "Nellis", "North Las Vegas",
        "Pahute Mesa", "Tonopah", "Tonopah Test Range",
    ),
    notes="NTTR (Nevada Test and Training Range). Red Flag training area.",
)

NORMANDY = TheatreInfo(
    name="Normandy",
    pydcs_class=Normandy,
    bounds=BoundingBox(left=-280000, bottom=-220000, right=280000, top=220000),
    default_bullseye=Position(x=0, y=0),
    notable_airports=(
        "Bazenville", "Beny-sur-Mer", "Cardonville", "Chippelle",
        "Lantheuil", "Longues", "Martragny", "Saint-Pierre-du-Mont",
        "Sainte-Croix-sur-Mer", "Tangmere",
    ),
    all_airports=(
        "Bazenville", "Beny-sur-Mer", "Cardonville", "Chippelle",
        "Lantheuil", "Longues", "Martragny", "Saint-Pierre-du-Mont",
        "Sainte-Croix-sur-Mer", "Tangmere",
    ),
    notes="WWII D-Day theatre. Smaller map, mostly grass airstrips.",
)

THE_CHANNEL = TheatreInfo(
    name="TheChannel",
    pydcs_class=TheChannel,
    bounds=BoundingBox(left=-280000, bottom=-220000, right=280000, top=220000),
    default_bullseye=Position(x=0, y=0),
    notable_airports=(
        "Biggin Hill", "Boulogne", "Calais", "Dunkirk", "Folkestone",
        "Hawkinge", "Lydd", "Manston", "Merville", "St Omer",
    ),
    all_airports=(
        "Biggin Hill", "Boulogne", "Calais", "Dunkirk", "Folkestone",
        "Hawkinge", "Lydd", "Manston", "Merville", "St Omer",
    ),
    notes="English Channel. WWII Battle of Britain theatre.",
)

MARIANA_ISLANDS = TheatreInfo(
    name="MarianaIslands",
    pydcs_class=MarianaIslands,
    bounds=BoundingBox(left=-350000, bottom=-350000, right=350000, top=350000),
    default_bullseye=Position(x=0, y=0),
    notable_airports=(
        "Anderson AFB", "Agana", "Guam Intl", "North Field",
        "Rota", "Saipan Intl", "Tinian",
    ),
    all_airports=(
        "Anderson AFB", "Agana", "Guam Intl", "North Field",
        "Rota", "Saipan Intl", "Tinian",
    ),
    notes="Pacific theatre. Large water area; carrier ops heavy.",
)

FALKLANDS = TheatreInfo(
    name="Falklands",
    pydcs_class=Falklands,
    bounds=BoundingBox(left=-250000, bottom=-350000, right=250000, top=350000),
    default_bullseye=Position(x=0, y=50000),
    notable_airports=(
        "Mount Pleasant", "Port Stanley", "Pebble Island", "Goose Green",
    ),
    all_airports=(
        "Mount Pleasant", "Port Stanley", "Pebble Island", "Goose Green",
    ),
    notes="South Atlantic. 1982 Falklands War setting.",
)

# ─── Index ──────────────────────────────────────────────────────────────────

TERRAIN_MAP: Dict[str, Type[Terrain]] = {
    "Caucasus": Caucasus,
    "PersianGulf": PersianGulf,
    "Syria": Syria,
    "Nevada": Nevada,
    "Normandy": Normandy,
    "TheChannel": TheChannel,
    "MarianaIslands": MarianaIslands,
    "Falklands": Falklands,
}

CATALOG: Dict[str, TheatreInfo] = {
    "Caucasus": CAUCASUS,
    "PersianGulf": PERSIAN_GULF,
    "Syria": SYRIA_THEATRE,
    "Nevada": NEVADA,
    "Normandy": NORMANDY,
    "TheChannel": THE_CHANNEL,
    "MarianaIslands": MARIANA_ISLANDS,
    "Falklands": FALKLANDS,
}

_INFO_MAP = CATALOG


# ─── Public API (preserved + extended) ──────────────────────────────────────

def resolve(name: str) -> Optional[Type[Terrain]]:
    """Return the terrain class for `name`, or None if unknown.

    Returns None rather than raising — the assembler decides whether
    to fall back to Caucasus or report an error.
    """
    return TERRAIN_MAP.get(name)


def all_aliases() -> List[str]:
    return sorted(TERRAIN_MAP)


def get_info(name: str) -> Optional[TheatreInfo]:
    """Return the TheatreInfo dataclass for `name`, or None if unknown."""
    return _INFO_MAP.get(name)


def lookup_airport(terrain: Terrain, name: str) -> Optional[Any]:
    """Case-insensitive airport lookup on a pydcs terrain instance.

    Returns the airport object or None if not found.
    """
    airport = terrain.airports.get(name)
    if airport is not None:
        return airport
    lower = name.lower()
    for aname, aobj in terrain.airports.items():
        if aname.lower() == lower:
            return aobj
    return None