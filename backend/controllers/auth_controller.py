import os
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import UPLOAD_DIR
from backend.repositories import user_repo

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)


def get_current_user(authorization: str | None = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="无效的Token")
    username = user_repo.get_user_by_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期")
    return username


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str
    nickname: str = ""


class ProfileUpdate(BaseModel):
    nickname: str = ""


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


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
    return {"status": "ok"}


@router.put("/profile")
async def update_profile(body: ProfileUpdate, username: str = Depends(get_current_user)):
    if not body.nickname.strip():
        raise HTTPException(status_code=400, detail="昵称不能为空")
    user_repo.update_profile(username, body.nickname.strip())
    return {"status": "ok", "nickname": body.nickname.strip()}


@router.put("/password")
async def change_password(body: PasswordChange, username: str = Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    ok = user_repo.change_password(username, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="当前密码错误")
    return {"status": "ok"}


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), username: str = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or ".png")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPG/GIF/WEBP 格式")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像不能超过 5MB")
    filename = f"avatar_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    avatar_url = f"/uploads/avatars/{filename}"
    user_repo.update_avatar(username, avatar_url)
    return {"avatar_url": avatar_url}
