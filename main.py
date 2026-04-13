import customtkinter as ctk
from db.migrate import run as run_migrations
from pages.login import LoginPage
from pages.dashboard import DashboardPage
from pages.students import StudentsPage
from pages.users import UsersPage
from pages.classes import ClassesPage
from pages.marks import MarksPage
from pages.reports import ReportsPage
from pages.analytics import AnalyticsPage
from pages.backup import BackupPage
from pages.communications import CommunicationsPage
from pages.settings import SettingsPage
from pages.setup_wizard import SetupWizard
from pages.splash import SplashScreen
from routes.auth import logout
from routes.settings import is_setup_complete, get_setting, get_user_permissions
from routes.terms import get_current_term
from utils.theme import *
from utils.session import Session


# Maps nav key → permission required (None = always visible)
NAV_PERMISSION = {
    "dashboard": None,
    "students":  "manage_students",
    "users":     "manage_users",
    "classes":   "manage_subjects",
    "marks":     "enter_marks",
    "grading":   "manage_exams",
    "reports":   "generate_reports",
    "analytics": "view_all_classes",
    "settings":  None,  # admin only via nav visibility
}

NAV_ITEMS = [
    ("dashboard", "Dashboard",   "⊞"),
    ("students",  "Students",    "👥"),
    ("users",     "Users",       "👤"),
    ("classes",   "Classes",     "🏫"),
    ("marks",     "Marks entry", "✏"),
    ("reports",   "Reports",     "▦"),
    ("analytics", "Analytics",   "▲"),
    ("settings",  "Settings",    "⚙"),
    ("comms",     "SMS & Comms", "✉"),
    ("backup",    "Backup",      "↓"),
]


