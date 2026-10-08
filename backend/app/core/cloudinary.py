import cloudinary
from app.core.config import settings
from cloudinary import uploader# Initialize Cloudinary using environment-driven settings
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

__all__ = ["cloudinary", "uploader"]