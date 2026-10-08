from sqlalchemy.orm import declarative_base

# هذا الكائن ترث منه كل الـ Models عشان يتعرف عليها محرك SQLAlchemy
Base = declarative_base()