"""Domain knowledge: alias maps and lookup tables for DCS types.

Each submodule exposes `resolve(name)` that maps a user-facing alias
to the underlying pydcs class. Unknown names raise ValueError — the
caller (a builder) catches and routes to the assembly report.
"""
