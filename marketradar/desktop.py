from __future__ import annotations

import json
import logging
import queue
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, StringVar, Tk, Toplevel, messagebox, ttk

from . import __version__
from .db import connect, sync_source_contracts, load_dynamic_source_records
from .logging_setup import configure_logging, install_exception_logging, close_logging
from .paths import app_root, data_root
from .pipeline import Pipeline
from .runtime import MarketRadarRuntime
from .source_registry import load_source_records
from .source_health import persist_health
from .resume import tailored_resume
from .proposal import generate_proposal

logger = logging.getLogger("marketradar")

# Visual system: inspired by established intelligence/BI products — dense information,
# persistent navigation, strong hierarchy, restrained accent color, and detail-on-demand.
BG = "#f6f8fb"
SURFACE = "#ffffff"
SURFACE_2 = "#f8fafc"
SIDEBAR = "#111827"
SIDEBAR_2 = "#182235"
SIDEBAR_TEXT = "#d7deea"
SIDEBAR_MUTED = "#8491a5"
TEXT = "#172033"
MUTED = "#6b7688"
BORDER = "#e5e9f0"
ACCENT = "#3b63f3"
ACCENT_DARK = "#294ac2"
ACCENT_SOFT = "#edf2ff"
GOOD = "#14805e"
GOOD_SOFT = "#eaf8f2"
WARN = "#b06b12"
WARN_SOFT = "#fff6e5"
DANGER = "#c63838"
DANGER_SOFT = "#fff0f0"
INFO = "#3570c9"
INFO_SOFT = "#edf5ff"

I18N = {
    "fa": {
        "Overview":"نمای کلی", "Daily Center":"مرکز روزانه", "Intelligence":"هوش بازار", "Opportunities":"فرصت‌ها", "Action Center":"مرکز اقدام", "Operations":"عملیات", "Career Kit":"پروفایل حرفه‌ای", "Sources":"منابع", "Source Strategy":"راهبرد منابع", "Federation":"فدراسیون",
        "WORKSPACE":"محیط کار", "SYSTEM":"سیستم", "Search":"جستجو", "Refresh":"به‌روزرسانی", "Ready":"آماده", "Overview":"نمای کلی",
        "Sources":"منابع", "Active":"فعال", "Execution ready":"آماده اجرا", "Blocked":"مسدود", "Daily scan":"اسکن روزانه", "Global discovery":"کشف جهانی", "Auto discovery":"کشف خودکار", "Policy confirmed":"تأیید سیاست",
        "registered contracts":"قراردادهای ثبت‌شده", "currently enabled":"فعال در حال حاضر", "strict evidence gate":"دروازه شواهد سخت‌گیرانه", "not eligible for execution":"غیرمجاز برای اجرا",
        "Signal activity":"فعالیت سیگنال", "Recent intelligence volume and operating cadence":"حجم اخیر هوش بازار و ریتم اجرا", "Priority queue":"صف اولویت", "Highest-value items requiring attention":"موارد با ارزش بالاتر برای اقدام", "Source health":"سلامت منابع", "Operational readiness of active sources":"آمادگی عملیاتی منابع فعال",
        "Verify all sources":"تأیید همه منابع", "Cancel":"لغو", "Federate active":"دریافت منابع فعال", "STATUS":"وضعیت", "FILTER":"فیلتر", "VIEW":"نما", "Apply":"اعمال",
        "Double-click for evidence detail":"دوبار کلیک برای جزئیات شواهد", "Double-click = evidence drill-down":"دوبار کلیک = جزئیات شواهد", "All statuses":"همه وضعیت‌ها", "All lanes":"همه مسیرها", "All Iran states":"همه وضعیت‌های ایران",
        "Daily project scan":"اسکن روزانه پروژه", "Market intelligence":"هوش بازار", "Blocked for Iran":"مسدود برای ایران", "Verification queue":"صف تأیید",
        "No actionable opportunities yet":"هنوز فرصت اقدام‌پذیری وجود ندارد", "Workspace refreshed":"محیط به‌روزرسانی شد", "Language":"زبان", "English":"English", "Persian":"فارسی",
        "Source Strategy":"راهبرد منابع", "Source evidence":"شواهد منبع", "Close":"بستن", "Source contract and runtime health":"قرارداد منبع و سلامت زمان اجرا",
        "NO SOURCES MATCH THE CURRENT FILTER.":"هیچ منبعی با فیلتر فعلی منطبق نیست.", "NO INTELLIGENCE YET":"هنوز هوش بازار ثبت نشده است",
        "Best opportunities":"بهترین فرصت‌ها", "Application ready":"آماده درخواست", "Opened today":"بازشده امروز", "Submitted":"ارسال‌شده", "Live sources":"منابع زنده", "Blocked jurisdictions":"حوزه‌های مسدود", "Open next fastest":"باز کردن سریع‌ترین",
        "No observations captured yet":"هنوز مشاهده‌ای ثبت نشده است", "Run federation to populate the intelligence timeline":"برای دریافت سیگنال‌های تازه، فدراسیون را اجرا کنید",
        "Checking…":"در حال بررسی…", "Show more":"نمایش بیشتر", "Show less":"نمایش کمتر", "Daily Recommendations":"پیشنهادهای روزانه", "Automatic":"خودکار", "Manual":"دستی", "No connected engine":"Engine متصل نیست", "Demand product opportunity":"فرصت ساخت محصول", "Needs verification":"نیازمند تأیید", "Needs attention":"نیازمند توجه", "System healthy":"سیستم سالم", "Status unavailable":"وضعیت در دسترس نیست"
    }
}


