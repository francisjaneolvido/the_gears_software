COLORS = {
    # Brand primaries
    "primary_orange": "#F19421",
    "primary_orange_dark": "#D97E10",
    "primary_orange_light": "#FFF1DF",
    "primary_red": "#B02029",
    "primary_red_dark": "#8E1A21",

    # Backgrounds
    "background": "#F8F6F3",
    "background_alt": "#F0EDE8",
    "card": "#FFFFFF",
    "card_hover": "#FAFAF9",

    # Text
    "white": "#FFFFFF",
    "text_dark": "#1A1A1A",
    "text_mid": "#444444",
    "text_grey": "#717171",
    "text_light": "#9E9E9E",

    # UI
    "border": "#E5E0D8",
    "border_focus": "#F19421",
    "shadow": "#DED6CF",
    "navy": "#0C1633",
    "navy_light": "#1A2A52",

    # Overlays (tkinter does not support alpha in hex; use stipple patterns instead)
    "overlay": "#0C1633",
    "overlay_light": "#F8F6F3",

    # Semantic
    "success": "#2E7D32",
    "error": "#B02029",
    "input_bg": "#F5F3F0",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 40,
    "xxl": 64,
}

FONTS = {
    "brand":      ("Hedvig Letters Serif 24pt", 24, "bold"),
    "hero":       ("Hedvig Letters Serif 24pt", 24, "bold"),
    "heading":    ("Poppins", 20, "bold"),
    "section":    ("Poppins", 16, "bold"),
    "card_title": ("Poppins", 13, "bold"),
    "body":       ("Poppins", 11),
    "body_bold":  ("Poppins", 11, "bold"),
    "small":      ("Poppins", 9),
    "small_bold": ("Poppins", 9, "bold"),
    "button":     ("Poppins", 10, "bold"),
    "tag":        ("Poppins", 8, "bold"),
    "label":      ("Poppins", 10),
    "input":      ("Poppins", 11),
    "modal_title":("Poppins", 18, "bold"),
    "link":       ("Poppins", 10, "underline"),
}

BUTTON_STYLES = {
    "primary": {
        "bg": COLORS["primary_orange"],
        "fg": COLORS["white"],
        "activebackground": COLORS["primary_orange_dark"],
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
        "font": FONTS["button"],
        "padx": 20,
        "pady": 10,
    },
    "secondary": {
        "bg": COLORS["primary_red"],
        "fg": COLORS["white"],
        "activebackground": COLORS["primary_red_dark"],
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
        "font": FONTS["button"],
        "padx": 20,
        "pady": 10,
    },
    "outline": {
        "bg": COLORS["white"],
        "fg": COLORS["primary_orange"],
        "activebackground": COLORS["primary_orange_light"],
        "activeforeground": COLORS["primary_orange"],
        "relief": "solid",
        "bd": 1,
        "cursor": "hand2",
        "font": FONTS["button"],
        "padx": 18,
        "pady": 9,
    },
    "ghost": {
        "bg": COLORS["background"],
        "fg": COLORS["text_dark"],
        "activebackground": COLORS["border"],
        "activeforeground": COLORS["text_dark"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
        "font": FONTS["button"],
        "padx": 18,
        "pady": 9,
    },
    "modal_primary": {
        "bg": COLORS["primary_orange"],
        "fg": COLORS["white"],
        "activebackground": COLORS["primary_orange_dark"],
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
        "font": FONTS["button"],
        "padx": 0,
        "pady": 12,
    },
    "modal_outline": {
        "bg": COLORS["white"],
        "fg": COLORS["text_grey"],
        "activebackground": COLORS["background"],
        "activeforeground": COLORS["text_dark"],
        "relief": "solid",
        "bd": 1,
        "cursor": "hand2",
        "font": FONTS["button"],
        "padx": 0,
        "pady": 12,
    },
}

RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
    "card": 10,
    "button": 6,
    "input": 6,
    "modal": 14,
}