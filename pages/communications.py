import customtkinter as ctk
import os
from tkinter import filedialog
from utils.theme import *
from routes.classes import get_classes
from routes.students import get_students
from routes.communications import (
    get_contacts, add_contact, update_contact, delete_contact,
    get_primary_contacts_for_class, get_all_primary_contacts,
    send_sms, get_sms_log, get_at_credentials, save_at_credentials,
)
from utils.grading import compute_class_results


class CommunicationsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._active_tab = "sms"
        self._build()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)
        heading(self, "Communications").pack(anchor="w", pady=(0, 14))

        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 14))
        self._tab_btns = {}
        from utils.session import Session as _Sess
        _user = _Sess.get()
        _is_admin = _user and _user.get("role") == "admin"
        _tabs = [("sms",      "Bulk SMS"),
                 ("contacts", "Parent contacts"),
                 ("log",      "SMS log")]
        if _is_admin:
            _tabs.append(("settings", "SMS settings"))
        for key, lbl in _tabs:
            btn = ctk.CTkButton(
                tabs, text=lbl, height=30,
                fg_color=ACCENT if key == "sms" else "transparent",
                text_color="white" if key == "sms" else TEXT_MUTED,
                hover_color=ACCENT_BG, corner_radius=6, font=("", 12),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn

        # Content area below tabs — frames placed inside this
        self._content_area = ctk.CTkFrame(self, fg_color="transparent")
        self._content_area.pack(fill="both", expand=True)

        self._frames = {}
        _frame_keys = ["sms", "contacts", "log"]
        if _is_admin:
            _frame_keys.append("settings")

        for key in _frame_keys:
            f = ctk.CTkFrame(self._content_area, fg_color="transparent")
            self._frames[key] = f
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_sms(self._frames["sms"])
        self._build_contacts(self._frames["contacts"])
        self._build_log(self._frames["log"])
        if _is_admin:
            self._build_settings(self._frames["settings"])
        self._switch_tab("sms")

    def _switch_tab(self, key):
        self._active_tab = key
        for k, f in self._frames.items():
            if k == key:
                f.lift()
            else:
                f.lower()
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color=ACCENT if k == key else "transparent",
                text_color="white" if k == key else TEXT_MUTED)

    # ── Bulk SMS ──────────────────────────────────────────────
    def _build_sms(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        # Message type
        sec1 = self._section(scroll, "Message type")
        f1 = ctk.CTkFrame(sec1, fg_color="transparent")
        f1.pack(fill="x", padx=16, pady=(0, 14))

        self._sms_type = ctk.StringVar(value="bulk")
        for val, lbl in [
            ("bulk",       "Bulk message to a class"),
            ("report",     "Report card summary to parents"),
            ("individual", "Custom message to selected students"),
        ]:
            ctk.CTkRadioButton(
                f1, text=lbl, variable=self._sms_type,
                value=val, font=("", 12), text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_DARK,
                command=self._on_sms_type_change,
            ).pack(anchor="w", pady=4)

        # Target selector
        sec2 = self._section(scroll, "Recipients")
        self._recip_frame = ctk.CTkFrame(sec2, fg_color="transparent")
        self._recip_frame.pack(fill="x", padx=16, pady=(0, 14))
        self._classes_data = get_classes()
        self._build_recipient_selector()

        # Message composer
        sec3 = self._section(scroll, "Message")
        f3 = ctk.CTkFrame(sec3, fg_color="transparent")
        f3.pack(fill="x", padx=16, pady=(0, 14))

        self._msg_frame = ctk.CTkFrame(f3, fg_color="transparent")
        self._msg_frame.pack(fill="x")
        self._build_message_composer()

        # Send
        sec4 = self._section(scroll, "Send")
        f4 = ctk.CTkFrame(sec4, fg_color="transparent")
        f4.pack(fill="x", padx=16, pady=(0, 14))

        self._preview_lbl = muted(f4, "")
        self._preview_lbl.pack(anchor="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(f4, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Preview recipients",
                  command=self._preview_recipients, width=160
                  ).pack(side="left", padx=(0, 10))
        primary_btn(btn_row, "Send SMS",
                    command=self._send, width=120).pack(side="left")

        self._send_status = ctk.CTkLabel(
            f4, text="", font=("", 12), text_color=TEXT_MUTED,
            wraplength=500, justify="left")
        self._send_status.pack(anchor="w", pady=(10, 0))

    def _on_sms_type_change(self):
        self._build_recipient_selector()
        self._build_message_composer()

    def _build_recipient_selector(self):
        for w in self._recip_frame.winfo_children():
            w.destroy()
        t = self._sms_type.get()

        cls_labels = ["All classes"] + [
            f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
            for c in self._classes_data]
        self._class_var = ctk.StringVar(value="All classes")

        if t in ("bulk", "report"):
            muted(self._recip_frame, "Class").pack(anchor="w")
            ctk.CTkOptionMenu(
                self._recip_frame, variable=self._class_var,
                values=cls_labels, width=320,
                fg_color=SURFACE, button_color=BORDER,
                text_color=TEXT, dropdown_fg_color=SURFACE,
            ).pack(anchor="w", pady=(4, 0))

        elif t == "individual":
            muted(self._recip_frame, "Class").pack(anchor="w")
            ctk.CTkOptionMenu(
                self._recip_frame, variable=self._class_var,
                values=cls_labels, width=320,
                fg_color=SURFACE, button_color=BORDER,
                text_color=TEXT, dropdown_fg_color=SURFACE,
                command=self._load_student_checklist,
            ).pack(anchor="w", pady=(4, 10))

            self._student_scroll = ctk.CTkScrollableFrame(
                self._recip_frame, fg_color=SURFACE,
                border_color=BORDER, border_width=1,
                corner_radius=8, height=180)
            self._student_scroll.pack(fill="x")
            self._student_vars = {}
            self._load_student_checklist()

    def _load_student_checklist(self, _=None):
        for w in self._student_scroll.winfo_children():
            w.destroy()
        self._student_vars = {}
        sel = self._class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == sel), None)
        students = get_students(class_id=cls["id"]) if cls else get_students()
        for s in students:
            var = ctk.BooleanVar(value=True)
            self._student_vars[s["id"]] = var
            ctk.CTkCheckBox(
                self._student_scroll,
                text=f"{s['full_name']}  ({s['admission_number']})",
                variable=var, font=("", 11), text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_DARK,
            ).pack(anchor="w", padx=8, pady=2)

    def _build_message_composer(self):
        for w in self._msg_frame.winfo_children():
            w.destroy()
        t = self._sms_type.get()

        if t == "report":
            muted(self._msg_frame,
                  "Report card summaries are auto-generated per student.\n"
                  "Select the assessment to include:"
                  ).pack(anchor="w", pady=(0, 8))
            from routes.assessments import get_assessments
            asmts = get_assessments()
            self._asmt_var = ctk.StringVar(
                value=asmts[0]["name"] if asmts else "—")
            ctk.CTkOptionMenu(
                self._msg_frame, variable=self._asmt_var,
                values=[a["name"] for a in asmts] if asmts else ["—"],
                width=320, fg_color=SURFACE,
                button_color=BORDER, text_color=TEXT,
                dropdown_fg_color=SURFACE,
            ).pack(anchor="w", pady=(0, 8))
            self._asmt_data = asmts

            muted(self._msg_frame,
                  "Preview of message that will be sent:"
                  ).pack(anchor="w", pady=(8, 4))
            school = __import__("routes.settings",
                                fromlist=["get_setting"]).get_setting(
                "school_name", "School")
            preview = (
                f"{school}\n"
                f"Dear Parent/Guardian,\n"
                f"[Student Name] scored [Mean]% "
                f"([Grade]) — Position [Pos] in class.\n"
                f"[Assessment Name]"
            )
            ctk.CTkLabel(self._msg_frame, text=preview,
                         font=("", 11), text_color=TEXT_MUTED,
                         fg_color="#F3F4F6", corner_radius=6,
                         justify="left",
                         ).pack(anchor="w", fill="x", pady=(0, 0))
        else:
            muted(self._msg_frame, "Message *").pack(anchor="w")
            self._msg_box = ctk.CTkTextbox(
                self._msg_frame, width=500, height=100,
                fg_color=SURFACE, border_color=BORDER, font=("", 12))
            self._msg_box.pack(anchor="w", pady=(4, 0))
            self._char_lbl = muted(self._msg_frame, "0 / 160 characters")
            self._char_lbl.pack(anchor="w", pady=(4, 0))
            self._msg_box.bind("<KeyRelease>", self._update_char_count)

    def _update_char_count(self, _=None):
        try:
            n = len(self._msg_box.get("1.0", "end").strip())
            self._char_lbl.configure(
                text=f"{n} / 160 characters",
                text_color=DANGER if n > 160 else TEXT_MUTED)
        except Exception:
            pass

    def _get_recipients(self) -> list[dict]:
        t   = self._sms_type.get()
        sel = self._class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == sel), None)

        if t == "individual":
            selected_ids = [sid for sid, v in self._student_vars.items()
                            if v.get()]
            contacts = []
            for sid in selected_ids:
                cts = get_contacts(sid)
                for c in cts:
                    if c["is_primary"]:
                        contacts.append({
                            "name":  c["name"],
                            "phone": c["phone"],
                            "student_id": sid,
                        })
            return contacts

        if cls:
            return [{"name": r["name"], "phone": r["phone"],
                     "student_id": None,
                     "student_name": r["student_name"]}
                    for r in get_primary_contacts_for_class(cls["id"])]
        return [{"name": r["name"], "phone": r["phone"],
                 "student_id": None}
                for r in get_all_primary_contacts()]

    def _preview_recipients(self):
        recips = self._get_recipients()
        self._preview_lbl.configure(
            text=f"{len(recips)} recipient(s) will receive this message.")

    def _send(self):
        api_key, username = get_at_credentials()
        if not api_key:
            self._send_status.configure(
                text="⚠ Africa's Talking credentials not set.\n"
                     "Go to the SMS Settings tab to configure.",
                text_color=DANGER)
            return

        recips = self._get_recipients()
        if not recips:
            self._send_status.configure(
                text="No recipients found. "
                     "Make sure contacts are added for these students.",
                text_color=DANGER)
            return

        t = self._sms_type.get()

        if t == "report":
            self._send_report_sms(recips, api_key, username)
        else:
            msg = self._msg_box.get("1.0", "end").strip()
            if not msg:
                self._send_status.configure(
                    text="Please type a message.", text_color=DANGER)
                return
            self._do_send(recips, msg, api_key, username)

    def _send_report_sms(self, recips, api_key, username):
        from routes.assessments import get_assessments
        asmt_name = getattr(self, "_asmt_var",
                            ctk.StringVar()).get()
        asmt = next((a for a in getattr(self, "_asmt_data", [])
                     if a["name"] == asmt_name), None)
        if not asmt:
            self._send_status.configure(
                text="No assessment selected.", text_color=DANGER)
            return

        school = __import__("routes.settings",
                            fromlist=["get_setting"]).get_setting(
            "school_name", "School")

        # Build personalised messages per student
        sel = self._class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == sel), None)

        if not cls:
            self._send_status.configure(
                text="Please select a class first.", text_color=DANGER)
            return

        results = compute_class_results(asmt["id"], cls["id"])
        result_map = {r["student_id"]: r for r in results}

        messages = []
        for r in recips:
            sid = r.get("student_id")
            if not sid:
                continue
            res = result_map.get(sid)
            if not res:
                continue
            msg = (f"{school}\n"
                   f"Dear {r['name']},\n"
                   f"{res['full_name']} scored {res['mean']:.1f}% "
                   f"({res['grade']}) — "
                   f"Position {res['position']} in class.\n"
                   f"{asmt_name}")
            messages.append({"name": r["name"], "phone": r["phone"],
                             "message": msg})

        if not messages:
            self._send_status.configure(
                text="No results found to send.", text_color=DANGER)
            return

        self._send_status.configure(
            text=f"Sending {len(messages)} personalised messages…",
            text_color=TEXT_MUTED)
        self.update()

        sent = failed = 0
        for m in messages:
            result = send_sms([{"name": m["name"], "phone": m["phone"]}],
                              m["message"], api_key, username)
            if "error" in result:
                self._send_status.configure(
                    text=result["error"], text_color=DANGER)
                return
            sent   += result.get("sent", 0)
            failed += result.get("failed", 0)

        self._send_status.configure(
            text=f"✓ Sent {sent} message(s). Failed: {failed}.",
            text_color=SUCCESS if failed == 0 else TEXT_MUTED)

    def _do_send(self, recips, message, api_key, username):
        self._send_status.configure(
            text=f"Sending to {len(recips)} recipient(s)…",
            text_color=TEXT_MUTED)
        self.update()
        result = send_sms(recips, message, api_key, username)
        if "error" in result:
            self._send_status.configure(
                text=result["error"], text_color=DANGER)
            return
        s = result["sent"]
        f = result["failed"]
        self._send_status.configure(
            text=f"✓ Sent: {s}  |  Failed: {f}",
            text_color=SUCCESS if f == 0 else TEXT_MUTED)

    # ── Parent contacts ───────────────────────────────────────
    def _build_contacts(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        heading(top, "Parent contacts", size=15).pack(side="left")

        # Class filter
        self._contact_class_var = ctk.StringVar(value="All classes")
        cls_labels = ["All classes"] + [
            f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
            for c in self._classes_data]
        ctk.CTkOptionMenu(
            top, variable=self._contact_class_var,
            values=cls_labels, width=200,
            fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
            command=self._load_contacts_list,
        ).pack(side="right")

        tcard = card(parent)
        tcard.pack(fill="both", expand=True)

        thead = ctk.CTkFrame(tcard, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))
        for txt, w in [("Student", 200), ("Contact name", 160),
                        ("Relationship", 110), ("Phone", 140),
                        ("Primary", 70), ("Actions", 120)]:
            ctk.CTkLabel(thead, text=txt, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(
                side="left", padx=(10, 0), pady=8)

        self._contacts_body = ctk.CTkScrollableFrame(
            tcard, fg_color=SURFACE, corner_radius=0)
        self._contacts_body.pack(fill="both", expand=True,
                                  padx=1, pady=(0, 1))
        self._load_contacts_list()

    def _load_contacts_list(self, _=None):
        for w in self._contacts_body.winfo_children():
            w.destroy()
        sel = self._contact_class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == sel), None)

        if cls:
            rows = get_primary_contacts_for_class(cls["id"])
        else:
            rows = get_all_primary_contacts()

        if not rows:
            muted(self._contacts_body,
                  "No contacts yet. Add contacts via the student edit form."
                  ).pack(pady=20)
            return

        for i, r in enumerate(rows):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._contacts_body, fg_color=bg,
                               corner_radius=0, height=36)
            row.pack(fill="x")
            row.pack_propagate(False)

            for txt, w in [
                (r["student_name"], 200),
                (r["name"],         160),
                (r["relationship"], 110),
                (r["phone"],        140),
                ("✓" if r.get("is_primary") else "", 70),
            ]:
                ctk.CTkLabel(row, text=str(txt), font=("", 11),
                             text_color=TEXT, width=w,
                             anchor="w").pack(
                    side="left", padx=(10, 0))

    # ── SMS Log ───────────────────────────────────────────────
    def _build_log(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        heading(top, "SMS log", size=15).pack(side="left")
        ghost_btn(top, "Refresh",
                  command=self._refresh_log, width=90).pack(side="right")

        tcard = card(parent)
        tcard.pack(fill="both", expand=True)

        thead = ctk.CTkFrame(tcard, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))
        for txt, w in [("Recipient", 150), ("Phone", 130),
                        ("Status", 220), ("Cost", 70),
                        ("Sent at", 150)]:
            ctk.CTkLabel(thead, text=txt, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(
                side="left", padx=(10, 0), pady=8)

        self._log_body = ctk.CTkScrollableFrame(
            tcard, fg_color=SURFACE, corner_radius=0)
        self._log_body.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self._refresh_log()

    def _refresh_log(self):
        for w in self._log_body.winfo_children():
            w.destroy()
        logs = get_sms_log(100)
        if not logs:
            muted(self._log_body, "No messages sent yet."
                  ).pack(pady=20)
            return
        for i, r in enumerate(logs):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._log_body, fg_color=bg,
                               corner_radius=0, height=34)
            row.pack(fill="x")
            row.pack_propagate(False)
            color = SUCCESS if r["status"] == "Success" else DANGER
            # Truncate long status/error messages
            status_txt = r["status"]
            if len(status_txt) > 35:
                status_txt = status_txt[:35] + "…"

            for txt, w, c in [
                (r["recipient"],   150, TEXT),
                (r["phone"],       130, TEXT_MUTED),
                (status_txt,       220, color),
                (r.get("cost","—"), 70, TEXT_MUTED),
                (r["sent_at"][:16], 150, TEXT_MUTED),
            ]:
                ctk.CTkLabel(row, text=str(txt), font=("", 11),
                             text_color=c, width=w,
                             anchor="w").pack(
                    side="left", padx=(10, 0))

    # ── SMS Settings ──────────────────────────────────────────
    def _build_settings(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        sec = self._section(scroll, "Africa's Talking credentials")
        f   = ctk.CTkFrame(sec, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(0, 16))

        info = ctk.CTkFrame(f, fg_color=ACCENT_BG, corner_radius=8)
        info.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            info,
            text="Sign up at africastalking.com — free sandbox available for testing.\n"
                 "Use 'sandbox' as username and your sandbox API key for testing.",
            font=("", 11), text_color=ACCENT, justify="left",
        ).pack(padx=12, pady=8, anchor="w")

        api_key, username = get_at_credentials()

        muted(f, "Username").pack(anchor="w")
        self._at_username = ctk.CTkEntry(
            f, width=380, fg_color=SURFACE, border_color=BORDER)
        self._at_username.insert(0, username or "sandbox")
        self._at_username.pack(anchor="w", pady=(4, 12))

        api_row = ctk.CTkFrame(f, fg_color="transparent")
        api_row.pack(anchor="w", fill="x", pady=(0, 4))
        muted(api_row, "API key").pack(side="left")
        self._show_key = False
        ctk.CTkButton(api_row, text="Show", width=50, height=20,
                      fg_color="transparent", text_color=ACCENT,
                      hover_color=ACCENT_BG, font=("", 11),
                      command=self._toggle_key_visibility,
                      ).pack(side="right")
        self._at_apikey = ctk.CTkEntry(
            f, width=380, fg_color=SURFACE, border_color=BORDER,
            show="•")
        self._at_apikey.insert(0, api_key or "")
        self._at_apikey.pack(anchor="w", pady=(0, 14))

        self._settings_msg = ctk.CTkLabel(
            f, text="", font=("", 12), text_color=SUCCESS)
        self._settings_msg.pack(anchor="w", pady=(0, 8))

        primary_btn(f, "Save credentials",
                    command=self._save_settings, width=160).pack(anchor="w")

    def _toggle_key_visibility(self):
        self._show_key = not self._show_key
        self._at_apikey.configure(show="" if self._show_key else "•")

    def _save_settings(self):
        save_at_credentials(
            self._at_apikey.get().strip(),
            self._at_username.get().strip(),
        )
        self._settings_msg.configure(text="✓ Saved.")
        self.after(2000, lambda: self._settings_msg.configure(text=""))

    def _section(self, parent, title):
        c = card(parent)
        c.pack(fill="x", pady=(0, 14))
        hdr = ctk.CTkFrame(c, fg_color=ACCENT_BG, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=title, font=("", 13, "bold"),
                     text_color=ACCENT).pack(
            anchor="w", padx=16, pady=10)
        return c
