# Development of an Automated Network Diagnostic and Connectivity Analysis Framework

A desktop application designed for Windows 10/11 that automates the standard step-by-step network troubleshooting workflow. Built with Python 3.11+, Tkinter, and native Windows networking utilities, this tool provides instant identification of connectivity issues ranging from disabled network adapters to DNS resolution failures.

---

## 📌 Project Objective

The objective of this project is to create an automated, offline-friendly network diagnostic tool for end users and network administrators. By automating the traditional 8-step troubleshooting workflow, it eliminates manual command-line execution (`ipconfig`, `ping`, `nslookup`) and instantly provides clear, actionable recommendations.

---

## ✨ Features

- **Automated 8-Step Diagnostic Workflow**:
  1. **Network Adapter Check**: Detects active physical interfaces (Wi-Fi, Ethernet) using `psutil`.
  2. **IP Address Check**: Identifies assigned IPv4 address while ignoring loopback (`127.0.0.1`) and self-assigned APIPA (`169.254.x.x`).
  3. **Default Gateway Check**: Determines the local router gateway via `ipconfig` / routing table and tests reachability with ICMP ping.
  4. **DNS Resolution Check**: Tests socket name resolution against `google.com`.
  5. **Internet Connectivity Check**: Verifies raw internet IP routing by pinging `8.8.8.8` (independent of DNS).
  6. **Data Synthesis**: Combines all 5 diagnostic vectors.
  7. **Rule-Based Diagnosis**: Evaluates state against pre-defined expert troubleshooting rules.
  8. **Recommendation Generation**: Displays direct user guidance for resolving the issue.
- **Multithreaded Responsive GUI**: Built with Tkinter; background execution prevents window freezing during ping or DNS timeouts.
- **Real-Time Progress Feedback**: Displays live progress bar and status steps during scanning.
- **PDF Diagnostic Reports**: Exports an executive summary, network configuration, connectivity and performance results, root-cause analysis, confidence score, recommendations, and session actions performed.
- **Safe Quick Remediation**: Flushes the DNS cache or renews the DHCP address only after explicit confirmation. Diagnostics can be re-run without changing network configuration.
- **Zero External Cloud Dependencies**: Works entirely locally without third-party APIs or database servers.

---

## 🛠️ Technologies Used

| Technology | Purpose |
| :--- | :--- |
| **Python 3.11+** | Core programming language |
| **Tkinter** | Native desktop GUI framework |
| **`psutil`** | Network interface status and IPv4 address inspection |
| **`socket`** | Standard library module for DNS resolution testing |
| **`subprocess`** | Windows command execution (`ipconfig`, `ping`, `route`) |
| **`threading`** | Asynchronous execution to keep GUI active |
| **ReportLab** | Structured PDF report generation |

---

## 💻 System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python Version**: Python 3.11 or higher installed and added to PATH
- **Network Interfaces**: Active Wi-Fi or Ethernet adapter

---

## 🚀 Installation & Setup

1. **Clone or Download the Repository**:
   ```bash
   git clone https://github.com/<your-username>/Automated-Network-Diagnostic.git
   cd Automated-Network-Diagnostic
   ```

2. **Install Required Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: `Tkinter`, `socket`, `subprocess`, `threading`, and `re` are built into standard Python on Windows).*

---

## 🏃 How to Run

Execute the main application using Python:

```bash
python main.py
```

## Automated Checks

Run the report and remediation unit tests with: python -m unittest discover -s tests -v

---

## 🔄 Diagnostic Workflow & Rule Engine

The application executes a rule-based diagnostic engine (`network_diagnostics.py`) based on standard networking hierarchy:

```
[Start Diagnostic]
       │
  Check Adapter ───────► (Disabled/Disconnected) ──► CASE 1: Adapter Disconnected
       │ (Active)
   Check IP ───────────► (No IP / APIPA) ──────────► CASE 2: No IP Assigned
       │ (Valid IP)
 Check Gateway ────────► (Unreachable) ────────────► CASE 3: Gateway Unreachable
       │ (Reachable)
   Check DNS & Internet
       ├── Internet OK + DNS Fail ────────────────► CASE 4: DNS Resolution Failure
       ├── DNS OK + Internet Fail ────────────────► CASE 5: Internet Down (ISP issue)
       └── DNS OK + Internet OK ──────────────────► CASE 6: Normal Operation
```

