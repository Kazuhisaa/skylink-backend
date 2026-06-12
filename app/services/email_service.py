import logging

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.settings import settings

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
)


async def send_verification_email(email: str, token: str):
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html = f"""
    <p>Thanks for using Skylink!</p>
    <p>Please click the link below to verify your email address:</p>
    <a href="{verification_url}">{verification_url}</a>
    """

    message = MessageSchema(
        subject="Skylink Email Verification",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")


async def send_password_reset_email(email: str, otp: str):
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 500px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        <div style="background-color: #1a73e8; padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px; letter-spacing: 1px;">Skylink Airlines</h1>
        </div>
        <div style="padding: 40px 30px; background-color: white;">
            <h2 style="color: #202124; margin-top: 0; font-size: 20px; text-align: center;">Password Reset Request</h2>
            <p style="color: #5f6368; line-height: 1.5; font-size: 16px; text-align: center;">
                You requested to reset your password. Use the verification code below to proceed:
            </p>
            <div style="background-color: #f8f9fa; border: 1px dashed #dadce0; border-radius: 8px; padding: 20px; margin: 30px 0; text-align: center;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: bold; color: #1a73e8; letter-spacing: 8px;">
                    {otp}
                </span>
            </div>
            <p style="color: #5f6368; font-size: 14px; text-align: center; margin-bottom: 0;">
                This code will expire in <strong>10 minutes</strong>.
            </p>
            <p style="color: #9aa0a6; font-size: 12px; text-align: center; margin-top: 30px;">
                If you did not request this, please ignore this email or contact support if you have concerns.
            </p>
        </div>
        <div style="background-color: #f1f3f4; padding: 20px; text-align: center;">
            <p style="color: #70757a; font-size: 12px; margin: 0;">&copy; 2026 Skylink Airlines. All rights reserved.</p>
        </div>
    </div>
    """

    message = MessageSchema(
        subject="Skylink Password Reset Code",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Password reset OTP sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset OTP to {email}: {str(e)}")
