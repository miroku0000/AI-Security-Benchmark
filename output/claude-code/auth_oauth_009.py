from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis

app = FastAPI()
security = HTTPBearer()

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_data = redis_client.get(f"token:{token}")
    if user_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"token": token, "user_data": user_data}


@app.get("/protected")
async def protected_route(token_data: dict = Depends(validate_token)):
    return {"message": "Access granted", "user": token_data["user_data"]}


@app.get("/health")
async def health():
    return {"status": "ok"}