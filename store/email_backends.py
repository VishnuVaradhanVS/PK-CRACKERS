"""Django email backend for Resend's HTTPS Email API.

Uses only Python's standard library so it works on Render Free without SMTP
connectivity and without adding another runtime dependency.
"""

import base64
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage instances through https://api.resend.com/emails."""

    api_url = "https://api.resend.com/emails"

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, "RESEND_API_KEY", "")
        self.timeout = getattr(settings, "EMAIL_TIMEOUT", 10)

    def open(self):
        # HTTPS requests are opened per message by urllib; no persistent socket.
        if not self.api_key:
            raise RuntimeError("EMAIL_PROVIDER is 'resend' but RESEND_API_KEY is not configured.")
        return True

    def close(self):
        return None

    @staticmethod
    def _attachment_payload(attachment):
        """Convert Django's supported attachment forms to Resend's API shape."""
        if isinstance(attachment, tuple):
            filename, content, mimetype = attachment
            if isinstance(content, str):
                content = content.encode("utf-8")
            result = {
                "filename": filename,
                "content": base64.b64encode(content).decode("ascii"),
            }
            if mimetype:
                result["content_type"] = mimetype
            return result

        # MIMEBase / MIMEText attachment objects.
        filename = attachment.get_filename() or "attachment"
        content = attachment.get_payload(decode=True)
        if content is None:
            content = attachment.as_bytes()
        result = {
            "filename": filename,
            "content": base64.b64encode(content).decode("ascii"),
        }
        content_type = attachment.get_content_type()
        if content_type:
            result["content_type"] = content_type
        return result

    def _payload_for(self, message):
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to or []),
            "subject": message.subject or "",
            "text": message.body or "",
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        html_parts = [content for content, mimetype in getattr(message, "alternatives", [])
                      if mimetype == "text/html"]
        if html_parts:
            payload["html"] = str(html_parts[-1])

        headers = getattr(message, "extra_headers", None) or {}
        if headers:
            payload["headers"] = {str(key): str(value) for key, value in headers.items()}

        attachments = getattr(message, "attachments", None) or []
        if attachments:
            payload["attachments"] = [self._attachment_payload(item) for item in attachments]
        return payload

    def _send(self, message):
        if not message.recipients():
            return False
        if not self.api_key:
            raise RuntimeError("RESEND_API_KEY is not configured.")

        body = json.dumps(self._payload_for(message)).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PK-Crackers-Django/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"Resend API returned HTTP {response.status}: {response_body[:1000]!r}")
                return True
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Resend API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not connect to Resend API: {exc.reason}") from exc

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            if self.fail_silently:
                logger.error("Resend email backend selected but RESEND_API_KEY is missing.")
                return 0
            self.open()

        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Email delivery through Resend failed.")
        return sent
