# Catalog reference

Alias maps, lookup helpers, and domain metadata live in
[`src/dcs_agentic/catalog/`](../src/dcs_agentic/catalog/).

Every module exposes `resolve(name)` (raises `ValueError` on unknown),
`all_aliases()`, and `get_info(name)` returning a structured `*Info`
dataclass. Aircraft, vehicles, and theatres additionally expose
`list_by_role(role_tag)` for agent lookups.

| Module | What it resolves | Extended API |
|---|---|---|
| [`aircraft.py`](../src/dcs_agentic/catalog/aircraft.py) | Planes + helicopters (with proxy substitutions) | `list_by_role()`, `all_flyable()`, `get_info()`, `AircraftInfo` dataclass |
| [`vehicles.py`](../src/dcs_agentic/catalog/vehicles.py) | Air defence, artillery, armor | `list_by_role()`, `get_info()`, `VehicleInfo` dataclass |
| [`ships.py`](../src/dcs_agentic/catalog/ships.py) | Surface ships | `all_aliases()` |
| [`statics.py`](../src/dcs_agentic/catalog/statics.py) | Statics (no alias table; resolves directly against `dcs.statics`) | `resolve()` |
| [`countries.py`](../src/dcs_agentic/catalog/countries.py) | Country names | `all_aliases()` |
| [`theatres.py`](../src/dcs_agentic/catalog/theatres.py) | Terrain classes, airports, bounds, bullseye defaults | `get_info()`, `TheatreInfo` dataclass (bounds, notable airports, default bullseye) |
| [`payloads.py`](../src/dcs_agentic/catalog/payloads.py) | Named loadout presets per aircraft | `resolve(aircraft, preset)`, `list_for_aircraft()`, `PayloadPreset` dataclass |
| [`callsigns.py`](../src/dcs_agentic/catalog/callsigns.py) | Callsign → numeric ID maps for AWACS, tanker, JTAC | `get_awacs_id()`, `get_tanker_id()`, `get_jtac_id()`, `all_*()` |

If you pass a name not in these tables, the relevant builder emits a
`*_BUILD_FAILED` error and continues with the other groups.

---

## Theatres

```
Caucasus, PersianGulf, Syria, Nevada, Normandy, TheChannel,
MarianaIslands, Falklands
```

Each theatre has a `TheatreInfo` dataclass with coordinate bounds,
default bullseye position, and notable-airport lists:

```python
from dcs_agentic.catalog import theatres

info = theatres.get_info("Caucasus")
info.bounds                  # BoundingBox(left, bottom, right, top)
info.bounds.contains(x, y)   # True if within bounds
info.default_bullseye        # Position(x, y) — logical centre
info.notable_airports        # tuple of major airports

theatres.lookup_airport(terrain, "Batumi")   # case-insensitive
```

Unknown theatres raise `ValidationError` at parse time.

### Coordinate bounds

| Theatre | left | bottom | right | top |
|---|---|---|---|---|
| Caucasus | -600k | -560k | 380k | 1130k |
| Persian Gulf | -218768 | -392081 | 197357 | 333129 |
| Syria | -320k | -579986 | 300k | 579998 |
| Nevada | -497177 | -329334 | -166934 | 209836 |

---

## Countries

| Alias | pydcs class |
|---|---|
| USA | `dcs_countries.USA` |
| UK | `dcs_countries.UK` |
| Russia | `dcs_countries.Russia` |
| China | `dcs_countries.China` |
| Iran | `dcs_countries.Iran` |
| Syria | `dcs_countries.Syria` |
| Germany | `dcs_countries.Germany` |
| France | `dcs_countries.France` |
| Italy | `dcs_countries.Italy` |
| Turkey | `dcs_countries.Turkey` |
| Israel | `dcs_countries.Israel` |
| Georgia | `dcs_countries.Georgia` |
| Ukraine | `dcs_countries.Ukraine` |
| Australia | `dcs_countries.Australia` |
| Canada | `dcs_countries.Canada` |
| Spain | `dcs_countries.Spain` |
| Netherlands | `dcs_countries.TheNetherlands` |
| Poland | `dcs_countries.Poland` |
| Norway | `dcs_countries.Norway` |
| Denmark | `dcs_countries.Denmark` |
| Belgium | `dcs_countries.Belgium` |
| SouthKorea | `dcs_countries.SouthKorea` |
| Japan | `dcs_countries.Japan` |
| Abkhazia | `dcs_countries.Abkhazia` |
| Belarus | `dcs_countries.Belarus` |
| Serbia | `dcs_countries.Serbia` |
| Kazakhstan | `dcs_countries.Kazakhstan` |
| NorthKorea | `dcs_countries.NorthKorea` |
| Croatia | `dcs_countries.Croatia` |
| CzechRepublic | `dcs_countries.CzechRepublic` |

