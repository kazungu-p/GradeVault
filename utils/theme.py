import customtkinter as ctk

# ── Appearance ───────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Palette ──────────────────────────────────────────────────
ACCENT      = "#4F46E5"
ACCENT_DARK = "#3730A3"
ACCENT_BG   = "#EEF2FF"
BG          = "#F5F4F0"
SURFACE     = "#FFFFFF"
BORDER      = "#E5E7EB"
TEXT        = "#111827"
TEXT_MUTED  = "#6B7280"
DANGER      = "#EF4444"
SUCCESS     = "#10B981"
WARNING     = "#F59E0B"
SIDEBAR_W   = 200


def label(parent, text, size=13, weight="normal", color=TEXT, **kw):
    return ctk.CTkLabel(parent, text=text, font=("", size, weight),
                        text_color=color, **kw)


def muted(parent, text, size=12, **kw):
    return label(parent, text, size=size, color=TEXT_MUTED, **kw)


def heading(parent, text, size=20, **kw):
    return label(parent, text, size=size, weight="bold", **kw)


def entry(parent, placeholder="", show=None, width=280, **kw):
    e = ctk.CTkEntry(parent, placeholder_text=placeholder,
                     width=width, show=show,
                     border_color=BORDER,
                     fg_color=SURFACE, **kw)
    return e


def primary_btn(parent, text, command=None, width=280, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         width=width, height=38,
                         fg_color=ACCENT, hover_color=ACCENT_DARK,
                         corner_radius=8, **kw)


def ghost_btn(parent, text, command=None, width=120, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         width=width, height=32,
                         fg_color="transparent",
                         border_color=BORDER, border_width=1,
                         text_color=TEXT_MUTED,
                         hover_color=BG,
                         corner_radius=8, **kw)


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=SURFACE,
                        border_color=BORDER, border_width=1,
                        corner_radius=12, **kw)


def sidebar_item(parent, text, icon, command, active=False):
    bg    = ACCENT_BG if active else "transparent"
    color = ACCENT    if active else TEXT_MUTED
    btn = ctk.CTkButton(
        parent, text=f"  {icon}  {text}",
        command=command,
        anchor="w",
        fg_color=bg,
        hover_color=ACCENT_BG,
        text_color=color,
        corner_radius=8,
        height=36,
        font=("", 13, "bold" if active else "normal"),
    )
    return btn


def divider(parent, **kw):
    return ctk.CTkFrame(parent, height=1, fg_color=BORDER, **kw)


class StyledDialog(ctk.CTkToplevel):
    """Base dialog with consistent styling: header, scrollable body, pinned footer."""
    def __init__(self, parent, title: str, width: int = 520,
                 height: int = 480):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.grab_set()
        self._outer = ctk.CTkFrame(self, fg_color=BG)
        self._outer.pack(fill="both", expand=True)

    def body(self) -> ctk.CTkScrollableFrame:
        """Returns a scrollable body frame — override or pack widgets into it."""
        f = ctk.CTkScrollableFrame(
            self._outer, fg_color=BG, corner_radius=0,
            scrollbar_button_color=BG,
            scrollbar_button_hover_color=BORDER)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))
        return f

    def footer(self) -> ctk.CTkFrame:
        """Returns a pinned footer frame for action buttons."""
        f = ctk.CTkFrame(self._outer, fg_color=SURFACE,
                          border_color=BORDER, border_width=1,
                          corner_radius=0, height=56)
        f.pack(fill="x", side="bottom")
        f.pack_propagate(False)
        return f

    def add_cancel(self, footer):
        ghost_btn(footer, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)

    def add_save(self, footer, text="Save", command=None, width=100):
        primary_btn(footer, text, command=command,
                    width=width).pack(side="right", padx=20, pady=10)


def make_dialog(window, title: str, width: int = 480,
                height: int = 400) -> tuple:
    """
    Create a consistently styled dialog.
    Returns (outer_frame, content_frame, footer_frame)
    Uses scrollable content with pinned footer.
    """
    window.geometry(f"{width}x{height}")
    window.resizable(False, False)
    try:
        window.grab_set()
    except Exception:
        pass

    outer = ctk.CTkFrame(window, fg_color=BG)
    outer.pack(fill="both", expand=True)

    content = ctk.CTkScrollableFrame(
        outer, fg_color=BG, corner_radius=0,
        scrollbar_button_color=BG,
        scrollbar_button_hover_color=BORDER)
    content.pack(fill="both", expand=True, padx=28, pady=(24, 0))

    footer = ctk.CTkFrame(
        outer, fg_color=SURFACE,
        border_color=BORDER, border_width=1,
        corner_radius=0, height=56)
    footer.pack(fill="x", side="bottom")
    footer.pack_propagate(False)

    return outer, content, footer


def invisible_scroll(parent, height=None, **kwargs):
    """CTkScrollableFrame with scrollbar blending into background."""
    kw = dict(fg_color=BG, scrollbar_button_color=BORDER,
               scrollbar_button_hover_color=TEXT_MUTED, corner_radius=0)
    kw.update(kwargs)
    if height:
        kw["height"] = height
    return ctk.CTkScrollableFrame(parent, **kw)
