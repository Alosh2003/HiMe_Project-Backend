import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = "HiMe Platform"

def send_verification_email(to_email: str, otp_code: str):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "رمز التحقق الخاص بحسابك",
        "htmlContent": f"""
            <div style="font-family: Arial, sans-serif; direction: rtl; text-align: right; padding: 20px;">
                <h2>مرحباً بك في منصة HiMe 👋</h2>
                <p>رمز التحقق الخاص بحسابك هو:</p>
                <h1 style="color: #2b6cb0; letter-spacing: 5px;">{otp_code}</h1>
                <p>صلاحية هذا الرمز هي <strong>10 دقائق</strong> فقط ⏳.</p>
                <p>إذا لم تطلب هذا الرمز، يمكنك تجاهل هذه الرسالة بأمان.</p>
            </div>
        """
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=10.0)
            if response.status_code != 201:
                print(f"❌ فشل إرسال البريد: {response.text}")
            else:
                print(f"✅ تم إرسال كود التحقق بنجاح إلى: {to_email}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاتصال بخدمة البريد: {e}")