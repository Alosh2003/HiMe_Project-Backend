import os
import uuid
from fastapi import UploadFile, HTTPException

# الامتدادات المسموح بها حسب العقد المتفق عليه (PDF أو DOCX)[cite: 2]
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # الحد الأقصى 5 ميجابايت
UPLOAD_DIR = "uploads/resumes"

# إنشاء مجلد الرفع تلقائياً لو لم يكن موجوداً
os.makedirs(UPLOAD_DIR, exist_ok=True)

class StorageService:
    @staticmethod
    async def save_resume(file: UploadFile) -> str:
        # 1. التحقق من صيغة الملف
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")
        
        # 2. التحقق من حجم الملف
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")
        
        # 3. حفظ الملف باسم فريد لمنع تكرار الأسماء
        filename = f"{uuid.uuid4()}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(contents)
            
        return f"/uploads/resumes/{filename}"