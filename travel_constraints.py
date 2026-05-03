from schemas import TravelStyle

TRAVEL_STYLE_CONFLICTS: dict[str, set[str]] = {
    "solo": {"family", "honeymoon"},
    "family": {"solo", "honeymoon"},
    "honeymoon": {"solo", "family"}
}

def filter_travel_styles(travel_styles: list[str]) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    removed: list[str] = []
    blocked: set[str] = set()

    for raw_style in travel_styles:
        style = str(raw_style).strip().lower()
        if not style or style not in TravelStyle._value2member_map_:
            continue
        if style in blocked:
            if style not in removed:
                removed.append(style)
            continue
        if style in selected:
            continue
        selected.append(style)
        blocked.update(TRAVEL_STYLE_CONFLICTS.get(style, set()))

    return selected, removed

def style_warning_message(removed: list[str]) -> list[str]:
    if not removed:
        return []
    return [f"Removed incompatible travel styles: {', '.join(removed)}."]