def get_visible_nav(user: dict, perms: list) -> list:
    """Return nav items this user is allowed to see."""
    if user["role"] == "admin":
        return NAV_ITEMS   # admins see everything
    visible = []
    for item in NAV_ITEMS:
        key = item[0]
        required = NAV_PERMISSION.get(key)
        if required is None or required in perms:
            visible.append(item)
    return visible


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GradeVault")
        self.geometry("1280x800")
        self.minsize(960, 600)
        self.configure(fg_color=BG)

        # App icon
        try:
            from pathlib import Path
            icon_path = Path(__file__).parent / "assets" / "icon.png"
            if icon_path.exists():
                from PIL import Image as PILImage
                from customtkinter import CTkImage
                pil_icon = PILImage.open(icon_path)
                icon_img = CTkImage(pil_icon, size=(32, 32))
                self.iconphoto(True, icon_img._light_image)
        except Exception:
            pass

        run_migrations()
        if not is_setup_complete():
            self._run_setup()
        else:
            SplashScreen(self, on_ready=self._show_login, duration=2.0)

    def _run_setup(self):
        self.withdraw()
        def on_complete():
            self.deiconify()
            SplashScreen(self, on_ready=self._show_login, duration=2.5)
        SetupWizard(self, on_complete=on_complete)

    def _show_login(self):
        if hasattr(self, "_shell"):
            self._shell.destroy()
        LoginPage(self, on_success=self._show_app)

    def _show_app(self, user):
        # Load permissions once and cache on session
        perms = get_user_permissions(user["id"]) if user["role"] == "teacher" else []
        user["perms"] = perms
        Session.set(user)

        self._shell = ctk.CTkFrame(self, fg_color=BG)
        self._shell.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._nav_btns = {}
        self._content_frame = None
        self._visible_nav = get_visible_nav(user, perms)
        self._build_sidebar()
        self._build_topbar()
        self._navigate("dashboard")

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self._shell, width=230,
                          fg_color=SURFACE, corner_radius=0,
                          border_color=BORDER, border_width=1)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        school_name = get_setting("school_name", "GradeVault")
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(fill="x", padx=12, pady=(14, 10))
        icon = ctk.CTkFrame(logo, width=32, height=32,
                             fg_color=ACCENT, corner_radius=8)
        icon.pack(side="left")
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, text="GV", text_color="white",
                     font=("", 13, "bold")).place(
            relx=0.5, rely=0.5, anchor="center")
        txt = ctk.CTkFrame(logo, fg_color="transparent")
        txt.pack(side="left", padx=(8, 0), fill="x", expand=True)
        label(txt, "GradeVault", size=13, weight="bold").pack(anchor="w")
        ctk.CTkLabel(txt, text=school_name, font=("", 9),
                     text_color=TEXT_MUTED, wraplength=165,
                     justify="left", anchor="w").pack(anchor="w")

        divider(sb).pack(fill="x")

        nav_area = ctk.CTkFrame(sb, fg_color="transparent")
        nav_area.pack(fill="both", expand=True, padx=6, pady=8)

        # Split visible nav into overview and academics
        overview_keys = {"dashboard", "students", "users", "classes", "settings"}
        overview = [n for n in self._visible_nav if n[0] in overview_keys]
        academics = [n for n in self._visible_nav if n[0] not in overview_keys]

        if overview:
            muted(nav_area, "OVERVIEW", size=10).pack(
                anchor="w", padx=6, pady=(8, 2))
            for key, lbl, icon in overview:
                self._nav_btns[key] = self._make_nav_btn(
                    nav_area, key, lbl, icon)

        if academics:
            muted(nav_area, "ACADEMICS", size=10).pack(
                anchor="w", padx=6, pady=(12, 2))
            for key, lbl, icon in academics:
                self._nav_btns[key] = self._make_nav_btn(
                    nav_area, key, lbl, icon)

        divider(sb).pack(fill="x")
        footer = ctk.CTkFrame(sb, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(10, 12))

        user = Session.get()
        initials = "".join(w[0].upper() for w in user["fullName"].split()[:2])

        user_row = ctk.CTkFrame(footer, fg_color="transparent")
        user_row.pack(fill="x", pady=(0, 8))
        av = ctk.CTkFrame(user_row, width=30, height=30,
                          fg_color=ACCENT_BG, corner_radius=15)
        av.pack(side="left")
        av.pack_propagate(False)
        ctk.CTkLabel(av, text=initials, text_color=ACCENT,
                     font=("", 11, "bold")).place(
            relx=0.5, rely=0.5, anchor="center")
        info = ctk.CTkFrame(user_row, fg_color="transparent")
        info.pack(side="left", padx=8)
        label(info, user["fullName"], size=12, weight="bold").pack(anchor="w")
        muted(info, user["role"].title(), size=11).pack(anchor="w")

        ctk.CTkButton(footer, text="Sign out", height=32,
                      fg_color="transparent", text_color=DANGER,
                      hover_color="#FEF2F2", corner_radius=8,
                      border_color=DANGER, border_width=1,
                      font=("", 12),
                      command=self._logout).pack(fill="x")

    def _make_nav_btn(self, parent, key, lbl, icon):
        btn = ctk.CTkButton(
            parent, text=f" {icon}  {lbl}", anchor="w",
            fg_color="transparent", hover_color=ACCENT_BG,
            text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=("", 13), command=lambda k=key: self._navigate(k),
        )
        btn.pack(fill="x", pady=1)
        return btn

    def _build_topbar(self):
        tb = ctk.CTkFrame(self._shell, height=48, fg_color=SURFACE,
                          corner_radius=0,
                          border_color=BORDER, border_width=1)
        tb.pack(side="top", fill="x")
        tb.pack_propagate(False)
        self._topbar_title = label(tb, "Dashboard", size=15, weight="bold")
        self._topbar_title.pack(side="left", padx=20)
        term = get_current_term()
        term_str = (f"Term {term['term']} · {term['year']}"
                    if term else "No term set")
        badge = ctk.CTkFrame(tb, fg_color=ACCENT_BG, corner_radius=6)
        badge.pack(side="right", padx=16)
        ctk.CTkLabel(badge, text=term_str, text_color=ACCENT,
                     font=("", 12, "bold")).pack(padx=10, pady=4)

    def _navigate(self, key):
        # Permission check
        user = Session.get()
        if user["role"] == "teacher":
            required = NAV_PERMISSION.get(key)
            perms = user.get("perms", [])
            if required and required not in perms:
                self._show_no_access(key)
                return

        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=ACCENT_BG, text_color=ACCENT,
                               font=("", 13, "bold"))
            else:
                btn.configure(fg_color="transparent",
                               text_color=TEXT_MUTED,
                               font=("", 13, "normal"))

        title = next((l for k, l, _ in NAV_ITEMS if k == key), key.title())
        self._topbar_title.configure(text=title)

        if self._content_frame:
            self._content_frame.destroy()

        self._content_frame = ctk.CTkFrame(
            self._shell, fg_color=BG, corner_radius=0)
        self._content_frame.pack(side="top", fill="both", expand=True)

        if key == "dashboard":
            DashboardPage(self._content_frame)
        elif key == "students":
            StudentsPage(self._content_frame)
        elif key == "users":
            UsersPage(self._content_frame)
        elif key == "classes":
            ClassesPage(self._content_frame)
        elif key == "marks":
            MarksPage(self._content_frame)
        elif key == "reports":
            ReportsPage(self._content_frame)
        elif key == "analytics":
            AnalyticsPage(self._content_frame)
        elif key == "backup":
            BackupPage(self._content_frame)
        elif key == "comms":
            CommunicationsPage(self._content_frame)
        elif key == "settings":
            SettingsPage(self._content_frame)
        else:
            ph = ctk.CTkFrame(self._content_frame, fg_color=BG)
            ph.pack(fill="both", expand=True, padx=24, pady=24)
            label(ph, title, size=20, weight="bold").pack(anchor="w")
            muted(ph, "This module is coming soon.").pack(
                anchor="w", pady=(4, 0))

    def _show_no_access(self, key):
        title = next((l for k, l, _ in NAV_ITEMS if k == key), key.title())
        if self._content_frame:
            self._content_frame.destroy()
        self._content_frame = ctk.CTkFrame(
            self._shell, fg_color=BG, corner_radius=0)
        self._content_frame.pack(side="top", fill="both", expand=True)
        ph = ctk.CTkFrame(self._content_frame, fg_color=BG)
        ph.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(ph, text="🔒", font=("", 40)).pack(pady=(40, 8))
        label(ph, "Access restricted", size=20, weight="bold").pack()
        muted(ph, f"You don't have permission to access {title}.\n"
                  "Contact your administrator to request access.").pack(
            pady=(8, 0))

    def _logout(self):
        logout()
        self._shell.destroy()
        self._show_login()


if __name__ == "__main__":
    app = App()
    app.mainloop()