---

## Aircraft

Each alias has an `AircraftInfo` dataclass available via `get_info(alias)`:

| Field | Description |
|---|---|
| `alias` | User-facing name, e.g. "F/A-18C" |
| `pydcs_class` | The pydcs Plane or Helicopter subclass |
| `pydcs_attr` | Attribute name on the pydcs module |
| `role` | Tuple of role tags (cap, strike, sead, cas, awacs, tanker, etc.) |
| `is_player_flyable` | True if a flyable DCS module |
| `is_helicopter` | True if rotary-wing |
| `is_proxy` | True if substituted with a different airframe |
| `proxy_target` | If proxy, the pydcs attr substituted in |
| `default_country` | Reasonable home country |
| `combat_radius_km` | Approximate unrefueled combat radius |

### Role lookup

```python
from dcs_agentic.catalog import aircraft

aircraft.list_by_role("cap")       # all CAP-capable fighters
aircraft.list_by_role("sead")      # SEAD-capable
aircraft.list_by_role("awacs")     # AEW&C platforms
aircraft.all_flyable()             # player-flyable modules only
aircraft.list_suitable_for_task("STRIKE")  # role tag lookup (case-insensitive)
```

### Alias table

Aliases below resolve via `resolve(name)`. The resolver also tries
`name.replace("-", "_").replace("/", "_")` against `dcs.planes` as
a last resort.

#### Western fighters
| Alias | pydcs attr | Flyable | Roles |
|---|---|---|---|
| FA-18C, F/A-18C | `FA_18C_hornet` | ✓ | multirole, cap, strike, sead, cas, antiship |
| F-15C | `F_15C` | ✓ | cap, intercept |
| F-15E | `F_15E` | ✓ | strike, ground_attack |
| F-16C | `F_16C_50` | ✓ | multirole, cap, strike, sead |
| F-14A | `F_14A` | ✓ | cap, intercept |
| F-14B | `F_14B` | ✓ | cap, intercept |
| F-5E | `F_5E_3` | ✓ | cap, intercept |
| F-4E | `F_4E` | ✓ | multirole, cap, strike |
| AV-8B | `AV8BNA` | ✓ | strike, cas |
| M-2000C | `M_2000C` | ✓ | cap, intercept |
| AJS-37 | `AJS37` | ✓ | strike, antiship |
| JF-17 | `JF_17` | ✓ | multirole, cap, strike, sead |

#### Attack
| Alias | pydcs attr | Flyable | Roles |
|---|---|---|---|
| A-10C | `A_10C` | ✓ | cas, ground_attack |
| A-10C-2 | `A_10C_2` | ✓ | cas, ground_attack |
| Su-25 | `Su_25` | ✓ | cas, ground_attack |
| Su-25T | `Su_25T` | ✓ | cas, strike |
| F-117A | `F_117A` | | strike |

#### Russian / Eastern fighters
| Alias | pydcs attr | Flyable | Roles |
|---|---|---|---|
| MiG-21Bis | `MiG_21Bis` | ✓ | cap, intercept |
| MiG-29S | `MiG_29S` | ✓ | cap, intercept |
| Su-27 | `Su_27` | ✓ | cap, intercept |
| Su-33 | `Su_33` | ✓ | cap, intercept |
| Su-30 | `Su_30` | | cap, strike |
| Su-34 | `Su_34` | | strike, sead |

