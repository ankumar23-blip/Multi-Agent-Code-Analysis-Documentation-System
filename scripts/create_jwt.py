# simple utility to create a demo JWT
import os, time
from jose import jwt
secret = os.getenv('JWT_SECRET','change-me')
payload = {
    'sub':'demo_user',
    'role':'admin',
    'iat': int(time.time()),
    'exp': int(time.time()) + 3600
}
token = jwt.encode(payload, secret, algorithm='HS256')
print(token)
