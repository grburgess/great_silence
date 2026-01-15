"""Preset selector component with clickable scenario cards."""

from nicegui import ui
from typing import Callable, Optional

PRESETS = {
    "moderate": {
        "icon": "⚖️",
        "title": "Moderate",
        "subtitle": "Balanced defaults",
        "description": "Fermi-consistent parameters. A balanced Great Filter scenario.",
        "color": "blue-grey",
    },
    "optimistic": {
        "icon": "🌱",
        "title": "Optimistic",
        "subtitle": "Life is common",
        "description": "High emergence rates, long-lived civilizations. Many contacts!",
        "color": "green",
    },
    "early_filter": {
        "icon": "🧬",
        "title": "Early Filter",
        "subtitle": "Abiogenesis is hard",
        "description": "Life rarely emerges, but survivors thrive for millions of years.",
        "color": "purple",
    },
    "late_filter": {
        "icon": "💥",
        "title": "Late Filter",
        "subtitle": "Tech self-destructs",
        "description": "Life emerges often but civilizations destroy themselves quickly.",
        "color": "red",
    },
    "rare_earth": {
        "icon": "🌍",
        "title": "Rare Earth",
        "subtitle": "Habitable worlds are rare",
        "description": "Few planets can support complex life. Those that do persist.",
        "color": "amber",
    },
}


class PresetSelector:
    """Component for selecting simulation presets via clickable cards."""

    def __init__(self, on_select: Optional[Callable[[str], None]] = None):
        self.on_select = on_select
        self.selected_preset: Optional[str] = "moderate"
        self._cards = {}
        self._build()

    def _build(self) -> None:
        with ui.card().classes("w-full"):
            ui.label("🎯 Quick Start: Choose a Scenario").classes(
                "text-lg font-semibold text-gray-300 mb-4"
            )

            with ui.row().classes("w-full gap-3 flex-wrap justify-center"):
                for preset_id, preset_info in PRESETS.items():
                    self._create_preset_card(preset_id, preset_info)

    def _create_preset_card(self, preset_id: str, info: dict) -> None:
        is_selected = preset_id == self.selected_preset
        base_classes = "cursor-pointer transition-all duration-200 hover:scale-105"
        selected_classes = f"ring-2 ring-{info['color']}-400 bg-{info['color']}-900/30"
        unselected_classes = "bg-gray-800 hover:bg-gray-700"

        card = ui.card().classes(
            f"{base_classes} {'selected_classes' if is_selected else unselected_classes} "
            f"w-40 p-3"
        )
        card.on("click", lambda p=preset_id: self._select_preset(p))
        self._cards[preset_id] = card

        with card:
            with ui.column().classes("items-center gap-1"):
                ui.label(info["icon"]).classes("text-3xl")
                ui.label(info["title"]).classes("text-sm font-bold text-white")
                ui.label(info["subtitle"]).classes("text-xs text-gray-400 text-center")

        card.tooltip(info["description"])

    def _select_preset(self, preset_id: str) -> None:
        self.selected_preset = preset_id
        self._update_card_styles()
        if self.on_select:
            self.on_select(preset_id)

    def _update_card_styles(self) -> None:
        for preset_id, card in self._cards.items():
            info = PRESETS[preset_id]
            is_selected = preset_id == self.selected_preset
            if is_selected:
                card.classes(
                    remove="bg-gray-800 hover:bg-gray-700",
                    add=f"ring-2 ring-{info['color']}-400 bg-{info['color']}-900/30",
                )
            else:
                card.classes(
                    add="bg-gray-800 hover:bg-gray-700",
                    remove=f"ring-2 ring-{info['color']}-400 bg-{info['color']}-900/30",
                )

    def get_selected(self) -> str:
        return self.selected_preset
