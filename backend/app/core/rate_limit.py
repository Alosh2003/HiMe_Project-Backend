from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import IPRateLimit

def get_client_ip(request: Request) -> str:
    """استخراج عنوان الـ IP الحقيقي للمستخدم حتى خلف Vercel / Cloudflare"""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def rate_limit_ip(
    max_requests: int = 5,
    window_minutes: int = 60,
    action: str = "otp_request"
):
    """Dependency للتحقق من عدد الطلبات المسموح بها لكل IP"""
    def dependency(request: Request, db: Session = Depends(get_db)):
        client_ip = get_client_ip(request)
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=window_minutes)

        record = (
            db.query(IPRateLimit)
            .filter(IPRateLimit.ip_address == client_ip, IPRateLimit.action == action)
            .first()
        )

        if not record:
            # أول طلب من هذا الـ IP
            new_record = IPRateLimit(
                ip_address=client_ip,
                action=action,
                request_count=1,
                first_request_at=now
            )
            db.add(new_record)
            db.commit()
            return

        # إذا انقضت فترة النافذة الزمنية (ساعة مثلاً)، نعيد تصفير العداد
        if record.first_request_at < window_start:
            record.request_count = 1
            record.first_request_at = now
            db.commit()
            return

        # إذا تجاوز الحد الأقصى خلال نفس النافذة
        if record.request_count >= max_requests:
            remaining_seconds = int((record.first_request_at + timedelta(minutes=window_minutes) - now).total_seconds())
            remaining_min = max(1, remaining_seconds // 60)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests from this network. Please try again after {remaining_min} minutes."
            )

        # زيادة العداد وحفظ السجل
        record.request_count += 1
        db.commit()

    return dependency