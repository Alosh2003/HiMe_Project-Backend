from pydantic import BaseModel
from typing import Optional, Any, List

class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[List[str]] = None