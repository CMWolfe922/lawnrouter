from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.services.s3_upload import generate_upload_url

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/upload-url")
def upload_url(filename: str, user=Depends(get_current_user)):
    return generate_upload_url(user.company_id, filename)

@router.get("/user-photos")
def user_photos(user=Depends(get_current_user)):
    return {"user": user.username, "company": user.company_id}
