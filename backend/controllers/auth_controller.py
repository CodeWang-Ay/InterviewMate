import os
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import UPLOAD_DIR
from backend.repositories import admin_repo, candidate_repo

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)


def _read_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="无效的Token")
    return token


def get_current_admin(authorization: str | None = Header(None)) -> str:
    token = _read_token(authorization)
    username = admin_repo.get_admin_by_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期")
    return username


def get_current_candidate(authorization: str | None = Header(None)) -> str:
    token = _read_token(authorization)
    username = candidate_repo.get_candidate_by_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期")
    return username


def get_current_identity(authorization: str | None = Header(None)) -> dict:
    token = _read_token(authorization)
    admin_username = admin_repo.get_admin_by_token(token)
    if admin_username:
        admin = admin_repo.get_admin_info(admin_username)
        if not admin:
            raise HTTPException(status_code=401, detail="管理员不存在")
        return {"kind": "admin", "username": admin_username, "profile": admin}

    candidate_username = candidate_repo.get_candidate_by_token(token)
    if candidate_username:
        candidate = candidate_repo.get_candidate_info(candidate_username)
        if not candidate:
            raise HTTPException(status_code=401, detail="候选人不存在")
        return {"kind": "candidate", "username": candidate_username, "profile": candidate}

    raise HTTPException(status_code=401, detail="登录已过期")


def get_current_admin_info(username: str = Depends(get_current_admin)) -> dict:
    user = admin_repo.get_admin_info(username)
    if not user:
        raise HTTPException(status_code=401, detail="管理员不存在")
    return user


def require_admin(user: dict = Depends(get_current_admin_info)) -> dict:
    return user


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str
    nickname: str = ""


class ProfileUpdate(BaseModel):
    nickname: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    bio: str = ""


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.post("/register")
async def register(body: RegisterBody):
    if not body.username.strip() or len(body.username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    result = admin_repo.register(body.username.strip(), body.password, body.nickname.strip())
    if result is None:
        raise HTTPException(status_code=400, detail="用户名已存在或密码过短（至少6位）")
    return {"status": "ok", "user": result}


@router.post("/login")
async def login(body: LoginBody):
    result = admin_repo.login(body.username.strip(), body.password)
    if result is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"status": "ok", **result}


@router.post("/candidate-login")
async def candidate_login(body: LoginBody):
    result = candidate_repo.login(body.username.strip(), body.password)
    if result is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"status": "ok", **result}


@router.get("/session")
async def session_info(identity: dict = Depends(get_current_identity)):
    profile = identity.get("profile", {})
    return {
        "status": "ok",
        "kind": identity["kind"],
        "username": identity["username"],
        "nickname": profile.get("nickname") or profile.get("candidate_name") or identity["username"],
        "role": "admin" if identity["kind"] == "admin" else "candidate",
    }


@router.post("/logout")
async def logout(body: LoginBody):
    return {"status": "ok"}


@router.put("/profile")
async def update_profile(body: ProfileUpdate, username: str = Depends(get_current_admin)):
    if not body.nickname.strip():
        raise HTTPException(status_code=400, detail="昵称不能为空")
    data = {k: v.strip() for k, v in body.model_dump().items() if v.strip()}
    admin_repo.update_profile(username, data)
    return {"status": "ok", **data}


@router.put("/password")
async def change_password(body: PasswordChange, username: str = Depends(get_current_admin)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    ok = admin_repo.change_password(username, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="当前密码错误")
    return {"status": "ok"}


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), username: str = Depends(get_current_admin)):
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
    admin_repo.update_avatar(username, avatar_url)
    return {"avatar_url": avatar_url}
