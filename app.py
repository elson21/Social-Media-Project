from fastapi import FastAPI, Form, status, Depends, Cookie, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.requests import Request
from fastapi.security import OAuth2
from fastapi.staticfiles import StaticFiles
from sqlite3 import Connection, Row
from secrets import token_hex
from passlib.hash import pbkdf2_sha256
from typing import Annotated
from uuid import uuid4
from pathlib import Path
import jwt

from database import (
            get_post,
            insert_post,
            create_user,
            get_user,
            add_like,
            get_single_post,
            check_like,
            delete_like,
            add_comment,
            get_comments
        )
from models import Post, UserPost, UserHashed, Like, PostId, UserPostId

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), "static")
connection = Connection("social.db")
connection.row_factory = Row

templates = Jinja2Templates("./templates")
JWT_KEY = "7e488e36d708c05f2bf6fccfac954d17528b888ae23fa617c818feb29cf2aea7"
EXPIRATION_TIME = 3600
ALGORITHM = "HS256"


def decrypt_access_token(access_token: str, ):
    _,token = access_token.split()
    data = jwt.decode(token, JWT_KEY, algorithms=[ALGORITHM])
    return data

class OAuthCookie(OAuth2):
    def __call__(self, request: Request) -> int:
        data = decrypt_access_token(request.cookies.get("access_token"))
        return data["user_id"]


oauth_cookie = OAuthCookie()

@app.get("/")
async def home(request: Request, access_token: Annotated[str | None, Cookie()]=None) -> HTMLResponse:
    context = get_post(connection).model_dump()
    context["login"] = False

    if access_token:
        context["login"] = True

    return templates.TemplateResponse(
        request, 
        "./index.html",
        context=context
    )

@app.get("/posts")
async def posts(
            request: Request,
            access_token: Annotated[str | None, Cookie()]=None
        ) -> HTMLResponse:
    user_id = None
    if access_token:
        user_id = decrypt_access_token(access_token)["user_id"]

    context = get_post(connection, user_id).model_dump()

    if access_token:
        context["login"] = True

    return templates.TemplateResponse(
        request,
        "./posts.html",
        context=context
    )


@app.post("/post")
async def add_post(post_title: Annotated[str, Form()],
                   post_text: Annotated[str, Form()],
                   request: Request,
                   post_image: UploadFile|None = File(None),
                   user_id: int=Depends(oauth_cookie)
                ) -> HTMLResponse:
    
    image_path = None

    if post_image is not None:
        image_path = Path("./static/images") / uuid4().hex
        image_data = await post_image.read()
        image_path.write_bytes(image_data)
        image_path = image_path.name

    post = UserPostId(
                    user_id=user_id,
                    post_title=post_title,
                    post_text=post_text,
                    post_image=image_path
                )
    insert_post(connection, post)
    context = {"post_added": True}

    return templates.TemplateResponse(
        request,
        "./add_post.html",
        context=context
    )


@app.get("/login")
async def login(request: Request) -> HTMLResponse:
    context = {"login": True}
    return templates.TemplateResponse(request, "./login.html", context=context)


@app.post("/login")
async def add_user(username: Annotated[str, Form()], password: Annotated[str, Form()], request: Request) -> HTMLResponse:
    user = get_user(connection, username)
    correct_password = pbkdf2_sha256.verify(password + user.salt, user.hash_password)

    if user is None or not correct_password:
        return templates.TemplateResponse(
                        request,
                        "./login.html",
                        context={"incorrect": True}
                    )

    token = jwt.encode({
        "username": username,
        "user_id" : user.user_id
        },
        JWT_KEY,
        algorithm=ALGORITHM
    )

    response = RedirectResponse("./", status.HTTP_303_SEE_OTHER)
    response.set_cookie(
                        "access_token",
                        f"Bearer {token}",
                        samesite="lax",
                        expires=EXPIRATION_TIME,
                        httponly=True,
                        # secure=True
                    )
    
    return response


