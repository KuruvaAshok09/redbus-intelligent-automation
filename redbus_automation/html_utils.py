"""Helpers for safely rendering untrusted text in HTML contexts."""

from html import escape


def escape_html(value: object) -> str:
    """Escapes text and quotes before interpolation into HTML markup."""
    return escape(str(value), quote=True)
