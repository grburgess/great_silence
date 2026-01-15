"""Space-themed color schemes for the webapp."""

from typing import Dict, Any


THEME_GRAPHICS = {
    "deep_space": """
        .theme-bg-effect {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        .theme-bg-effect::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background-image: 
                radial-gradient(2px 2px at 20px 30px, #fff, transparent),
                radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
                radial-gradient(1px 1px at 90px 40px, #fff, transparent),
                radial-gradient(2px 2px at 160px 120px, rgba(255,255,255,0.9), transparent),
                radial-gradient(1px 1px at 230px 80px, #fff, transparent),
                radial-gradient(2px 2px at 300px 150px, rgba(255,255,255,0.7), transparent),
                radial-gradient(1px 1px at 50px 180px, #fff, transparent),
                radial-gradient(2px 2px at 120px 220px, rgba(255,255,255,0.8), transparent);
            background-size: 350px 250px;
            animation: twinkle-stars 4s ease-in-out infinite alternate;
        }
        @keyframes twinkle-stars {
            0% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    """,
    "nebula": """
        .theme-bg-effect {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        .theme-bg-effect::before,
        .theme-bg-effect::after {
            content: '';
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            animation: nebula-drift 20s ease-in-out infinite;
        }
        .theme-bg-effect::before {
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(232,121,249,0.3) 0%, transparent 70%);
            top: -200px;
            left: -100px;
        }
        .theme-bg-effect::after {
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(244,114,182,0.25) 0%, transparent 70%);
            bottom: -150px;
            right: -100px;
            animation-delay: -10s;
        }
        @keyframes nebula-drift {
            0%, 100% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(30px, 20px) scale(1.1); }
        }
    """,
    "solar_flare": """
        .theme-bg-effect {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        .theme-bg-effect::before {
            content: '';
            position: absolute;
            width: 800px;
            height: 800px;
            background: radial-gradient(circle, rgba(249,115,22,0.4) 0%, rgba(251,191,36,0.2) 30%, transparent 70%);
            top: -400px;
            right: -200px;
            border-radius: 50%;
            animation: solar-pulse 8s ease-in-out infinite;
        }
        .theme-bg-effect::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(ellipse 100px 300px at 80% 20%, rgba(251,191,36,0.15) 0%, transparent 100%),
                radial-gradient(ellipse 80px 250px at 85% 30%, rgba(249,115,22,0.1) 0%, transparent 100%);
            animation: flare-wave 6s ease-in-out infinite;
        }
        @keyframes solar-pulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.15); opacity: 1; }
        }
        @keyframes flare-wave {
            0%, 100% { opacity: 0.5; transform: translateY(0); }
            50% { opacity: 1; transform: translateY(-20px); }
        }
    """,
    "aurora": """
        .theme-bg-effect {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        .theme-bg-effect::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 60%;
            top: 0;
            left: -50%;
            background: 
                linear-gradient(180deg, 
                    transparent 0%,
                    rgba(16,185,129,0.1) 20%,
                    rgba(20,184,166,0.15) 40%,
                    rgba(16,185,129,0.1) 60%,
                    transparent 100%
                );
            filter: blur(30px);
            animation: aurora-wave 15s ease-in-out infinite;
            transform-origin: center top;
        }
        .theme-bg-effect::after {
            content: '';
            position: absolute;
            width: 150%;
            height: 50%;
            top: 5%;
            left: -25%;
            background: 
                linear-gradient(180deg, 
                    transparent 0%,
                    rgba(20,184,166,0.08) 30%,
                    rgba(16,185,129,0.12) 50%,
                    transparent 100%
                );
            filter: blur(40px);
            animation: aurora-wave 12s ease-in-out infinite reverse;
            animation-delay: -5s;
        }
        @keyframes aurora-wave {
            0%, 100% { transform: translateX(-10%) skewX(-5deg); }
            50% { transform: translateX(10%) skewX(5deg); }
        }
    """,
    "event_horizon": """
        .theme-bg-effect {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        .theme-bg-effect::before {
            content: '';
            position: absolute;
            width: 500px;
            height: 500px;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: 
                radial-gradient(circle, 
                    #000 0%, 
                    #000 20%,
                    rgba(239,68,68,0.3) 25%,
                    rgba(249,115,22,0.2) 35%,
                    transparent 50%
                );
            border-radius: 50%;
            animation: horizon-spin 30s linear infinite;
        }
        .theme-bg-effect::after {
            content: '';
            position: absolute;
            width: 600px;
            height: 200px;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotateX(75deg);
            background: 
                conic-gradient(from 0deg, 
                    transparent 0deg,
                    rgba(239,68,68,0.4) 30deg,
                    rgba(249,115,22,0.3) 60deg,
                    transparent 120deg,
                    rgba(239,68,68,0.3) 180deg,
                    rgba(249,115,22,0.4) 240deg,
                    transparent 300deg,
                    transparent 360deg
                );
            border-radius: 50%;
            filter: blur(20px);
            animation: accretion-disk 20s linear infinite;
        }
        @keyframes horizon-spin {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        @keyframes accretion-disk {
            from { transform: translate(-50%, -50%) rotateX(75deg) rotate(0deg); }
            to { transform: translate(-50%, -50%) rotateX(75deg) rotate(360deg); }
        }
    """,
    "cosmic_microwave": """
        .theme-bg-effect {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }
        .theme-bg-effect::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 200%;
            top: -50%;
            left: -50%;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
            opacity: 0.04;
            animation: cmb-shift 30s linear infinite;
        }
        .theme-bg-effect::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(ellipse at 30% 20%, rgba(245,158,11,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 60%, rgba(251,113,133,0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 40% 80%, rgba(245,158,11,0.05) 0%, transparent 40%);
            animation: cmb-pulse 10s ease-in-out infinite;
        }
        @keyframes cmb-shift {
            from { transform: translate(0, 0); }
            to { transform: translate(50%, 50%); }
        }
        @keyframes cmb-pulse {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; }
        }
    """,
}


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
    graphics = THEME_GRAPHICS.get(theme_name, THEME_GRAPHICS["deep_space"])

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
        {graphics}
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
