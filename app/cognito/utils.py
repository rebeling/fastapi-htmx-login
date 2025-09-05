from fastapi import HTTPException, Request
from jose import JWTError, jwt
from starlette.responses import RedirectResponse

from config import SECRET_KEY

ALGORITHM = "HS256"


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/"})

    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract multiple fields
        user_data = {
            "email": payload.get("sub"),
            # "tenant": payload.get("tenant"),
            # "role": payload.get("role"),
            # "version": payload.get("version"),
        }

        if not user_data["email"]:
            raise JWTError

        return user_data
    except JWTError as err:
        response = RedirectResponse(url="/")
        response.delete_cookie("access_token")
        raise HTTPException(
            status_code=302,
            headers={"Location": "/"},
            detail="Invalid or expired token",
        ) from err
