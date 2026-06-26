"""Weather builder."""

from dcs import Mission
from dcs.weather import Weather as PydcsWeather, Wind

from ...errors import AssemblyReport
from ...schemas import MissionSpec


def build_weather(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    w = spec.weather
    if w is None:
        return

    weather = PydcsWeather(mission.terrain)

    # `season` has no direct pydcs attribute today; left as TODO.
    if w.qnh is not None:
        weather.qnh = float(w.qnh)
    if w.temperature is not None:
        weather.season_temperature = w.temperature
    if w.fog_enabled:
        weather.enable_fog = True
        weather.fog_visibility = w.fog_visibility or 1000
    if w.clouds_thickness is not None:
        weather.clouds_thickness = w.clouds_thickness
    if w.clouds_density is not None:
        weather.clouds_density = w.clouds_density
    if w.clouds_base is not None:
        weather.clouds_base = w.clouds_base
    if w.clouds_iprecptns is not None:
        weather.clouds_iprecptns = PydcsWeather.Preceptions(w.clouds_iprecptns)
    if w.wind_at_ground is not None:
        weather.wind_at_ground = Wind(
            direction=w.wind_at_ground.dir,
            speed=w.wind_at_ground.speed,
        )
    if w.wind_at_height is not None:
        weather.wind_at_8000 = Wind(
            direction=w.wind_at_height.dir,
            speed=w.wind_at_height.speed,
        )
    if w.enable_dust:
        weather.enable_dust = True

    mission.weather = weather
