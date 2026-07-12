from pydantic import BaseModel


class JDContent(BaseModel):
    content: str


class ResumeParse(BaseModel):
    resume_filename: str


class PlanGenerate(BaseModel):
    jd_filename: str
    resume_filename: str


class ChatStart(BaseModel):
    jd_filename: str
    resume_filename: str


class ChatMessage(BaseModel):
    session_id: str
    message: str