#### Bombers / Transport
| Alias | pydcs attr | Roles |
|---|---|---|
| B-1B | `B_1B` | strike, ground_attack |
| B-52H | `B_52H` | strike, ground_attack |
| Tu-160 | `Tu_160` | strike, ground_attack |
| C-130 | `C_130` | transport |
| C-17A | `C_17A` | transport |
| IL-76 | `IL_76MD` | transport |

#### Tankers / AWACS
| Alias | pydcs attr | Roles |
|---|---|---|
| KC-135 | `KC_135` | refueling, tanker |
| KC-135MPRS | `KC135MPRS` | refueling, tanker |
| KC-130 | `KC130` | refueling, tanker |
| IL-78 | `IL_78M` | refueling, tanker |
| E-3A | `E_3A` | awacs |
| E-2C | `E_2C` | awacs |
| A-50 | `A_50` | awacs |

#### Helicopters
| Alias | pydcs attr | Flyable | Roles |
|---|---|---|---|
| Ka-50 | `Ka_50` | ✓ | helicopter, cas |
| AH-64D | `AH_64D` | ✓ | helicopter, cas |
| Mi-8 | `Mi_8MT` | ✓ | helicopter, transport |
| Mi-24P | `Mi_24P` | ✓ | helicopter, cas, transport |
| UH-1H | `UH_1H` | ✓ | helicopter, transport |
| SA-342L/M/Mistral | various | ✓ | helicopter, cas |

#### Proxy substitutions (warn at use)
| Alias | Substituted with | Reason |
|---|---|---|
| Su-35 | `Su_27` | Not modelled in pydcs |
| Su-57 | `Su_30` | Not modelled in pydcs |

---

## Vehicles

Each alias has a `VehicleInfo` dataclass with role tags:

```python
from dcs_agentic.catalog import vehicles

vehicles.list_by_role("sam")       # SAM systems
vehicles.list_by_role("mrsam")     # medium-range SAM
vehicles.list_by_role("ewr")       # early warning radars
vehicles.list_by_role("mbt")       # main battle tanks
vehicles.list_by_role("aaa")       # anti-aircraft artillery
vehicles.get_info("SA-11-LN")      # VehicleInfo(alias="SA-11-LN", role=("sam","ln","mrsam"))
```

### Common role tags

| Tag | Meaning | Examples |
|---|---|---|
| `sam` | Surface-to-air missile | SA-2-LN, SA-11-LN, Patriot-LN |
| `shorad` | Short-range air defence | SA-8, SA-15, Avenger |
| `mrsam` | Medium-range SAM | SA-11, Hawk |
| `lrsam` | Long-range SAM | SA-10, Patriot, S-200 |
| `radar` | Radar component | SA-10-SR, Hawk-SR, Dog-Ear |
| `ewr` | Early warning radar | 1L13-EWR, 55G6-EWR |
| `aaa` | Anti-aircraft artillery | ZSU-23-4, Gepard, Vulcan |
| `artillery` | Tube/rocket artillery | M-109, MLRS, BM-21 |
| `armor` | Armoured vehicles | M1-Abrams, T-72B, BMP-2 |
| `mbt` | Main battle tank | M1-Abrams, T-90, Leopard-2 |
| `ifv` | Infantry fighting vehicle | BMP-2, M2-Bradley |
| `apc` | Armoured personnel carrier | M-113, BTR-80 |

### Full vehicle alias tables

#### Air Defence (SAM, AAA, EWR)

Aircraft-resolution takes precedence in `FlightGroup` context; ship
resolution in `ShipGroup`.

---

## Ships

| Alias | pydcs attr |
|---|---|
| Stennis, CVN-74 | `Stennis` |
| CVN-71 | `CVN_71` |
| Kuznetsov | `KUZNECOW` |
| Arleigh-Burke, DDG-51 | `USS_Arleigh_Burke_IIa` |
| Ticonderoga, CG-Ticonderoga | `TICONDEROG` |
| Perry, FFG-7 | `PERRY` |
| Type-054A | `Type_054A` |
| … (40 aliases total) | |

The resolver also tries `name.replace("-", "_")` against `dcs.ships` as
a fallback. Note the `H-6J` collision: the same alias is in both the
aircraft and ship tables; context determines which resolver is called.

