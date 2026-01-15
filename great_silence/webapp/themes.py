"""Space-themed color schemes for the webapp."""

from typing import Dict, Any


SPACE_THEMES: Dict[str, Dict[str, Any]] = {
    "deep_space": {
        "name": "Deep Space",
        "icon": "🌌",
        "background_gradient": "linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #24243e 100%)",
        "card_bg": "rgba(30, 30, 50, 0.8)",
        "card_border": "rgba(100, 100, 150, 0.2)",
        "expansion_bg": "rgba(30, 30, 50, 0.6)",
        "primary_accent": "#06b6d4",
        "secondary_accent": "#a855f7",
        "slider_track": "rgba(100, 100, 150, 0.3)",
        "slider_selection": "#06b6d4",
        "progress_track": "rgba(100, 100, 150, 0.3)",
        "progress_gradient": "linear-gradient(90deg, #06b6d4, #22d3ee)",
        "scrollbar_track": "rgba(30, 30, 50, 0.5)",
        "scrollbar_thumb": "rgba(100, 100, 150, 0.5)",
        "header_gradient": "from-cyan-400 to-purple-500",
    },
    "nebula": {
        "name": "Nebula",
        "icon": "🔮",
        "background_gradient": "linear-gradient(135deg, #1a0a2e 0%, #2d1b4e 50%, #4a1942 100%)",
        "card_bg": "rgba(45, 27, 78, 0.8)",
        "card_border": "rgba(232, 121, 249, 0.2)",
        "expansion_bg": "rgba(45, 27, 78, 0.6)",
        "primary_accent": "#e879f9",
        "secondary_accent": "#f472b6",
        "slider_track": "rgba(150, 80, 150, 0.3)",
        "slider_selection": "#e879f9",
        "progress_track": "rgba(150, 80, 150, 0.3)",
        "progress_gradient": "linear-gradient(90deg, #e879f9, #f472b6)",
        "scrollbar_track": "rgba(45, 27, 78, 0.5)",
        "scrollbar_thumb": "rgba(232, 121, 249, 0.5)",
        "header_gradient": "from-fuchsia-400 to-pink-500",
    },
    "solar_flare": {
        "name": "Solar Flare",
        "icon": "☀️",
        "background_gradient": "linear-gradient(135deg, #1a0a00 0%, #2d1200 50%, #3d1a00 100%)",
        "card_bg": "rgba(45, 18, 0, 0.8)",
        "card_border": "rgba(249, 115, 22, 0.2)",
        "expansion_bg": "rgba(45, 18, 0, 0.6)",
        "primary_accent": "#f97316",
        "secondary_accent": "#fbbf24",
        "slider_track": "rgba(150, 80, 30, 0.3)",
        "slider_selection": "#f97316",
        "progress_track": "rgba(150, 80, 30, 0.3)",
        "progress_gradient": "linear-gradient(90deg, #f97316, #fbbf24)",
        "scrollbar_track": "rgba(45, 18, 0, 0.5)",
        "scrollbar_thumb": "rgba(249, 115, 22, 0.5)",
        "header_gradient": "from-orange-400 to-amber-400",
    },
    "aurora": {
        "name": "Aurora",
        "icon": "🌠",
        "background_gradient": "linear-gradient(135deg, #0a1a0f 0%, #0f2418 50%, #142d1f 100%)",
        "card_bg": "rgba(15, 36, 24, 0.8)",
        "card_border": "rgba(16, 185, 129, 0.2)",
        "expansion_bg": "rgba(15, 36, 24, 0.6)",
        "primary_accent": "#10b981",
        "secondary_accent": "#14b8a6",
        "slider_track": "rgba(30, 120, 80, 0.3)",
        "slider_selection": "#10b981",
        "progress_track": "rgba(30, 120, 80, 0.3)",
        "progress_gradient": "linear-gradient(90deg, #10b981, #14b8a6)",
        "scrollbar_track": "rgba(15, 36, 24, 0.5)",
        "scrollbar_thumb": "rgba(16, 185, 129, 0.5)",
        "header_gradient": "from-emerald-400 to-teal-400",
    },
    "event_horizon": {
        "name": "Event Horizon",
        "icon": "🕳️",
        "background_gradient": "linear-gradient(135deg, #050505 0%, #0a0a0a 50%, #0f0f0f 100%)",
        "card_bg": "rgba(10, 10, 10, 0.9)",
        "card_border": "rgba(239, 68, 68, 0.3)",
        "expansion_bg": "rgba(10, 10, 10, 0.7)",
        "primary_accent": "#ef4444",
        "secondary_accent": "#f97316",
        "slider_track": "rgba(80, 30, 30, 0.4)",
        "slider_selection": "#ef4444",
        "progress_track": "rgba(80, 30, 30, 0.4)",
        "progress_gradient": "linear-gradient(90deg, #ef4444, #f97316)",
        "scrollbar_track": "rgba(10, 10, 10, 0.6)",
        "scrollbar_thumb": "rgba(239, 68, 68, 0.5)",
        "header_gradient": "from-red-500 to-orange-500",
    },
    "cosmic_microwave": {
        "name": "Cosmic Microwave",
        "icon": "📡",
        "background_gradient": "linear-gradient(135deg, #1a1512 0%, #252018 50%, #2f281e 100%)",
        "card_bg": "rgba(37, 32, 24, 0.8)",
        "card_border": "rgba(245, 158, 11, 0.2)",
        "expansion_bg": "rgba(37, 32, 24, 0.6)",
        "primary_accent": "#f59e0b",
        "secondary_accent": "#fb7185",
        "slider_track": "rgba(120, 90, 40, 0.3)",
        "slider_selection": "#f59e0b",
        "progress_track": "rgba(120, 90, 40, 0.3)",
        "progress_gradient": "linear-gradient(90deg, #f59e0b, #fb7185)",
        "scrollbar_track": "rgba(37, 32, 24, 0.5)",
        "scrollbar_thumb": "rgba(245, 158, 11, 0.5)",
        "header_gradient": "from-amber-400 to-rose-400",
    },
}


