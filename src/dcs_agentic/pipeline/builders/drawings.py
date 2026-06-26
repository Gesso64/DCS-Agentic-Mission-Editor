"""Drawings builder — zones and map markers.

Zones are rendered as filled circles on the Common drawing layer.
Map markers are rendered as text boxes on a layer matching their
coalition field (blue/red/all → Blue/Red/Common).
"""

from dcs import Mission
from dcs.drawing.drawing import Rgba
from dcs.drawing.drawings import StandardLayer
from dcs.mapping import Point as MapPoint

from ...errors import AssemblyReport
from ...schemas import MapMarker, MissionSpec, Zone


_COALITION_TO_LAYER = {
    "blue": StandardLayer.Blue,
    "red": StandardLayer.Red,
    "all": StandardLayer.Common,
    "neutrals": StandardLayer.Neutral,
}


def _parse_color(s: str | None, default=Rgba(255, 0, 0, 255)) -> Rgba:
    """Parse an 'rgba(r,g,b,a)' or '0xRRGGBBAA' string."""
    if not s:
        return default
    s = s.strip()
    try:
        if s.startswith("rgba"):
            inner = s[s.index("(") + 1 : s.rindex(")")]
            parts = [p.strip() for p in inner.split(",")]
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            a_raw = float(parts[3]) if len(parts) >= 4 else 1.0
            a = int(a_raw * 255) if a_raw <= 1.0 else int(a_raw)
            return Rgba(r, g, b, a)
        if s.startswith("0x") or s.startswith("#"):
            return Rgba.from_color_string(s)
    except (ValueError, IndexError):
        pass
    return default


def build_drawings(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.zones and not spec.markers:
        return

    common = mission.drawings.get_layer(StandardLayer.Common)
    for zone in spec.zones or []:
        try:
            _build_zone(mission, zone, common, report)
        except Exception as e:
            report.error(
                "ZONE_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=zone.name,
            )

    for marker in spec.markers or []:
        try:
            _build_marker(mission, marker, report)
        except Exception as e:
            report.error(
                "MARKER_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=marker.name,
            )


def _build_zone(mission: Mission, zone: Zone, layer, report: AssemblyReport) -> None:
    color = _parse_color(zone.color, default=Rgba(255, 0, 0, 255))
    fill = Rgba(color.r, color.g, color.b, max(60, color.a // 4))
    pos = MapPoint(zone.center.x, zone.center.y, mission.terrain)
    layer.add_circle(position=pos, radius=zone.radius, color=color, fill=fill)
    # Label the zone with a text box at the centre.
    layer.add_text_box(position=pos, text=zone.name, color=color, fill=fill)
    report.info(
        "ZONE_CREATED",
        f"Created zone '{zone.name}' radius {zone.radius:.0f}m",
    )


def _build_marker(mission: Mission, marker: MapMarker, report: AssemblyReport) -> None:
    side = (marker.coalition or "all").lower()
    layer_kind = _COALITION_TO_LAYER.get(side, StandardLayer.Common)
    layer = mission.drawings.get_layer(layer_kind)
    if layer is None:
        report.warn(
            "MARKER_LAYER_UNKNOWN",
            f"Marker '{marker.name}' coalition '{side}' has no matching "
            f"drawing layer; falling back to Common",
            context=marker.name,
        )
        layer = mission.drawings.get_layer(StandardLayer.Common)

    pos = MapPoint(marker.position.x, marker.position.y, mission.terrain)
    layer.add_text_box(position=pos, text=marker.text)
    report.info(
        "MARKER_CREATED",
        f"Created marker '{marker.name}' on layer {layer_kind.value}",
    )
