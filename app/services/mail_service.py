import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


class MailDeliveryError(ValueError):
    """Raised when the application cannot deliver an email via SMTP."""


class MailService:
    def _is_production(self) -> bool:
        return settings.ENVIRONMENT.strip().lower() == "production"

    def _is_placeholder_value(self, value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in {
            "your_email@gmail.com",
            "your_app_password",
        } or normalized.startswith("replace_with_")

    def _log_dev_reset_code(self, to_email: str, code: str, reason: str) -> None:
        logger.warning(
            "Password reset email skipped (%s). DEV fallback code for %s: %s",
            reason,
            to_email,
            code,
        )

    async def send_password_reset_code(self, to_email: str, code: str, expires_minutes: int) -> None:
        if not settings.SMTP_ENABLED:
            if self._is_production():
                raise MailDeliveryError("SMTP is disabled")
            self._log_dev_reset_code(to_email, code, "SMTP disabled")
            return

        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            if self._is_production():
                raise MailDeliveryError("SMTP credentials are missing")
            self._log_dev_reset_code(to_email, code, "SMTP credentials missing")
            return

        if self._is_placeholder_value(settings.SMTP_USERNAME) or self._is_placeholder_value(settings.SMTP_PASSWORD):
            if self._is_production():
                raise MailDeliveryError("SMTP credentials are placeholders. Update SMTP_USERNAME and SMTP_PASSWORD in .env")
            self._log_dev_reset_code(to_email, code, "SMTP placeholder credentials")
            return

        message = EmailMessage()
        message["Subject"] = "Smart Classroom - Password Reset Code"
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message.set_content(
            (
                "We received a request to reset your password.\n\n"
                f"Your verification code is: {code}\n"
                f"This code expires in {expires_minutes} minutes.\n\n"
                "If you did not request this, you can safely ignore this email."
            )
        )

        try:
            await asyncio.to_thread(self._send_message, message)
        except MailDeliveryError:
            raise
        except Exception as exc:
            raise MailDeliveryError("Unable to send reset email. Please check SMTP configuration") from exc

    def _send_message(self, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise MailDeliveryError("Unable to send reset email. Please check SMTP host, port, username, password and TLS settings") from exc


mail_service = MailService()