def get_theme_css(theme_name: str) -> str:
    """Generate CSS string for a given theme."""
    theme = SPACE_THEMES.get(theme_name, SPACE_THEMES["deep_space"])

    return f"""
        body {{
            background: {theme['background_gradient']};
            min-height: 100vh;
        }}
        .q-card {{
            background: {theme['card_bg']} !important;
            border: 1px solid {theme['card_border']};
            backdrop-filter: blur(10px);
        }}
        .q-expansion-item {{
            background: {theme['expansion_bg']} !important;
        }}
        .q-slider__track {{
            background: {theme['slider_track']} !important;
        }}
        .q-slider__selection {{
            background: {theme['primary_accent']} !important;
        }}
        .q-linear-progress__track {{
            background: {theme['progress_track']} !important;
        }}
        .q-linear-progress__model {{
            background: {theme['progress_gradient']} !important;
        }}
        ::-webkit-scrollbar-track {{
            background: {theme['scrollbar_track']};
        }}
        ::-webkit-scrollbar-thumb {{
            background: {theme['scrollbar_thumb']};
            border-radius: 4px;
        }}
        .theme-accent {{
            color: {theme['primary_accent']} !important;
        }}
        .theme-accent-secondary {{
            color: {theme['secondary_accent']} !important;
        }}
        .q-btn--flat:hover {{
            color: {theme['primary_accent']} !important;
        }}
        .q-toggle__inner--truthy {{
            color: {theme['primary_accent']} !important;
        }}
        .q-checkbox__inner--truthy {{
            color: {theme['primary_accent']} !important;
        }}
    """


def get_base_css() -> str:
    """Get base CSS that doesn't change between themes."""
    return """
        :root {
            --q-dark: #1a1a2e;
            --q-dark-page: #16213e;
        }
        .nicegui-content {
            padding: 0 !important;
        }
        ::-webkit-scrollbar {
            width: 8px;
        }
        .star-field {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }
        @keyframes twinkle {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
        #theme-styles {
            /* Placeholder for dynamic theme styles */
        }
    """


def get_theme_options() -> list:
    """Get list of theme options for dropdown."""
    return [
        {"label": f"{theme['icon']} {theme['name']}", "value": key}
        for key, theme in SPACE_THEMES.items()
    ]