@app.get("/logout")
async def logout(response: RedirectResponse) -> HTMLResponse:
    response = RedirectResponse("./login")
    response.delete_cookie("access_token")

    return response


@app.get("/signup")
async def signup(request: Request) -> HTMLResponse:
    context = {"login": False}
    return templates.TemplateResponse(request, "./signup.html", context=context)


@app.post("/signup")
async def add_user(username: Annotated[str, Form()], password: Annotated[str, Form()], request: Request) -> HTMLResponse:
    if get_user(connection, username) is not None:
        return templates.TemplateResponse(
                        request,
                        "./signup.html",
                        context={"taken": True, "username": username}
                    )

    hex_int = 15
    salt = token_hex(hex_int)
    
    # hashs user password
    hash_password = pbkdf2_sha256.hash(password + salt)   

    # update db
    hashed_user = UserHashed(
                    username=username,
                    salt=salt,
                    hash_password=hash_password
                )
    
    create_user(connection, hashed_user)

    return RedirectResponse("./login", status.HTTP_303_SEE_OTHER)


@app.post("/like")
async def upload_like(
                    post_id: PostId,
                    request: Request, 
                    user_id: int=Depends(oauth_cookie),
                ) -> HTMLResponse:
    like = Like(user_id=user_id, post_id=post_id.post_id)

    if check_like(connection, like):
        delete_like(connection, like)
    else:
        add_like(connection, like)

    context = get_single_post(connection, post_id.post_id, user_id).model_dump()
    context = {"post": context}
    context["login"] = True
    return templates.TemplateResponse(request, "./post.html", context=context)

@app.get("/add_comment_form_{post_id}")
async def add_comment_form(
                        post_id: int,
                        request: Request,
                        user_id: int=Depends(oauth_cookie)
                    ) -> HTMLResponse:
    
    context = get_single_post(connection, post_id, user_id).model_dump()
    context = {"post": context}
    context["comment_form"] = True
    context["login"] = True

    return templates.TemplateResponse(request, "./post.html", context=context)


@app.post("/add_comment_{post_id}")
async def add_comment_form(
                        post_id: int,
                        request: Request,
                        post: UserPost,
                        user_id: int=Depends(oauth_cookie)
                    ) -> HTMLResponse:
    
    post = UserPostId(user_id=user_id, **post.model_dump())
    comment_id = insert_post(connection, post)
    add_comment(connection, comment_id, post_id)

    context = get_single_post(connection, post_id, user_id).model_dump()
    context = {"post": context}
    context["comment_form"] = False
    context["login"] = True

    return templates.TemplateResponse(request, "./post.html", context=context)


def get_comment_thread_helper(
                            access_token: str|None,
                            post_id: int,
                            hide: bool=False
                        ) -> dict:
    user_id = None
    context = {}

    if access_token:
        user_id = decrypt_access_token(access_token)["user_id"]
        context["login"] = True

    context["main_post"] =  {"posts": [get_single_post(connection, post_id, user_id).model_dump()]}
    context["main_post"]["posts"][0]["hide_see_comments"] = not hide

    if hide:
        return context
    
    comments = get_comments(connection, post_id, user_id).model_dump()
    context["comments"] = comments

    return context


@app.get("/get_thread{post_id}")
async def get_thread(
                    post_id: int,
                    request: Request,
                    access_token: Annotated[str|None, Cookie()]=None
                ) -> HTMLResponse:
    
    context = get_comment_thread_helper(access_token, post_id)

    return templates.TemplateResponse(request, "./comment_thread.html", context=context)


@app.get("/hide_thread{post_id}")
async def hide_thread(
                    post_id: int,
                    request: Request,
                    access_token: Annotated[str|None, Cookie()]=None
                ) -> HTMLResponse:
    
    context = get_comment_thread_helper(access_token, post_id, hide=True)

    return templates.TemplateResponse(request, "./comment_thread.html", context=context)