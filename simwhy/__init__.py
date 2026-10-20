"""SimWhy: transparent, hypothesis-driven physical feasibility simulations."""
from .core import Config, simulate, nozzle_flow
from .audit import audit_directory, AuditReport, Finding, format_report_text, format_report_json
__all__ = ["Config", "simulate", "nozzle_flow", "audit_directory", "AuditReport", "Finding", "format_report_text", "format_report_json"]
__version__ = "0.1.0"
