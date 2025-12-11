from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
import os

security = HTTPBearer()
JWT_SECRET = os.getenv('JWT_SECRET', 'change-me')

def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail='Invalid token')

def require_role(role: str):
    def dependency(credentials: HTTPAuthorizationCredentials = Security(security)):
        token = credentials.credentials
        payload = decode_token(token)
        if payload.get('role') != role:
            raise HTTPException(status_code=403, detail='Insufficient role')
        return payload
    return dependency
