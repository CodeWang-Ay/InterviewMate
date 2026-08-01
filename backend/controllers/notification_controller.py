from fastapi import APIRouter, Depends, HTTPException

from backend.controllers.auth_controller import get_current_candidate
from backend.repositories import notification_repo

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(username: str = Depends(get_current_candidate)):
    return notification_repo.list_by_candidate(username)


@router.post("/{notification_id}/read")
async def read_notification(notification_id: int, username: str = Depends(get_current_candidate)):
    if not notification_repo.mark_read(notification_id, username):
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"status": "ok"}


@router.post("/read-all")
async def read_all_notifications(username: str = Depends(get_current_candidate)):
    notification_repo.mark_all_read(username)
    return {"status": "ok"}
