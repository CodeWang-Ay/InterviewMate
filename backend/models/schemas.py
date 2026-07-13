from pydantic import BaseModel


class JDContent(BaseModel):
    content: str


class ResumeParse(BaseModel):
    resume_filename: str


class PlanGenerate(BaseModel):
    jd_filename: str
    resume_filename: str


class ChatStart(BaseModel):
    jd_filename: str = ""
    resume_filename: str = ""
    plan_id: int | None = None


class ChatMessage(BaseModel):
    session_id: str
    message: str


class InterviewerTrainingStart(BaseModel):
    jd_id: int
    resume_id: int
    training_mode: str = "结构化面试"
    candidate_style: str = "标准型"


class InterviewerTrainingMessage(BaseModel):
    session_id: str
    message: str
