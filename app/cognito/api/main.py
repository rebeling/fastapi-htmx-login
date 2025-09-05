from fastapi import APIRouter

from app.cognito.api.routes import login

login_router = APIRouter()
login_router.include_router(login.router)
