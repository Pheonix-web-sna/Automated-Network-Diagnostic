"""
recommendations_view.py — IntelliNet Recommendations View
Displays Root Cause Analysis breakdown, diagnostic confidence, and step-by-step remediation plan.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import config as cfg
from models import DiagnosticResult


class RecommendationsView(tk.Frame):
    """
    Dedicated Recommendations Page:
      - RCA Header: Case code, severity, primary cause, confidence meter.
      - Contributing Factors: Secondary causes identified by the engine.
      - Actionable Remediation Plan: Numbered step-by-step guidance cards.
    """

    def __init__(
        self,
        parent,
        on_retest: Optional[Callable[[], None]] = None,
        on_flush_dns: Optional[Callable[[], None]] = None,
        on_renew_ip: Optional[Callable[[], None]] = None,
        **kw,
    ):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self.on_retest = on_retest
        self.on_flush_dns = on_flush_dns
        self.on_renew_ip = on_renew_ip
        self.step_frames = []
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # ═══════════════════════════════════════════════════════════════
        # TOP CARD: ROOT CAUSE ANALYSIS & CONFIDENCE
        # ═══════════════════════════════════════════════════════════════
        rca_card = tk.Frame(
            container,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        rca_card.pack(fill="x", pady=(0, 14))

        head_row = tk.Frame(rca_card, bg=cfg.COLOR_PANEL)
        head_row.pack(fill="x")

        tk.Label(
            head_row,
            text="ROOT CAUSE ANALYSIS ENGINE OUTPUT",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.sev_badge = tk.Label(
            head_row,
            text="STATUS PENDING",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_ALT,
            fg=cfg.COLOR_TEXT_MUTED,
            padx=8,
            pady=2,
        )
        self.sev_badge.pack(side="right")

        self.case_code_badge = tk.Label(
            head_row,
            text="CASE: —",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_ALT,
            fg=cfg.COLOR_TEXT_MUTED,
            padx=8,
            pady=2,
        )
        self.case_code_badge.pack(side="right", padx=(0, 8))

        # Primary Cause Title
        self.primary_lbl = tk.Label(
            rca_card,
            text="Run a diagnostic scan to generate root cause analysis and recommendations.",
            font=("Segoe UI", 11, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
            wraplength=850,
            justify="left",
            anchor="w",
        )
        self.primary_lbl.pack(fill="x", pady=(10, 8))

        # Confidence bar & Secondary factors row
        meta_row = tk.Frame(rca_card, bg=cfg.COLOR_PANEL)
        meta_row.pack(fill="x")

        # Confidence score box
        conf_box = tk.Frame(meta_row, bg=cfg.COLOR_PANEL_DARK, padx=10, pady=6)
        conf_box.pack(side="left", padx=(0, 16))

        tk.Label(
            conf_box,
            text="DIAGNOSTIC CONFIDENCE",
            font=("Segoe UI", 7, "bold"),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        self.conf_val = tk.Label(
            conf_box,
            text="— %",
            font=("Segoe UI", 12, "bold"),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_PURPLE,
        )
        self.conf_val.pack(anchor="w")

        # Contributing factors list
        self.factors_frame = tk.Frame(meta_row, bg=cfg.COLOR_PANEL)
        self.factors_frame.pack(side="left", fill="both", expand=True)

        self.factors_label = tk.Label(
            self.factors_frame,
            text="Contributing Factors: None detected.",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=600,
            justify="left",
        )
        self.factors_label.pack(fill="x")

        # ═══════════════════════════════════════════════════════════════
        # BOTTOM CARD: ACTIONABLE REMEDIATION PLAN
        # ═══════════════════════════════════════════════════════════════
        plan_card = tk.Frame(
            container,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        plan_card.pack(fill="both", expand=True)

        plan_head = tk.Frame(plan_card, bg=cfg.COLOR_PANEL)
        plan_head.pack(fill="x", pady=(0, 10))

        tk.Label(
            plan_head,
            text="ACTIONABLE REMEDIATION STEPS",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        if self.on_retest:
            btn_retest = tk.Button(
                plan_head,
                text="🔄  Re-test Network",
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_ACCENT,
                activebackground=cfg.COLOR_ACCENT,
                activeforeground="#FFFFFF",
                relief="flat",
                cursor="hand2",
                command=self.on_retest,
                padx=10,
                pady=3,
            )
            btn_retest.pack(side="right")

        # Safe remediation controls. The coordinator asks for confirmation
        # before dispatching either network-changing action.
        action_row = tk.Frame(plan_card, bg=cfg.COLOR_PANEL)
        action_row.pack(fill="x", pady=(0, 8))
        tk.Label(
            action_row,
            text="Quick fixes (confirmation required)",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        if self.on_renew_ip:
            self.btn_renew_ip = tk.Button(
                action_row,
                text="Renew IP",
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_TEXT_PRIMARY,
                activebackground=cfg.COLOR_ACCENT,
                activeforeground="#FFFFFF",
                relief="flat",
                cursor="hand2",
                command=self.on_renew_ip,
                padx=10,
                pady=4,
            )
            self.btn_renew_ip.pack(side="right", padx=(6, 0))

        if self.on_flush_dns:
            self.btn_flush_dns = tk.Button(
                action_row,
                text="Flush DNS",
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_TEXT_PRIMARY,
                activebackground=cfg.COLOR_ACCENT,
                activeforeground="#FFFFFF",
                relief="flat",
                cursor="hand2",
                command=self.on_flush_dns,
                padx=10,
                pady=4,
            )
            self.btn_flush_dns.pack(side="right")

        # Scrollable container for steps
        canvas = tk.Canvas(plan_card, bg=cfg.COLOR_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(plan_card, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=cfg.COLOR_PANEL)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=840)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Default placeholder step
        self._add_step_card(
            1,
            "Awaiting diagnostic execution",
            "Click 'Run Diagnostics' above to evaluate your network and generate step-by-step fix instructions.",
        )

    def _add_step_card(self, num: int, title: str, instructions: str):
        """Add a clean numbered step card into the scrollable remediation plan."""
        card = tk.Frame(
            self.scroll_frame,
            bg=cfg.COLOR_PANEL_DARK,
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL,
        )
        card.pack(fill="x", pady=4)

        top_row = tk.Frame(card, bg=cfg.COLOR_PANEL_DARK)
        top_row.pack(fill="x")

        pill = tk.Label(
            top_row,
            text=f"STEP {num:02d}",
            font=("Segoe UI", 7, "bold"),
            bg=cfg.COLOR_ACCENT,
            fg="#FFFFFF",
            padx=6,
            pady=1,
        )
        pill.pack(side="left", padx=(0, 8))

        tk.Label(
            top_row,
            text=title,
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_TEXT_PRIMARY,
        ).pack(side="left")

        body_lbl = tk.Label(
            card,
            text=instructions,
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=800,
        )
        body_lbl.pack(fill="x", pady=(4, 0))

        self.step_frames.append(card)

    def update_data(self, result: DiagnosticResult):
        """Update the recommendation view with live RCA and Recommendation."""
        rca = result.rca
        rec = result.recommendation

        # Severity Badge
        sev_colors = {
            "CRITICAL":    cfg.COLOR_FAILURE,
            "WARNING":     cfg.COLOR_WARNING,
            "PERFORMANCE": cfg.COLOR_WARNING,
            "NORMAL":      cfg.COLOR_SUCCESS,
        }
        col = sev_colors.get(rca.severity, cfg.COLOR_ACCENT)
        self.sev_badge.config(
            text=f"{rca.severity} — {rca.overall_status}",
            bg=col,
            fg="#0F172A" if rca.severity in ("NORMAL", "WARNING", "PERFORMANCE") else "#FFFFFF",
        )

        self.case_code_badge.config(
            text=f"CASE: {rca.case_code}",
            bg=cfg.COLOR_PANEL_ALT,
            fg=cfg.COLOR_TEXT_PRIMARY,
        )

        # Primary cause
        self.primary_lbl.config(text=rca.primary_cause)

        # Confidence
        self.conf_val.config(text=f"{rca.confidence}%")

        # Contributing factors
        if rca.secondary_causes:
            factors_text = "Contributing Factors:\n" + "\n".join(f"  • {f}" for f in rca.secondary_causes)
            self.factors_label.config(text=factors_text, fg=cfg.COLOR_WARNING)
        else:
            self.factors_label.config(
                text="Contributing Factors: None (all baseline checks passed)",
                fg=cfg.COLOR_SUCCESS,
            )

        # Clear and repopulate steps
        for card in self.step_frames:
            card.destroy()
        self.step_frames.clear()

        # Step 0: Summary
        self._add_step_card(1, "Diagnostic Summary", rec.summary)

        # Action Steps
        for idx, step_text in enumerate(rec.steps, 2):
            self._add_step_card(idx, f"Action Item {idx - 1}", step_text)
