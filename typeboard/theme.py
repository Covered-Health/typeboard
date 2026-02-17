from dataclasses import dataclass


@dataclass
class Theme:
    """Theme configuration — controls Web Awesome light/dark mode."""

    mode: str = "light"  # "light" or "dark"


LIGHT = Theme()

DARK = Theme(mode="dark")
