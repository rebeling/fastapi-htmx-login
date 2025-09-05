from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.cognito.api.main import login_router
from app.cognito.utils import get_current_user

router = APIRouter(tags=["login"])

templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title="FastAPI HTMX Login",
    description="A authentication demo password, magic link auth using HTMX.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(login_router)


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page(request: Request, user: str = Depends(get_current_user)):
    """Welcome page for authorized user"""
    content = {"request": request, "user": user["email"]}
    return templates.TemplateResponse("welcome.html", content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",  # points to 'app' in main.py
        host="0.0.0.0",  # listen on all interfaces
        port=8000,  # default port
        reload=True,  # auto-reload for dev
    )
