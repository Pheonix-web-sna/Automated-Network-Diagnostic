"""
main.py — IntelliNet Application (Phase 3)
Intelligent Network Health & Diagnostics System

Architecture:
  - Multi-page responsive desktop interface using Tkinter.
  - Sidebar navigation: Dashboard, Diagnostics, Network Info, Performance,
    Recommendations, History, Monitoring.
  - Multi-threaded diagnostic engine with thread-safe queue.Queue event loop.
  - Background monitoring thread with configurable scan interval.
  - SQLite persistent storage for diagnostic history, metrics, and events.
  - Automatic network degradation detection with alert system.
  - Zero hardcoding — all data is retrieved live from the local network stack.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import sys
import os

# Ensure local imports work regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg
import network_diagnostics as nd
import performance as perf
import collector
import db_manager as db
from models import PerformanceMetrics, WiFiInfo, DiagnosticResult

# Import View Components
from sidebar import Sidebar
from dashboard_view import DashboardView
from diagnostics_view import DiagnosticsView
from network_info_view import NetworkInfoView
from performance_view import PerformanceView
from recommendations_view import RecommendationsView
from history_view import HistoryView
from monitoring_view import MonitoringView


class IntelliNetApp:
    """
    IntelliNet Application Coordinator (Phase 3).
    Manages pages, navigation, thread-safe async diagnostic worker,
    live UI synchronization, background monitoring, database persistence,
    and degradation detection across all dashboard views.
    """

    PAGE_TITLES = {
        "dashboard": ("Dashboard", "Real-Time System Overview & Network Health Score"),
        "diagnostics": ("Live Diagnostics", "8-Step Layer-by-Layer Automated Network Diagnostic Engine"),
        "network_info": ("Network Information", "Physical Adapter, IP Addressing, Wi-Fi Link & Traffic Counters"),
        "performance": ("Performance Analytics", "Multi-Ping Latency, Jitter, Packet Loss & Usability Assessment"),
        "recommendations": ("Recommendations & RCA", "Root Cause Analysis, Confidence Metric & Remediation Steps"),
        "history": ("Diagnostic History", "Historical Trends, Charts & Session Archive (SQLite)"),
        "monitoring": ("Network Monitoring", "Continuous Background Scanning, Event Log & Degradation Alerts"),
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{cfg.APP_NAME} — {cfg.APP_SUBTITLE}")
        self.root.geometry(f"{cfg.WINDOW_WIDTH}x{cfg.WINDOW_HEIGHT}")
        self.root.minsize(cfg.WINDOW_MIN_WIDTH, cfg.WINDOW_MIN_HEIGHT)
        self.root.configure(bg=cfg.COLOR_BG)

        self.is_running = False
        self.diagnostic_data: DiagnosticResult = None
        self.ui_queue = queue.Queue()

        # Monitoring state
        self._monitor_active = False
        self._monitor_thread: threading.Thread = None
        self._monitor_stop_event = threading.Event()
        self._monitor_scan_count = 0
        self._monitor_alert_count = 0

        self._setup_ttk_styles()
        self._build_layout()
        self._poll_ui_queue()

        # Log application startup
        db.log_event("SYSTEM", "IntelliNet application started", severity="INFO")

        # Trigger automatic initial network scan on launch
        self.root.after(300, self.start_diagnostic)

    # ── TTK Styles ──────────────────────────────────────────────────────────

    def _setup_ttk_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Sleek Sky-Blue Progressbar
        style.configure(
            "Intellinet.Horizontal.TProgressbar",
            troughcolor=cfg.COLOR_PANEL_DARK,
            background=cfg.COLOR_ACCENT,
            darkcolor=cfg.COLOR_ACCENT,
            lightcolor=cfg.COLOR_ACCENT,
            bordercolor=cfg.COLOR_PANEL_ALT,
            thickness=5,
        )

        style.configure(
            "Vertical.TScrollbar",
            troughcolor=cfg.COLOR_PANEL_DARK,
            background=cfg.COLOR_PANEL_ALT,
            arrowcolor=cfg.COLOR_TEXT_MUTED,
            relief="flat",
        )

    # ── Layout Construction ──────────────────────────────────────────────────

    def _build_layout(self):
        # Master container
        self.main_container = tk.Frame(self.root, bg=cfg.COLOR_BG)
        self.main_container.pack(fill="both", expand=True)

        # 1. Left Sidebar
        self.sidebar = Sidebar(
            self.main_container,
            on_navigate=self.show_page,
        )
        self.sidebar.pack(side="left", fill="y")

        # 2. Right Content Area (Header + Switchable Pages)
        self.content_area = tk.Frame(self.main_container, bg=cfg.COLOR_BG)
        self.content_area.pack(side="left", fill="both", expand=True)

        self._build_header()
        self._build_pages()

    def _build_header(self):
        """Top Application Header with dynamic titles, status message, and Run CTA."""
        self.header_frame = tk.Frame(self.content_area, bg=cfg.COLOR_PANEL, padx=24, pady=12)
        self.header_frame.pack(fill="x")

        # Left: Titles
        title_box = tk.Frame(self.header_frame, bg=cfg.COLOR_PANEL)
        title_box.pack(side="left", fill="y")

        self.lbl_page_title = tk.Label(
            title_box,
            text="Dashboard",
            font=("Segoe UI", 16, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
        )
        self.lbl_page_title.pack(anchor="w")

        self.lbl_page_subtitle = tk.Label(
            title_box,
            text="Real-Time System Overview & Network Health Score",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        )
        self.lbl_page_subtitle.pack(anchor="w", pady=(1, 0))

        # Right: Action CTA & Status Indicator
        action_box = tk.Frame(self.header_frame, bg=cfg.COLOR_PANEL)
        action_box.pack(side="right", fill="y")

        self.lbl_status = tk.Label(
            action_box,
            text="Ready to scan",
            font=("Segoe UI", 9),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        )
        self.lbl_status.pack(side="left", padx=(0, 16))

        self.btn_run = tk.Button(
            action_box,
            text="▶  Run Diagnostics",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_ACCENT,
            fg="#FFFFFF",
            activebackground=cfg.COLOR_ACCENT_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.start_diagnostic,
            padx=16,
            pady=7,
        )
        self.btn_run.pack(side="left")

        # Top Progress Bar
        self.progress_bar = ttk.Progressbar(
            self.content_area,
            style="Intellinet.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.progress_bar.pack(fill="x")

    def _build_pages(self):
        """Instantiate all 7 views and keep them ready for instant switching."""
        self.page_container = tk.Frame(self.content_area, bg=cfg.COLOR_BG)
        self.page_container.pack(fill="both", expand=True)

        self.pages = {}

        # 1. Dashboard View
        self.pages["dashboard"] = DashboardView(
            self.page_container,
            on_view_recommendations=lambda: self.show_page("recommendations"),
        )

        # 2. Diagnostics View
        self.pages["diagnostics"] = DiagnosticsView(self.page_container)

        # 3. Network Information View
        self.pages["network_info"] = NetworkInfoView(self.page_container)

        # 4. Performance View
        self.pages["performance"] = PerformanceView(self.page_container)

        # 5. Recommendations View
        self.pages["recommendations"] = RecommendationsView(
            self.page_container,
            on_retest=self.start_diagnostic,
        )

        # 6. History View (Phase 3)
        self.pages["history"] = HistoryView(self.page_container)

        # 7. Monitoring View (Phase 3)
        self.pages["monitoring"] = MonitoringView(
            self.page_container,
            on_start_monitor=self._start_monitoring,
            on_stop_monitor=self._stop_monitoring,
        )

        # Show initial page
        self.current_page = None
        self.show_page("dashboard")

    def show_page(self, page_id: str):
        """Switch between the 7 dashboard pages with smooth transitions."""
        if page_id not in self.pages:
            return

        # Hide current page
        if self.current_page and self.current_page in self.pages:
            self.pages[self.current_page].pack_forget()

        # Show target page
        self.pages[page_id].pack(fill="both", expand=True)
        self.current_page = page_id

        # Update Sidebar active state
        self.sidebar.set_active(page_id)

        # Update Header title & subtitle
        title, sub = self.PAGE_TITLES.get(page_id, ("IntelliNet", ""))
        self.lbl_page_title.config(text=title)
        self.lbl_page_subtitle.config(text=sub)

        # Re-sync data if available
        if self.diagnostic_data:
            self.pages[page_id].update_data(self.diagnostic_data)

    # ── Thread-Safe Event Queue ──────────────────────────────────────────────

    def _poll_ui_queue(self):
        """Process pending UI updates from worker threads on the main GUI thread."""
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                try:
                    fn()
                except Exception:
                    pass
        except queue.Empty:
            pass
        self.root.after(40, self._poll_ui_queue)

    def _dispatch_ui(self, fn):
        """Post a callable onto the UI queue."""
        self.ui_queue.put(fn)

    # ── Diagnostic Execution Engine ──────────────────────────────────────────

    def start_diagnostic(self):
        """Trigger background diagnostic run."""
        if self.is_running:
            return

        self.is_running = True
        self.btn_run.config(state="disabled", bg=cfg.COLOR_PANEL_ALT)
        self.progress_bar["value"] = 0
        self.lbl_status.config(text="Scanning network...", fg=cfg.COLOR_WARNING)

        # Reset Diagnostics page table
        diag_view: DiagnosticsView = self.pages["diagnostics"]
        diag_view.reset_table()
        diag_view.append_log("Starting automated diagnostic sequence...")

        # Update sidebar footer
        self.sidebar.update_status(
            self.diagnostic_data.adapter.name if self.diagnostic_data else "Scanning",
            is_running=True,
            is_healthy=True,
        )

        threading.Thread(target=self._run_diagnostic_worker, daemon=True).start()

    def _run_diagnostic_worker(self):
        """
        Worker thread: sequentially executes all real network probes,
        posting live progress and log updates to the UI queue.
        """
        try:
            diag_view: DiagnosticsView = self.pages["diagnostics"]

            def update_step(step_idx, status_text, sym, details, tag, log_msg):
                self._dispatch_ui(lambda: diag_view.set_row_result(step_idx, sym, details, tag))
                self._dispatch_ui(lambda: diag_view.append_log(log_msg))

            def set_status(text, col=cfg.COLOR_TEXT_PRIMARY):
                self._dispatch_ui(lambda: self.lbl_status.config(text=text, fg=col))

            def set_progress(val):
                self._dispatch_ui(lambda: self.progress_bar.config(value=val))

            # ── Step 1: Network Adapter ──────────────────────────────
            set_status("Detecting network adapter...", cfg.COLOR_ACCENT)
            set_progress(10)
            self._dispatch_ui(lambda: diag_view.set_row_testing(0))
            time.sleep(0.15)

            adapter_res = nd.get_active_adapter()
            a_ok, a_name, a_det = adapter_res
            sym = "✓" if a_ok else "✗"
            tag = "pass" if a_ok else "fail"
            update_step(0, "Active" if a_ok else "Failed", sym, a_det, tag,
                        f"Step 1: Network Adapter -> {a_name} ({'UP' if a_ok else 'DOWN'})")

            # ── Step 2: IPv4 Address ─────────────────────────────────
            set_status("Detecting IPv4 configuration...", cfg.COLOR_ACCENT)
            set_progress(24)
            self._dispatch_ui(lambda: diag_view.set_row_testing(1))
            time.sleep(0.15)

            ip_res = nd.get_ipv4_address(a_name if a_ok else None)
            ip_ok, ip_addr, ip_det = ip_res
            sym = "✓" if ip_ok else "✗"
            tag = "pass" if ip_ok else "fail"
            update_step(1, "Assigned" if ip_ok else "Failed", sym, ip_det, tag,
                        f"Step 2: IPv4 Address -> {ip_addr}")

            # ── Step 3: Default Gateway ──────────────────────────────
            set_status("Checking default gateway reachability...", cfg.COLOR_ACCENT)
            set_progress(38)
            self._dispatch_ui(lambda: diag_view.set_row_testing(2))
            time.sleep(0.15)

            gw_res = nd.check_gateway()
            gw_has, gw_ip, gw_reach, gw_disp = gw_res
            gw_ok = gw_has and gw_reach
            sym = "✓" if gw_ok else "✗"
            tag = "pass" if gw_ok else ("warn" if gw_has else "fail")
            update_step(2, "Reachable" if gw_ok else "Unreachable", sym, gw_disp, tag,
                        f"Step 3: Default Gateway -> {gw_ip} ({'Reachable' if gw_reach else 'Unreachable'})")

            # ── Step 4: Wi-Fi Parameters ─────────────────────────────
            set_status("Querying Wi-Fi & physical link parameters...", cfg.COLOR_ACCENT)
            set_progress(50)
            self._dispatch_ui(lambda: diag_view.set_row_testing(3))
            time.sleep(0.15)

            wifi_info: WiFiInfo = nd.get_wifi_info()
            w_sym = "✓" if wifi_info.is_wifi else "ℹ"
            w_tag = "pass" if wifi_info.is_wifi else "info"
            w_det = wifi_info.display if wifi_info.display else ("Connected" if a_ok else "No Link")
            update_step(3, "Connected", w_sym, w_det, w_tag,
                        f"Step 4: Wi-Fi / Link -> {w_det}")

            # ── Step 5: DNS Resolution ───────────────────────────────
            set_status(f"Resolving DNS ({cfg.DNS_TEST_DOMAIN})...", cfg.COLOR_ACCENT)
            set_progress(64)
            self._dispatch_ui(lambda: diag_view.set_row_testing(4))
            time.sleep(0.15)

            dns_res = nd.check_dns(cfg.DNS_TEST_DOMAIN)
            dns_ok, dns_status, dns_det = dns_res
            sym = "✓" if dns_ok else "✗"
            tag = "pass" if dns_ok else "fail"
            update_step(4, dns_status, sym, dns_det, tag,
                        f"Step 5: DNS Resolution -> {dns_det}")

            # ── Step 6: Internet Connectivity ────────────────────────
            set_status(f"Testing WAN internet connectivity ({cfg.PING_TARGET_PRIMARY})...", cfg.COLOR_ACCENT)
            set_progress(76)
            self._dispatch_ui(lambda: diag_view.set_row_testing(5))
            time.sleep(0.15)

            inet_res = nd.check_internet(cfg.PING_TARGET_PRIMARY)
            inet_ok, inet_status, inet_det = inet_res
            sym = "✓" if inet_ok else "✗"
            tag = "pass" if inet_ok else "fail"
            update_step(5, inet_status, sym, inet_det, tag,
                        f"Step 6: Internet Access -> {inet_det}")

            # ── Step 7 & 8: Performance Measurement ──────────────────
            set_status("Measuring latency & packet loss (4 ICMP pings)...", cfg.COLOR_TEAL)
            set_progress(88)
            self._dispatch_ui(lambda: diag_view.set_row_testing(6))
            self._dispatch_ui(lambda: diag_view.set_row_testing(7))

            target = cfg.PING_TARGET_PRIMARY if inet_ok else (gw_ip if gw_reach else "")
            if target:
                perf_metrics = perf.measure_performance(target, cfg.PING_COUNT, cfg.PING_TIMEOUT_MS)
            else:
                perf_metrics = PerformanceMetrics(
                    avg_latency_ms=-1, min_latency_ms=-1, max_latency_ms=-1,
                    jitter_ms=-1, packet_loss_pct=100.0, ping_count=0,
                    target_host="", error="No reachable host for performance test"
                )

            # Update Latency Row (Step 7)
            if perf_metrics.is_valid:
                lat_tag = "pass" if perf_metrics.avg_latency_ms <= cfg.LATENCY_FAIR_MS else "warn"
                lat_sym = "✓" if perf_metrics.avg_latency_ms <= cfg.LATENCY_FAIR_MS else "⚠"
                update_step(6, f"{perf_metrics.avg_latency_ms:.0f} ms", lat_sym, perf_metrics.latency_display, lat_tag,
                            f"Step 7: Latency -> {perf_metrics.latency_display}")
            else:
                update_step(6, "N/A", "—", "Measurement unavailable", "muted", "Step 7: Latency -> Unavailable")

            # Update Packet Loss Row (Step 8)
            if perf_metrics.is_valid:
                loss_tag = "pass" if perf_metrics.packet_loss_pct <= cfg.LOSS_FAIR_PCT else "warn"
                loss_sym = "✓" if perf_metrics.packet_loss_pct <= cfg.LOSS_FAIR_PCT else "⚠"
                update_step(7, f"{perf_metrics.packet_loss_pct:.0f}%", loss_sym, perf_metrics.loss_display, loss_tag,
                            f"Step 8: Packet Loss -> {perf_metrics.loss_display}")
            else:
                update_step(7, "N/A", "—", "Measurement unavailable", "muted", "Step 8: Packet Loss -> Unavailable")

            # ── Final Assembly & RCA Evaluation ──────────────────────
            set_progress(95)
            diag_result = collector.build_diagnostic_result(
                adapter_res, ip_res, gw_res, wifi_info, dns_res, inet_res, perf_metrics
            )
            set_progress(100)

            # ── Save to Database (Phase 3) ───────────────────────────
            try:
                session_id = db.save_diagnostic(diag_result)
                db.log_event(
                    "DIAGNOSTIC",
                    f"Scan completed — Health: {diag_result.health.score}/100 "
                    f"({diag_result.health.label}), RCA: {diag_result.rca.overall_status}",
                    severity="INFO" if diag_result.health.score >= 70 else "WARNING",
                )
            except Exception as e:
                db.log_event("ERROR", f"Failed to save diagnostic: {str(e)}", severity="CRITICAL")

            # ── Degradation Detection (Phase 3) ──────────────────────
            try:
                degradation_alerts = db.detect_degradation(diag_result)
                if degradation_alerts:
                    for alert in degradation_alerts:
                        db.log_event("DEGRADATION", alert, severity="WARNING")
                    self._dispatch_ui(
                        lambda: self._show_degradation_alerts(degradation_alerts)
                    )
            except Exception:
                pass

            # Finalize on UI thread
            self._dispatch_ui(lambda: self._finalize_scan(diag_result))

        except Exception as e:
            self._dispatch_ui(lambda: self._handle_error(str(e)))

    def _finalize_scan(self, result: DiagnosticResult):
        """Update all views, reset buttons, and refresh sidebar footer."""
        self.is_running = False
        self.diagnostic_data = result
        self.btn_run.config(state="normal", bg=cfg.COLOR_ACCENT)

        # Status text
        hlth = result.health
        self.lbl_status.config(
            text=f"Health: {hlth.score}/100 ({hlth.label}) — {result.rca.overall_status}",
            fg=hlth.color,
        )

        # Push data to all 7 views
        for page in self.pages.values():
            try:
                page.update_data(result)
            except Exception:
                pass

        # Update sidebar footer
        self.sidebar.update_status(
            result.adapter.name,
            is_running=False,
            is_healthy=(hlth.score >= 70),
        )

        # Append final completion to console log
        diag_view: DiagnosticsView = self.pages["diagnostics"]
        diag_view.append_log(
            f"Diagnostic scan completed successfully. Health Score: {hlth.score}/100 ({hlth.label})."
        )

    def _handle_error(self, err_msg: str):
        """Handle worker errors safely on the main thread."""
        self.is_running = False
        self.btn_run.config(state="normal", bg=cfg.COLOR_ACCENT)
        self.lbl_status.config(text=f"Error: {err_msg}", fg=cfg.COLOR_FAILURE)

        diag_view: DiagnosticsView = self.pages["diagnostics"]
        diag_view.append_log(f"ERROR: Diagnostic worker exception: {err_msg}")

        db.log_event("ERROR", f"Diagnostic error: {err_msg}", severity="CRITICAL")

    def _show_degradation_alerts(self, alerts: list):
        """Show degradation alerts on the monitoring page."""
        mon_view: MonitoringView = self.pages["monitoring"]
        mon_view.show_alerts(alerts)
        self._monitor_alert_count += len(alerts)
        mon_view.update_alert_count(self._monitor_alert_count)

    # ═══════════════════════════════════════════════════════════════
    # BACKGROUND MONITORING ENGINE (Phase 3)
    # ═══════════════════════════════════════════════════════════════

    def _start_monitoring(self, interval_sec: int):
        """Start the background monitoring thread."""
        if self._monitor_active:
            return

        self._monitor_active = True
        self._monitor_stop_event.clear()
        self._monitor_scan_count = 0
        self._monitor_alert_count = 0

        db.log_event("MONITORING", f"Background monitoring started (interval: {interval_sec}s)", severity="INFO")

        mon_view: MonitoringView = self.pages["monitoring"]
        mon_view.append_event(f"Monitoring started — scanning every {interval_sec}s", "success")

        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_sec,),
            daemon=True,
        )
        self._monitor_thread.start()

    def _stop_monitoring(self):
        """Signal the monitoring thread to stop."""
        if not self._monitor_active:
            return

        self._monitor_active = False
        self._monitor_stop_event.set()

        db.log_event("MONITORING", "Background monitoring stopped by user", severity="INFO")

        mon_view: MonitoringView = self.pages["monitoring"]
        mon_view.append_event(
            f"Monitoring stopped — {self._monitor_scan_count} scans completed, "
            f"{self._monitor_alert_count} alerts",
            "info",
        )

    def _monitoring_loop(self, interval_sec: int):
        """
        Background monitoring loop.
        Runs collect_diagnostic() at the specified interval,
        saves results, checks for degradation, and updates the UI.

        The loop sleeps in 1-second increments to allow responsive stop.
        """
        while not self._monitor_stop_event.is_set():
            # Countdown before next scan
            for remaining in range(interval_sec, 0, -1):
                if self._monitor_stop_event.is_set():
                    return
                self._dispatch_ui(
                    lambda r=remaining: self.pages["monitoring"].update_next_scan(r)
                )
                time.sleep(1)

            if self._monitor_stop_event.is_set():
                return

            # ── Run silent diagnostic ──────────────────────────────
            try:
                self._dispatch_ui(
                    lambda: self.pages["monitoring"].append_event("Running background scan...", "info")
                )

                result = collector.collect_diagnostic()
                self._monitor_scan_count += 1

                # Save to database
                db.save_diagnostic(result)
                db.log_event(
                    "MONITOR_SCAN",
                    f"Monitor scan #{self._monitor_scan_count} — "
                    f"Health: {result.health.score}/100, "
                    f"Latency: {result.performance.avg_latency_ms:.0f}ms",
                    severity="INFO" if result.health.score >= 70 else "WARNING",
                )

                # Degradation detection
                alerts = db.detect_degradation(result)
                if alerts:
                    for alert in alerts:
                        db.log_event("DEGRADATION", alert, severity="WARNING")

                # Update UI from main thread
                scan_num = self._monitor_scan_count
                health_score = result.health.score
                health_label = result.health.label

                def _update_monitor_ui(
                    _result=result, _alerts=alerts,
                    _scan_num=scan_num, _health=health_score, _label=health_label
                ):
                    mon_view: MonitoringView = self.pages["monitoring"]
                    mon_view.update_scan_count(_scan_num)
                    mon_view.update_last_scan_time(
                        _result.timestamp.strftime("%H:%M:%S")
                    )
                    mon_view.append_event(
                        f"Scan #{_scan_num} complete — Health: {_health}/100 ({_label})",
                        "success" if _health >= 70 else "warning",
                    )

                    if _alerts:
                        mon_view.show_alerts(_alerts)
                        self._monitor_alert_count += len(_alerts)
                        mon_view.update_alert_count(self._monitor_alert_count)
                        for a in _alerts:
                            mon_view.append_event(f"DEGRADATION: {a}", "degradation")
                    else:
                        mon_view.show_alerts([])

                    # Update main diagnostic data and all views
                    self.diagnostic_data = _result
                    for page in self.pages.values():
                        try:
                            page.update_data(_result)
                        except Exception:
                            pass

                    # Update sidebar
                    self.sidebar.update_status(
                        _result.adapter.name,
                        is_running=False,
                        is_healthy=(_health >= 70),
                    )

                    # Update header status
                    self.lbl_status.config(
                        text=f"Monitor: {_health}/100 ({_label})",
                        fg=_result.health.color,
                    )

                self._dispatch_ui(_update_monitor_ui)

            except Exception as e:
                err_msg = str(e)
                self._dispatch_ui(
                    lambda: self.pages["monitoring"].append_event(
                        f"Monitor scan error: {err_msg}", "critical"
                    )
                )
                db.log_event("ERROR", f"Monitor scan error: {err_msg}", severity="CRITICAL")


# ═══════════════════════════════════════════════════════════════
# APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    app = IntelliNetApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