def load_settings(root: Path) -> dict:
    path = root / "config" / "settings.json"
    if not path.exists():
        return {"db": "data/marketradar.db", "http_timeout": 10, "android_secret": None}
    settings = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(settings, dict):
        raise ValueError("SETTINGS_INVALID")
    timeout = settings.get("http_timeout", 10)
    if isinstance(timeout, bool):
        raise ValueError("HTTP_TIMEOUT_INVALID")
    try:
        timeout = float(timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("HTTP_TIMEOUT_INVALID") from exc
    if not 0.1 <= timeout <= 120.0:
        raise ValueError("HTTP_TIMEOUT_INVALID")
    settings["http_timeout"] = timeout
    return settings


def open_runtime():
    root = app_root()
    settings = load_settings(root)
    db_path = data_root() / Path(settings.get("db", "data/marketradar.db")).name
    records = load_source_records(root / "config" / "sources.json")
    conn = connect(db_path)
    profile_path = data_root() / "profile.json"
    if profile_path.exists():
        try: settings['profile'] = json.loads(profile_path.read_text(encoding='utf-8'))
        except (OSError, ValueError, json.JSONDecodeError): pass
    dynamic = load_dynamic_source_records(conn)
    records = records + [r for r in dynamic if r['name'] not in {x['name'] for x in records}]
    sync_source_contracts(conn, records)
    runtime = MarketRadarRuntime(conn, records, None, http_timeout=settings.get("http_timeout", 10), settings=settings)
    return root, settings, records, conn, runtime


class MarketRadarDesktop:
    """Professional desktop intelligence workspace.

    This is a Presentation Layer upgrade only. Federation, evidence, pipeline,
    security, application lifecycle and storage responsibilities remain in Core.
    """

    NAV = ("Overview", "Daily Center", "Intelligence", "Opportunities", "Action Center", "Operations", "Finance & Reports", "Notifications", "Email", "Career Kit", "Sources", "Source Strategy", "Federation")
    NAV_LABELS = {
        "Overview": "Overview",
        "Daily Center": "Daily Center",
        "Intelligence": "Intelligence",
        "Opportunities": "Opportunities",
        "Sources": "Sources",
        "Federation": "Federation",
        "Source Strategy": "Source Strategy",
        "Action Center": "Action Center",
        "Operations": "Operations",
        "Career Kit": "Career Kit",
    }

    def __init__(self, master: Tk):
        self.master = master
        self.master.title(f"SEPP-MarketRadar  |  v{__version__}")
        self.master.geometry("1365x850")
        self.master.minsize(1180, 740)
        self.master.configure(bg=BG)
        self.root, self.settings, self.sources, self.conn, self.runtime = open_runtime()
        self.profile = self._load_profile()
        self.language_var = StringVar(value=str(self.settings.get("language", "en")))

        self.status_var = StringVar(value="Ready")
        self.source_status = StringVar(value="")
        self.progress_var = StringVar(value="")
        self.search_var = StringVar()
        self.daily_show_all = False
        self.opp_filter_var = StringVar(value="All states")
        self.source_filter_var = StringVar(value="All statuses")
        self.intel_scope_var = StringVar(value="All observations")
        self.timeframe_var = StringVar(value="7 days")

        self._queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._worker = None
        self._nav_buttons = {}
        self._views = {}
        self._detail_window = None
        self._chart_widgets = []

        self._configure_style()
        self._build()
        self.refresh_all()
        install_exception_logging(self.master)
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.master.bind("<Control-k>", self._focus_search)
        self.master.bind("<Escape>", lambda _e: self.search_var.set(""))
        self.master.bind("<Configure>", self._on_resize)

    # -------------------- visual system --------------------
    def _configure_style(self):
        style = ttk.Style(self.master)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("App.TFrame", background=BG)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("Header.TFrame", background=SURFACE)
        style.configure("Sidebar.TFrame", background=SIDEBAR)
        style.configure("Title.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Page.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 18, "bold"))
        style.configure("PageSub.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("PanelTitle.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("PanelSub.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 8))
        style.configure("Section.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("Body.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 9))
        style.configure("Metric.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 23, "bold"))
        style.configure("MetricName.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 8, "bold"))
        style.configure("MetricHint.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 8))
        style.configure("Nav.TButton", background=SIDEBAR, foreground=SIDEBAR_TEXT, borderwidth=0, padding=(14, 6), anchor="w", font=("Segoe UI", 8, "bold"))
        style.map("Nav.TButton", background=[("active", SIDEBAR_2)], foreground=[("active", "white")])
        style.configure("NavActive.TButton", background=SIDEBAR_2, foreground="white", borderwidth=0, padding=(14, 6), anchor="w", font=("Segoe UI", 8, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 8), foreground="white", background=ACCENT, borderwidth=0)
        style.map("Accent.TButton", background=[("active", ACCENT_DARK), ("disabled", "#aeb8c5")])
        style.configure("Ghost.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 7), foreground=TEXT, background=SURFACE, bordercolor=BORDER, borderwidth=1)
        style.map("Ghost.TButton", background=[("active", SURFACE_2)])
        style.configure("Toolbar.TFrame", background=BG)
        style.configure("Search.TEntry", fieldbackground=SURFACE, foreground=TEXT, bordercolor=BORDER, padding=(11, 8))
        style.configure("TCombobox", fieldbackground=SURFACE, foreground=TEXT, padding=(7, 6))
        style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT, rowheight=38, font=("Segoe UI", 9), borderwidth=0)
        style.configure("Treeview.Heading", background="#f3f5f8", foreground="#5b6575", font=("Segoe UI", 8, "bold"), padding=(8, 9), borderwidth=0)
        style.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", TEXT)])
        style.configure("Status.TFrame", background=SURFACE, borderwidth=1, relief="solid")
        style.configure("Status.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 8))
        style.configure("Empty.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 9), justify="center")
        style.configure("EmptyTitle.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 11, "bold"), justify="center")

    def _build(self):
        shell = ttk.Frame(self.master, style="App.TFrame")
        shell.pack(fill=BOTH, expand=True)
        self._build_header(shell)
        body = ttk.Frame(shell, style="App.TFrame")
        body.pack(fill=BOTH, expand=True)
        self.sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=196)
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)
        self.content = ttk.Frame(body, style="App.TFrame", padding=(18, 14, 18, 10))
        self.content.pack(side=LEFT, fill=BOTH, expand=True)
        self._build_sidebar()
        self._build_views()
        self._build_status(shell)
        self.show_view("Overview")

    def _build_header(self, parent):
        header = ttk.Frame(parent, style="Header.TFrame", padding=(22, 13, 22, 13))
        header.pack(fill=X)
        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(left, text="SEPP-MarketRadar", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text="Market intelligence workspace", style="Subtitle.TLabel").pack(anchor="w", pady=(1, 0))

        right = ttk.Frame(header, style="Header.TFrame")
        right.pack(side=RIGHT)
        ttk.Label(right, text="⌕", foreground=MUTED, background=SURFACE, font=("Segoe UI Symbol", 14)).pack(side=LEFT, padx=(0, 4))
        self.global_search = ttk.Entry(right, textvariable=self.search_var, width=31, style="Search.TEntry")
        self.global_search.pack(side=LEFT)
        self.global_search.insert(0, "")
        self.global_search.bind("<Return>", lambda _e: self.search_all())
        ttk.Label(right, text="Ctrl+K", foreground=MUTED, background=SURFACE, font=("Segoe UI", 8)).pack(side=LEFT, padx=(7, 10))
        ttk.Button(right, text="Search", command=self.search_all, style="Accent.TButton").pack(side=LEFT)
        ttk.Button(right, text="Refresh", command=self.refresh_all, style="Ghost.TButton").pack(side=LEFT, padx=(8, 0))
        ttk.Label(right, text="Language", foreground=MUTED, background=SURFACE, font=("Segoe UI", 8)).pack(side=LEFT, padx=(12, 5))
        lang = ttk.Combobox(right, textvariable=self.language_var, values=("en", "fa"), state="readonly", width=5)
        lang.pack(side=LEFT)
        lang.bind("<<ComboboxSelected>>", lambda _e: self.set_language(self.language_var.get()))

    def _translate_widget_tree(self, widget, lang):
        mapping = I18N.get(lang, {})
        try:
            text = widget.cget("text")
            if text in mapping:
                widget.configure(text=mapping[text])
        except Exception:
            pass
        for child in widget.winfo_children():
            self._translate_widget_tree(child, lang)

    def set_language(self, lang):
        lang = lang if lang in {"en", "fa"} else "en"
        self.language_var.set(lang)
        self.settings["language"] = lang
        try:
            mapping = I18N.get(lang, {})
            # Translate only exact UI labels. Technical identifiers, source names and
            # evidence are intentionally left untouched.
            self._translate_widget_tree(self.master, lang)
            if lang == "en":
                # Rebuild is the reliable way back from Persian because the original
                # English labels are the source strings.
                self._rebuild_for_language()
            if lang == "fa": self._translate_widget_tree(self.master, "fa")
            self.status_var.set(mapping.get("Workspace refreshed", "Workspace refreshed") if lang == "fa" else "Workspace refreshed")
        except Exception:
            pass

    def _rebuild_for_language(self):
        # Reconstructing the Tk view preserves the data layer and avoids keeping a
        # second, error-prone reverse translation dictionary.
        for frame in self._views.values(): frame.destroy()
        self._views = {}
        self._nav_buttons = {}
        self._build_views()
        self.show_view("Overview")
        self.refresh_all()

    def _build_sidebar(self):
        brand = ttk.Frame(self.sidebar, style="Sidebar.TFrame", padding=(16, 12, 16, 10))
        brand.pack(fill=X)
        badge = tk.Canvas(brand, width=34, height=34, bg=SIDEBAR, highlightthickness=0)
        badge.pack(anchor="w")
        badge.create_oval(2, 2, 32, 32, fill=ACCENT, outline="")
        badge.create_text(17, 17, text="MR", fill="white", font=("Segoe UI", 8, "bold"))
        tk.Label(brand, text="INTELLIGENCE", bg=SIDEBAR, fg="#7fa0ff", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(13, 1))
        tk.Label(brand, text="MarketRadar", bg=SIDEBAR, fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        tk.Label(self.sidebar, text="WORKSPACE", bg=SIDEBAR, fg=SIDEBAR_MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(8, 5))
        nav = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        nav.pack(fill=X, padx=8)
        glyphs = {"Overview": "▦", "Daily Center": "★", "Intelligence": "◈", "Opportunities": "◆", "Action Center": "⚡", "Operations": "◒", "Finance & Reports": "¤", "Notifications": "!", "Email": "@", "Career Kit": "✦", "Sources": "◎", "Federation": "↻", "Source Strategy": "◉"}
        for name in self.NAV:
            btn = ttk.Button(nav, text=f"  {glyphs[name]}   {name}", style="Nav.TButton", command=lambda n=name: self.show_view(n))
            btn.pack(fill=X, pady=2)
            self._nav_buttons[name] = btn

        spacer = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        spacer.pack(fill=BOTH, expand=True)
        system = ttk.Frame(self.sidebar, style="Sidebar.TFrame", padding=(18, 12, 18, 18))
        system.pack(fill=X)
        tk.Label(system, text="SYSTEM", bg=SIDEBAR, fg=SIDEBAR_MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.sidebar_health = tk.Label(system, text="Checking…", bg=SIDEBAR, fg=SIDEBAR_MUTED, font=("Segoe UI", 9, "bold"))
        self.sidebar_health.pack(anchor="w", pady=(5, 0))
        self.sidebar_health_detail = tk.Label(system, text="", bg=SIDEBAR, fg=SIDEBAR_MUTED, font=("Segoe UI", 8))
        self.sidebar_health_detail.pack(anchor="w", pady=(2, 0))
        tk.Label(system, text=f"Release {__version__}", bg=SIDEBAR, fg=SIDEBAR_MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(12, 0))

    def _build_views(self):
        for name in self.NAV:
            self._views[name] = ttk.Frame(self.content, style="App.TFrame")
        self._build_overview(self._views["Overview"])
        self._build_daily_center(self._views["Daily Center"])
        self._build_intelligence(self._views["Intelligence"])
        self._build_opportunities(self._views["Opportunities"])
        self._build_action_center(self._views["Action Center"])
        self._build_operations(self._views["Operations"])
        self._build_finance(self._views["Finance & Reports"])
        self._build_notifications(self._views["Notifications"])
        self._build_email(self._views["Email"])
        self._build_career_kit(self._views["Career Kit"])
        self._build_sources(self._views["Sources"])
        self._build_source_strategy(self._views["Source Strategy"])
        self._build_federation(self._views["Federation"])

    def show_view(self, name):
        for frame in self._views.values():
            frame.pack_forget()
        self._views[name].pack(fill=BOTH, expand=True)
        for nav, btn in self._nav_buttons.items():
            btn.configure(style="NavActive.TButton" if nav == name else "Nav.TButton")
        self.status_var.set(f"{name}  •  workspace ready")
        if name == "Notifications" and hasattr(self, "notification_box"): self.refresh_notifications()
        if name == "Daily Center" and hasattr(self, "daily_body"):
            self.refresh_daily_center()

    def _panel(self, parent, padx=16, pady=14):
        return ttk.Frame(parent, style="Surface.TFrame", padding=(padx, pady))

    def _page_header(self, parent, title, subtitle, action=None):
        box = ttk.Frame(parent, style="App.TFrame")
        box.pack(fill=X, pady=(0, 14))
        left = ttk.Frame(box, style="App.TFrame"); left.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(left, text=title, style="Page.TLabel").pack(anchor="w")
        ttk.Label(left, text=subtitle, style="PageSub.TLabel").pack(anchor="w", pady=(3, 0))
        if action:
            action.pack(side=RIGHT)
        return box

    def _card(self, parent, name, hint, key, accent=ACCENT):
        card = ttk.Frame(parent, style="Surface.TFrame", padding=(15, 13))
        top = ttk.Frame(card, style="Surface.TFrame"); top.pack(fill=X)
        dot = tk.Canvas(top, width=24, height=24, bg=SURFACE, highlightthickness=0); dot.pack(side=LEFT)
        dot.create_oval(3, 3, 21, 21, fill=accent, outline="")
        dot.create_text(12, 12, text="·", fill="white", font=("Segoe UI", 10, "bold"))
        ttk.Label(top, text=name.upper(), style="MetricName.TLabel").pack(side=LEFT, padx=(7, 0))
        var = StringVar(value="0")
        ttk.Label(card, textvariable=var, style="Metric.TLabel").pack(anchor="w", pady=(9, 0))
        ttk.Label(card, text=hint, style="MetricHint.TLabel").pack(anchor="w", pady=(1, 0))
        card.bind("<Button-1>", lambda _e, k=key: self._metric_action(k))
        return card, var

    def _metric_action(self, key):
        mapping = {"Sources": "Sources", "Opportunities": "Opportunities", "Execute": "Opportunities", "Active": "Sources", "Daily scan": "Source Strategy", "Execution ready": "Source Strategy", "Global discovery": "Source Strategy", "Blocked": "Source Strategy", "Auto discovery": "Source Strategy"}
        if key in mapping:
            self.show_view(mapping[key])
            if key == "Execute":
                self.opp_filter_var.set("DISCOVERED")
                self.refresh_opportunities()

    # -------------------- daily center --------------------
    def _build_daily_center(self, parent):
        self._page_header(parent, "Daily Center", "پیشنهادهای روزانه بر اساس سطح، حوزه، سیاست منبع و قابلیت اجرای خودکار.", ttk.Button(parent, text="Refresh", command=self.refresh_daily_center, style="Ghost.TButton"))
        toolbar=ttk.Frame(parent, style="App.TFrame"); toolbar.pack(fill=X, pady=(0,10))
        self.daily_toggle=ttk.Button(toolbar, text="Show more", command=self._toggle_daily, style="Ghost.TButton"); self.daily_toggle.pack(side=RIGHT)
        self.daily_body=ttk.Frame(parent, style="App.TFrame"); self.daily_body.pack(fill=BOTH, expand=True)
        self.refresh_daily_center()

    def _toggle_daily(self):
        self.daily_show_all=not self.daily_show_all
        self.daily_toggle.configure(text="Show less" if self.daily_show_all else "Show more")
        self.refresh_daily_center()

    def _daily_request(self, opportunity_id, mode):
        try:
            options=self.runtime.execution_options(opportunity_id)
            if mode == 'AUTO':
                if not options.get('automatic'):
                    messagebox.showinfo('اجرای خودکار', 'اجرای خودکار هنوز آماده نیست؛ پروژه حذف نمی‌شود و می‌توانید دستی درخواست دهید یا Engine مناسب را متصل/تکمیل کنید.', parent=self.master)
                    return
                messagebox.showinfo('اجرای خودکار', 'Provider متصل است؛ اجرای Engine در لایه اجرای مربوط به Provider انجام می‌شود.', parent=self.master)
                return
            result=self.runtime.open_application(opportunity_id)
            messagebox.showinfo('درخواست دستی', f"پروژه برای بررسی باز شد.\n\n{result.get('title','')}", parent=self.master)
        except Exception as exc:
            messagebox.showerror('درخواست پروژه', str(exc), parent=self.master)

    def refresh_daily_center(self):
        if not hasattr(self, "daily_body"): return
        for child in self.daily_body.winfo_children(): child.destroy()
        try:
            center=self.runtime.daily_center()
            top=center.get("top7",[])
            visible=top if self.daily_show_all else top[:3]
            panel=self._panel(self.daily_body); panel.pack(fill=X, pady=(0,10))
            ttk.Label(panel, text="Daily Recommendations", style="Section.TLabel").pack(anchor="w")
            if not visible:
                ttk.Label(panel, text="هنوز پیشنهاد مناسبی ثبت نشده است.", style="Empty.TLabel").pack(anchor="w", pady=16)
            for item in visible:
                auto=item.get("automation",{})
                status=auto.get("status_label_fa", "فعلاً دستی / نیازمند بررسی")
                rowf=ttk.Frame(panel, style="Surface.TFrame")
                rowf.pack(fill=X, pady=4)
                ttk.Label(rowf, text=f"#{item['rank']}  {item['title']}  |  {item['domain_label_fa']}  |  {status}", style="Body.TLabel").pack(side=LEFT, fill=X, expand=True)
                ttk.Button(rowf, text="درخواست دستی", style="Ghost.TButton", command=lambda oid=item['opportunity_id']: self._daily_request(oid, 'MANUAL')).pack(side=RIGHT, padx=(6,0))
                ttk.Button(rowf, text="خودکار", style="Accent.TButton", command=lambda oid=item['opportunity_id']: self._daily_request(oid, 'AUTO')).pack(side=RIGHT, padx=(6,0))
            domains=center.get("domains",{})
            for domain,payload in domains.items():
                if not payload.get("recommendations"): continue
                dp=self._panel(self.daily_body); dp.pack(fill=X, pady=(0,8))
                ttk.Label(dp, text=payload.get("label_fa",domain), style="Section.TLabel").pack(anchor="w")
                for item in payload["recommendations"][:3]:
                    status=item.get("automation",{}).get("status_label_fa","فعلاً دستی")
                    rowf=ttk.Frame(dp, style="Surface.TFrame")
                    rowf.pack(fill=X, pady=3)
                    ttk.Label(rowf, text=f"{item['rank']}. {item['title']}  —  {status}", style="Body.TLabel").pack(side=LEFT, fill=X, expand=True)
                    ttk.Button(rowf, text="درخواست دستی", style="Ghost.TButton", command=lambda oid=item['opportunity_id']: self._daily_request(oid, 'MANUAL')).pack(side=RIGHT, padx=(6,0))
                    ttk.Button(rowf, text="خودکار", style="Accent.TButton", command=lambda oid=item['opportunity_id']: self._daily_request(oid, 'AUTO')).pack(side=RIGHT, padx=(6,0))
            products=center.get("product_opportunities",[])
            if products:
                pp=self._panel(self.daily_body); pp.pack(fill=X, pady=(0,8))
                ttk.Label(pp, text="Demand product opportunities", style="Section.TLabel").pack(anchor="w")
                for spec in products[:7]:
                    ttk.Label(pp, text=f"{spec['product_name']}  |  تقاضا {spec['demand_score']:.2f}  |  {spec['opportunity_count']} پروژه", style="Body.TLabel").pack(anchor="w", pady=3)
        except Exception as exc:
            ttk.Label(self.daily_body, text=f"Daily Center unavailable: {exc}", style="Empty.TLabel").pack(anchor="center", pady=30)

    # -------------------- overview --------------------
    def _build_overview(self, parent):
        self._page_header(parent, "Overview", "A decision-first view of coverage, signals, source health and next actions.")

        cards = ttk.Frame(parent, style="App.TFrame")
        cards.pack(fill=X, pady=(0, 14))
        self.metrics = {}
        specs = (
            ("Best opportunities", "ranked projects ready for review", "Opportunities", ACCENT),
            ("Application ready", "qualified opportunities with a fast path", "Execute", GOOD),
            ("Opened today", "applications opened for review", "Opportunities", INFO),
            ("Submitted", "tracked application lifecycle", "Opportunities", WARN),
        )
        for i, (name, hint, key, accent) in enumerate(specs):
            card, var = self._card(cards, name, hint, key, accent)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 9, 0))
            cards.columnconfigure(i, weight=1)
            self.metrics[name] = var
        secondary = ttk.Frame(parent, style="App.TFrame")
        secondary.pack(fill=X, pady=(0, 12))
        for i, (name, key) in enumerate((("Sources", "Sources"), ("Live sources", "Policy confirmed"), ("Auto discovery", "Auto discovery"), ("Blocked jurisdictions", "Blocked"))):
            box = self._panel(secondary, 11, 8); box.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0)); secondary.columnconfigure(i, weight=1)
            var = StringVar(value="0"); self.metrics[name] = var
            ttk.Label(box, text=name.upper(), foreground=MUTED, background=SURFACE, font=("Segoe UI", 7, "bold")).pack(side=LEFT)
            ttk.Label(box, textvariable=var, foreground=TEXT, background=SURFACE, font=("Segoe UI", 12, "bold")).pack(side=RIGHT)

        grid = ttk.Frame(parent, style="App.TFrame")
        grid.pack(fill=BOTH, expand=True)
        grid.columnconfigure(0, weight=3); grid.columnconfigure(1, weight=2); grid.rowconfigure(0, weight=1); grid.rowconfigure(1, weight=1)

        activity = self._panel(grid, 16, 14); activity.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 9))
        head = ttk.Frame(activity, style="Surface.TFrame"); head.pack(fill=X)
        ttk.Label(head, text="Signal activity", style="PanelTitle.TLabel").pack(side=LEFT)
        ttk.Label(head, textvariable=self.timeframe_var, style="PanelSub.TLabel").pack(side=RIGHT)
        ttk.Label(activity, text="Recent intelligence volume and operating cadence", style="PanelSub.TLabel").pack(anchor="w", pady=(2, 6))
        self.activity_chart = tk.Canvas(activity, bg=SURFACE, highlightthickness=0, height=215)
        self.activity_chart.pack(fill=BOTH, expand=True)

        action = self._panel(grid, 16, 14); action.grid(row=0, column=1, sticky="nsew", pady=(0, 9))
        ttk.Label(action, text="Priority queue", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(action, text="Highest-value items requiring attention", style="PanelSub.TLabel").pack(anchor="w", pady=(2, 8))
        self.action_list = ttk.Treeview(action, columns=("score", "title", "state"), show="headings", height=6)
        self.action_list.heading("score", text="SCORE"); self.action_list.heading("title", text="SIGNAL"); self.action_list.heading("state", text="STATE")
        self.action_list.column("score", width=55, anchor="center"); self.action_list.column("title", width=260, anchor="w"); self.action_list.column("state", width=90, anchor="w")
        self.action_list.pack(fill=BOTH, expand=True)
        self.action_list.tag_configure("high", foreground=ACCENT)
        self.action_list.bind("<Double-1>", lambda _e: self._open_selected_opportunity(self.action_list))

        health = self._panel(grid, 16, 14); health.grid(row=1, column=1, sticky="nsew")
        ttk.Label(health, text="Source health", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(health, text="Operational readiness of active sources", style="PanelSub.TLabel").pack(anchor="w", pady=(2, 6))
        self.health_canvas = tk.Canvas(health, bg=SURFACE, highlightthickness=0, height=125)
        self.health_canvas.pack(fill=BOTH, expand=True)

    # -------------------- intelligence --------------------
    def _build_intelligence(self, parent):
        self._page_header(parent, "Intelligence", "Monitor signal quality, confidence, eligibility and recency across the source network.")
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame"); toolbar.pack(fill=X, pady=(0, 10))
        ttk.Label(toolbar, text="VIEW", foreground=MUTED, background=BG, font=("Segoe UI", 8, "bold")).pack(side=LEFT)
        self.intel_scope = ttk.Combobox(toolbar, textvariable=self.intel_scope_var, values=("All observations", "High quality", "Actionable"), state="readonly", width=18)
        self.intel_scope.pack(side=LEFT, padx=(7, 8)); ttk.Button(toolbar, text="Apply", command=self.refresh_intelligence, style="Ghost.TButton").pack(side=LEFT)
        ttk.Label(toolbar, text="Double-click for evidence detail", foreground=MUTED, background=BG, font=("Segoe UI", 8)).pack(side=RIGHT)
        panel = self._panel(parent, 8, 8); panel.pack(fill=BOTH, expand=True)
        self.intel_tree = ttk.Treeview(panel, columns=("source", "title", "quality", "confidence", "eligibility", "seen"), show="headings")
        for col, width in (("source", 145), ("title", 450), ("quality", 90), ("confidence", 105), ("eligibility", 110), ("seen", 180)):
            self.intel_tree.heading(col, text=col.upper()); self.intel_tree.column(col, width=width, minwidth=65, anchor="w")
        self.intel_tree.tag_configure("execute", foreground=GOOD)
        self.intel_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(panel, command=self.intel_tree.yview); self.intel_tree.configure(yscrollcommand=scroll.set); scroll.pack(side=RIGHT, fill=Y)
        self.intel_empty = ttk.Label(panel, text="NO INTELLIGENCE YET\n\nRun federation to bring fresh signals into the workspace.", style="Empty.TLabel")
        self.intel_empty.place(relx=0.5, rely=0.5, anchor="center")
        self.intel_tree.bind("<Double-1>", lambda _e: self._open_selected_opportunity(self.intel_tree))

    # -------------------- opportunities --------------------
    def _build_opportunities(self, parent):
        self._page_header(parent, "Opportunities", "Ranked opportunities with evidence, provenance and lifecycle state.")
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame"); toolbar.pack(fill=X, pady=(0, 10))
        ttk.Label(toolbar, text="STATE", foreground=MUTED, background=BG, font=("Segoe UI", 8, "bold")).pack(side=LEFT)
        self.opp_filter = ttk.Combobox(toolbar, textvariable=self.opp_filter_var, values=("All states", "DISCOVERED", "ELIGIBILITY_CHECK", "RECOMMENDED", "APPROVAL_PENDING", "SUBMITTED", "VIEWED", "MESSAGE_RECEIVED", "NEGOTIATION", "ACCEPTED", "IN_PROGRESS", "DELIVERED", "PAID", "REJECTED", "EXPIRED", "CANCELLED"), state="readonly", width=16)
        self.opp_filter.pack(side=LEFT, padx=(7, 8)); ttk.Button(toolbar, text="Apply", command=self.refresh_opportunities, style="Ghost.TButton").pack(side=LEFT)
        ttk.Label(toolbar, text="Double-click a row to inspect evidence", foreground=MUTED, background=BG, font=("Segoe UI", 8)).pack(side=RIGHT)
        panel = self._panel(parent, 8, 8); panel.pack(fill=BOTH, expand=True)
        self.opp_tree = ttk.Treeview(panel, columns=("id", "source", "title", "eligibility", "rank", "fit", "learn", "speed", "track", "state"), show="headings")
        for col, width in (("id", 48), ("source", 125), ("title", 360), ("eligibility", 90), ("rank", 65), ("fit", 55), ("learn", 65), ("speed", 65), ("track", 105), ("state", 105)):
            self.opp_tree.heading(col, text=col.upper()); self.opp_tree.column(col, width=width, minwidth=50, anchor="w")
        self.opp_tree.tag_configure("execute", foreground=GOOD)
        self.opp_tree.tag_configure("review", foreground=WARN)
        self.opp_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(panel, command=self.opp_tree.yview); self.opp_tree.configure(yscrollcommand=scroll.set); scroll.pack(side=RIGHT, fill=Y)
        self.opp_empty = ttk.Label(panel, text="NO OPPORTUNITIES MATCH THIS VIEW\n\nAdjust the filter or run federation.", style="Empty.TLabel")
        self.opp_empty.place(relx=0.5, rely=0.5, anchor="center")
        self.opp_tree.bind("<Double-1>", lambda _e: self._open_selected_opportunity(self.opp_tree))

    # -------------------- action center --------------------
    def _build_action_center(self, parent):
        self._page_header(parent, "Action Center", "Turn a discovered opportunity into a tool proposal, tailored application material and a safe submission plan.")
        toolbar=ttk.Frame(parent, style="Toolbar.TFrame"); toolbar.pack(fill=X, pady=(0,10))
        ttk.Label(toolbar,text="OPPORTUNITY",foreground=MUTED,background=BG,font=("Segoe UI",8,"bold")).pack(side=LEFT)
        self.action_opp_var=StringVar(); self.action_opp=ttk.Combobox(toolbar,textvariable=self.action_opp_var,state="readonly",width=55); self.action_opp.pack(side=LEFT,padx=8)
        ttk.Button(toolbar,text="Analyze need",command=self._action_analyze,style="Accent.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Resume + proposal",command=self._action_materials,style="Ghost.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Submission plan",command=self._action_plan,style="Ghost.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Open next fastest",command=self._action_open_next,style="Accent.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Where to send",command=self._action_distribution,style="Ghost.TButton").pack(side=LEFT,padx=3)
        grid=ttk.Frame(parent,style="App.TFrame"); grid.pack(fill=BOTH,expand=True); grid.columnconfigure(0,weight=1); grid.columnconfigure(1,weight=1); grid.rowconfigure(0,weight=1)
        left=self._panel(grid,15,13); left.grid(row=0,column=0,sticky="nsew",padx=(0,8)); ttk.Label(left,text="Need → Tool",style="PanelTitle.TLabel").pack(anchor="w")
        self.action_need=tk.Text(left,wrap="word",bg=SURFACE,fg=TEXT,relief="flat",font=("Segoe UI",10)); self.action_need.pack(fill=BOTH,expand=True,pady=(8,0)); self.action_need.configure(state="disabled")
        right=self._panel(grid,15,13); right.grid(row=0,column=1,sticky="nsew",padx=(8,0)); ttk.Label(right,text="Application material",style="PanelTitle.TLabel").pack(anchor="w")
        self.action_material=tk.Text(right,wrap="word",bg=SURFACE,fg=TEXT,relief="flat",font=("Segoe UI",9)); self.action_material.pack(fill=BOTH,expand=True,pady=(8,0)); self.action_material.configure(state="disabled")

    def _action_selected_id(self):
        value=self.action_opp_var.get().strip()
        try:return int(value.split(" | ",1)[0])
        except (ValueError,IndexError):return None
    def _action_set_text(self,widget,text):
        widget.configure(state="normal"); widget.delete("1.0",END); widget.insert("1.0",text); widget.configure(state="disabled")
    def _refresh_action_options(self):
        rows=self.conn.execute("SELECT id,title,COALESCE(rank_score,score) AS rank_score FROM opportunities WHERE state='DISCOVERED' ORDER BY COALESCE(rank_score,score) DESC LIMIT 50").fetchall()
        values=[f"{r['id']} | {r['title']} | rank {r['rank_score']:.1f}" for r in rows]; self.action_opp['values']=values
        if values and self.action_opp_var.get() not in values:self.action_opp_var.set(values[0])
    def _action_analyze(self):
        oid=self._action_selected_id()
        if oid is None:return
        result=self.runtime.analyze_opportunity(oid); self._action_set_text(self.action_need,json.dumps(result,ensure_ascii=False,indent=2)); self.refresh_all()
    def _action_materials(self):
        oid=self._action_selected_id()
        if oid is None:return
        result=self.runtime.build_resume_and_proposal(oid,self.profile); self._action_set_text(self.action_material,"RESUME\n\n"+result['resume']+"\n\nPROPOSAL\n\n"+result['proposal'])
    def _action_plan(self):
        oid=self._action_selected_id()
        if oid is None:return
        plan=self.runtime.create_submission_plan(oid,self.profile); self._action_set_text(self.action_need,json.dumps({'mode':plan.mode,'url':plan.url,'fields':plan.fields,'authorization_required':plan.authorization_required},ensure_ascii=False,indent=2))
    def _action_open_next(self):
        try:
            result=self.runtime.open_next_application(); self._action_set_text(self.action_need,json.dumps(result,ensure_ascii=False,indent=2)); self.refresh_all()
        except Exception as exc:
            messagebox.showerror('Application queue',str(exc))
    def _action_distribution(self):
        oid=self._action_selected_id()
        if oid is None:return
        result=self.runtime.distribution_recommendation(oid)
        sites=result.get('recommended_sites',[])
        payload={'category':result.get('category'),'daily_project_sites':result.get('daily_project_sites',[]),'needs_analysis_sites':result.get('needs_analysis_sites',[]),'recommended_sites':sites,'generic_channels':result.get('recommended_channels',[]),'rule':result.get('rule')}
        self._action_set_text(self.action_need,json.dumps(payload,ensure_ascii=False,indent=2))


    # -------------------- finance / notifications / email --------------------
    def _build_finance(self,parent):
        self._page_header(parent,"Finance & Reports","Multi-account routing, ledger evidence and weekly/monthly/quarterly/annual reports.")
        bar=ttk.Frame(parent,style="Toolbar.TFrame"); bar.pack(fill=X,pady=(0,10))
        for period in ("weekly","monthly","quarterly","annual"):
            ttk.Button(bar,text=period.title(),command=lambda p=period:self._finance_report(p),style="Ghost.TButton").pack(side=LEFT,padx=3)
        account=self._panel(parent,12,10); account.pack(fill=X,pady=(0,10))
        self.finance_account_name=tk.StringVar(); self.finance_currency=tk.StringVar(value="IRR"); self.finance_iban=tk.StringVar(); self.finance_number=tk.StringVar(); self.finance_institution=tk.StringVar()
        for i,(label,var) in enumerate((("Account",self.finance_account_name),("Currency",self.finance_currency),("IBAN / Sheba",self.finance_iban),("Account number",self.finance_number),("Bank / Wallet",self.finance_institution))):
            ttk.Label(account,text=label,background=SURFACE,foreground=MUTED).grid(row=0,column=i,sticky="w",padx=4)
            ttk.Entry(account,textvariable=var,width=18).grid(row=1,column=i,padx=4,pady=(3,0),sticky="ew")
            account.columnconfigure(i,weight=1)
        ttk.Button(account,text="Save account",command=self._finance_save_account,style="Accent.TButton").grid(row=1,column=5,padx=6)
        body=self._panel(parent,12,12); body.pack(fill=BOTH,expand=True)
        self.finance_box=tk.Text(body,wrap="none",bg=SURFACE,fg=TEXT,relief="flat",font=("Consolas",9)); self.finance_box.pack(fill=BOTH,expand=True)
    def _finance_save_account(self):
        try:
            if not self.finance_account_name.get().strip() or not self.finance_currency.get().strip(): raise ValueError("ACCOUNT_NAME_AND_CURRENCY_REQUIRED")
            row=self.runtime.finance_add_account(name=self.finance_account_name.get().strip(),currency=self.finance_currency.get().strip(),institution=self.finance_institution.get().strip() or None,account_number=self.finance_number.get().strip() or None,iban=self.finance_iban.get().strip() or None)
            self.status_var.set(f"Account saved: {row['name']}")
        except Exception as exc: messagebox.showerror("Finance account",str(exc))
    def _finance_report(self,period):
        try:
            result=self.runtime.finance_period_report(period); self.finance_box.delete("1.0",END); self.finance_box.insert("1.0",json.dumps(result,ensure_ascii=False,indent=2,default=str)); self.status_var.set(f"Financial {period} report exported")
        except Exception as exc: messagebox.showerror("Finance report",str(exc))
    def _build_notifications(self,parent):
        self._page_header(parent,"Notifications","Durable reminders for new opportunities, replies, deadlines, payments and policy changes.")
        bar=ttk.Frame(parent,style="Toolbar.TFrame"); bar.pack(fill=X,pady=(0,10)); ttk.Button(bar,text="Refresh",command=self.refresh_notifications,style="Accent.TButton").pack(side=LEFT)
        self.notification_box=tk.Text(parent,wrap="word",bg=SURFACE,fg=TEXT,relief="flat",font=("Segoe UI",10)); self.notification_box.pack(fill=BOTH,expand=True); self.refresh_notifications()
    def refresh_notifications(self):
        try:
            rows=self.runtime.notifications(200); self.notification_box.delete("1.0",END);
            for r in rows: self.notification_box.insert(END,f"[{r['priority']}] {r['title']}\n{r['body']}\nID={r['id']}  Due={r.get('due_at')}\n\n")
            if not rows: self.notification_box.insert(END,"No unread notifications.")
        except Exception as exc: self.status_var.set(f"Notification error: {exc}")
    def _build_email(self,parent):
        self._page_header(parent,"Email","Prepare tailored emails; external sending remains approval-gated.")
        form=self._panel(parent,12,12); form.pack(fill=BOTH,expand=False)
        self.email_account_name=tk.StringVar(); self.email_address=tk.StringVar(); self.email_smtp=tk.StringVar(); self.email_imap=tk.StringVar(); self.email_secret=tk.StringVar(); self.email_to=tk.StringVar(); self.email_subject=tk.StringVar()
        for i,(label,var) in enumerate((("Account",self.email_account_name),("Address",self.email_address),("SMTP host",self.email_smtp),("IMAP host",self.email_imap),("Password env",self.email_secret))):
            ttk.Label(form,text=label).grid(row=0,column=i,sticky="w",padx=3); ttk.Entry(form,textvariable=var,width=19).grid(row=1,column=i,padx=3,pady=(3,8),sticky="ew")
        ttk.Button(form,text="Save email account",command=self._email_save_account,style="Ghost.TButton").grid(row=1,column=5,padx=5)
        ttk.Label(form,text="Recipient").grid(row=2,column=0,sticky="w"); ttk.Entry(form,textvariable=self.email_to,width=60).grid(row=2,column=1,columnspan=3,sticky="ew",padx=8)
        ttk.Label(form,text="Subject").grid(row=3,column=0,sticky="w",pady=6); ttk.Entry(form,textvariable=self.email_subject,width=60).grid(row=3,column=1,columnspan=3,sticky="ew",padx=8,pady=6); form.columnconfigure(3,weight=1)
        self.email_body=tk.Text(form,height=10,wrap="word",bg=SURFACE,fg=TEXT,relief="flat"); self.email_body.grid(row=4,column=0,columnspan=6,sticky="nsew");
        ttk.Button(form,text="Create draft",command=self._email_create_draft,style="Accent.TButton").grid(row=5,column=0,pady=8,sticky="w")
        ttk.Label(parent,text="Drafts are stored in SQLite. Configure an email account/SMTP secret through the Core API before approving a send.",foreground=MUTED,background=BG).pack(anchor="w",padx=12,pady=8)
    def _email_save_account(self):
        try:
            row=self.runtime.email_add_account(name=self.email_account_name.get().strip(),address=self.email_address.get().strip(),smtp_host=self.email_smtp.get().strip() or None,imap_host=self.email_imap.get().strip() or None,password_env=self.email_secret.get().strip() or None)
            self.status_var.set(f"Email account saved: {row['name'] if row else self.email_account_name.get().strip()}")
        except Exception as exc: messagebox.showerror("Email account",str(exc))
    def _email_create_draft(self):
        try:
            oid=self._op_selected_id() if hasattr(self,'op_opp_var') else None
            account=self.conn.execute('SELECT id FROM email_accounts ORDER BY id DESC LIMIT 1').fetchone()
            if not account: raise ValueError("EMAIL_ACCOUNT_REQUIRED")
            did=self.runtime.email_create_draft(recipient=self.email_to.get().strip(),subject=self.email_subject.get().strip(),body=self.email_body.get("1.0",END).strip(),opportunity_id=oid,account_id=account['id'])
            messagebox.showinfo("Email draft",f"Draft #{did} created. Use the Core approval path before sending.")
        except Exception as exc: messagebox.showerror("Email draft",str(exc))

    # -------------------- operations --------------------
    def _build_operations(self, parent):
        self._page_header(parent, "Operations", "Project lifecycle, payment verification, deadlines, follow-ups and final revenue reporting.")
        cards=ttk.Frame(parent,style="App.TFrame"); cards.pack(fill=X,pady=(0,10)); self.op_metrics={}
        for i,(label,key) in enumerate((("Submitted","submitted"),("Accepted / active","accepted"),("Rejected","rejected"),("Waiting payment","waiting_payment"),("Paid","paid"),("Due follow-ups","due_followups"))):
            box=self._panel(cards,10,8); box.grid(row=0,column=i,sticky="ew",padx=(0 if i==0 else 7,0)); cards.columnconfigure(i,weight=1)
            ttk.Label(box,text=label.upper(),foreground=MUTED,background=SURFACE,font=("Segoe UI",7,"bold")).pack(anchor="w")
            v=StringVar(value="0"); self.op_metrics[key]=v; ttk.Label(box,textvariable=v,foreground=TEXT,background=SURFACE,font=("Segoe UI",14,"bold")).pack(anchor="w",pady=(4,0))
        toolbar=ttk.Frame(parent,style="Toolbar.TFrame"); toolbar.pack(fill=X,pady=(0,10))
        ttk.Label(toolbar,text="PROJECT",foreground=MUTED,background=BG,font=("Segoe UI",8,"bold")).pack(side=LEFT)
        self.op_opp_var=StringVar(); self.op_opp=ttk.Combobox(toolbar,textvariable=self.op_opp_var,state="readonly",width=52); self.op_opp.pack(side=LEFT,padx=8)
        ttk.Button(toolbar,text="Refresh",command=self._refresh_operations,style="Ghost.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Final report",command=self._op_report,style="Accent.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Payment check",command=self._op_payment_check,style="Ghost.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Schedule follow-up",command=self._op_followup,style="Ghost.TButton").pack(side=LEFT,padx=3)
        ttk.Button(toolbar,text="Set lifecycle",command=self._op_lifecycle,style="Ghost.TButton").pack(side=LEFT,padx=3)
        grid=ttk.Frame(parent,style="App.TFrame"); grid.pack(fill=BOTH,expand=True); grid.columnconfigure(0,weight=3); grid.columnconfigure(1,weight=2); grid.rowconfigure(0,weight=1)
        left=self._panel(grid,10,10); left.grid(row=0,column=0,sticky="nsew",padx=(0,8))
        ttk.Label(left,text="Lifecycle / project timeline",style="PanelTitle.TLabel").pack(anchor="w")
        self.op_tree=ttk.Treeview(left,columns=("at","from","to","actor"),show="headings")
        for col,w in (("at",170),("from",120),("to",150),("actor",100)): self.op_tree.heading(col,text=col.upper()); self.op_tree.column(col,width=w,anchor="w")
        self.op_tree.pack(fill=BOTH,expand=True,pady=(8,0))
        right=self._panel(grid,10,10); right.grid(row=0,column=1,sticky="nsew")
        ttk.Label(right,text="Project / payment",style="PanelTitle.TLabel").pack(anchor="w")
        self.op_detail=tk.Text(right,wrap="word",bg=SURFACE,fg=TEXT,relief="flat",font=("Consolas",9)); self.op_detail.pack(fill=BOTH,expand=True,pady=(8,0)); self.op_detail.configure(state="disabled")
        self._refresh_operations()

    def _op_selected_id(self):
        try:return int(self.op_opp_var.get().split(" | ",1)[0])
        except Exception:return None
    def _refresh_operations(self):
        try:
            d=self.runtime.operation_dashboard()
            for k,v in self.op_metrics.items(): v.set(str(d.get(k,0)))
            rows=self.conn.execute("SELECT id,title,source,state,deadline_at FROM opportunities WHERE state NOT IN ('DISCOVERED','ELIGIBILITY_CHECK') ORDER BY last_seen DESC LIMIT 100").fetchall()
            vals=[f"{r['id']} | {r['title']} | {r['state']}" for r in rows]; self.op_opp['values']=vals
            if vals and self.op_opp_var.get() not in vals:self.op_opp_var.set(vals[0])
            oid=self._op_selected_id()
            self.op_tree.delete(*self.op_tree.get_children())
            if oid:
                events=self.conn.execute("SELECT at,from_state,to_state,actor FROM application_events WHERE opportunity_id=? ORDER BY at",(oid,)).fetchall()
                for e in events:self.op_tree.insert('',END,values=(e['at'],e['from_state'],e['to_state'],e['actor']))
                report=self.runtime.project_report(oid)
                self._action_set_text(self.op_detail,json.dumps(report,ensure_ascii=False,indent=2,default=str))
        except Exception as exc:
            self.status_var.set(f"Operations error: {exc}")
    def _op_report(self):
        oid=self._op_selected_id()
        if not oid:return
        try:
            path,report=self.runtime.generate_final_report(oid); self._action_set_text(self.op_detail,json.dumps(report,ensure_ascii=False,indent=2,default=str)); messagebox.showinfo("Final report",f"Report created:\n{path}")
        except Exception as exc: messagebox.showerror("Final report",str(exc))
    def _op_payment_check(self):
        oid=self._op_selected_id()
        if not oid:return
        status=messagebox.askyesnocancel("Payment verification","Has the payment actually been received?\n\nYes = VERIFIED\nNo = NOT_VERIFIED")
        if status is None:return
        try:
            self.runtime.check_payment(oid,'VERIFIED' if status else 'NOT_VERIFIED',actor='human'); self._refresh_operations(); self.refresh_all()
        except Exception as exc: messagebox.showerror("Payment verification",str(exc))
    def _op_followup(self):
        oid=self._op_selected_id()
        if not oid:return
        self.runtime.schedule_followup(oid,(datetime.now(timezone.utc)+__import__('datetime').timedelta(hours=24)).isoformat(),"Follow up on submitted application / project status.",channel='MANUAL',requires_approval=1)
        self.runtime.operation_tick(); self._refresh_operations(); messagebox.showinfo("Follow-up","Follow-up scheduled for 24 hours from now. External sending remains approval-gated.")
    def _op_lifecycle(self):
        oid=self._op_selected_id()
        if not oid:return
        states=("VIEWED","MESSAGE_RECEIVED","NEGOTIATION","ACCEPTED","REJECTED","IN_PROGRESS","DELIVERED")
        win=Toplevel(self.master); win.title("Set project lifecycle"); win.geometry("420x180")
        var=StringVar(value=states[0]); ttk.Label(win,text="New state").pack(pady=(20,5)); cb=ttk.Combobox(win,textvariable=var,values=states,state='readonly'); cb.pack()
        def apply():
            try:self.runtime.set_lifecycle_state(oid,var.get(),'human'); win.destroy(); self._refresh_operations(); self.refresh_all()
            except Exception as exc: messagebox.showerror("Lifecycle",str(exc),parent=win)
        ttk.Button(win,text="Apply",command=apply,style="Accent.TButton").pack(pady=15)

    # -------------------- career kit --------------------
    def _build_career_kit(self,parent):
        self._page_header(parent,"Career Kit","Your reusable profile powers tailored resumes, proposals and daily project recommendations.")
        toolbar=ttk.Frame(parent,style="Toolbar.TFrame"); toolbar.pack(fill=X,pady=(0,10))
        ttk.Button(toolbar,text="Save profile",command=self._save_profile,style="Accent.TButton").pack(side=LEFT)
        ttk.Button(toolbar,text="Reload",command=self._load_profile_into_editor,style="Ghost.TButton").pack(side=LEFT,padx=7)
        ttk.Label(toolbar,text="Skill levels and search domains are stored locally.",foreground=MUTED,background=BG,font=("Segoe UI",8)).pack(side=LEFT,padx=12)
        pref=self._panel(parent,15,10); pref.pack(fill=X,pady=(0,10))
        ttk.Label(pref,text="Search preferences",style="Section.TLabel").pack(anchor="w",pady=(0,6))
        self.domain_pref_frame=ttk.Frame(pref,style="Surface.TFrame"); self.domain_pref_frame.pack(fill=X)
        self.domain_pref_vars={}
        self.domain_level_vars={}
        self.domain_day_vars={}
        from .recommendation_engine import DOMAIN_LABELS_FA
        for col,(domain,label) in enumerate(DOMAIN_LABELS_FA.items()):
            box=ttk.Frame(self.domain_pref_frame,style="Surface.TFrame"); box.grid(row=0,column=col,sticky="nw",padx=(0 if col==0 else 8,0))
            enabled=tk.BooleanVar(value=True); level=tk.IntVar(value=2); day=tk.IntVar(value=0)
            self.domain_pref_vars[domain]=enabled; self.domain_level_vars[domain]=level; self.domain_day_vars[domain]=day
            ttk.Checkbutton(box,text=label,variable=enabled).pack(anchor="w")
            ttk.Label(box,text="سطح",style="Status.TLabel").pack(anchor="w",pady=(4,0))
            ttk.Spinbox(box,from_=1,to=5,textvariable=level,width=4).pack(anchor="w")
            ttk.Label(box,text="روز دوره",style="Status.TLabel").pack(anchor="w",pady=(3,0))
            ttk.Spinbox(box,from_=0,to=10000,textvariable=day,width=6).pack(anchor="w")
        panel=self._panel(parent,15,13); panel.pack(fill=BOTH,expand=True)
        self.profile_editor=tk.Text(panel,wrap="none",bg=SURFACE,fg=TEXT,relief="flat",font=("Consolas",9)); self.profile_editor.pack(fill=BOTH,expand=True); self._load_profile_into_editor()
    def _profile_path(self): return data_root()/"profile.json"
    def _load_profile(self):
        p=self._profile_path()
        if p.exists():
            try:return json.loads(p.read_text(encoding="utf-8"))
            except Exception: pass
        example=self.root/"config"/"profile.example.json"
        return json.loads(example.read_text(encoding="utf-8")) if example.exists() else {'name':'Candidate','skills':[],'projects':[]}
    def _load_profile_into_editor(self):
        self.profile=self._load_profile()
        domains=self.profile.get('domains',{}) if isinstance(self.profile.get('domains'),dict) else {}
        for domain,var in self.domain_pref_vars.items():
            item=domains.get(domain,{})
            var.set(bool(item.get('enabled',True)))
            self.domain_level_vars[domain].set(int(item.get('level',2) or 2))
            self.domain_day_vars[domain].set(int(item.get('course_day',0) or 0))
        self.profile_editor.delete("1.0",END); self.profile_editor.insert("1.0",json.dumps(self.profile,ensure_ascii=False,indent=2))
    def _save_profile(self):
        try:
            value=json.loads(self.profile_editor.get("1.0",END))
            if not isinstance(value,dict): raise ValueError('PROFILE_INVALID')
            domains=value.get('domains') if isinstance(value.get('domains'),dict) else {}
            selected=[]
            for domain,var in self.domain_pref_vars.items():
                item=dict(domains.get(domain) or {})
                item['enabled']=bool(var.get())
                item['level']=max(1,min(5,int(self.domain_level_vars[domain].get())))
                item['course_day']=max(0,int(self.domain_day_vars[domain].get()))
                domains[domain]=item
                if item['enabled']: selected.append(domain)
            value['domains']=domains
            value['selected_domains']=selected
            data_root().mkdir(parents=True,exist_ok=True); self._profile_path().write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
            self.profile=value; self.runtime.set_learning_profile(value); self.status_var.set("Profile saved")
        except Exception as exc: messagebox.showerror("Profile error",str(exc))

    # -------------------- sources --------------------
    def _build_sources(self, parent):
        self._page_header(parent, "Sources", "Coverage, acquisition contracts, verification state and runtime health.")
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame"); toolbar.pack(fill=X, pady=(0, 10))
        self.verify_button = ttk.Button(toolbar, text="Verify all sources", command=self.verify_registry, style="Accent.TButton"); self.verify_button.pack(side=LEFT)
        self.cancel_button = ttk.Button(toolbar, text="Cancel", command=self.cancel_verification, state="disabled", style="Ghost.TButton"); self.cancel_button.pack(side=LEFT, padx=7)
        ttk.Button(toolbar, text="Federate active", command=self.verify_active_sources, style="Ghost.TButton").pack(side=LEFT)
        ttk.Label(toolbar, text="STATUS", foreground=MUTED, background=BG, font=("Segoe UI", 8, "bold")).pack(side=LEFT, padx=(18, 6))
        self.source_filter = ttk.Combobox(toolbar, textvariable=self.source_filter_var, values=("All statuses", "active", "candidate", "disabled"), state="readonly", width=15)
        self.source_filter.pack(side=LEFT); self.source_lane_var=StringVar(value="All lanes"); self.source_lane=ttk.Combobox(toolbar,textvariable=self.source_lane_var,values=("All lanes","DAILY_PROJECT_SCAN","MARKET_INTELLIGENCE_ONLY","BLACKLIST_ARCHIVE","GLOBAL_DISCOVERY","NEEDS_ANALYSIS","BLOCKED_IRAN","REVIEW"),state="readonly",width=21); self.source_lane.pack(side=LEFT,padx=(8,0)); self.source_lane.bind("<<ComboboxSelected>>", lambda _e: self.refresh_sources()); self.source_filter.bind("<<ComboboxSelected>>", lambda _e: self.refresh_sources())
        ttk.Label(toolbar, textvariable=self.source_status, foreground=MUTED, background=BG, font=("Segoe UI", 8)).pack(side=LEFT, padx=12)
        ttk.Label(toolbar, textvariable=self.progress_var, foreground=MUTED, background=BG, font=("Segoe UI", 8)).pack(side=RIGHT)
        panel = self._panel(parent, 8, 8); panel.pack(fill=BOTH, expand=True)
        self.source_tree = ttk.Treeview(panel, columns=("name", "role", "lane", "iran", "status", "verification", "health", "last_checked"), show="headings")
        for col, width in (("name", 175), ("role", 125), ("lane", 155), ("iran", 70), ("status", 80), ("verification", 105), ("health", 70), ("last_checked", 170)):
            self.source_tree.heading(col, text=col.replace("_", " ").upper()); self.source_tree.column(col, width=width, minwidth=55, anchor="w")
        self.source_tree.tag_configure("healthy", foreground=GOOD)
        self.source_tree.tag_configure("degraded", foreground=DANGER)
        self.source_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(panel, command=self.source_tree.yview); self.source_tree.configure(yscrollcommand=scroll.set); scroll.pack(side=RIGHT, fill=Y)
        self.source_empty = ttk.Label(panel, text="NO SOURCES MATCH THE CURRENT FILTER.", style="Empty.TLabel")
        self.source_empty.place(relx=0.5, rely=0.5, anchor="center")
        self.source_tree.bind("<Double-1>", lambda _e: self._open_source_detail())

    # -------------------- source strategy --------------------
    def _build_source_strategy(self, parent):
        self._page_header(parent, "Source Strategy", "Policy-driven routing: daily execution, global discovery, intelligence-only, blocked and verification queues.")
        cards=ttk.Frame(parent,style="App.TFrame"); cards.pack(fill=X,pady=(0,10))
        self.strategy_vars={}
        for i,(name,lane,accent) in enumerate((("Daily project scan","DAILY_PROJECT_SCAN",GOOD),("Execution ready","__EXEC_READY__",WARN),("Global discovery","GLOBAL_DISCOVERY",INFO),("Market intelligence","MARKET_INTELLIGENCE_ONLY",INFO),("Blocked for Iran","BLOCKED_IRAN",DANGER),("Verification queue","__VERIFY__",WARN))):
            card,var=self._card(cards,name,lane,lane,accent); card.grid(row=0,column=i,sticky="nsew",padx=(0 if i==0 else 7,0)); cards.columnconfigure(i,weight=1); self.strategy_vars[lane]=var
        toolbar=ttk.Frame(parent,style="Toolbar.TFrame"); toolbar.pack(fill=X,pady=(0,8))
        ttk.Label(toolbar,text="FILTER",foreground=MUTED,background=BG,font=("Segoe UI",8,"bold")).pack(side=LEFT)
        self.strategy_search_var=StringVar(); ent=ttk.Entry(toolbar,textvariable=self.strategy_search_var,width=27,style="Search.TEntry"); ent.pack(side=LEFT,padx=(7,7)); ent.bind("<KeyRelease>",lambda _e:self.refresh_source_strategy())
        self.strategy_lane_var=StringVar(value="All lanes"); lane=ttk.Combobox(toolbar,textvariable=self.strategy_lane_var,values=("All lanes","DAILY_PROJECT_SCAN","MARKET_INTELLIGENCE_ONLY","BLACKLIST_ARCHIVE","GLOBAL_DISCOVERY","NEEDS_ANALYSIS","BLOCKED_IRAN","REVIEW"),state="readonly",width=25); lane.pack(side=LEFT); lane.bind("<<ComboboxSelected>>",lambda _e:self.refresh_source_strategy())
        self.strategy_iran_var=StringVar(value="All Iran states"); iran=ttk.Combobox(toolbar,textvariable=self.strategy_iran_var,values=("All Iran states","ALLOW","BLOCK","UNKNOWN","OPPORTUNITY_ONLY"),state="readonly",width=17); iran.pack(side=LEFT,padx=(7,0)); iran.bind("<<ComboboxSelected>>",lambda _e:self.refresh_source_strategy())
        ttk.Label(toolbar,text="Double-click = evidence drill-down",foreground=MUTED,background=BG,font=("Segoe UI",8)).pack(side=RIGHT)
        panel=self._panel(parent,8,8); panel.pack(fill=BOTH,expand=True)
        self.strategy_tree=ttk.Treeview(panel,columns=("name","family","lane","iran","region","status","verification","kyc","evidence","exec"),show="headings")
        for col,w in (("name",175),("family",115),("lane",175),("iran",75),("region",95),("status",75),("verification",125),("kyc",90),("evidence",80),("exec",65)):
            self.strategy_tree.heading(col,text=col.upper()); self.strategy_tree.column(col,width=w,minwidth=55,anchor="w",stretch=False)
        self.strategy_tree.tag_configure("daily",foreground=GOOD); self.strategy_tree.tag_configure("blocked",foreground=DANGER); self.strategy_tree.tag_configure("review",foreground=WARN); self.strategy_tree.tag_configure("ready",foreground=ACCENT)
        self.strategy_tree.pack(side=LEFT,fill=BOTH,expand=True)
        sc=ttk.Scrollbar(panel,command=self.strategy_tree.yview); self.strategy_tree.configure(yscrollcommand=sc.set); sc.pack(side=RIGHT,fill=Y)
        hsc=ttk.Scrollbar(parent,orient="horizontal",command=self.strategy_tree.xview); self.strategy_tree.configure(xscrollcommand=hsc.set); hsc.pack(fill=X,pady=(0,6))
        self.strategy_tree.bind("<Double-1>",lambda _e:self._open_strategy_source())

    def refresh_source_strategy(self):
        search=self.strategy_search_var.get().strip().lower(); lane_filter=self.strategy_lane_var.get(); iran_filter=self.strategy_iran_var.get()
        rows=self.conn.execute("SELECT name,source_role,COALESCE(source_lane,policy_lane),iran_status,region,status,source_verification_state,kyc_requirement,evidence_confidence,execution_ready,source_family,iran_eligibility FROM sources ORDER BY COALESCE(source_lane,policy_lane),name").fetchall()
        counts={k:0 for k in self.strategy_vars}
        for i in self.strategy_tree.get_children(): self.strategy_tree.delete(i)
        counts["__EXEC_READY__"]=self.conn.execute("SELECT COUNT(*) FROM sources WHERE execution_ready=1 AND source_verification_state='LIVE_CONFIRMED'").fetchone()[0]
        counts["__VERIFY__"]=self.conn.execute("SELECT COUNT(*) FROM sources WHERE source_verification_state IN ('DISCOVERED','STALE')").fetchone()[0]
        for r in rows:
            lane=str(r[2] or "REVIEW"); iran=str(r[11] or r[3] or "UNKNOWN")
            if lane_filter!="All lanes" and lane!=lane_filter: continue
            if iran_filter!="All Iran states" and iran!=iran_filter: continue
            hay=f"{r[0]} {r[1]} {r[10]} {r[4]}".lower()
            if search and search not in hay: continue
            counts[lane]=counts.get(lane,0)+1
            tag="daily" if lane=="DAILY_PROJECT_SCAN" else ("blocked" if lane=="BLOCKED_IRAN" else ("review" if lane in {"REVIEW","NEEDS_ANALYSIS","MARKET_INTELLIGENCE_ONLY"} else ("ready" if r[9] else "")))
            vals=(r[0],r[10] or "—",lane,r[3] or "UNKNOWN",r[4] or "—",r[5] or "—",r[6] or "—",r[7] or "UNKNOWN",f"{float(r[8] or 0):.0%}","YES" if r[9] else "NO")
            self.strategy_tree.insert("",END,values=vals,tags=(tag,))
        for k,v in counts.items():
            if k in self.strategy_vars: self.strategy_vars[k].set(str(v))

    def _open_strategy_source(self):
        sel=self.strategy_tree.selection()
        if not sel:return
        name=self.strategy_tree.item(sel[0],"values")[0]
        row=self.conn.execute("SELECT name,base_url,source_role,source_family,policy_lane,iran_eligibility,kyc_requirement,payment_capabilities,terms_status,source_verification_state,evidence_confidence,execution_ready,last_verified_at,payout_evidence_url,kyc_evidence_url,terms_evidence_url FROM sources WHERE name=?",(name,)).fetchone()
        if not row:return
        lines=[]
        for k,v in zip(("Name","URL","Role","Family","Lane","Iran eligibility","KYC","Payment capabilities","Terms","Verification","Evidence confidence","Execution ready","Last verified","Payout evidence","KYC evidence","Terms evidence"),row):
            if k=="Payment capabilities" and v:
                try:v=", ".join(json.loads(v))
                except Exception:pass
            lines.append(f"{k}: {v or '—'}")
        note=next((x.get("notes","") for x in self.sources if x.get("name")==name), "")
        lines.append(f"Notes: {note or '—'}")
        messagebox.showinfo("Source evidence", "\n".join(lines), parent=self.master)

    # -------------------- federation --------------------
    def _build_federation(self, parent):
        self._page_header(parent, "Federation", "Acquisition runs, response health, retries and recovery history.")
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame"); toolbar.pack(fill=X, pady=(0, 10))
        ttk.Label(toolbar, text="ACTIVE SOURCES", foreground=MUTED, background=BG, font=("Segoe UI", 8, "bold")).pack(side=LEFT)
        self.fed_count = StringVar(value="0")
        ttk.Label(toolbar, textvariable=self.fed_count, foreground=TEXT, background=BG, font=("Segoe UI", 9, "bold")).pack(side=LEFT, padx=(7, 0))
        ttk.Label(toolbar, textvariable=self.progress_var, foreground=MUTED, background=BG, font=("Segoe UI", 8)).pack(side=RIGHT)
        panel = self._panel(parent, 8, 8); panel.pack(fill=BOTH, expand=True)
        self.run_tree = ttk.Treeview(panel, columns=("source", "status", "http", "count", "started", "error"), show="headings")
        for col, width in (("source", 180), ("status", 90), ("http", 70), ("count", 80), ("started", 205), ("error", 410)):
            self.run_tree.heading(col, text=col.upper()); self.run_tree.column(col, width=width, minwidth=55, anchor="w")
        self.run_tree.tag_configure("ok", foreground=GOOD); self.run_tree.tag_configure("error", foreground=DANGER)
        self.run_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(panel, command=self.run_tree.yview); self.run_tree.configure(yscrollcommand=scroll.set); scroll.pack(side=RIGHT, fill=Y)
        self.run_empty = ttk.Label(panel, text="NO FEDERATION RUNS RECORDED YET.\n\nUse Sources → Federate active to start acquisition.", style="Empty.TLabel")
        self.run_empty.place(relx=0.5, rely=0.5, anchor="center")

    def _build_status(self, parent):
        status = ttk.Frame(parent, style="Status.TFrame", padding=(18, 6)); status.pack(fill=X)
        self.status_dot = tk.Canvas(status, width=12, height=12, bg=SURFACE, highlightthickness=0); self.status_dot.pack(side=LEFT, padx=(0, 6)); self.status_dot.create_oval(2, 2, 10, 10, fill=GOOD, outline="")
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side=LEFT, fill=X, expand=True)
        self.last_refresh_var = StringVar(value="")
        ttk.Label(status, textvariable=self.last_refresh_var, style="Status.TLabel").pack(side=RIGHT, padx=(0, 16))
        ttk.Label(status, text=f"SEPP-MarketRadar  •  v{__version__}", style="Status.TLabel").pack(side=RIGHT)

    # -------------------- data --------------------
    def refresh_all(self):
        try: self.runtime.operation_tick()
        except Exception: pass
        self.refresh_dashboard(); self.refresh_intelligence(); self.refresh_sources(); self.refresh_source_strategy(); self.refresh_opportunities(); self.refresh_runs()
        if hasattr(self, "op_opp"): self._refresh_operations()
        if hasattr(self, "daily_body"): self.refresh_daily_center()
        if hasattr(self, "action_opp"): self._refresh_action_options()
        self._refresh_sidebar_health()
        self.last_refresh_var.set("Updated " + datetime.now().strftime("%H:%M:%S"))
        self.status_var.set("Workspace refreshed")

    def refresh_dashboard(self):
        total = len(self.sources)
        active = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active'").fetchone()[0]
        health = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active' AND health >= 80").fetchone()[0]
        opps = self.conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        execute = self.conn.execute("SELECT COUNT(*) FROM opportunities WHERE eligibility='EXECUTE' AND state='DISCOVERED'").fetchone()[0]
        if "Best opportunities" in self.metrics: self.metrics["Best opportunities"].set(str(self.conn.execute("SELECT COUNT(*) FROM opportunities WHERE state='DISCOVERED'").fetchone()[0]))
        if "Application ready" in self.metrics: self.metrics["Application ready"].set(str(self.conn.execute("SELECT COUNT(*) FROM opportunities WHERE application_ready=1 AND state='DISCOVERED'").fetchone()[0]))
        if "Opened today" in self.metrics: self.metrics["Opened today"].set(str(self.conn.execute("SELECT COUNT(*) FROM application_queue WHERE status='OPENED' AND updated_at >= datetime('now','start of day')").fetchone()[0]))
        if "Submitted" in self.metrics: self.metrics["Submitted"].set(str(self.conn.execute("SELECT COUNT(*) FROM opportunities WHERE state='SUBMITTED'").fetchone()[0]))
        try:
            self.metrics["Sources"].set(str(total))
            self.metrics["Policy confirmed"].set(str(self.conn.execute("SELECT COUNT(*) FROM sources WHERE source_verification_state='LIVE_CONFIRMED'").fetchone()[0]))
            self.metrics["Auto discovery"].set(str(self.conn.execute("SELECT COUNT(*) FROM sources WHERE source_origin='dynamic_discovery'").fetchone()[0]))
            self.metrics["Blocked"].set(str(self.conn.execute("SELECT COUNT(*) FROM sources WHERE policy_lane='BLOCKED_IRAN'").fetchone()[0]))
        except Exception:
            pass
        self.fed_count.set(str(active))
        self.action_list.delete(*self.action_list.get_children())
        rows = Pipeline(self.conn, settings={'profile': self.profile}).actions()
        for row in rows[:10]:
            rank=float(row["rank_score"] or row["score"] or 0)
            tag = "high" if rank >= 80 else ""
            self.action_list.insert("", END, iid=str(row["id"]), values=(f"{rank:.0f}", row["title"], row["state"] or "DISCOVERED"), tags=(tag,))
        if not rows:
            self.action_list.insert("", END, values=("—", "No actionable opportunities yet", "WAITING"))
        self._draw_activity_chart()
        self._draw_health_chart()

    def _draw_activity_chart(self):
        c = self.activity_chart; c.delete("all")
        c.update_idletasks(); w = max(c.winfo_width(), 520); h = max(c.winfo_height(), 215)
        try:
            total = self.conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            recent = self.conn.execute("SELECT COUNT(*) FROM opportunities WHERE last_seen >= datetime('now','-7 day')").fetchone()[0]
            runs = self.conn.execute("SELECT COUNT(*) FROM federation_runs WHERE started_at >= datetime('now','-7 day')").fetchone()[0]
            evidence = self.conn.execute("SELECT COUNT(*) FROM evidence WHERE observed_at >= datetime('now','-7 day')").fetchone()[0]
        except Exception:
            total = recent = runs = evidence = 0
        values = [total, recent, evidence, runs]
        labels = ["All signals", "7d signals", "7d evidence", "7d runs"]
        maxv = max(values + [1])
        base = h - 38; top = 35; gap = 24; bw = max(38, int((w - 80 - gap * 3) / 4))
        c.create_text(12, 8, anchor="nw", text="Operating signal volume", fill=MUTED, font=("Segoe UI", 8, "bold"))
        for i, (label, val) in enumerate(zip(labels, values)):
            x = 28 + i * (bw + gap)
            bar_h = max(2, int((base - top) * (val / maxv))) if val else 2
            fill = ACCENT if i == 1 else "#cbd6ef"
            c.create_rectangle(x, base - bar_h, x + bw, base, fill=fill, outline="")
            c.create_text(x + bw / 2, base - bar_h - 8, text=str(val), fill=TEXT, font=("Segoe UI", 9, "bold"))
            c.create_text(x + bw / 2, base + 10, text=label, fill=MUTED, font=("Segoe UI", 8))
        c.create_line(20, base, w - 20, base, fill=BORDER)
        if max(values) == 0:
            c.create_text(w / 2, h / 2 - 2, text="No observations captured yet", fill=MUTED, font=("Segoe UI", 9, "bold"))
            c.create_text(w / 2, h / 2 + 17, text="Run federation to populate the intelligence timeline", fill=MUTED, font=("Segoe UI", 8))

    def _draw_health_chart(self):
        c = self.health_canvas; c.delete("all"); c.update_idletasks(); w = max(c.winfo_width(), 350); h = max(c.winfo_height(), 80)
        try:
            active = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active'").fetchone()[0]
            healthy = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active' AND health >= 80").fetchone()[0]
            degraded = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active' AND health < 50").fetchone()[0]
            unverified = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active' AND health IS NULL").fetchone()[0]
        except Exception:
            active = healthy = degraded = unverified = 0
        values=(('Active',active,ACCENT),('Healthy',healthy,GOOD),('Unverified',unverified,WARN),('Degraded',degraded,DANGER))
        x0=8; gap=10; bw=max(70,(w-16-gap*3)//4)
        for i,(label,val,fill) in enumerate(values):
            x=x0+i*(bw+gap); c.create_text(x,12,anchor='nw',text=label.upper(),fill=MUTED,font=('Segoe UI',7,'bold')); c.create_text(x,32,anchor='nw',text=str(val),fill=TEXT,font=('Segoe UI',13,'bold')); c.create_rectangle(x,58,x+bw,64,fill='#e8edf4',outline=''); ratio=(val/active) if active else 0; c.create_rectangle(x,58,x+bw*ratio,64,fill=fill,outline='')

    def refresh_intelligence(self):
        for x in self.intel_tree.get_children(): self.intel_tree.delete(x)
        scope = self.intel_scope_var.get()
        where = ""; params = []
        if scope == "High quality": where = " WHERE quality_score >= 0.75"
        elif scope == "Actionable": where = " WHERE eligibility='EXECUTE' AND state='DISCOVERED'"
        rows = self.conn.execute(f"SELECT source,title,quality_score,evidence_confidence,eligibility,last_seen,id FROM opportunities{where} ORDER BY quality_score DESC, last_seen DESC LIMIT 200", params).fetchall()
        for row in rows:
            tag = "execute" if row[4] == "EXECUTE" else ""
            self.intel_tree.insert("", END, iid=str(row[6]), values=(row[0], row[1], f"{(row[2] or 0):.2f}", f"{(row[3] or 0):.2f}", row[4] or "UNKNOWN", row[5] or ""), tags=(tag,))
        if rows: self.intel_empty.place_forget()
        else: self.intel_empty.place(relx=0.5, rely=0.5, anchor="center")

    def refresh_sources(self):
        for x in self.source_tree.get_children(): self.source_tree.delete(x)
        rows = self.conn.execute("SELECT name,source_role,COALESCE(source_lane,policy_lane),iran_status,status,verification_state,health,last_checked FROM sources ORDER BY name").fetchall()
        known = {r[0] for r in rows}
        for s in self.sources:
            if s["name"] not in known:
                rows.append((s["name"], s.get("source_role", ""), s.get("policy_lane", "REVIEW"), s.get("iran_status", "UNKNOWN"), s.get("status", "candidate"), s.get("verification_state", "unverified"), "", ""))
        filt = self.source_filter_var.get()
        for row in rows:
            if filt != "All statuses" and str(row[4]) != filt: continue
            if self.source_lane_var.get() != "All lanes" and str(row[2]) != self.source_lane_var.get(): continue
            try: health = float(row[6]) if row[6] is not None else None
            except (TypeError, ValueError): health = None
            tag = "degraded" if health is not None and health < 50 else ("healthy" if health is not None and health >= 80 else "")
            self.source_tree.insert("", END, iid=str(row[0]), values=tuple(row), tags=(tag,))
        if self.source_tree.get_children(): self.source_empty.place_forget()
        else: self.source_empty.place(relx=0.5, rely=0.5, anchor="center")

    def refresh_opportunities(self):
        for x in self.opp_tree.get_children(): self.opp_tree.delete(x)
        state = self.opp_filter_var.get()
        query = self.search_var.get().strip().lower()
        clauses = []
        params = []
        if state != 'All states':
            clauses.append('state=?'); params.append(state)
        if query:
            clauses.append('(LOWER(source) LIKE ? OR LOWER(title) LIKE ? OR LOWER(eligibility) LIKE ? OR LOWER(state) LIKE ?)')
            q = f'%{query}%'
            params.extend([q, q, q, q])
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        rows = self.conn.execute(f'SELECT id,source,title,eligibility,COALESCE(rank_score,score) AS rank_score,skill_fit,learning_value,application_speed_score,track,state FROM opportunities{where} ORDER BY COALESCE(rank_score,score) DESC LIMIT 300', params).fetchall()
        visible = list(rows)
        for row in visible:
            tag = "execute" if row[3] == "EXECUTE" else ""
            values=(row[0],row[1],row[2],row[3],f'{float(row[4] or 0):.1f}',f'{float(row[5] or 0):.2f}',f'{float(row[6] or 0):.2f}',f'{float(row[7] or 0):.2f}',row[8] or 'software_engineering',row[9] or 'DISCOVERED')
            self.opp_tree.insert("", END, iid=str(row[0]), values=values, tags=(tag,))
        if visible: self.opp_empty.place_forget()
        else: self.opp_empty.place(relx=0.5, rely=0.5, anchor="center")

    def refresh_runs(self):
        for x in self.run_tree.get_children(): self.run_tree.delete(x)
        rows = self.conn.execute("SELECT source,status,http_status,observation_count,started_at,error FROM federation_runs ORDER BY id DESC LIMIT 300").fetchall()
        for row in rows:
            tag = "ok" if str(row[1]).upper() == "OK" else "error"
            self.run_tree.insert("", END, values=tuple(row), tags=(tag,))
        if rows: self.run_empty.place_forget()
        else: self.run_empty.place(relx=0.5, rely=0.5, anchor="center")

    def _refresh_sidebar_health(self):
        try:
            active = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active'").fetchone()[0]
            unverified = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active' AND health IS NULL").fetchone()[0]
            degraded = self.conn.execute("SELECT COUNT(*) FROM sources WHERE status='active' AND health < 50").fetchone()[0]
            if unverified:
                self.sidebar_health.configure(text="Needs verification", fg=WARN)
                self.sidebar_health_detail.configure(text=f"{unverified} not checked  •  {degraded} degraded")
                self.status_dot.itemconfigure(1, fill=WARN)
            elif degraded:
                self.sidebar_health.configure(text="Needs attention", fg=DANGER)
                self.sidebar_health_detail.configure(text=f"{degraded} degraded of {active} active")
                self.status_dot.itemconfigure(1, fill=DANGER)
            else:
                self.sidebar_health.configure(text="System healthy", fg=GOOD)
                self.sidebar_health_detail.configure(text=f"{active} active source{'s' if active != 1 else ''}")
                self.status_dot.itemconfigure(1, fill=GOOD)
        except Exception:
            self.sidebar_health.configure(text="Status unavailable", fg=SIDEBAR_MUTED)
            self.sidebar_health_detail.configure(text="")

    # -------------------- interaction / drill-down --------------------
    def _focus_search(self, _event=None):
        self.global_search.focus_set(); return "break"

    def search_all(self):
        self.show_view("Opportunities")
        self.refresh_opportunities()
        query = self.search_var.get().strip()
        self.status_var.set(f"Search: {query or 'all opportunities'}")

    def _open_selected_opportunity(self, tree):
        selected = tree.selection()
        if not selected: return
        try: oid = int(selected[0])
        except (TypeError, ValueError): return
        row = self.conn.execute("SELECT id,source,title,url,description,category,budget,currency,payment,evidence_confidence,quality_score,eligibility,score,time_to_money,state,rejection_reason,first_seen,last_seen FROM opportunities WHERE id=?", (oid,)).fetchone()
        if row: self._show_opportunity_detail(row)

    def _show_opportunity_detail(self, row):
        if self._detail_window and self._detail_window.winfo_exists(): self._detail_window.destroy()
        win = Toplevel(self.master); self._detail_window = win
        win.title(f"Opportunity #{row[0]}  |  SEPP-MarketRadar"); win.geometry("860x650"); win.minsize(720, 560); win.configure(bg=BG); win.transient(self.master)
        outer = ttk.Frame(win, style="App.TFrame", padding=24); outer.pack(fill=BOTH, expand=True)
        head = ttk.Frame(outer, style="App.TFrame"); head.pack(fill=X)
        ttk.Label(head, text=row[2] or "Untitled opportunity", foreground=TEXT, background=BG, font=("Segoe UI", 18, "bold"), wraplength=760).pack(side=LEFT, fill=X, expand=True, anchor="w")
        ttk.Button(head, text="Close", command=win.destroy, style="Ghost.TButton").pack(side=RIGHT, padx=(12, 0))
        meta = ttk.Frame(outer, style="App.TFrame"); meta.pack(fill=X, pady=(13, 14))
        self._detail_pill(meta, "Score", f"{row[12] or 0:.1f}", ACCENT_SOFT)
        self._detail_pill(meta, "Quality", f"{row[10] or 0:.2f}", INFO_SOFT)
        self._detail_pill(meta, "Confidence", f"{row[9] or 0:.2f}", INFO_SOFT)
        self._detail_pill(meta, "State", row[14] or "UNKNOWN", SURFACE)
        self._detail_pill(meta, "Eligibility", row[11] or "UNKNOWN", GOOD_SOFT if row[11] == "EXECUTE" else WARN_SOFT)
        grid = ttk.Frame(outer, style="App.TFrame"); grid.pack(fill=BOTH, expand=True); grid.columnconfigure(0, weight=2); grid.columnconfigure(1, weight=3); grid.rowconfigure(0, weight=1)
        source_panel = self._panel(grid, 15, 13); source_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        ttk.Label(source_panel, text="Evidence & provenance", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(source_panel, text=f"Source  {row[1] or 'unknown'}", style="PanelSub.TLabel").pack(anchor="w", pady=(8, 3))
        ttk.Label(source_panel, text=row[3] or "No source URL", foreground=ACCENT, background=SURFACE, font=("Segoe UI", 8), wraplength=300, justify=LEFT).pack(anchor="w")
        ttk.Label(source_panel, text=f"First seen  {row[16] or '—'}\nLast seen   {row[17] or '—'}\nCategory    {row[5] or '—'}\nBudget      {row[6] or '—'} {row[7] or ''}\nPayment     {row[8] or '—'}", style="PanelSub.TLabel", justify=LEFT).pack(anchor="w", pady=(16, 0))
        body = self._panel(grid, 15, 13); body.grid(row=0, column=1, sticky="nsew")
        ttk.Label(body, text="Captured intelligence", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(body, text="Description", style="PanelSub.TLabel").pack(anchor="w", pady=(8, 3))
        widget = tk.Text(body, wrap="word", bg=SURFACE, fg=TEXT, relief="flat", bd=0, font=("Segoe UI", 10), padx=3, pady=3)
        widget.insert("1.0", row[4] or "No description captured."); widget.configure(state="disabled"); widget.pack(fill=BOTH, expand=True)

    def _detail_pill(self, parent, label, value, bg):
        box = tk.Frame(parent, bg=bg, padx=10, pady=6, highlightthickness=1, highlightbackground=BORDER); box.pack(side=LEFT, padx=(0, 7))
        tk.Label(box, text=label.upper(), bg=bg, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        tk.Label(box, text=value, bg=bg, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(1, 0))

    def _open_source_detail(self):
        selected = self.source_tree.selection()
        if not selected: return
        name = selected[0]
        row = self.conn.execute("SELECT name,base_url,source_kind,acquisition,adapter,status,verification_state,access_scope,terms_status,health,failure_count,last_error,next_retry_at,last_checked FROM sources WHERE name=?", (name,)).fetchone()
        if not row: return
        win = Toplevel(self.master); win.title(f"Source: {name}"); win.geometry("720x560"); win.minsize(650, 500); win.configure(bg=BG); win.transient(self.master)
        outer = ttk.Frame(win, style="App.TFrame", padding=24); outer.pack(fill=BOTH, expand=True)
        head = ttk.Frame(outer, style="App.TFrame"); head.pack(fill=X)
        ttk.Label(head, text=name, foreground=TEXT, background=BG, font=("Segoe UI", 18, "bold")).pack(side=LEFT)
        ttk.Button(head, text="Close", command=win.destroy, style="Ghost.TButton").pack(side=RIGHT)
        ttk.Label(outer, text="Source contract and runtime health", foreground=MUTED, background=BG, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 15))
        panel = self._panel(outer, 16, 14); panel.pack(fill=BOTH, expand=True)
        fields = ("Base URL", "Kind", "Acquisition", "Adapter", "Status", "Verification", "Access", "Terms", "Health", "Failures", "Last error", "Next retry", "Last checked")
        for label, value in zip(fields, row[1:]):
            line = ttk.Frame(panel, style="Surface.TFrame"); line.pack(fill=X, pady=3)
            ttk.Label(line, text=label.upper(), foreground=MUTED, background=SURFACE, font=("Segoe UI", 7, "bold"), width=16).pack(side=LEFT)
            ttk.Label(line, text=str(value if value not in (None, "") else "—"), foreground=TEXT, background=SURFACE, font=("Segoe UI", 9), wraplength=500).pack(side=LEFT, fill=X, expand=True)

    def _on_resize(self, _event=None):
        try:
            if hasattr(self, "activity_chart"): self._draw_activity_chart()
            if hasattr(self, "health_canvas"): self._draw_health_chart()
        except Exception:
            pass

    # -------------------- background work --------------------
    def _set_verification_ui(self, running):
        self.verify_button.config(state="disabled" if running else "normal")
        self.cancel_button.config(state="normal" if running else "disabled")

    def verify_registry(self):
        if self._worker and self._worker.is_alive(): return
        self._cancel_event.clear(); self._set_verification_ui(True)
        self.status_var.set("Verifying source registry in background…"); self.source_status.set(""); self.progress_var.set("Starting…")
        names = [s["name"] for s in self.sources if s.get("status") != "disabled"]
        self._worker = threading.Thread(target=self._verify_worker, args=(names,), daemon=True); self._worker.start(); self.master.after(100, self._poll_verification)

    def _verify_worker(self, names):
        # Tk callbacks run on the UI thread, but verification is intentionally a
        # background operation. SQLite connections are thread-affine by default,
        # so never reuse self.conn/self.runtime from the UI thread here.
        worker_conn = None
        try:
            worker_conn = connect(data_root() / Path(self.settings.get("db", "data/marketradar.db")).name)
            worker_runtime = MarketRadarRuntime(
                worker_conn, self.sources, None,
                http_timeout=self.settings.get("http_timeout", 10),
                settings=self.settings,
            )
            def progress(result): self._queue.put(("progress", result))
            results = worker_runtime.verify_source_policies(
                names, progress_callback=progress, stop_event=self._cancel_event, persist=True
            )
            self._queue.put(("done", results))
        except Exception as exc:
            logger.exception("Registry verification failed"); self._queue.put(("error", exc))
        finally:
            if worker_conn is not None:
                worker_conn.close()

    def _poll_verification(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "progress": self._queue_progress(payload)
                elif kind == "done":
                    self.conn.commit(); self._finish_verification(payload); return
                elif kind == "error":
                    self._set_verification_ui(False); self.status_var.set("Verification failed; see logs."); messagebox.showerror("Verification error", str(payload)); return
        except queue.Empty: pass
        if self._worker and self._worker.is_alive(): self.master.after(100, self._poll_verification)
        else:
            self._set_verification_ui(False); self.status_var.set("Verification stopped unexpectedly; see logs.")

    def _queue_progress(self, result):
        status = "BLOCK" if result.get("iran_eligibility")=="BLOCK" else ("LIVE" if result.get("source_verification_state")=="LIVE_CONFIRMED" else "UNKNOWN"); self.progress_var.set(f"{result['source']}  •  {status}")

    def _finish_verification(self, results):
        ok = sum(r.get("source_verification_state") == "LIVE_CONFIRMED" for r in results); errors = sum(r.get("source_verification_state") == "DEAD" for r in results); cancelled = self._cancel_event.is_set(); self._set_verification_ui(False)
        self.source_status.set(f"{ok} OK  •  {errors} errors" + ("  •  cancelled" if cancelled else "")); self.progress_var.set(f"{len(results)} completed"); self.refresh_all()

    def cancel_verification(self):
        self._cancel_event.set(); self.status_var.set("Cancellation requested…")

    def verify_active_sources(self):
        if self._worker and self._worker.is_alive(): return
        active = [s["name"] for s in self.sources if s.get("status") == "active"]
        self._cancel_event.clear(); self._set_verification_ui(True); self.status_var.set("Federating active sources in background…"); self.progress_var.set(f"0 / {len(active)}")
        self._worker = threading.Thread(target=self._federate_worker, args=(active,), daemon=True); self._worker.start(); self.master.after(100, self._poll_federation)

    def _federate_worker(self, names):
        worker_conn = None
        results = []
        try:
            worker_conn = connect(data_root() / Path(self.settings.get("db", "data/marketradar.db")).name)
            worker_runtime = MarketRadarRuntime(worker_conn, self.sources, None, http_timeout=self.settings.get("http_timeout", 10), settings=self.settings)
            for name in names:
                if self._cancel_event.is_set(): break
                try: result = worker_runtime.federate(name)
                except Exception as exc: logger.exception("Federation failed for %s", name); result = {"source": name, "status": "ERROR", "error": str(exc)}
                results.append(result); self._queue.put(("fed_progress", result))
            self._queue.put(("fed_done", results))
        except Exception as exc:
            logger.exception("Federation worker failed")
            self._queue.put(("fed_error", exc))
        finally:
            if worker_conn is not None: worker_conn.close()

    def _poll_federation(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "fed_progress": self.progress_var.set(f"{payload['source']}  •  {'OK' if payload.get('status') == 'OK' else 'ERROR'}")
                elif kind == "fed_done":
                    ok = sum(x.get("status") == "OK" for x in payload); self._set_verification_ui(False); self.source_status.set(f"{ok} OK  •  {len(payload)-ok} errors" + ("  •  cancelled" if self._cancel_event.is_set() else "")); self.refresh_all(); return
                elif kind == "fed_error":
                    self._set_verification_ui(False); self.status_var.set("Federation failed; see logs."); messagebox.showerror("Federation error", str(payload)); return
        except queue.Empty: pass
        if self._worker and self._worker.is_alive(): self.master.after(100, self._poll_federation)

    def close(self):
        self._cancel_event.set()
        try:
            self.conn.close()
        finally:
            try:
                close_logging()
            finally:
                self.master.destroy()


def smoke_test():
    root = None
    conn = None
    try:
        root, settings, sources, conn, runtime = open_runtime()
        target_path = root / "config" / "source_targets.json"
        target = json.loads(target_path.read_text(encoding="utf-8"))["target_registered_sources"]
        contracts = conn.execute("SELECT COUNT(*) FROM source_contracts").fetchone()[0]
        if not __version__:
            raise RuntimeError("SMOKE_VERSION_MISSING")
        if target < 500:
            raise RuntimeError(f"SMOKE_TARGET_BELOW_MINIMUM target={target}")
        if len(sources) < 5:
            raise RuntimeError(f"SMOKE_SOURCE_REGISTRY_TOO_SMALL count={len(sources)}")
        if runtime is None:
            raise RuntimeError("SMOKE_RUNTIME_MISSING")
        if contracts != len(sources):
            raise RuntimeError(f"SMOKE_SOURCE_CONTRACT_MISMATCH sources={len(sources)} contracts={contracts}")
        logger.info("Installed/portable smoke PASS version=%s root=%s sources=%s contracts=%s target=%s",
                    __version__, root, len(sources), contracts, target)
        return 0
    except Exception:
        logger.exception("Desktop smoke test FAILED root=%s", root)
        return 1
    finally:
        if conn is not None:
            conn.close()


def ui_smoke_test():
    root = Tk()
    app = None
    try:
        app = MarketRadarDesktop(root); root.update_idletasks(); root.update()
        assert len(app._views) == 13
        assert app.master.title().endswith(__version__)
        assert set(app._nav_buttons) == set(MarketRadarDesktop.NAV)
        assert app.metrics["Sources"].get() != ""
        return 0
    finally:
        try:
            if app: app.close()
            else: root.destroy()
        except Exception:
            root.destroy()


def worker_tick():
    root, settings, sources, conn, runtime = open_runtime()
    try:
        result = runtime.operation_tick()
        print(json.dumps(result, ensure_ascii=False, default=str))
        return 0
    finally:
        conn.close()

def scheduled_cycle():
    from tools.scheduled_cycle import main as cycle_main
    cycle_main()
    return 0

def main():
    install_exception_logging()
    if "--smoke-test" in sys.argv: raise SystemExit(smoke_test())
    if "--ui-smoke-test" in sys.argv: raise SystemExit(ui_smoke_test())
    if "--operation-tick" in sys.argv: raise SystemExit(worker_tick())
    if "--final-verify" in sys.argv:
        from .final_readiness import run_final_verification
        result=run_final_verification(); print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(0 if result.get('pass') else 2)
    if "--scheduled-cycle" in sys.argv: raise SystemExit(scheduled_cycle())
    root = Tk(); MarketRadarDesktop(root); root.mainloop()
