import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
INTERVIEW_DIR = os.path.join(BASE_DIR, "interviews")
DB_PATH = os.path.join(BASE_DIR, "data", "interviewmate.db")
VOICE_DIR = os.path.join(UPLOAD_DIR, "voice")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


DEFAULT_QUESTIONS = [
    "请做一个简短的自我介绍，重点介绍与这个岗位相关的经历。",
    "根据 JD 中的核心技术要求，请分享一个你做过的相关项目，遇到了哪些挑战，如何解决的？",
    "对于这个岗位所需的技术栈，你的理解深度如何？有深入学习过哪些方面？",
    "请描述一次你在团队中解决冲突或推动协作的经历。",
    "你对这个岗位的期望是什么？未来 3 年的职业规划是怎样的？",
    "你有什么问题想问我们吗？",
]

# 面试会话内存存储
chat_sessions: dict[str, dict] = {}
