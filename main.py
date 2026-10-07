"""
Automated Network Diagnostic and Connectivity Analysis Framework
Main GUI Application using Tkinter

Author: College Academic Project
Target Platform: Windows 10/11
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import sys
import os

# Ensure local imports work regardless of execution directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import network_diagnostics as nd


class NetworkDiagnosticApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automated Network Diagnostic & Connectivity Analysis Framework")
        self.root.geometry("860x780")
        self.root.minsize(780, 680)

        # Apply Modern Color Scheme (Dark Slate / Deep Navy)
        self.COLOR_BG = "#0F172A"         # Main background
        self.COLOR_PANEL = "#1E293B"      # Panel background
        self.COLOR_PANEL_ALT = "#334155"  # Secondary panel / border
        self.COLOR_ACCENT = "#0EA5E9"     # Sky blue primary accent
        self.COLOR_ACCENT_HOVER = "#0284C7"
        self.COLOR_TEXT_PRIMARY = "#F8FAFC"
        self.COLOR_TEXT_MUTED = "#94A3B8"
        self.COLOR_SUCCESS = "#22C55E"    # Green
        self.COLOR_FAILURE = "#EF4444"    # Red
        self.COLOR_WARNING = "#F59E0B"    # Amber

        self.root.configure(bg=self.COLOR_BG)

        # Diagnostic state store
        self.is_running = False
        self.diagnostic_data = None

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        """Configure ttk styles for Treeview and Progressbar."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Table (Treeview) styling
        self.style.configure(
            "Custom.Treeview",
            background=self.COLOR_PANEL,
            foreground=self.COLOR_TEXT_PRIMARY,
            fieldbackground=self.COLOR_PANEL,
            rowheight=38,
            font=("Segoe UI", 11)
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background="#090D16",
            foreground="#38BDF8",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0
        )
        self.style.map("Custom.Treeview", background=[("selected", "#334155")])

        # Progressbar styling
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=self.COLOR_PANEL,
            bordercolor=self.COLOR_PANEL,
            background=self.COLOR_ACCENT,
            thickness=8
        )

    def _build_ui(self):
        """Construct GUI layout."""
        # ------------------- HEADER -------------------
        header_frame = tk.Frame(self.root, bg=self.COLOR_BG, pady=15, padx=25)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(
            header_frame,
            text="AUTOMATED NETWORK DIAGNOSTIC\n& CONNECTIVITY ANALYSIS",
            font=("Segoe UI", 18, "bold"),
            fg=self.COLOR_TEXT_PRIMARY,
            bg=self.COLOR_BG,
            justify="center"
        )
        title_lbl.pack()

        subtitle_lbl = tk.Label(
            header_frame,
            text="Development of an Automated Network Diagnostic and Connectivity Analysis Framework",
            font=("Segoe UI", 10, "italic"),
            fg=self.COLOR_ACCENT,
            bg=self.COLOR_BG
        )
        subtitle_lbl.pack(pady=(4, 0))

        # Divider line
        divider = tk.Frame(self.root, bg=self.COLOR_PANEL_ALT, height=2)
        divider.pack(fill="x", padx=25, pady=5)

        # ------------------- ACTION BAR (RUN BUTTON) -------------------
        self.action_frame = tk.Frame(self.root, bg=self.COLOR_BG, pady=10)
        self.action_frame.pack(fill="x", padx=25)

        self.btn_run = tk.Button(
            self.action_frame,
            text="▶  RUN NETWORK DIAGNOSTIC",
            font=("Segoe UI", 12, "bold"),
            fg="#FFFFFF",
            bg=self.COLOR_ACCENT,
            activebackground=self.COLOR_ACCENT_HOVER,
            activeforeground="#FFFFFF",
            bd=0,
            padx=24,
            pady=10,
            cursor="hand2",
            command=self.start_diagnostic
        )
        self.btn_run.pack()

        # Status text & Progress Bar
        self.status_lbl = tk.Label(
            self.action_frame,
            text="System ready. Click button above to initiate diagnostics.",
            font=("Segoe UI", 10),
            fg=self.COLOR_TEXT_MUTED,
            bg=self.COLOR_BG
        )
        self.status_lbl.pack(pady=(8, 4))

        self.progress_bar = ttk.Progressbar(
            self.action_frame,
            style="Custom.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            length=600
        )
        self.progress_bar.pack(pady=4)

        # ------------------- RESULTS TABLE -------------------
        table_container = tk.Frame(self.root, bg=self.COLOR_PANEL, bd=1, relief="solid")
        table_container.pack(fill="both", expand=True, padx=25, pady=10)

        columns = ("check", "status", "details")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="none"
        )
        
        self.tree.heading("check", text="  CHECK", anchor="w")
        self.tree.heading("status", text="STATUS", anchor="center")
        self.tree.heading("details", text="DETAILS", anchor="w")

        self.tree.column("check", width=220, anchor="w")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("details", width=440, anchor="w")

        self.tree.pack(fill="both", expand=True, padx=2, pady=2)

        # Configure row colors tag
        self.tree.tag_configure("pass", foreground=self.COLOR_SUCCESS)
        self.tree.tag_configure("fail", foreground=self.COLOR_FAILURE)

        # Populate empty table template
        self._populate_empty_table()

        # ------------------- DIAGNOSIS CARD -------------------
        diag_card = tk.Frame(self.root, bg=self.COLOR_PANEL, bd=1, relief="solid")
        diag_card.pack(fill="x", padx=25, pady=(0, 10))

        # Card Title Header
        card_header = tk.Frame(diag_card, bg=self.COLOR_PANEL_ALT, pady=6, padx=15)
        card_header.pack(fill="x")

        tk.Label(
            card_header,
            text="DIAGNOSIS & RECOMMENDATION REPORT",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_TEXT_PRIMARY,
            bg=self.COLOR_PANEL_ALT
        ).pack(side="left")

        self.overall_badge = tk.Label(
            card_header,
            text="STATUS: READY",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_TEXT_MUTED,
            bg=self.COLOR_PANEL_ALT
        )
        self.overall_badge.pack(side="right")

        # Card Content Frame
        card_body = tk.Frame(diag_card, bg=self.COLOR_PANEL, pady=12, padx=15)
        card_body.pack(fill="x")

        # Diagnosis Row
        tk.Label(
            card_body,
            text="DIAGNOSIS:",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_ACCENT,
            bg=self.COLOR_PANEL,
            anchor="w"
        ).grid(row=0, column=0, sticky="nw", pady=2)

        self.diag_val_lbl = tk.Label(
            card_body,
            text="No diagnostic data available yet. Please run the diagnostic process.",
            font=("Segoe UI", 10),
            fg=self.COLOR_TEXT_PRIMARY,
            bg=self.COLOR_PANEL,
            anchor="w",
            wraplength=650,
            justify="left"
        )
        self.diag_val_lbl.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)

        # Recommendation Row
        tk.Label(
            card_body,
            text="RECOMMENDATION:",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_SUCCESS,
            bg=self.COLOR_PANEL,
            anchor="w"
        ).grid(row=1, column=0, sticky="nw", pady=(8, 2))

        self.rec_val_lbl = tk.Label(
            card_body,
            text="N/A",
            font=("Segoe UI", 10),
            fg=self.COLOR_TEXT_PRIMARY,
            bg=self.COLOR_PANEL,
            anchor="w",
            wraplength=650,
            justify="left"
        )
        self.rec_val_lbl.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(8, 2))

        # ------------------- FOOTER ACTION BUTTONS -------------------
        footer = tk.Frame(self.root, bg=self.COLOR_BG, pady=10, padx=25)
        footer.pack(fill="x")

        self.btn_re_run = tk.Button(
            footer,
            text="🔄  RUN AGAIN",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=self.COLOR_PANEL_ALT,
            activebackground=self.COLOR_ACCENT,
            activeforeground="#FFFFFF",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self.start_diagnostic
        )
        self.btn_re_run.pack(side="left", padx=(0, 10))

        self.btn_save = tk.Button(
            footer,
            text="📋  SAVE REPORT",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=self.COLOR_PANEL_ALT,
            activebackground=self.COLOR_ACCENT,
            activeforeground="#FFFFFF",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self.save_report
        )
        self.btn_save.pack(side="left")

        self.btn_exit = tk.Button(
            footer,
            text="❌  EXIT",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=self.COLOR_FAILURE,
            activebackground="#DC2626",
            activeforeground="#FFFFFF",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.root.quit
        )
        self.btn_exit.pack(side="right")

    def _populate_empty_table(self):
        """Display initial empty state in Treeview table."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        initial_rows = [
            ("Network Adapter", "--", "Pending diagnostic run..."),
            ("IP Address", "--", "Pending diagnostic run..."),
            ("Default Gateway", "--", "Pending diagnostic run..."),
            ("DNS Resolution", "--", "Pending diagnostic run..."),
            ("Internet Connectivity", "--", "Pending diagnostic run...")
        ]
        for row in initial_rows:
            self.tree.insert("", "end", values=row)

    def start_diagnostic(self):
        """Initiate diagnostic in a background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.btn_run.config(state="disabled", bg=self.COLOR_PANEL_ALT)
        self.btn_re_run.config(state="disabled")
        self.btn_save.config(state="disabled")

        self.progress_bar["value"] = 0
        self.status_lbl.config(fg=self.COLOR_ACCENT, text="Starting diagnostic workflow...")

        # Clear diagnosis box
        self.overall_badge.config(text="STATUS: TESTING...", fg=self.COLOR_WARNING)
        self.diag_val_lbl.config(text="Diagnostic in progress...")
        self.rec_val_lbl.config(text="Diagnostic in progress...")

        # Launch background thread
        threading.Thread(target=self._run_diagnostic_workflow, daemon=True).start()

    def _update_tree_row(self, index, check_name, status_symbol, details, is_success):
        """Safely update a specific row in the Treeview."""
        children = self.tree.get_children()
        if index < len(children):
            item_id = children[index]
            tag = "pass" if is_success else "fail"
            self.tree.item(item_id, values=(f"  {check_name}", status_symbol, details), tags=(tag,))

    def _run_diagnostic_workflow(self):
        """Executed on background thread to prevent UI freezing."""
        try:
            # Step 1: Check Network Adapter
            self.root.after(0, lambda: self.status_lbl.config(text="Checking network adapter..."))
            self.root.after(0, lambda: self.progress_bar.config(value=15))
            adapter_res = nd.get_active_adapter()
            time.sleep(0.4)

            adapter_ok, adapter_name, adapter_det = adapter_res
            symbol_1 = "✓" if adapter_ok else "✗"
            self.root.after(
                0, lambda: self._update_tree_row(0, "Network Adapter", symbol_1, adapter_name, adapter_ok)
            )

            # Step 2: Check IP Address
            self.root.after(0, lambda: self.status_lbl.config(text="Checking IP address..."))
            self.root.after(0, lambda: self.progress_bar.config(value=35))
            ip_res = nd.get_ipv4_address(adapter_name if adapter_ok else None)
            time.sleep(0.4)

            ip_ok, ip_addr, ip_det = ip_res
            symbol_2 = "✓" if ip_ok else "✗"
            self.root.after(
                0, lambda: self._update_tree_row(1, "IP Address", symbol_2, ip_det, ip_ok)
            )

            # Step 3: Check Default Gateway
            self.root.after(0, lambda: self.status_lbl.config(text="Checking default gateway..."))
            self.root.after(0, lambda: self.progress_bar.config(value=55))
            gateway_res = nd.check_gateway()
            time.sleep(0.4)

            gw_has, gw_ip, gw_reachable, gw_disp = gateway_res
            symbol_3 = "✓" if (gw_has and gw_reachable) else "✗"
            self.root.after(
                0, lambda: self._update_tree_row(2, "Default Gateway", symbol_3, gw_disp, gw_has and gw_reachable)
            )

            # Step 4: Check DNS Resolution
            self.root.after(0, lambda: self.status_lbl.config(text="Testing DNS..."))
            self.root.after(0, lambda: self.progress_bar.config(value=75))
            dns_res = nd.check_dns("google.com")
            time.sleep(0.4)

            dns_ok, dns_status, dns_det = dns_res
            symbol_4 = "✓" if dns_ok else "✗"
            self.root.after(
                0, lambda: self._update_tree_row(3, "DNS Resolution", symbol_4, dns_status, dns_ok)
            )

            # Step 5: Check Internet Connectivity
            self.root.after(0, lambda: self.status_lbl.config(text="Testing internet connectivity..."))
            self.root.after(0, lambda: self.progress_bar.config(value=90))
            internet_res = nd.check_internet("8.8.8.8")
            time.sleep(0.4)

            inet_ok, inet_status, inet_det = internet_res
            symbol_5 = "✓" if inet_ok else "✗"
            self.root.after(
                0, lambda: self._update_tree_row(4, "Internet Connectivity", symbol_5, inet_status, inet_ok)
            )

            # Step 6 & 7 & 8: Analyze & Diagnose
            self.root.after(0, lambda: self.status_lbl.config(text="Analyzing results..."))
            self.root.after(0, lambda: self.progress_bar.config(value=100))
            diag = nd.diagnose_network(adapter_res, ip_res, gateway_res, dns_res, internet_res)
            time.sleep(0.3)

            # Store result for save feature
            self.diagnostic_data = {
                "adapter": adapter_res,
                "ip": ip_res,
                "gateway": gateway_res,
                "dns": dns_res,
                "internet": internet_res,
                "diagnosis": diag
            }

            # Update UI with diagnosis results
            self.root.after(0, lambda: self._finalize_ui_state(diag))

        except Exception as e:
            self.root.after(0, lambda: self._handle_error(str(e)))

    def _finalize_ui_state(self, diag):
        """Update diagnosis display and restore action buttons on main thread."""
        self.is_running = False
        self.btn_run.config(state="normal", bg=self.COLOR_ACCENT)
        self.btn_re_run.config(state="normal")
        self.btn_save.config(state="normal")
        self.status_lbl.config(fg=self.COLOR_SUCCESS, text="Diagnostic completed successfully!")

        overall = diag["overall_status"]
        if "NORMAL" in overall or "HEALTHY" in overall:
            badge_fg = self.COLOR_SUCCESS
        elif "CRITICAL" in overall:
            badge_fg = self.COLOR_FAILURE
        else:
            badge_fg = self.COLOR_WARNING

        self.overall_badge.config(text=f"OVERALL STATUS: {overall}", fg=badge_fg)
        self.diag_val_lbl.config(text=diag["diagnosis"])
        self.rec_val_lbl.config(text=diag["recommendation"])

    def _handle_error(self, err_msg):
        """Handle exceptions gracefully."""
        self.is_running = False
        self.btn_run.config(state="normal", bg=self.COLOR_ACCENT)
        self.btn_re_run.config(state="normal")
        self.status_lbl.config(fg=self.COLOR_FAILURE, text=f"Diagnostic error: {err_msg}")
        messagebox.showerror("Diagnostic Error", f"An unexpected error occurred:\n{err_msg}")

    def save_report(self):
        """Save diagnostic results to a text file."""
        if not self.diagnostic_data:
            messagebox.showinfo("Save Report", "No diagnostic data to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="network_diagnostic_report.txt",
            title="Save Diagnostic Report"
        )
        if not file_path:
            return

        d = self.diagnostic_data
        diag = d["diagnosis"]

        report_content = f"""=================================================================
AUTOMATED NETWORK DIAGNOSTIC & CONNECTIVITY ANALYSIS REPORT
=================================================================
Date/Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

1. NETWORK ADAPTER CHECK:
   Status  : {"✓ Connected" if d["adapter"][0] else "✗ Disconnected"}
   Details : {d["adapter"][2]}

2. IP ADDRESS CHECK:
   Status  : {"✓ Valid IP" if d["ip"][0] else "✗ Not Available"}
   Address : {d["ip"][1]}

3. DEFAULT GATEWAY CHECK:
   Status  : {"✓ Reachable" if (d["gateway"][0] and d["gateway"][2]) else "✗ Unreachable / Not Available"}
   Gateway : {d["gateway"][3]}

4. DNS RESOLUTION CHECK:
   Status  : {"✓ Working" if d["dns"][0] else "✗ Failed"}
   Details : {d["dns"][2]}

5. INTERNET CONNECTIVITY CHECK:
   Status  : {"✓ Connected" if d["internet"][0] else "✗ Unreachable"}
   Details : {d["internet"][2]}

=================================================================
SUMMARY & DIAGNOSIS
=================================================================
Overall Status : {diag["overall_status"]}
Case Code      : {diag["case_code"]}
Diagnosis      : {diag["diagnosis"]}
Recommendation : {diag["recommendation"]}
=================================================================
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            messagebox.showinfo("Save Report", f"Report saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save report: {e}")


def main():
    root = tk.Tk()
    app = NetworkDiagnosticApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
