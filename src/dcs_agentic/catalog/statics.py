"""Static object resolver.

Static types are not aliased — the spec field accepts the pydcs class
attribute name directly. The resolver walks four containers in pydcs's
dcs.statics module looking for a match.
"""

import dcs.statics as _dcs_statics


_CONTAINERS = ("Fortification", "GroundObject", "Warehouse", "Cargo")


def resolve(name: str):
    """Return the pydcs static class for `name`. Raises ValueError if unknown.

    Tries the raw name first, then a sanitized variant
    (`name.replace("-", "_").replace("/", "_").replace(" ", "_")`)
    against each container in order.
    """
    sanitized = name.replace("-", "_").replace("/", "_").replace(" ", "_")
    for container_name in _CONTAINERS:
        container = getattr(_dcs_statics, container_name, None)
        if container is None:
            continue
        for cand in (name, sanitized):
            if hasattr(container, cand):
                return getattr(container, cand)
    raise ValueError(f"Unknown static type: {name}")
