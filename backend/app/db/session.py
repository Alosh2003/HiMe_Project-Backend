from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# إنشاء محرك الاتصال برابط قاعدة البيانات
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# تجهيز الجلسات
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# دالة يجيب منها السيرفر جلسة اتصل ويرجع يسكرها بعد الانتهاء
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()