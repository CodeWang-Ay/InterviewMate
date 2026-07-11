import uvicorn
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="InterviewMate")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """模式选择首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/interviewer", response_class=HTMLResponse)
async def interviewer_mode(request: Request):
    """面试官模式页面"""
    return templates.TemplateResponse("interviewer.html", {"request": request})


@app.get("/interviewee", response_class=HTMLResponse)
async def interviewee_mode(request: Request):
    """面试者模式页面"""
    return templates.TemplateResponse("interviewee.html", {"request": request})


if __name__ == "__main__":
    # webbrowser.open("http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
