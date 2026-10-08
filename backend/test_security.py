from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, decode_access_token

# 1. تجربة التشفير
password = "MyPassword123"
hashed = hash_password(password)

print(f"🔑   plain text: {password}")
print(f"🔒 encrypted text   : {hashed}")

# 2. تجربة المطابقة
is_valid = verify_password("MyPassword123", hashed)
print(f"  if pass correct ?{is_valid}")

# 3. تجربة إنشاء JWT Token
dummy_data = {"sub": "user_id_12345", "role": "job_seeker"}
token = create_access_token(dummy_data)
print({token})

# 4. تجربة فك تشفير الـ Token
decoded = decode_access_token(token)
print(f"token{decoded}")