import os
from typing import List, Optional

from django.conf import settings

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except Exception:  # pragma: no cover - optional dependency in dev
    SendGridAPIClient = None
    Mail = None


def send_email(to_emails: List[str], subject: str, html_content: str, from_email: Optional[str] = None) -> None:
    """Send an email using SendGrid.

    Requires SENDGRID_API_KEY in settings. No-op if dependency or key missing.
    """
    api_key = getattr(settings, 'SENDGRID_API_KEY', '')
    if not api_key or SendGridAPIClient is None or Mail is None:
        return

    sender = from_email or getattr(settings, 'SENDGRID_FROM_EMAIL', 'no-reply@example.com')

    message = Mail(
        from_email=sender,
        to_emails=to_emails,
        subject=subject,
        html_content=html_content,
    )

    sg = SendGridAPIClient(api_key)
    # EU Residency pinning if configured
    if getattr(settings, 'SENDGRID_EU_RESIDENCY', False):
        try:
            sg.set_sendgrid_data_residency("eu")
        except Exception:
            pass

    sg.send(message)


