import customtkinter as ctk
from utils.theme import *
from routes.terms import get_all_terms, get_current_term
from routes.assessments import get_assessments
from routes.classes import get_classes


from pages.analytics_tabs import AnalyticsTabsMixin


class AnalyticsPage(AnalyticsTabsMixin, ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._terms_data   = []
        self._asmt_data    = []
        self._asmt2_data   = []
        self._classes_data = []
        self._active_tab   = "overview"
        self._build()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        heading(self, "Analytics").pack(anchor="w", pady=(0, 12))

        # ── Filter bar ────────────────────────────────────────
        fbar = ctk.CTkFrame(self, fg_color=SURFACE,
                             border_color=BORDER, border_width=1,
                             corner_radius=8)
        fbar.pack(fill="x", pady=(0, 14))
        ff = ctk.CTkFrame(fbar, fg_color="transparent")
        ff.pack(fill="x", padx=14, pady=10)

        muted(ff, "Term:").pack(side="left", padx=(0, 6))
        self._terms_data = get_all_terms()
        term_labels = [f"Term {t['term']}, {t['year']}"
                       for t in self._terms_data]
        current = get_current_term()
        default_t = (f"Term {current['term']}, {current['year']}"
                     if current and term_labels
                     else (term_labels[0] if term_labels else "—"))
        self._term_var = ctk.StringVar(value=default_t)
        ctk.CTkOptionMenu(ff, variable=self._term_var,
                          values=term_labels if term_labels else ["—"],
                          width=150, fg_color=SURFACE,
                          button_color=BORDER, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          command=self._on_term_change,
                          ).pack(side="left", padx=(0, 14))

        muted(ff, "Assessment:").pack(side="left", padx=(0, 6))
        self._asmt_var  = ctk.StringVar(value="—")
        self._asmt_data = []
        self._asmt_menu = ctk.CTkOptionMenu(
            ff, variable=self._asmt_var, values=["—"],
            width=190, fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
            command=self._on_filter_change)
        self._asmt_menu.pack(side="left", padx=(0, 14))

        muted(ff, "Class:").pack(side="left", padx=(0, 6))
        self._classes_data = get_classes()
        cls_labels = ["All classes"] + [
            f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
            for c in self._classes_data
        ]
        self._class_var = ctk.StringVar(value="All classes")
        ctk.CTkOptionMenu(ff, variable=self._class_var,
                          values=cls_labels, width=170,
                          fg_color=SURFACE, button_color=BORDER,
                          text_color=TEXT, dropdown_fg_color=SURFACE,
                          command=self._on_filter_change,
                          ).pack(side="left", padx=(0, 14))

        # Comparison filter (shown for improvement tabs)
        self._cmp_frame = ctk.CTkFrame(ff, fg_color="transparent")
        muted(self._cmp_frame, "Compare with:").pack(side="left", padx=(0, 6))
        self._asmt2_var  = ctk.StringVar(value="— (none)")
        self._asmt2_data = []
        self._asmt2_menu = ctk.CTkOptionMenu(
            self._cmp_frame, variable=self._asmt2_var,
            values=["— (none)"], width=190,
            fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
            command=self._on_filter_change)
        self._asmt2_menu.pack(side="left")

        # Multi-assessment selector (shown for combined tab)
        self._multi_frame = ctk.CTkFrame(ff, fg_color="transparent")
        muted(self._multi_frame, "Add assessment:").pack(side="left", padx=(0, 6))
        self._multi_add_var = ctk.StringVar(value="— select —")
        self._multi_add_menu = ctk.CTkOptionMenu(
            self._multi_frame, variable=self._multi_add_var,
            values=["— select —"], width=190,
            fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
            command=self._on_multi_add)
        self._multi_add_menu.pack(side="left", padx=(0, 6))
        self._multi_selected: list = []  # list of (id, name) tuples
        self._multi_lbl = muted(self._multi_frame, "None selected")
        self._multi_lbl.pack(side="left", padx=(0, 6))
        ghost_btn(self._multi_frame, "Clear",
                  command=self._on_multi_clear, width=60
                  ).pack(side="left")

        # ── Tab bar — horizontal scrollable so all tabs visible ─
        tab_outer = ctk.CTkFrame(self, fg_color="transparent", height=36)
        tab_outer.pack(fill="x", pady=(0, 10))
        tab_outer.pack_propagate(False)
        tabs_scroll = ctk.CTkScrollableFrame(
            tab_outer, fg_color="transparent",
            orientation="horizontal", height=36,
            scrollbar_button_color=SURFACE,
            scrollbar_button_hover_color=SURFACE)
        tabs_scroll.pack(fill="both", expand=True)
        # Hide the horizontal scrollbar track — scroll still works via mouse/touch
        try:
            tabs_scroll._scrollbar.grid_remove()
        except Exception:
            pass
        self._tab_btns = {}
        for key, lbl in [
            ("overview",          "School overview"),
            ("subjects",          "Subject performance"),
            ("ranking",           "Exam ranking"),
            ("improved_students", "Most improved students"),
            ("improved_subjects", "Most improved subjects"),
            ("top_per_subject",   "Top per subject"),
            ("combined",          "Combined assessments"),
        ]:
            btn = ctk.CTkButton(
                tabs_scroll, text=lbl, height=30,
                fg_color=ACCENT if key == "overview" else "transparent",
                text_color="white" if key == "overview" else TEXT_MUTED,
                hover_color=ACCENT_BG, corner_radius=6, font=("", 11),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 3))
            self._tab_btns[key] = btn

        # ── Content ───────────────────────────────────────────
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        # Now safe to load data — _content exists
        self._on_term_change()

    # ── Filter logic ──────────────────────────────────────────
    def _on_term_change(self, _=None):
        t_label = self._term_var.get()
        term = next((t for t in self._terms_data
                     if f"Term {t['term']}, {t['year']}" == t_label), None)
        if not term:
            return
        asmts = get_assessments(term_id=term["id"])
        self._asmt_data = asmts
        labels = [a["name"] for a in asmts]
        self._asmt_menu.configure(values=labels if labels else ["—"])
        self._asmt_var.set(labels[0] if labels else "—")

        all_asmts = get_assessments()
        self._asmt2_data = all_asmts
        all_labels = [a["name"] for a in all_asmts]
        self._asmt2_menu.configure(values=["— (none)"] + all_labels)
        self._asmt2_var.set("— (none)")

        # Populate multi-assessment menu with ALL assessments (across all terms)
        self._multi_add_menu.configure(values=["— select —"] + all_labels)
        self._multi_add_var.set("— select —")
        self._multi_selected = []
        try:
            self._multi_lbl.configure(text="None selected")
        except Exception:
            pass

        self._on_filter_change()

    def _on_multi_add(self, name):
        """Add an assessment to the combined list."""
        if name == "— select —":
            return
        # Search full assessment list (asmt2_data holds all assessments)
        all_asmts = self._asmt2_data or self._asmt_data
        asmt = next((a for a in all_asmts if a["name"] == name), None)
        if not asmt:
            return
        # avoid duplicates
        if asmt["id"] not in [x[0] for x in self._multi_selected]:
            self._multi_selected.append((asmt["id"], asmt["name"]))
        self._multi_add_var.set("— select —")
        n_sel = len(self._multi_selected)
        names = ", ".join(n for _, n in self._multi_selected)
        self._multi_lbl.configure(
            text=f"{n_sel} selected: {names}" if n_sel else "None selected")
        self._on_filter_change()

    def _on_multi_clear(self):
        self._multi_selected = []
        self._multi_lbl.configure(text="None selected")
        self._on_filter_change()

    def _show_placeholder(self):
        """Show empty state until user selects filters."""
        for w in self._content.winfo_children():
            w.destroy()
        f = ctk.CTkFrame(self._content, fg_color="transparent")
        f.pack(expand=True, pady=60)
        ctk.CTkLabel(f, text="▲", font=("", 40),
                     text_color=TEXT_MUTED).pack()
        label(f, "Select a term and assessment", size=14,
              weight="bold").pack(pady=(8, 4))
        muted(f, "Choose filters above to view analytics.").pack()

    def _on_filter_change(self, _=None):
        if self._active_tab in ("improved_students", "improved_subjects"):
            self._cmp_frame.pack(side="left")
        else:
            self._cmp_frame.pack_forget()
        # Show multi-assessment selector only for combined tab
        if self._active_tab == "combined":
            self._multi_frame.pack(side="left")
        else:
            self._multi_frame.pack_forget()
        self._render_tab()

    def _switch_tab(self, key):
        self._active_tab = key
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color=ACCENT if k == key else "transparent",
                text_color="white" if k == key else TEXT_MUTED)
        self._on_filter_change()

    def _get_filter(self):
        asmt = next((a for a in self._asmt_data
                     if a["name"] == self._asmt_var.get()), None)
        asmt_id = asmt["id"] if asmt else None

        sel = self._class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == sel), None)
        class_id = cls["id"] if cls else None

        asmt2 = next((a for a in self._asmt2_data
                      if a["name"] == self._asmt2_var.get()), None)
        asmt2_id = asmt2["id"] if asmt2 else None

        return asmt_id, class_id, asmt2_id

    # ── Tab renderer ─────────────────────────────────────────
    def _render_tab(self):
        for w in self._content.winfo_children():
            w.destroy()
        asmt_id, class_id, asmt2_id = self._get_filter()

        if not asmt_id:
            muted(self._content,
                  "Select a term and assessment to view analytics."
                  ).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(
            self._content, fg_color=BG, corner_radius=0,
            scrollbar_button_color=BG, scrollbar_button_hover_color=BG)
        scroll.pack(fill="both", expand=True)
        # Hide scrollbar track but keep scroll functionality
        try:
            scroll._scrollbar.grid_remove()
        except Exception:
            pass
        # Enable keyboard scroll
        def _on_key(event):
            try:
                canvas = scroll._parent_canvas
                if event.keysym in ("Down", "Next"):
                    canvas.yview_scroll(3, "units")
                elif event.keysym in ("Up", "Prior"):
                    canvas.yview_scroll(-3, "units")
                elif event.keysym == "End":
                    canvas.yview_moveto(1.0)
                elif event.keysym == "Home":
                    canvas.yview_moveto(0.0)
            except Exception:
                pass
        scroll.bind_all("<Down>",  _on_key)
        scroll.bind_all("<Up>",    _on_key)
        scroll.bind_all("<Next>",  _on_key)
        scroll.bind_all("<Prior>", _on_key)
        scroll.bind_all("<End>",   _on_key)
        scroll.bind_all("<Home>",  _on_key)

        try:
            {
                "overview":          self._tab_overview,
                "subjects":          self._tab_subjects,
                "ranking":           self._tab_ranking,
                "improved_students": self._tab_improved_students,
                "improved_subjects": self._tab_improved_subjects,
                "top_per_subject":   self._tab_top_per_subject,
                "combined":          self._tab_combined,
            }[self._active_tab](scroll, asmt_id, class_id, asmt2_id)
        except Exception as _e:
            import traceback
            err_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            err_frame.pack(fill="x", pady=20)
            muted(err_frame, f"Error loading tab: {_e}").pack(anchor="w")
            muted(err_frame, traceback.format_exc()[:300]).pack(anchor="w")

    # ── Overview ──────────────────────────────────────────────