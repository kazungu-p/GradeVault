import customtkinter as ctk
from utils.theme import *
from utils.session import Session
from routes.users import (
    get_users, create_user, update_user,
    toggle_user_active, get_assignments, assign_teacher,
    remove_assignment, get_subjects, get_classes,
)
from routes.settings import (
    ALL_PERMISSIONS, get_user_permissions, set_user_permissions,
)


class UsersPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()
        self._load()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        heading(header, "Users & Teachers").pack(side="left")
        primary_btn(header, "+ Add user",
                    command=self._open_add_form,
                    width=120).pack(side="right")

        # Role filter tabs
        self._role_var = ctk.StringVar(value="All")
        self._tabs_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._tabs_frame.pack(fill="x", pady=(0, 10))
        self._render_tabs("All")

        tcard = card(self)
        tcard.pack(fill="both", expand=True)

        thead = ctk.CTkFrame(tcard, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))
        for col_name, col_w in [
            ("Full name", 200), ("Username", 130),
            ("Role", 80), ("Status", 80), ("Actions", 260)
        ]:
            ctk.CTkLabel(thead, text=col_name, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=col_w,
                         anchor="w").pack(side="left", padx=(12, 0), pady=8)

        self._body = ctk.CTkScrollableFrame(
            tcard, fg_color=SURFACE, corner_radius=0)
        self._body.pack(fill="both", expand=True, padx=1, pady=(0, 1))

    def _render_tabs(self, active):
        for w in self._tabs_frame.winfo_children():
            w.destroy()
        for role in ["All", "Admin", "Teacher"]:
            is_active = role == active
            ctk.CTkButton(
                self._tabs_frame, text=role, width=90, height=30,
                fg_color=ACCENT if is_active else "transparent",
                text_color="white" if is_active else TEXT_MUTED,
                hover_color=ACCENT_BG, corner_radius=6, font=("", 12),
                command=lambda r=role: self._filter(r),
            ).pack(side="left", padx=(0, 6))

    def _filter(self, role):
        self._role_var.set(role)
        self._render_tabs(role)
        self._load()

    def _load(self):
        role_map = {"All": None, "Admin": "admin", "Teacher": "teacher"}
        self._users = get_users(role=role_map.get(self._role_var.get()))
        self._render_rows()

    def _render_rows(self):
        for w in self._body.winfo_children():
            w.destroy()

        if not self._users:
            muted(self._body, "No users found.").pack(pady=24)
            return

        current_user = Session.get()

        for i, u in enumerate(self._users):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._body, fg_color=bg,
                               corner_radius=0, height=44)
            row.pack(fill="x")
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=u["full_name"], font=("", 12),
                         text_color=TEXT, width=200,
                         anchor="w").pack(side="left", padx=(12, 0))
            ctk.CTkLabel(row, text=u["username"], font=("", 12),
                         text_color=TEXT_MUTED, width=130,
                         anchor="w").pack(side="left", padx=(12, 0))

            role_color = ACCENT_BG if u["role"] == "admin" else "#F0FDF4"
            role_text  = ACCENT    if u["role"] == "admin" else SUCCESS
            badge_wrap = ctk.CTkFrame(row, fg_color="transparent",
                                       width=90)
            badge_wrap.pack(side="left", padx=(12, 0))
            badge_wrap.pack_propagate(False)
            badge = ctk.CTkFrame(badge_wrap, fg_color=role_color,
                                  corner_radius=6)
            badge.place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(badge, text=u["role"].title(),
                         font=("", 11),
                         text_color=role_text).pack(padx=10, pady=3)

            status_color = SUCCESS if u["is_active"] else DANGER
            ctk.CTkLabel(row,
                         text="Active" if u["is_active"] else "Inactive",
                         font=("", 12), text_color=status_color,
                         width=80,
                         anchor="w").pack(side="left", padx=(12, 0))

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="left", padx=8)

            ctk.CTkButton(actions, text="Edit", width=50, height=26,
                          fg_color="transparent", border_color=BORDER,
                          border_width=1, text_color=TEXT, corner_radius=6,
                          hover_color=BG, font=("", 11),
                          command=lambda usr=u: self._open_edit_form(usr)
                          ).pack(side="left", padx=(0, 4))

            if u["role"] == "teacher":
                ctk.CTkButton(actions, text="Assignments", width=90,
                              height=26,
                              fg_color="transparent", border_color=BORDER,
                              border_width=1, text_color=TEXT,
                              corner_radius=6, hover_color=BG, font=("", 11),
                              command=lambda usr=u: self._open_assignments(usr)
                              ).pack(side="left", padx=(0, 4))

            if u["id"] != current_user["id"]:
                toggle_text  = "Deactivate" if u["is_active"] else "Activate"
                toggle_color = DANGER if u["is_active"] else SUCCESS
                ctk.CTkButton(actions, text=toggle_text, width=80,
                              height=26, fg_color="transparent",
                              border_color=toggle_color, border_width=1,
                              text_color=toggle_color, corner_radius=6,
                              hover_color="#FEF2F2" if u["is_active"] else "#F0FDF4",
                              font=("", 11),
                              command=lambda usr=u: self._toggle(usr)
                              ).pack(side="left")

    def _open_add_form(self):
        UserForm(self, title="Add user", on_save=self._on_save_new)

    def _open_edit_form(self, user):
        UserForm(self, title="Edit user", user=user,
                 on_save=self._on_save_edit)

    def _open_assignments(self, user):
        AssignmentsDialog(self, user=user)

    def _on_save_new(self, data):
        ok, msg = create_user(data["username"], data["full_name"],
                              data["role"], data["password"])
        if ok and data["role"] == "teacher":
            from db.connection import query_one
            row = query_one("SELECT id FROM users WHERE username=?",
                            (data["username"],))
            if row:
                set_user_permissions(row["id"], data.get("perms", []))
        if ok:
            self._load()
        return ok, msg

    def _on_save_edit(self, data):
        ok, msg = update_user(data["user_id"], data["full_name"],
                              data["role"],
                              data.get("password") or None)
        if ok and data["role"] == "teacher":
            set_user_permissions(data["user_id"], data.get("perms", []))
        if ok:
            self._load()
        return ok, msg

    def _toggle(self, user):
        toggle_user_active(user["id"])
        self._load()


