"""PDF diagnostic report generation for IntelliNet."""

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable, Mapping
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models import DiagnosticResult


NAVY = colors.HexColor("#12233F")
BLUE = colors.HexColor("#147DAB")
PALE_BLUE = colors.HexColor("#EAF4FA")
INK = colors.HexColor("#203047")
MUTED = colors.HexColor("#64748B")
GRID = colors.HexColor("#D9E2EC")
WHITE = colors.white


def _display(value, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _action_value(action, key: str, default=""):
    if isinstance(action, Mapping):
        return action.get(key, default)
    return getattr(action, key, default)


def _action_timestamp(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return _display(value)


def build_report_sections(
    result: DiagnosticResult,
    actions: Iterable[object] = (),
) -> list[tuple[str, list[tuple[str, str]]]]:
    """Return report sections in display order for rendering and validation."""
    adapter = result.adapter
    ip = result.ip
    gateway = result.gateway
    wifi = result.wifi
    dns = result.dns
    internet = result.internet
    performance = result.performance
    rca = result.rca
    recommendation = result.recommendation

    if performance.is_valid:
        performance_rows = [
            ("Measurement target", _display(performance.target_host)),
            ("Average latency", f"{performance.avg_latency_ms:.1f} ms"),
            ("Minimum / maximum latency", f"{performance.min_latency_ms:.1f} / {performance.max_latency_ms:.1f} ms"),
            ("Jitter", f"{performance.jitter_ms:.1f} ms"),
            ("Packet loss", f"{performance.packet_loss_pct:.1f}%"),
            ("Probe count", str(performance.ping_count)),
            ("Quality rating", performance.latency_rating),
        ]
    else:
        performance_rows = [
            ("Measurement status", "Unavailable"),
            ("Reason", _display(performance.error)),
            ("Measurement target", _display(performance.target_host)),
        ]

    action_rows = []
    for action in actions:
        label = _action_value(action, "action", "Action")
        status = _action_value(action, "status", "Unknown")
        details = _action_value(action, "details", _action_value(action, "message", ""))
        timestamp = _action_timestamp(_action_value(action, "timestamp", ""))
        action_rows.append(
            (f"{timestamp} | {_display(label)} | {_display(status)}", _display(details))
        )
    if not action_rows:
        action_rows = [("No actions performed", "No remediation actions have been performed in this session.")]

    return [
        (
            "Network Configuration",
            [
                ("Adapter", _display(adapter.name)),
                ("Adapter type", _display(adapter.adapter_type)),
                ("Adapter active", _yes_no(adapter.is_up)),
                ("Link speed", f"{adapter.speed_mbps} Mbps" if adapter.speed_mbps else "Not available"),
                ("MAC address", _display(adapter.mac_address)),
                ("IPv4 address", _display(ip.ipv4)),
                ("Subnet mask", _display(ip.subnet_mask)),
                ("Default gateway", _display(gateway.ip)),
                ("Configured DNS servers", ", ".join(dns.dns_servers) or "Not available"),
                ("Wi-Fi network (SSID)", _display(wifi.ssid) if wifi.is_wifi else "Not using Wi-Fi"),
                ("Wi-Fi signal", f"{wifi.signal_pct}%" if wifi.is_wifi and wifi.signal_pct >= 0 else "Not available"),
            ],
        ),
        (
            "Connectivity Results",
            [
                ("Adapter", "Connected" if adapter.is_up else "Unavailable"),
                ("IPv4 configuration", "Valid" if ip.is_valid else "Missing or invalid"),
                ("Default gateway", "Reachable" if gateway.is_reachable else "Unreachable"),
                (f"DNS resolution ({_display(dns.domain_tested)})", "Passed" if dns.is_working else "Failed"),
                ("Internet access", "Connected" if internet.is_connected else "Unavailable"),
                ("DNS details", _display(dns.display)),
                ("Internet details", _display(internet.display)),
            ],
        ),
        ("Performance Analysis", performance_rows),
        (
            "Root-Cause Analysis",
            [
                ("Case", _display(rca.case_code)),
                ("Severity", _display(rca.severity)),
                ("Overall status", _display(rca.overall_status)),
                ("Primary cause", _display(rca.primary_cause)),
                ("Contributing factors", "\n".join(rca.secondary_causes) or "None identified"),
            ],
        ),
        (
            "Diagnostic Confidence",
            [
                ("Confidence score", f"{rca.confidence}%"),
                ("Interpretation", "Estimated strength of evidence supporting the identified root cause."),
            ],
        ),
        (
            "Recommendations",
            [
                ("Summary", _display(recommendation.summary)),
                ("Recommended steps", "\n".join(
                    f"{index}. {step}" for index, step in enumerate(recommendation.steps, 1)
                ) or "No steps provided."),
            ],
        ),
        ("Actions Performed", action_rows),
    ]


def _register_report_font() -> str:
    """Prefer ReportLab's bundled Unicode-capable Vera font when available."""
    try:
        import reportlab

        font_path = os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf")
        if os.path.isfile(font_path):
            if "IntelliNetVera" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("IntelliNetVera", font_path))
            return "IntelliNetVera"
    except Exception:
        pass
    return "Helvetica"


def _paragraph(value: str, style: ParagraphStyle) -> Paragraph:
    text = escape(_display(value)).replace("\n", "<br/>")
    return Paragraph(text, style)


def _draw_footer(canvas, document):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "IntelliNet | Confidential diagnostic snapshot")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def generate_pdf_report(
    result: DiagnosticResult,
    destination,
    actions: Iterable[object] = (),
) -> Path:
    """Generate and return a polished, multi-page PDF report."""
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_name = _register_report_font()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "IntelliNetTitle", parent=styles["Title"], fontName=font_name,
        fontSize=21, leading=25, textColor=WHITE, alignment=TA_LEFT, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "IntelliNetSubtitle", parent=styles["Normal"], fontName=font_name,
        fontSize=9, leading=13, textColor=colors.HexColor("#D5E7F4"),
    )
    section_style = ParagraphStyle(
        "IntelliNetSection", parent=styles["Heading2"], fontName=font_name,
        fontSize=11, leading=14, textColor=NAVY, spaceBefore=10, spaceAfter=5,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "IntelliNetBody", parent=styles["BodyText"], fontName=font_name,
        fontSize=8.5, leading=12, textColor=INK, alignment=TA_LEFT,
    )
    label_style = ParagraphStyle(
        "IntelliNetLabel", parent=body_style, fontName=font_name,
        textColor=MUTED,
    )
    summary_style = ParagraphStyle(
        "IntelliNetSummary", parent=body_style, fontSize=9.5, leading=14,
    )

    timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    hero = Table(
        [[
            Paragraph("NETWORK DIAGNOSTIC REPORT", title_style),
            Paragraph(
                f"Generated {escape(timestamp)}<br/>"
                f"Health: {result.health.score}/100 ({escape(result.health.label)})",
                subtitle_style,
            ),
        ]],
        colWidths=[112 * mm, 62 * mm],
    )
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    story = [hero, Spacer(1, 8)]
    executive_summary = (
        f"<b>{escape(result.rca.overall_status)}</b> - "
        f"{escape(result.rca.primary_cause)}<br/>"
        f"{escape(result.recommendation.summary)}"
    )
    story.extend([
        Paragraph("Executive Summary", section_style),
        Table(
            [[Paragraph(executive_summary, summary_style)]],
            colWidths=[174 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.6, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        ),
    ])

    for title, rows in build_report_sections(result, actions):
        story.append(Paragraph(escape(title), section_style))
        table_data = [
            [_paragraph(label, label_style), _paragraph(value, body_style)]
            for label, value in rows
        ]
        table = Table(table_data, colWidths=[52 * mm, 122 * mm], repeatRows=0, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title="IntelliNet Diagnostic Report",
        author="IntelliNet",
        subject="Network configuration, connectivity, performance, and remediation",
    )
    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return output_path
