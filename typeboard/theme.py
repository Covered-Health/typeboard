from dataclasses import dataclass


@dataclass
class Theme:
    """Configurable color theme for the admin dashboard."""

    # Backgrounds
    bg_body: str = "#f5f5f5"
    bg_sidebar: str = "#ffffff"
    bg_card: str = "#ffffff"
    bg_input: str = "#ffffff"
    bg_hover: str = "#f0f0f0"
    bg_row_alt: str = "#fafafa"

    # Borders
    border: str = "#e5e5e5"
    border_focus: str = "#0455BF"

    # Text
    text_primary: str = "#011140"
    text_secondary: str = "#52525b"
    text_muted: str = "#a1a1aa"

    # Accent (buttons, links, active states)
    accent: str = "#0455BF"
    accent_hover: str = "#034299"
    accent_text: str = "#ffffff"

    # Danger (delete, errors)
    danger: str = "#dc2626"
    danger_hover: str = "#b91c1c"

    # Typography
    font_family: str = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
    font_url: str = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap"

    # Shape
    radius: str = "8px"
    radius_sm: str = "6px"


# Sensible presets
LIGHT = Theme()

DARK = Theme(
    bg_body="#09090b",
    bg_sidebar="#0c0c0e",
    bg_card="#111113",
    bg_input="#18181b",
    bg_hover="#1c1c1f",
    bg_row_alt="#0e0e10",
    border="#27272a",
    border_focus="#6366f1",
    text_primary="#fafafa",
    text_secondary="#a1a1aa",
    text_muted="#71717a",
    accent="#818cf8",
    accent_hover="#6366f1",
    accent_text="#ffffff",
    danger="#ef4444",
    danger_hover="#dc2626",
    font_family="'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    font_url="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
)