# ── User form with permissions ────────────────────────────────
class UserForm(ctk.CTkToplevel):
    def __init__(self, parent, title, on_save, user=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("520x660")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save
        self._user = user
        self._perm_vars = {}
        self._build()
        if user:
            self._populate(user)

    def _build(self):
        outer = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        outer.pack(fill="both", expand=True)
        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(f, self.title()).pack(anchor="w", pady=(0, 16))

        # ── Basic info ───────────────────────────────────────
        muted(f, "Full name *").pack(anchor="w")
        self._name = ctk.CTkEntry(f, width=420,
                                   fg_color=SURFACE, border_color=BORDER)
        self._name.pack(anchor="w", pady=(4, 14))

        muted(f, "Username *").pack(anchor="w")
        self._username = ctk.CTkEntry(f, width=420,
                                       fg_color=SURFACE, border_color=BORDER)
        self._username.pack(anchor="w", pady=(4, 14))
        if self._user:
            self._username.configure(state="disabled")

        muted(f, "Role *").pack(anchor="w")
        self._role_var = ctk.StringVar(value="teacher")
        role_row = ctk.CTkFrame(f, fg_color="transparent")
        role_row.pack(anchor="w", pady=(4, 14))
        for role in ["teacher", "admin"]:
            ctk.CTkRadioButton(
                role_row, text=role.title(),
                variable=self._role_var, value=role,
                font=("", 12), text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_DARK,
                command=self._toggle_perms,
            ).pack(side="left", padx=(0, 20))

        pw_label = "New password (leave blank to keep)" \
            if self._user else "Password *"
        muted(f, pw_label).pack(anchor="w")
        self._password = ctk.CTkEntry(f, width=420,
                                       fg_color=SURFACE,
                                       border_color=BORDER, show="•")
        self._password.pack(anchor="w", pady=(4, 14))

        # ── Permissions (teachers only) ──────────────────────
        self._perms_card = ctk.CTkFrame(
            f, fg_color=SURFACE,
            border_color=BORDER, border_width=1, corner_radius=8)
        self._perms_card.pack(fill="x", pady=(0, 10))

        perms_header = ctk.CTkFrame(
            self._perms_card, fg_color=ACCENT_BG, corner_radius=0)
        perms_header.pack(fill="x")
        ctk.CTkLabel(perms_header, text="Permissions",
                     font=("", 12, "bold"),
                     text_color=ACCENT).pack(
            anchor="w", padx=12, pady=8)

        self._perms_body = ctk.CTkFrame(
            self._perms_card, fg_color="transparent")
        self._perms_body.pack(fill="x", padx=12, pady=(6, 10))

        for key, label_text, desc in ALL_PERMISSIONS:
            var = ctk.BooleanVar(value=(key == "enter_marks"))
            self._perm_vars[key] = var
            row = ctk.CTkFrame(self._perms_body, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkCheckBox(
                row, text=label_text,
                variable=var,
                font=("", 12), text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_DARK,
                width=160,
            ).pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("", 11),
                         text_color=TEXT_MUTED,
                         anchor="w").pack(side="left", padx=(8, 0))

        self._error = ctk.CTkLabel(f, text="",
                                    text_color=DANGER, font=("", 12))
        self._error.pack(anchor="w")

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        ghost_btn(btn_row, "Cancel",
                  command=self.destroy, width=100).pack(side="left")
        primary_btn(btn_row, "Save",
                    command=self._submit, width=100).pack(side="right")

        self._toggle_perms()

    def _toggle_perms(self):
        """Show permissions only for teachers."""
        show = self._role_var.get() == "teacher"
        if show:
            self._perms_card.pack(fill="x", pady=(0, 10))
        else:
            self._perms_card.pack_forget()

    def _populate(self, u):
        self._name.insert(0, u["full_name"])
        self._username.insert(0, u["username"])
        self._role_var.set(u["role"])
        self._toggle_perms()
        if u["role"] == "teacher":
            current_perms = get_user_permissions(u["id"])
            for key, var in self._perm_vars.items():
                var.set(key in current_perms)

    def _submit(self):
        self._error.configure(text="")
        data = {
            "full_name": self._name.get().strip(),
            "username":  self._username.get().strip(),
            "role":      self._role_var.get(),
            "password":  self._password.get(),
            "perms": [k for k, v in self._perm_vars.items() if v.get()],
        }
        if self._user:
            data["user_id"] = self._user["id"]
        ok, msg = self._on_save(data)
        if ok:
            self.destroy()
        else:
            self._error.configure(text=msg)


# ── Assignments dialog ────────────────────────────────────────
class AssignmentsDialog(ctk.CTkToplevel):
    def __init__(self, parent, user):
        super().__init__(parent)
        self.title(f"Assignments — {user['full_name']}")
        self.geometry("560x560")
        self.resizable(False, False)
        self.grab_set()
        self._user = user
        self._subjects = get_subjects()
        self._classes  = get_classes()
        self._build()
        self._load()

    def _build(self):
        self._f = ctk.CTkFrame(self, fg_color=BG)
        self._f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(self._f,
                f"Assignments — {self._user['full_name']}",
                size=15).pack(anchor="w", pady=(0, 4))
        muted(self._f,
              "Subjects and classes this teacher is responsible for."
              ).pack(anchor="w", pady=(0, 12))

        self._list_frame = ctk.CTkScrollableFrame(
            self._f, fg_color=SURFACE, corner_radius=8,
            border_color=BORDER, border_width=1, height=200)
        self._list_frame.pack(fill="x", pady=(0, 16))

        divider(self._f).pack(fill="x", pady=(0, 12))
        muted(self._f, "Add new assignment").pack(anchor="w", pady=(0, 6))

        add_row = ctk.CTkFrame(self._f, fg_color="transparent")
        add_row.pack(fill="x")

        subj_labels = [s["name"] for s in self._subjects]
        self._subj_var = ctk.StringVar(
            value=subj_labels[0] if subj_labels else "")
        ctk.CTkOptionMenu(add_row, variable=self._subj_var,
                          values=subj_labels, width=180,
                          fg_color=SURFACE, button_color=BORDER,
                          button_hover_color=ACCENT, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(side="left", padx=(0, 8))

        class_labels = [
            f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
            for c in self._classes
        ]
        self._class_var = ctk.StringVar(
            value=class_labels[0] if class_labels else "")
        ctk.CTkOptionMenu(add_row, variable=self._class_var,
                          values=class_labels, width=150,
                          fg_color=SURFACE, button_color=BORDER,
                          button_hover_color=ACCENT, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(side="left", padx=(0, 8))

        primary_btn(add_row, "Add",
                    command=self._add, width=80).pack(side="left")

        self._msg = ctk.CTkLabel(self._f, text="", font=("", 12),
                                  text_color=DANGER)
        self._msg.pack(anchor="w", pady=(8, 0))

    def _load(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        assignments = get_assignments(self._user["id"])
        if not assignments:
            muted(self._list_frame,
                  "No assignments yet.").pack(pady=12)
            return
        for a in assignments:
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            stream = a.get("stream", "") or ""
            ctk.CTkLabel(
                row,
                text=f"{a['subject_name']}  —  {a['class_name']}{' ' + stream if stream else ''}",
                font=("", 12), text_color=TEXT,
                anchor="w").pack(side="left", padx=(4, 0))
            ctk.CTkButton(row, text="Remove", width=70, height=24,
                          fg_color="transparent", border_color=DANGER,
                          border_width=1, text_color=DANGER,
                          corner_radius=6, hover_color="#FEF2F2",
                          font=("", 11),
                          command=lambda aid=a["id"]: self._remove(aid)
                          ).pack(side="right", padx=4)
            divider(self._list_frame).pack(fill="x")

    def _add(self):
        self._msg.configure(text="")
        subj = next((s for s in self._subjects
                     if s["name"] == self._subj_var.get()), None)
        cls  = next((c for c in self._classes if
                     f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
                     == self._class_var.get()), None)
        if not subj or not cls:
            self._msg.configure(text="Select a valid subject and class.")
            return
        from routes.users import assign_teacher
        ok, msg = assign_teacher(self._user["id"], subj["id"], cls["id"])
        self._msg.configure(
            text=msg,
            text_color=SUCCESS if ok else DANGER)
        if ok:
            self._load()

    def _remove(self, assignment_id):
        from routes.users import remove_assignment
        remove_assignment(assignment_id)
        self._load()
