from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from models import InterviewBooking
from settings import settings
from utils.logger import get_logger

logger = get_logger()


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.hostname = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL

    async def _send(self, msg: MIMEMultipart) -> bool:
        try:
            await aiosmtplib.send(
                msg,
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                start_tls=True,
            )
            return True
        except aiosmtplib.SMTPException as e:
            logger.error(
                "Failed to send email", extra={"error": str(e), "to": msg["To"]}
            )
            return False

    def _base_message(self, to: str, subject: str) -> MIMEMultipart:
        """Create a base MIME message with common headers."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to
        return msg

    async def send_interview_booking_confirmation(
        self, booking: InterviewBooking
    ) -> bool:
        """Send an interview booking confirmation email to candidate."""
        msg = self._base_message(
            to=booking.email,
            subject="Interview Booking Confirmation",
        )
        plain = f"""
        Hello {booking.full_name},
        
        Your interview booking has been confirmed. Please find the details below:
        
        Date: {booking.interview_date.strftime("%B %d, %Y")}
        Time: {booking.interview_time.strftime("%I:%M %p")}
        
        Thank you,
        {settings.APP_NAME}
        """.strip()

        html = f"""
        <html>
            <body>
                <p>Hello <strong>{booking.full_name}</strong>,</p>
                <p>Your interview booking has been confirmed. Please find the details below:</p>
                <ul>
                    <li>Date: {booking.interview_date.strftime("%B %d, %Y")}</li>
                    <li>Time: {booking.interview_time.strftime("%I:%M %p")}</li>
                </ul>
                <p>Thank you,</p>
                <p>{settings.APP_NAME}</p>
            </body>
        </html>
        """.strip()

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))
        success = await self._send(msg)
        if success:
            logger.info(
                "Email sent successfully",
                extra={"to": booking.email, "booking_id": booking.id},
            )

        return success
