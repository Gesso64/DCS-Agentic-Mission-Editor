"""Unit conversions.

Speed values at the schema boundary are **km/h** (pydcs convention).
pydcs internally stores m/s. Altitude is meters everywhere.

If you find yourself dividing by 3.6 or multiplying by 0.5144 inline
in a builder, stop and call one of these named functions instead.
"""


def kmh_to_ms(v: float) -> float:
    """km/h → m/s (pydcs's internal speed unit)."""
    return v / 3.6


def ms_to_kmh(v: float) -> float:
    """m/s → km/h (schema boundary unit)."""
    return v * 3.6


def kt_to_kmh(v: float) -> float:
    """knots → km/h. Useful when humans give airspeeds in knots."""
    return v * 1.852


def kmh_to_kt(v: float) -> float:
    """km/h → knots."""
    return v / 1.852


def kt_to_ms(v: float) -> float:
    """knots → m/s (direct conversion)."""
    return v * 0.5144


def m_to_ft(v: float) -> float:
    """meters → feet."""
    return v * 3.28084


def ft_to_m(v: float) -> float:
    """feet → meters (DCS altitudes are MSL meters)."""
    return v / 3.28084
