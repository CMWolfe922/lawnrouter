from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.services.s3_upload import generate_upload_url

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/upload-url")
def upload_url(filename: str, user: dict = Depends(get_current_user)):
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")
    return generate_upload_url(company_id, filename)


@router.get("/user-photos")
def user_photos(user: dict = Depends(get_current_user)):
    company_id = user.get("custom:company_id") or user.get("company_id")
    username = user.get("cognito:username") or user.get("username") or user.get("sub")
    return {"user": username, "company": company_id}
