"""Shared enum contract used before either MCP or CLI generation."""

TEXT_ALIGN_VALUES = {"Left", "Center", "Right", "Justified"}
VERTICAL_ALIGN_VALUES = {"Top", "Middle", "Bottom"}
LAYOUT_GROUP_VALUES = {"Horizontal", "Vertical"}
CHILD_ALIGNMENT_VALUES = {
    vertical + horizontal
    for vertical in ("Upper", "Middle", "Lower")
    for horizontal in ("Left", "Center", "Right")
}
ENUM_VALUES = {
    "textAlign": TEXT_ALIGN_VALUES,
    "verticalAlign": VERTICAL_ALIGN_VALUES,
    "layoutGroup": LAYOUT_GROUP_VALUES,
    "layoutChildAlignment": CHILD_ALIGNMENT_VALUES,
}
