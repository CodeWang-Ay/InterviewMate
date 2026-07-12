from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.repositories import user_repo

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str
    nickname: str = ""


@router.post("/register")
async def register(body: RegisterBody):
    if not body.username.strip() or len(body.username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    result = user_repo.register(body.username.strip(), body.password, body.nickname.strip())
    if result is None:
        raise HTTPException(status_code=400, detail="用户名已存在或密码过短（至少6位）")
    return {"status": "ok", "user": result}


@router.post("/login")
async def login(body: LoginBody):
    result = user_repo.login(body.username.strip(), body.password)
    if result is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"status": "ok", **result}


@router.post("/logout")
async def logout(body: LoginBody):
    # 简单实现：token 通过 header 传
    return {"status": "ok"}