### Expert Rule Matrix

| Case | Adapter | IP Address | Gateway Ping | DNS Test | Internet Ping | Diagnosis | Actionable Recommendation |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **Case 1** | ✗ Disconnected | ✗ | ✗ | ✗ | ✗ | Network adapter is disconnected or disabled. | Connect to Wi-Fi or Ethernet and retry. |
| **Case 2** | ✓ Connected | ✗ No Valid IP | ✗ | ✗ | ✗ | No valid IP address has been assigned. | Reconnect to the network or renew the IP configuration. |
| **Case 3** | ✓ Connected | ✓ Valid IP | ✗ Unreachable | ✗ | ✗ | Local network or default gateway connectivity problem. | Check the router, Wi-Fi connection, or local network configuration. |
| **Case 4** | ✓ Connected | ✓ Valid IP | ✓ Reachable | ✗ Failed | ✓ Connected | DNS resolution problem. | Check DNS configuration or try an alternative DNS server (e.g. 8.8.8.8). |
| **Case 5** | ✓ Connected | ✓ Valid IP | ✓ Reachable | ✓ Working | ✗ Unreachable | Internet connectivity problem. | Check router internet access or ISP connectivity. |
| **Case 6** | ✓ Connected | ✓ Valid IP | ✓ Reachable | ✓ Working | ✓ Connected | Network connection is functioning normally. | No action required. |

---

## 📹 Live Demonstration Guide

To test and demonstrate the framework during project presentation:

### Scenario 1: Normal Connected State
1. Connect laptop/PC to Wi-Fi or Ethernet.
2. Launch app: `python main.py`
3. Click **RUN NETWORK DIAGNOSTIC**.
4. **Expected Output**:
   - Adapter: `✓ Wi-Fi` (or Ethernet)
   - IP Address: `✓ 172.16.x.x` (or 192.168.x.x)
   - Default Gateway: `✓ 172.16.0.1`
   - DNS Resolution: `✓ Working`
   - Internet Connectivity: `✓ Connected`
   - **Diagnosis**: Network connection is functioning normally.
   - **Recommendation**: No action required.

### Scenario 2: Adapter Disconnected State
1. Disconnect Wi-Fi (turn off Wi-Fi in Windows settings).
2. Click **RUN NETWORK DIAGNOSTIC** (or **RUN AGAIN**).
3. **Expected Output**:
   - Adapter: `✗ Disconnected / None`
   - IP Address: `✗ Not Available`
   - Default Gateway: `✗ Not Available`
   - DNS Resolution: `✗ Failed`
   - Internet Connectivity: `✗ Unreachable`
   - **Diagnosis**: Network adapter is disconnected or disabled.
   - **Recommendation**: Connect to Wi-Fi or Ethernet and retry.
4. Re-enable Wi-Fi and click **RUN AGAIN** to verify recovery to Scenario 1.

---

## 📂 Project Structure

```
Automated-Network-Diagnostic/
│
├── main.py                  # Tkinter GUI, diagnostics, PDF export, and remediation confirmations
├── reporting.py             # Structured PDF diagnostic report generator
├── remediation.py           # Confirmed DNS flush, IP renewal, and diagnostic rerun actions
├── network_diagnostics.py   # Adapter, IP, gateway, DNS, connectivity, and Wi-Fi probes
├── models.py                # Typed diagnostic and remediation data
├── tests/                   # Report, network configuration, and remediation unit tests
├── requirements.txt         # Required Python packages
├── README.md                # Full project documentation & presentation guide
└── screenshots/             # Interface preview screenshots
```

---

## 🔮 Future Enhancements

- Speed test integration using socket throughput estimation.
- Automatic log generation for network administrator diagnostics.

---

## 🎓 Academic Metadata

- **Project Title**: Development of an Automated Network Diagnostic and Connectivity Analysis Framework
- **Target Audience**: Academic Presentation & Demonstration
- **Target OS**: Windows 10 / Windows 11
- **License**: MIT