---

## Statics

Static types are resolved by name against four pydcs containers in order:

1. `dcs.statics.Fortification`
2. `dcs.statics.GroundObject`
3. `dcs.statics.Warehouse`
4. `dcs.statics.Cargo`

No curated alias table — the spec field accepts the pydcs class
attribute name directly. Refer to `dcs/statics.py` for the full list.

---

## Payload presets

Named loadout presets for common mission profiles:

```python
from dcs_agentic.catalog import payloads

# List presets for an aircraft
payloads.list_for_aircraft("F/A-18C")
# -> ["CAP A-A", "STRIKE GBU-38", "SEAD HARM", "CAS Maverick", "ANTISHIP Harpoon"]

# Resolve a preset
preset = payloads.resolve("F/A-18C", "CAP A-A")
preset.name              # "CAP A-A"
preset.aircraft_alias    # "F/A-18C"
preset.pylons            # ((1, clsid, 1), (2, clsid, 1), ...)
preset.fuel              # 1.0
preset.description       # human-readable summary

# All aircraft with presets
payloads.list_aircraft_with_presets()
# -> ["A-10C", "AH-64D", "F/A-18C", "F-15C", "F-16C", "Ka-50", "MiG-29S", "Su-27"]
```

| Aircraft | Presets |
|---|---|
| F/A-18C | CAP A-A, STRIKE GBU-38, SEAD HARM, CAS Maverick, ANTISHIP Harpoon |
| F-16C | CAP A-A, STRIKE GBU-38, CAS LGB |
| F-15C | CAP A-A |
| A-10C | CAS |
| AH-64D | CAS Hellfire |
| Su-27 | CAP A-A |
| MiG-29S | CAP A-A |
| Ka-50 | CAS |

---

## Callsigns

Numeric ID maps for radio callsigns, verified against pydcs's
`Country` class definitions:

```python
from dcs_agentic.catalog import callsigns

callsigns.get_awacs_id("Magic")     # 1
callsigns.get_tanker_id("Texaco")   # 0
callsigns.get_jtac_id("Warrior")   # 2

callsigns.all_awacs()    # ["Darkstar", "Focus", "Magic", "Overlord", "Wizard"]
callsigns.all_tankers()  # ["Arco", "Shell", "Texaco"]
callsigns.all_jtac()     # ["Axeman", "Badger", ..., "Warrior", "Whiplash"] (18 names)
```

### AWACS callsigns

| Name | ID |
|---|---|
| Overlord | 0 |
| Magic | 1 |
| Wizard | 2 |
| Focus | 3 |
| Darkstar | 4 |

### Tanker callsigns

| Name | ID |
|---|---|
| Texaco | 0 |
| Arco | 1 |
| Shell | 2 |

### JTAC callsigns

Axeman(0), Darknight(1), Warrior(2), Pointer(3), Eyeball(4),
Moonbeam(5), Whiplash(6), Finger(7), Pinpoint(8), Ferret(9),
Shaba(10), Playboy(11), Hammer(12), Jaguar(13), Deathstar(14),
Firefly(15), Mantis(16), Badger(17).

---

## Enum mappings

### TaskType → pydcs
See [`schema-reference.md`](schema-reference.md#tasktype) for the
human-readable mapping. The full table lives in `task_to_pydcs()` in
`pipeline/builders/__init__.py`.

### Skill → pydcs
1:1 mapping. `Player`, `Client`, `Excellent`, `Good`, `High`, `Average`,
`Random`.

### StartType → pydcs
`cold` → `Cold`, `warm` → `Warm`, `runway` → `Runway`.

### Waypoint action → PointAction
| spec string | pydcs |
|---|---|
| `TURNING_POINT` | `TurningPoint` (default) |
| `FROM_PARKING_AREA` | `FromParkingArea` |
| `FROM_PARKING_AREA_HOT` | `FromParkingAreaHot` |
| `FROM_RUNWAY` | `FromRunway` |
| `LANDING` | `Landing` |
| `FLY_OVER_POINT` | `FlyOverPoint` |
| `OFF_ROAD` | `OffRoad` |
