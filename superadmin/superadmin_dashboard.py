import tkinter as tk
from tkinter import messagebox
from theme import COLORS, FONTS


class SuperadminDashboard:
    def __init__(self, root, user=None):
        self.root = root
        self.user = user
        self.root.title("The Gears — Superadmin")
        self.root.geometry("1280x800")
        self.root.minsize(1050, 680)

        # Layout constants
        self.HEADER_H   = 68
        self.BAR_H      = 5
        self.TOP_OFFSET = self.HEADER_H + self.BAR_H
        self.SIDEBAR_W  = 248

        # State
        self.sidebar_visible            = False
        self.content_management_visible = False
        self.user_menu_visible          = False
        self.dark_mode                  = False

        # Themes
        self.light = COLORS.copy()
        self.dark  = {
            **COLORS,
            "background":           "#141414",
            "background_alt":       "#1A1A1A",
            "card":                 "#1E1E1E",
            "card_hover":           "#252525",
            "text_dark":            "#F0F0F0",
            "text_mid":             "#D0D0D0",
            "text_grey":            "#A0A0A0",
            "text_light":           "#787878",
            "border":               "#2E2219",
            "shadow":               "#000000",
            "input_bg":             "#252525",
            "primary_orange_light": "#3A2210",
            "white":                "#FFFFFF",
        }
        self.theme = self.light

        # Demo data
        self.stats = {
            "Total Admins":    "12",
            "Total Users":     "1,248",
            "Total Articles":  "386",
            "Pending Reviews": "19",
            "Pending Users":   "7",
        }
        self.recent_articles = [
            ("Campus Journalism Workshop Opens",        "Maria Santos", "Apr 27, 2026"),
            ("Editorial Board Releases New Guidelines", "John Reyes",   "Apr 26, 2026"),
            ("Student Feature: Voices of The Gears",   "Alyssa Cruz",  "Apr 25, 2026"),
        ]
        self.recent_users = [
            ("Rafael Dela Cruz", "rafael@example.com",  "Apr 27, 2026"),
            ("Nicole Mendoza",   "nicole@example.com",  "Apr 26, 2026"),
            ("Jasmine Torres",   "jasmine@example.com", "Apr 25, 2026"),
        ]

        self.initials = (
            (self.user[0][:1] + self.user[1][:1]).upper()
            if self.user and len(self.user) >= 2
            else "SA"
        )

        self._build_ui()
        self.root.bind("<Configure>", self._on_root_resize)

    # ═══════════════════════════════════════════════════════════════
    #  Build / Rebuild
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.root.configure(bg=self.theme["background"])
        self._make_header()
        self._make_orange_bar()
        self._make_sidebar()
        self._make_main()
        self._make_user_menu()
        self.header.lift()
        self.orange_bar.lift()

    def _rebuild(self):
        self.sidebar_visible            = False
        self.content_management_visible = False
        self.user_menu_visible          = False
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._sync_geometry()

    # ═══════════════════════════════════════════════════════════════
    #  Header
    # ═══════════════════════════════════════════════════════════════

    def _make_header(self):
        self.header = tk.Frame(
            self.root,
            bg=self.theme["card"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
        )
        self.header.place(x=0, y=0, relwidth=1, height=self.HEADER_H)

        left = tk.Frame(self.header, bg=self.theme["card"])
        left.pack(side="left", fill="y", padx=(18, 0))

        tk.Button(
            left, text="☰",
            command=self.toggle_sidebar,
            bg=self.theme["card"],
            fg=self.theme["primary_orange"],
            activebackground=self.theme["primary_orange_light"],
            activeforeground=self.theme["primary_orange"],
            font=("Poppins", 20, "bold"),
            bd=0, relief="flat", cursor="hand2",
        ).pack(side="left", padx=(0, 16))

        logo_c = tk.Canvas(left, width=36, height=36,
                           bg=self.theme["primary_orange"], highlightthickness=0)
        logo_c.pack(side="left", padx=(0, 14))
        logo_c.create_text(18, 18, text="TG", fill="white",
                           font=("Poppins", 11, "bold"))

        tk.Label(
            left, text="The Gears",
            bg=self.theme["card"],
            fg=self.theme["primary_orange"],
            font=("Hedvig Letters Serif 24pt", 17, "bold"),
        ).pack(side="left")

        tk.Label(
            left, text="  ·  Superadmin",
            bg=self.theme["card"],
            fg=self.theme["text_grey"],
            font=("Poppins", 11),
        ).pack(side="left")

        right = tk.Frame(self.header, bg=self.theme["card"])
        right.pack(side="right", fill="y", padx=(0, 22))

        tk.Label(
            right, text="SUPERADMIN",
            bg=self.theme["primary_orange_light"],
            fg=self.theme["primary_orange"],
            font=FONTS["tag"],
            padx=12, pady=5,
        ).pack(side="left", padx=(0, 14))

        av = tk.Canvas(right, width=36, height=36,
                       bg=self.theme["card"], highlightthickness=0, cursor="hand2")
        av.pack(side="left")
        av.create_oval(1, 1, 35, 35,
                       fill=self.theme["primary_orange"],
                       outline=self.theme["primary_orange"])
        av.create_text(18, 18, text=self.initials,
                       fill="white", font=("Poppins", 10, "bold"))
        av.bind("<Button-1>", lambda e: self.toggle_user_menu())

    # ═══════════════════════════════════════════════════════════════
    #  Orange bar
    # ═══════════════════════════════════════════════════════════════

    def _make_orange_bar(self):
        self.orange_bar = tk.Frame(self.root, bg=self.theme["primary_orange"])
        self.orange_bar.place(x=0, y=self.HEADER_H, relwidth=1, height=self.BAR_H)

    # ═══════════════════════════════════════════════════════════════
    #  Sidebar
    # ═══════════════════════════════════════════════════════════════

    def _make_sidebar(self):
        rh = self.root.winfo_height() or 800

        self.sidebar = tk.Frame(
            self.root,
            bg=self.theme["card"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
        )
        self.sidebar.place(
            x=-self.SIDEBAR_W,
            y=self.TOP_OFFSET,
            width=self.SIDEBAR_W,
            height=rh - self.TOP_OFFSET,
        )

        # Top label
        strip = tk.Frame(self.sidebar,
                         bg=self.theme["primary_orange_light"], height=50)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        tk.Label(strip, text="NAVIGATION",
                 bg=self.theme["primary_orange_light"],
                 fg=self.theme["primary_orange"],
                 font=FONTS["tag"], padx=22).pack(side="left", fill="y")

        self._nav("🏠  Dashboard",           self._go_dashboard,         active=True)
        self._nav("👤  Manage Admins",        self.show_manage_admins)
        self._nav("👥  Manage Users",         self.show_manage_users)
        self.content_btn = self._nav(
            "📂  Content  ▾", self.toggle_content_management
        )

        self.dropdown_frame = tk.Frame(self.sidebar, bg=self.theme["background_alt"])
        self._subnav("   📄  Pending Articles", self.show_pending_articles)
        self._subnav("   🏷️  Categories",        self.show_categories)
        self._subnav("   📋  Activity Logs",     self.show_activity_logs)

        tk.Frame(self.sidebar, bg=self.theme["card"]).pack(fill="both", expand=True)

        tk.Frame(self.sidebar, bg=self.theme["border"], height=1).pack(
            fill="x", padx=14, pady=(0, 2)
        )
        tk.Button(
            self.sidebar, text="🚪  Logout",
            command=self.logout,
            anchor="w",
            bg=self.theme["card"],
            fg=self.theme["primary_red"],
            activebackground="#FFF0F0",
            activeforeground=self.theme["primary_red"],
            font=FONTS["body_bold"],
            bd=0, relief="flat",
            padx=22, pady=14,
            cursor="hand2",
        ).pack(fill="x")

    def _nav(self, text, command, active=False):
        bg = self.theme["primary_orange_light"] if active else self.theme["card"]
        fg = self.theme["primary_orange"]        if active else self.theme["text_dark"]
        btn = tk.Button(
            self.sidebar, text=text, command=command,
            anchor="w", bg=bg, fg=fg,
            activebackground=self.theme["primary_orange_light"],
            activeforeground=self.theme["primary_orange"],
            font=FONTS["button"] if active else FONTS["body"],
            bd=0, relief="flat", padx=22, pady=13, cursor="hand2",
        )
        btn.pack(fill="x", padx=8, pady=1)
        return btn

    def _subnav(self, text, command):
        tk.Button(
            self.dropdown_frame, text=text, command=command,
            anchor="w",
            bg=self.theme["background_alt"],
            fg=self.theme["text_grey"],
            activebackground=self.theme["primary_orange_light"],
            activeforeground=self.theme["primary_orange"],
            font=FONTS["body"],
            bd=0, relief="flat", padx=28, pady=11, cursor="hand2",
        ).pack(fill="x", padx=8)

    # ═══════════════════════════════════════════════════════════════
    #  Main scrollable content
    # ═══════════════════════════════════════════════════════════════

    def _make_main(self):
        rw = self.root.winfo_width()  or 1280
        rh = self.root.winfo_height() or 800

        self.main = tk.Frame(self.root, bg=self.theme["background"])
        self.main.place(x=0, y=self.TOP_OFFSET,
                        width=rw, height=rh - self.TOP_OFFSET)

        outer = tk.Frame(self.main, bg=self.theme["background"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=self.theme["background"],
                                highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.content = tk.Frame(self.canvas, bg=self.theme["background"])
        self._cwin = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )

        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._cwin, width=e.width))
        self.canvas.bind("<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self.inner = tk.Frame(self.content, bg=self.theme["background"])
        self.inner.pack(fill="both", expand=True, padx=36, pady=(30, 44))

        self._section_header()
        self._section_metrics()
        self._section_quick_actions()
        self._section_activity()

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ═══════════════════════════════════════════════════════════════
    #  User menu
    # ═══════════════════════════════════════════════════════════════

    def _make_user_menu(self):
        self.user_menu = tk.Frame(
            self.root,
            bg=self.theme["card"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
        )

        if self.user:
            name  = f"{self.user[0]} {self.user[1]}" if len(self.user) >= 2 else self.user[0]
            email = self.user[2] if len(self.user) > 2 else ""
            info  = tk.Frame(self.user_menu,
                             bg=self.theme["primary_orange_light"], pady=10)
            info.pack(fill="x")
            tk.Label(info, text=name,
                     bg=self.theme["primary_orange_light"],
                     fg=self.theme["text_dark"],
                     font=FONTS["small_bold"],
                     anchor="w", padx=14).pack(fill="x")
            tk.Label(info, text=email,
                     bg=self.theme["primary_orange_light"],
                     fg=self.theme["text_grey"],
                     font=FONTS["small"],
                     anchor="w", padx=14).pack(fill="x")

        tk.Frame(self.user_menu, bg=self.theme["border"], height=1).pack(
            fill="x", padx=8, pady=2
        )

        for label, cmd, red in [
            ("🌙  Toggle Dark Mode", self.toggle_dark_mode, False),
            ("🚪  Logout",           self.logout,           True),
        ]:
            tk.Button(
                self.user_menu, text=label, command=cmd,
                anchor="w",
                bg=self.theme["card"],
                fg=self.theme["primary_red"] if red else self.theme["text_dark"],
                activebackground=self.theme["primary_orange_light"],
                activeforeground=self.theme["primary_red"] if red else self.theme["primary_orange"],
                font=FONTS["body_bold"] if red else FONTS["body"],
                bd=0, relief="flat", padx=14, pady=10, cursor="hand2",
            ).pack(fill="x")

    # ═══════════════════════════════════════════════════════════════
    #  Page sections
    # ═══════════════════════════════════════════════════════════════

    def _section_header(self):
        wrap = tk.Frame(self.inner, bg=self.theme["background"])
        wrap.pack(fill="x", pady=(0, 22))

        name = (
            f"{self.user[0]} {self.user[1]}"
            if self.user and len(self.user) >= 2
            else "Superadmin"
        )
        tk.Label(wrap, text="OVERVIEW",
                 bg=self.theme["background"],
                 fg=self.theme["primary_orange"],
                 font=("Poppins", 22, "bold")).pack(anchor="w")
        tk.Label(wrap,
                 text=f"Welcome back, {name}. Here's your platform snapshot.",
                 bg=self.theme["background"],
                 fg=self.theme["text_grey"],
                 font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

    def _section_metrics(self):
        self.cards_frame = tk.Frame(self.inner, bg=self.theme["background"])
        self.cards_frame.pack(fill="x")

        COLS = 3
        for c in range(COLS):
            self.cards_frame.grid_columnconfigure(c, weight=1, uniform="mc")

        for i, (title, value) in enumerate(self.stats.items()):
            self._metric_card(
                self.cards_frame, title, value,
                self._card_subtitle(title), self._card_chip(title),
                row=i // COLS, col=i % COLS,
            )

    def _metric_card(self, parent, title, value, subtitle, chip, row, col):
        outer = tk.Frame(parent, bg=self.theme["background"], padx=7, pady=7)
        outer.grid(row=row, column=col, sticky="nsew")

        card = tk.Frame(
            outer,
            bg=self.theme["card"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
            padx=20, pady=16,
        )
        card.pack(fill="both", expand=True)

        # Orange accent line
        tk.Frame(card, bg=self.theme["primary_orange"], height=3).pack(
            fill="x", pady=(0, 12)
        )

        top = tk.Frame(card, bg=self.theme["card"])
        top.pack(fill="x")

        tk.Label(top, text=title.upper(),
                 bg=self.theme["card"],
                 fg=self.theme["text_grey"],
                 font=FONTS["small_bold"]).pack(side="left")

        tk.Label(top, text=chip,
                 bg=self.theme["primary_orange_light"],
                 fg=self.theme["primary_orange"],
                 font=FONTS["tag"],
                 padx=8, pady=3).pack(side="right")

        tk.Label(card, text=value,
                 bg=self.theme["card"],
                 fg=self.theme["text_dark"],
                 font=("Poppins", 28, "bold")).pack(anchor="w", pady=(10, 3))

        tk.Label(card, text=subtitle,
                 bg=self.theme["card"],
                 fg=self.theme["text_grey"],
                 font=FONTS["small"],
                 wraplength=280, justify="left").pack(anchor="w")

    def _section_quick_actions(self):
        sec = self._section("Quick Actions",
                            "Jump straight into the most important tasks.")
        grid = tk.Frame(sec, bg=self.theme["card"])
        grid.pack(fill="x", pady=(4, 0))
        grid.grid_columnconfigure(0, weight=1, uniform="qa")
        grid.grid_columnconfigure(1, weight=1, uniform="qa")

        self._quick_card(grid, "📝  Review Articles",
                         "Check new submissions and approve or request changes.",
                         self.show_pending_articles, col=0)
        self._quick_card(grid, "👥  Manage Users",
                         "Update roles, deactivate accounts, or review new signups.",
                         self.show_manage_users, col=1)

    def _quick_card(self, parent, title, subtitle, command, col):
        wrap = tk.Frame(parent, bg=self.theme["card"], padx=7, pady=7)
        wrap.grid(row=0, column=col, sticky="nsew")

        card = tk.Frame(
            wrap,
            bg=self.theme["background"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
            padx=20, pady=18,
            cursor="hand2",
        )
        card.pack(fill="both", expand=True)

        tk.Label(card, text=title,
                 bg=self.theme["background"],
                 fg=self.theme["primary_orange"],
                 font=FONTS["card_title"]).pack(anchor="w")

        tk.Label(card, text=subtitle,
                 bg=self.theme["background"],
                 fg=self.theme["text_grey"],
                 font=FONTS["small"],
                 wraplength=400, justify="left").pack(anchor="w", pady=(8, 0))

        def _click(e=None): command()
        card.bind("<Button-1>", _click)
        for ch in card.winfo_children():
            ch.bind("<Button-1>", _click)

        def _enter(e): card.configure(highlightbackground=COLORS["primary_orange"])
        def _leave(e): card.configure(highlightbackground=self.theme["border"])
        card.bind("<Enter>", _enter)
        card.bind("<Leave>", _leave)

    def _section_activity(self):
        art = self._section("Recent Articles",
                            "Latest content activity across the platform.",
                            link_text="View All →", link_cmd=self.show_articles)
        self._activity_list(art, "A",
            [(t, f"{a}  ·  {d}") for t, a, d in self.recent_articles])

        usr = self._section("Recent Users",
                            "New members who recently joined The Gears.",
                            link_text="View All →", link_cmd=self.show_manage_users)
        self._activity_list(usr, "U",
            [(n, f"{e}  ·  Joined {d}") for n, e, d in self.recent_users])

    def _section(self, title, subtitle, link_text=None, link_cmd=None):
        sec = tk.Frame(
            self.inner,
            bg=self.theme["card"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
            padx=22, pady=18,
        )
        sec.pack(fill="x", pady=(20, 0))

        hdr = tk.Frame(sec, bg=self.theme["card"])
        hdr.pack(fill="x", pady=(0, 12))

        lft = tk.Frame(hdr, bg=self.theme["card"])
        lft.pack(side="left", fill="x", expand=True)

        tk.Label(lft, text=title.upper(),
                 bg=self.theme["card"],
                 fg=self.theme["primary_orange"],
                 font=FONTS["section"]).pack(anchor="w")

        tk.Label(lft, text=subtitle,
                 bg=self.theme["card"],
                 fg=self.theme["text_grey"],
                 font=FONTS["small"]).pack(anchor="w", pady=(2, 0))

        if link_text:
            tk.Button(hdr, text=link_text, command=link_cmd,
                      bg=self.theme["card"],
                      fg=self.theme["primary_orange"],
                      activebackground=self.theme["primary_orange_light"],
                      activeforeground=self.theme["primary_orange_dark"],
                      font=FONTS["button"],
                      bd=0, relief="flat", cursor="hand2").pack(side="right")

        return sec

    def _activity_list(self, parent, icon_letter, items):
        lf = tk.Frame(parent, bg=self.theme["card"])
        lf.pack(fill="x")

        for i, (title, sub) in enumerate(items):
            row = tk.Frame(lf, bg=self.theme["card"])
            row.pack(fill="x", pady=5)

            badge = tk.Canvas(row, width=38, height=38,
                              bg=self.theme["card"], highlightthickness=0)
            badge.pack(side="left", padx=(0, 14))
            badge.create_oval(1, 1, 37, 37,
                              fill=self.theme["primary_orange_light"], outline="")
            badge.create_text(19, 19, text=icon_letter,
                              fill=self.theme["primary_orange"],
                              font=("Poppins", 9, "bold"))

            info = tk.Frame(row, bg=self.theme["card"])
            info.pack(side="left", fill="x", expand=True)

            tk.Label(info, text=title,
                     bg=self.theme["card"],
                     fg=self.theme["text_dark"],
                     font=FONTS["body_bold"], anchor="w").pack(fill="x")

            tk.Label(info, text=sub,
                     bg=self.theme["card"],
                     fg=self.theme["text_grey"],
                     font=FONTS["small"], anchor="w").pack(fill="x", pady=(2, 0))

            if i < len(items) - 1:
                tk.Frame(lf, bg=self.theme["border"], height=1).pack(
                    fill="x", pady=(4, 0)
                )

    # ═══════════════════════════════════════════════════════════════
    #  Geometry helpers
    # ═══════════════════════════════════════════════════════════════

    def _sync_geometry(self):
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        body_h = rh - self.TOP_OFFSET

        sx = 0 if self.sidebar_visible else -self.SIDEBAR_W
        self.sidebar.place_configure(x=sx, y=self.TOP_OFFSET,
                                     width=self.SIDEBAR_W, height=body_h)

        mx = self.SIDEBAR_W if self.sidebar_visible else 0
        self.main.place_configure(x=mx, y=self.TOP_OFFSET,
                                  width=rw - mx, height=body_h)

    def _on_root_resize(self, event=None):
        if event and event.widget is not self.root:
            return
        self._sync_geometry()

    # ═══════════════════════════════════════════════════════════════
    #  Toggles
    # ═══════════════════════════════════════════════════════════════

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        if self.sidebar_visible:
            self.sidebar.lift()
        self._sync_geometry()

    def toggle_content_management(self):
        self.content_management_visible = not self.content_management_visible
        if self.content_management_visible:
            self.dropdown_frame.pack(fill="x", pady=(0, 4))
            self.content_btn.configure(text="📂  Content  ▴")
        else:
            self.dropdown_frame.pack_forget()
            self.content_btn.configure(text="📂  Content  ▾")

    def toggle_user_menu(self):
        self.user_menu_visible = not self.user_menu_visible
        if self.user_menu_visible:
            rw = self.root.winfo_width()
            self.user_menu.place(x=rw - 240, y=self.TOP_OFFSET, width=228)
            self.user_menu.lift()
        else:
            self.user_menu.place_forget()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.theme = self.dark if self.dark_mode else self.light
        self._rebuild()

    # ═══════════════════════════════════════════════════════════════
    #  Navigation
    # ═══════════════════════════════════════════════════════════════

    def _go_dashboard(self):
        pass  # already on dashboard

    def show_manage_admins(self):
        from superadmin.superadmin_manage_admins import ManageAdmins
        for w in self.root.winfo_children():
            w.destroy()
        ManageAdmins(self.root, user=self.user)

    def show_manage_users(self):
        messagebox.showinfo("Manage Users", "Navigating to Manage Users.")

    def show_pending_articles(self):
        messagebox.showinfo("Pending Articles", "Navigating to Pending Articles.")

    def show_categories(self):
        messagebox.showinfo("Categories", "Navigating to Categories.")

    def show_activity_logs(self):
        messagebox.showinfo("Activity Logs", "Navigating to Activity Logs.")

    def show_articles(self):
        messagebox.showinfo("Articles", "Navigating to all Articles.")

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            if hasattr(self.root, "show_landing"):
                self.root.show_landing()
            else:
                self.root.destroy()

    # ═══════════════════════════════════════════════════════════════
    #  Data helpers
    # ═══════════════════════════════════════════════════════════════

    def _card_subtitle(self, title):
        return {
            "Total Admins":    "Superadmins and content admins combined.",
            "Total Users":     "Registered readers and contributors.",
            "Total Articles":  "Published, scheduled, and draft content.",
            "Pending Reviews": "Articles waiting for admin approval.",
            "Pending Users":   "New users awaiting verification.",
        }.get(title, "")

    def _card_chip(self, title):
        return {
            "Total Admins":    "All roles",
            "Total Users":     "Platform",
            "Total Articles":  "All statuses",
            "Pending Reviews": "⚠ Attention",
            "Pending Users":   "⚠ Review",
        }.get(title, "Metric")


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    SuperadminDashboard(
        root,
        user=("Francis Jane", "Olvido", "admin@gears.com", 1, "superadmin"),
    )
    root.mainloop()