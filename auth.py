from fastapi import Depends, HTTPException
from jose import jwt
import requests
import os

USER_POOL_ID = os.getenv("USER_POOL_ID")
REGION = "us-east-1"

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
JWKS = requests.get(JWKS_URL).json()


def verify_token(token):
    header = jwt.get_unverified_header(token)
    key = next(k for k in JWKS["keys"] if k["kid"] == header["kid"])
    return jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})


def get_current_user(auth: str = Depends(lambda x: x.headers.get("Authorization"))):
    if not auth:
        raise HTTPException(401)

    token = auth.replace("Bearer ", "")
    payload = verify_token(token)
    return payload
