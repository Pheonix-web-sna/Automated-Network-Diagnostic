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
  - Probe targets, thresholds, and UI settings are centralized in config.py.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import time
import logging
import sys
import os
from datetime import datetime

# Ensure local imports work regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg
import collector
import db_manager as db
from models import DiagnosticResult
from reporting import generate_pdf_report
from remediation import (
    ACTION_LABELS,
    ActionRecord,
    execute_remediation,
)

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
        try:
            db.init_db()
        except Exception:
            logging.exception("Could not initialize diagnostic history database")
            messagebox.showwarning(
                "History storage unavailable",
                "IntelliNet can still run live diagnostics and create reports, but history and monitoring events may not be saved.",
                parent=root,
            )
        self.root = root
        self.root.title(f"{cfg.APP_NAME} — {cfg.APP_SUBTITLE}")
        self.root.geometry(f"{cfg.WINDOW_WIDTH}x{cfg.WINDOW_HEIGHT}")
        self.root.minsize(cfg.WINDOW_MIN_WIDTH, cfg.WINDOW_MIN_HEIGHT)
        self.root.configure(bg=cfg.COLOR_BG)

        self.is_running = False
        self.diagnostic_data: DiagnosticResult = None
        self.ui_queue = queue.Queue()
        self.action_history = []
        self._remediation_running = False
        self._diagnostic_started_at = None

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
        self._safe_log_event("SYSTEM", "IntelliNet application started", severity="INFO")

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

        self.btn_export_pdf = tk.Button(
            action_box,
            text="Export PDF",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_ALT,
            fg=cfg.COLOR_TEXT_PRIMARY,
            activebackground=cfg.COLOR_ACCENT,
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.export_report,
            state="disabled",
            padx=12,
            pady=7,
        )
        self.btn_export_pdf.pack(side="left", padx=(0, 8))

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
            on_retest=lambda: self.run_remediation("rerun_diagnostics"),
            on_flush_dns=lambda: self.run_remediation("flush_dns"),
            on_renew_ip=lambda: self.run_remediation("renew_ip"),
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
                    logging.exception("A queued UI update failed")
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
            return False

        self.is_running = True
        self._diagnostic_started_at = datetime.now()
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
        return True

    def _run_diagnostic_worker(self):
        """
        Worker thread: sequentially executes all real network probes,
        posting live progress and log updates to the UI queue.
        """
        try:
            diag_view: DiagnosticsView = self.pages["diagnostics"]

            def report_progress(row, headline, status, symbol, details, tag, message, percent):
                def update_row():
                    if row is not None:
                        diag_view.set_row_testing(row)
                        diag_view.set_row_result(row, symbol, details, tag)
                    if message:
                        diag_view.append_log(message)
                    self.lbl_status.config(
                        text=headline,
                        fg=cfg.COLOR_TEAL if row in (6, 7) else cfg.COLOR_ACCENT,
                    )
                    self.progress_bar.config(value=percent)
                self._dispatch_ui(update_row)

            result = collector.collect_diagnostic(progress_callback=report_progress)
            try:
                degradation_alerts = db.detect_degradation(result)
            except Exception:
                logging.exception("Could not check diagnostic degradation")
                degradation_alerts = []
            try:
                db.save_diagnostic(result)
                self._safe_log_event(
                    "DIAGNOSTIC",
                    f"Scan completed — Health: {result.health.score}/100 "
                    f"({result.health.label}), RCA: {result.rca.overall_status}",
                    severity="INFO" if result.health.score >= 70 else "WARNING",
                )
            except Exception:
                logging.exception("Could not save diagnostic history")
            for alert in degradation_alerts:
                self._safe_log_event("DEGRADATION", alert, severity="WARNING")
            if degradation_alerts:
                self._dispatch_ui(lambda alerts=degradation_alerts: self._show_degradation_alerts(alerts))
            self._dispatch_ui(lambda result=result: self._finalize_scan(result))
        except Exception as exc:
            logging.exception("Diagnostic worker failed")
            error_message = str(exc)
            self._dispatch_ui(lambda message=error_message: self._handle_error(message))

    def _finalize_scan(self, result: DiagnosticResult):
        """Update all views, reset buttons, and refresh sidebar footer."""
        self.is_running = False
        self.diagnostic_data = result
        self.btn_run.config(state="normal", bg=cfg.COLOR_ACCENT)
        self.btn_export_pdf.config(state="normal")
        self._record_action(
            "Run diagnostics",
            "Completed",
            f"Health score: {result.health.score}/100; {result.rca.overall_status}.",
            self._diagnostic_started_at,
        )

        # Status text
        hlth = result.health
        self.lbl_status.config(
            text=f"Health: {hlth.score}/100 ({hlth.label}) — {result.rca.overall_status}",
            fg=hlth.color,
        )

        # Refresh the visible view. Other views sync when opened, avoiding
        # hidden chart redraws and history database reads on every scan.
        page = self.pages.get(self.current_page)
        if page:
            try:
                page.update_data(result)
            except Exception:
                logging.exception("The visible view failed to refresh after a diagnostic")

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
        self._record_action(
            "Run diagnostics",
            "Failed",
            err_msg,
            self._diagnostic_started_at,
        )
        self.lbl_status.config(text=f"Error: {err_msg}", fg=cfg.COLOR_FAILURE)

        diag_view: DiagnosticsView = self.pages["diagnostics"]
        diag_view.append_log(f"ERROR: Diagnostic worker exception: {err_msg}")

        self._safe_log_event("ERROR", f"Diagnostic error: {err_msg}", severity="CRITICAL")

    @staticmethod
    def _safe_log_event(event_type: str, message: str, severity: str = "INFO", details: str = ""):
        try:
            db.log_event(event_type, message, severity=severity, details=details)
        except Exception:
            logging.exception("Could not write event log entry: %s", event_type)

    def export_report(self):
        """Save the latest completed diagnostic and session actions as a PDF."""
        if not self.diagnostic_data:
            messagebox.showwarning(
                "No diagnostic available",
                "Run diagnostics before exporting a report.",
                parent=self.root,
            )
            return

        suggested_name = (
            "IntelliNet_Report_"
            + self.diagnostic_data.timestamp.strftime("%Y%m%d_%H%M%S")
            + ".pdf"
        )
        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export diagnostic report",
            defaultextension=".pdf",
            initialfile=suggested_name,
            filetypes=[("PDF report", "*.pdf")],
        )
        if not destination:
            return

        try:
            path = generate_pdf_report(
                self.diagnostic_data,
                destination,
                actions=self.action_history,
            )
        except Exception as exc:
            messagebox.showerror(
                "Report export failed",
                f"The PDF report could not be created:\n{exc}",
                parent=self.root,
            )
            return

        messagebox.showinfo(
            "Report exported",
            f"Diagnostic report saved to:\n{path}",
            parent=self.root,
        )

    def run_remediation(self, action: str):
        """Confirm and dispatch one of the available remediation actions."""
        if action == "rerun_diagnostics":
            outcome = execute_remediation(
                action,
                diagnostic_callback=self.start_diagnostic,
            )
            if not outcome.succeeded:
                messagebox.showwarning(
                    "Diagnostics not started",
                    outcome.message,
                    parent=self.root,
                )
            return

        label = ACTION_LABELS.get(action)
        if not label:
            messagebox.showerror(
                "Unsupported action",
                "This remediation action is not available.",
                parent=self.root,
            )
            return
        if self._remediation_running:
            messagebox.showinfo(
                "Action in progress",
                "Please wait for the current network action to finish.",
                parent=self.root,
            )
            return

        prompts = {
            "flush_dns": (
                "Flush the Windows DNS resolver cache now? "
                "This clears cached name lookups and may briefly affect name resolution."
            ),
            "renew_ip": (
                "Renew DHCP IPv4 leases for configured adapters now? "
                "Network connectivity may be interrupted briefly while Windows requests new leases."
            ),
        }
        if action not in prompts:
            messagebox.showerror(
                "Unsupported action",
                "This remediation action is not available.",
                parent=self.root,
            )
            return
        if not messagebox.askyesno(
            f"Confirm {label}",
            prompts[action],
            icon="warning",
            parent=self.root,
        ):
            return

        self._remediation_running = True
        self.lbl_status.config(text=f"Running {label.lower()}...", fg=cfg.COLOR_WARNING)
        threading.Thread(
            target=self._run_remediation_worker,
            args=(action,),
            daemon=True,
        ).start()

    def _run_remediation_worker(self, action: str):
        """Run a previously confirmed action without blocking the GUI."""
        outcome = execute_remediation(action, confirmed=True)
        self._dispatch_ui(lambda: self._finalize_remediation(outcome))

    def _finalize_remediation(self, outcome):
        """Record remediation results and report them to the user."""
        self._remediation_running = False
        label = ACTION_LABELS.get(outcome.action, outcome.action)
        self._record_action(label, outcome.status.title(), outcome.message, outcome.timestamp)

        severity = "INFO" if outcome.succeeded else "WARNING"
        try:
            db.log_event(
                "REMEDIATION",
                f"{label}: {outcome.status}",
                severity=severity,
                details=outcome.message,
            )
        except Exception:
            pass

        self.lbl_status.config(
            text=f"{label}: {outcome.status}",
            fg=cfg.COLOR_SUCCESS if outcome.succeeded else cfg.COLOR_FAILURE,
        )
        if outcome.succeeded:
            messagebox.showinfo(
                "Network action completed",
                outcome.message,
                parent=self.root,
            )
        else:
            messagebox.showerror(
                "Network action failed",
                outcome.message,
                parent=self.root,
            )

    def _record_action(self, action: str, status: str, details: str, timestamp=None):
        """Keep a report-ready in-memory history for this application session."""
        record = ActionRecord(
            action=action,
            status=status,
            details=details,
            timestamp=timestamp or datetime.now(),
        )
        self.action_history.append(record)
        return record

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

        interval_sec = max(
            cfg.MONITOR_MIN_INTERVAL_SEC,
            min(int(interval_sec), cfg.MONITOR_MAX_INTERVAL_SEC),
        )

        self._monitor_active = True
        self._monitor_stop_event.clear()
        self._monitor_scan_count = 0
        self._monitor_alert_count = 0

        self._safe_log_event("MONITORING", f"Background monitoring started (interval: {interval_sec}s)", severity="INFO")

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

        self._safe_log_event("MONITORING", "Background monitoring stopped by user", severity="INFO")

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

                # Degradation detection
                try:
                    alerts = db.detect_degradation(result)
                except Exception:
                    logging.exception("Could not check monitoring degradation")
                    alerts = []

                # Save after comparison so this scan does not become its own baseline.
                try:
                    db.save_diagnostic(result)
                    self._safe_log_event(
                        "MONITOR_SCAN",
                        f"Monitor scan #{self._monitor_scan_count} — "
                        f"Health: {result.health.score}/100, "
                        f"Latency: {result.performance.avg_latency_ms:.0f}ms",
                        severity="INFO" if result.health.score >= 70 else "WARNING",
                    )
                except Exception:
                    logging.exception("Could not save monitoring scan")

                if alerts:
                    for alert in alerts:
                        self._safe_log_event("DEGRADATION", alert, severity="WARNING")

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
                    page = self.pages.get(self.current_page)
                    if page:
                        try:
                            page.update_data(_result)
                        except Exception:
                            logging.exception("The visible view failed to refresh after a monitoring scan")

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

            except Exception as exc:
                logging.exception("Monitoring scan failed")
                err_msg = str(exc)
                self._dispatch_ui(
                    lambda message=err_msg: self.pages["monitoring"].append_event(
                        f"Monitor scan error: {message}", "critical"
                    )
                )
                self._safe_log_event("ERROR", f"Monitor scan error: {err_msg}", severity="CRITICAL")


# ═══════════════════════════════════════════════════════════════
# APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    app = IntelliNetApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
