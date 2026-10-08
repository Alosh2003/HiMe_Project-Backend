
from passlib.context import CryptContext
import hashlib
import secrets
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # قص كلمة المرور تلقائياً لو تجاوزت 72 حرفاً لمنع خطأ bcrypt
    safe_password = password[:72]
    return pwd_context.hash(safe_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    safe_password = plain_password[:72]
    return pwd_context.verify(safe_password, hashed_password)



def generate_otp(length: int = 6) -> tuple[str, str]:
    plain_code = "".join(secrets.choice("0123456789") for _ in range(length))
    code_hash = hashlib.sha256(plain_code.encode("utf-8")).hexdigest()
    return plain_code, code_hash