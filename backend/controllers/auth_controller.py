import os
import uuid
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.config import UPLOAD_DIR
from backend.repositories import admin_repo, application_repo, candidate_repo, favorite_repo, plan_repo, resume_repo

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
    remember_me: bool = False


class RegisterBody(BaseModel):
    username: str
    password: str
    nickname: str = ""
    phone: str = ""


class ProfileUpdate(BaseModel):
    nickname: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    bio: str = ""


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class CandidateProfileUpdate(BaseModel):
    candidate_name: str
    email: str = ""
    phone: str = ""


class CandidatePasswordReset(BaseModel):
    username: str
    phone: str
    new_password: str


class CandidateAccountDelete(BaseModel):
    password: str


def _validate_candidate_contact(name: str, phone: str, email: str) -> None:
    if not name.strip():
        raise HTTPException(status_code=400, detail="姓名不能为空")
    if phone and (not phone.isdigit() or len(phone) != 11):
        raise HTTPException(status_code=400, detail="请输入正确的11位手机号")
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=400, detail="请输入正确的邮箱地址")


@router.post("/register")
async def register(body: RegisterBody):
    if not body.username.strip() or len(body.username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    phone = body.phone.strip()
    if phone and (not phone.isdigit() or len(phone) != 11):
        raise HTTPException(status_code=400, detail="请输入正确的11位手机号")
    result = candidate_repo.register(body.username.strip(), body.password, body.nickname.strip(), phone)
    if result is None:
        raise HTTPException(status_code=400, detail="用户名已存在或密码过短（至少6位）")
    return {"status": "ok", "user": result}


@router.post("/login")
async def login(body: LoginBody):
    result = admin_repo.login(body.username.strip(), body.password, body.remember_me)
    if result is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"status": "ok", **result}


@router.post("/candidate-login")
async def candidate_login(body: LoginBody):
    result = candidate_repo.login(body.username.strip(), body.password, body.remember_me)
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
        "avatar": profile.get("avatar") or "",
        "phone": profile.get("phone") or "",
        "email": profile.get("email") or "",
        "company": profile.get("company") or "",
        "bio": profile.get("bio") or "",
    }


@router.post("/logout")
async def logout(authorization: str | None = Header(None)):
    token = _read_token(authorization)
    admin_repo.logout(token)
    candidate_repo.logout(token)
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


@router.put("/candidate-profile")
async def update_candidate_profile(body: CandidateProfileUpdate, username: str = Depends(get_current_candidate)):
    data = {key: value.strip() for key, value in body.model_dump().items()}
    _validate_candidate_contact(data["candidate_name"], data["phone"], data["email"])
    if not candidate_repo.update_profile(username, data):
        raise HTTPException(status_code=404, detail="候选人不存在")
    return {"status": "ok", **data}


@router.put("/candidate-password")
async def change_candidate_password(body: PasswordChange, username: str = Depends(get_current_candidate)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    if not candidate_repo.change_password(username, body.old_password, body.new_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    return {"status": "ok", "message": "密码修改成功，请重新登录"}


@router.post("/candidate-password/reset")
async def reset_candidate_password(body: CandidatePasswordReset):
    username = body.username.strip()
    phone = body.phone.strip()
    if not username or not phone:
        raise HTTPException(status_code=400, detail="请输入用户名和注册手机号")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    if not candidate_repo.reset_password_by_phone(username, phone, body.new_password):
        raise HTTPException(status_code=400, detail="用户名与注册手机号不匹配")
    return {"status": "ok", "message": "密码已重置，请使用新密码登录"}


@router.get("/candidate-data-export")
async def export_candidate_data(username: str = Depends(get_current_candidate)):
    profile = candidate_repo.get_candidate_info(username) or {}
    profile.pop("password_hash", None)
    payload = {
        "exported_at": datetime.now().astimezone().isoformat(),
        "profile": profile,
        "applications": application_repo.list_by_candidate_username(username),
        "plans": plan_repo.list_by_candidate_username(username),
        "resumes": resume_repo.list_by_candidate_username(username),
        "favorites": favorite_repo.list_by_candidate(username),
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="InterviewMate-{username}-data.json"'},
    )


@router.delete("/candidate-account")
async def delete_candidate_account(body: CandidateAccountDelete, username: str = Depends(get_current_candidate)):
    candidate = candidate_repo.login(username, body.password)
    if not candidate:
        raise HTTPException(status_code=400, detail="密码错误，无法注销账号")
    candidate_repo.logout(candidate["token"])
    if not candidate_repo.delete_account(username):
        raise HTTPException(status_code=404, detail="候选人不存在")
    return {"status": "ok", "message": "账号及个人业务数据已删除"}


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


@router.post("/candidate-avatar")
async def upload_candidate_avatar(file: UploadFile = File(...), username: str = Depends(get_current_candidate)):
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
    candidate_repo.update_profile(username, {"avatar": avatar_url})
    return {"avatar_url": avatar_url}
