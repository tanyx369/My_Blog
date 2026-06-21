from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError # handle validation error 
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# FastAPI is built on top of Starlette 
# IF we just use the HTTPException from fastapi then it will only catch the error built in our script 
# Hence we need to use the exception from starlette to capture other exception that are not stated in our script 
from starlette.exceptions import HTTPException as StarletteHTTPException 
from sqlalchemy import select, func  # Help us to do query
from sqlalchemy.orm import Session, selectinload  # Session use for type hints 
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

# from app.schemas import PostCreate, PostResponse, PostUpdate, UserResponse, UserCreate, UserUpdate (we no longer use them here after using router)
from app.database import Base, engine, get_db # Base & engine help us to create table ; get_db provides database sessions 
import app.models as models
from config import settings
from routers import posts, users
from typing import Annotated

# Create database tables
# This look at all the models inherited from Base and create table if haven't created 
# If the table already exists, then nothing happen

# Base.metadata.create_all(bind=engine) synchronus method 

# asynchronus method 
@asynccontextmanager
async def lifespan(_app:FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    
    # shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan) 

# app.mount('_directory_', StaticFiles(directory='directory_name'), name=ref_name_for_use_in_template)
app.mount("/static", StaticFiles(directory='static'), name='static')
app.mount('/media', StaticFiles(directory='media'), name='media')

# We save our templates in the 'templates' folder and use JinJa2 object to access them
templates = Jinja2Templates(directory="templates")

app.include_router(users.router, prefix='/api/users', tags=['users'])
app.include_router(posts.router, prefix='/api/posts', tags=['posts'])
# FastAPI uses function name as default to search for route
# Hence the template function names should not be the same as router function name


### Sample Data (no need after we have a proper database)

# posts: list[dict] = [
#     {
#         "id": 1,
#         "author": "Corey Schafer",
#         "title": "FastAPI is Awesome",
#         "content": "This framework is really easy to use and super fast.",
#         "date_posted": "April 20, 2025",
#     },
#     {
#         "id": 2,
#         "author": "Jane Doe",
#         "title": "Python is Great for Web Development",
#         "content": "Python is a great language for web development, and FastAPI makes it even better.",
#         "date_posted": "April 21, 2025",
#     },
# ]


##### Main Functions (Template routes) ######

##### (1) #####

# By stacking two route, we can make that the two endpoints will lead to the same function
# @app.get("/", response_class=HTMLResponse)
# @app.get("/posts", response_class=HTMLResponse)

# Now we are using Jinja2 templates 
@app.get("/", include_in_schema=False, name='home')
@app.get("/posts", include_in_schema=False, name='posts')
# If we did not set the name for route explicitly, the url_for() will just use the function name as reference and use the lastest route we define in the script
# If we set the name, then url_for() will refer to the name of the routes instead of the function name
async def home(request:Request, db:Annotated[AsyncSession, Depends(get_db)]):
    # return({'message':'Hello World'})
    # return(f"<h1>This is my website</h1>")
    # return(templates.TemplateResponse(request, 'home.html', context={"posts":posts, "title":"Home"}))
    # result = db.execute(select(models.Post))
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).order_by(models.Post.date_posted.desc()))  
    posts = result.scalars().all()
    return(templates.TemplateResponse(request, 'home.html', context={"posts":posts, "title":"Home"}))

##### (2) #####

## post_page
@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

#### (3) ####

## user_posts_page
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id)) # Here we don't need relevant relationship object, so no need selectinload
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )
    

## login and register template_routes
@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


@app.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(
        request,
        "account.html",
        {"title": "Account"},
    )

##### API Endpoints for documentation ######




##### Exception Handler ######
# create a general exception handler and lead to the error page template

## StarletteHTTPException Handler
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    

    if request.url.path.startswith("/api"):
        # return JSONResponse(
        #     status_code=exception.status_code,
        #     content={"detail": message},
        # )
        return(await http_exception_handler(request, exception))
    
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )
    
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,  # we need to pass in so that to ensure the browser will get the correct status code, otherwise it will assume successful since we have smth return to it 
    )

# Since starlette can capture any exception, we no need to specify the href in error.html.
# Once the fastapi captured error, it will directly lead to @app.exception_handler(StarletteHTTPException)

### RequestValidationError Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        # return JSONResponse(
        #     status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        #     content={"detail": exception.errors()},
        # )
        return(await request_validation_exception_handler(request, exception))
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
