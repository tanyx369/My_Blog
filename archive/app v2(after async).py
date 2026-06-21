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
from sqlalchemy import select # Help us to do query
from sqlalchemy.orm import Session # Use for type hints 
from contextlib import asynccontextmanager

from app.schemas import PostCreate, PostResponse, PostUpdate, UserResponse, UserCreate, UserUpdate
from app.database import Base, engine, get_db # Base & engine help us to create table ; get_db provides database sessions 
import app.models as models
from typing import Annotated

# Create database tables
# This look at all the models inherited from Base and create table if haven't created 
# If the table already exists, then nothing happen
Base.metadata.create_all(bind=engine)

app = FastAPI() 

# app.mount('_directory_', StaticFiles(directory='directory_name'), name=ref_name_for_use_in_template)
app.mount("/static", StaticFiles(directory='static'), name='static')
app.mount('/media', StaticFiles(directory='media'), name='media')

# We save our templates in the 'templates' folder and use JinJa2 object to access them
templates = Jinja2Templates(directory="templates")

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


##### Main Functions ######

##### (1) #####

# By stacking two route, we can make that the two endpoints will lead to the same function
# @app.get("/", response_class=HTMLResponse)
# @app.get("/posts", response_class=HTMLResponse)

# Now we are using Jinja2 templates 
@app.get("/", include_in_schema=False, name='home')
@app.get("/posts", include_in_schema=False, name='posts')
# If we did not set the name for route explicitly, the url_for() will just use the function name as reference and use the lastest route we define in the script
# If we set the name, then url_for() will refer to the name of the routes instead of the function name
def home(request:Request, db:Annotated[Session, Depends(get_db)]):
    # return({'message':'Hello World'})
    # return(f"<h1>This is my website</h1>")
    # return(templates.TemplateResponse(request, 'home.html', context={"posts":posts, "title":"Home"}))
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return(templates.TemplateResponse(request, 'home.html', context={"posts":posts, "title":"Home"}))

##### (2) #####

## post_page
@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
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
def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )

##### API Endpoints for documentation ######

## Get all posts
@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts


## Get a single post 
# The parameter name set at the endpoint must be the same as the name set in the function
@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

## Update full of the existing post 
@app.put("/api/posts/{post_id}", response_model=PostResponse)
def update_post_full(post_id: int, post_data:PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # update logic 
    # check whether the user exist 
    if post_data.user_id != post.user_id:
        result = db.execute(select(models.User).where(models.User.id == post.user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
            
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id
    
    db.commit()
    db.refresh(post)
    return(post)

## Update part of the existing post 
@app.patch("/api/posts/{post_id}", response_model=PostResponse)
def update_post_partial(post_id: int, post_data:PostUpdate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    update_data = post_data.model_dump(exclude_unset=True) # do this to exclude the field that user didn't want to update (to prevent none value as our schema default set as None)
    
    for field, value in update_data.items():
        setattr(post, field, value) # set the attribute of the object 
    
    db.commit()
    db.refresh(post)
    return(post)


## Create Post
@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post
    # we use PostCreate to validate the input and PostResponse as a reference for the data this function return


## Create new user
@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    # Depends(get_db) => Tells FastAPI: "before calling this function, run get_db() first and pass its result in as db"
    # Session => Just the type hint — tells you (and your IDE) that db is a SQLAlchemy Session object.
    # Annotated[Session, Depends(get_db)] => Annotated is a Python typing tool that lets you attach metadata to a type:
    # Annotated[Session,        Depends(get_db)]
    #         ↑ type hint     ↑ FastAPI metadata
    #         (for IDE)       (triggers DI)
    
    # Check username availability
    
    result = db.execute(select(models.User).where(models.User.username == user.username))
    existing_user = result.scalars().first() # Get the first user object or none if there is no match 
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already exists')
    
    result = db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first() # Get the first user object or none if there is no match 
    
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email already exists')
    
    new_user = models.User(username=user.username, email= user.email)
    db.add(new_user) # add the new user
    db.commit() # execute and save the changes 
    db.refresh(new_user) # reload the saved objects (After you db.commit(), SQLAlchemy expires all attributes on your objects — meaning it clears the in-memory values to ensure stale data isn't used)
    return(new_user)


## Get user
@app.get(
    "/api/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def get_user(user_id:int, db: Annotated[Session, Depends(get_db)]):
    # Depends(get_db) => Tells FastAPI: "before calling this function, run get_db() first and pass its result in as db"
    # Session => Just the type hint — tells you (and your IDE) that db is a SQLAlchemy Session object.
    # Annotated[Session, Depends(get_db)] => Annotated is a Python typing tool that lets you attach metadata to a type:
    # Annotated[Session,        Depends(get_db)]
    #         ↑ type hint     ↑ FastAPI metadata
    #         (for IDE)       (triggers DI)
    
    # Check username availability
    
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first() # Get the first user object or none if there is no match 
    
    if user:
        return(user)
        
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')


## get_user_posts
@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts


## update_user
@app.patch("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_update.username is not None and user_update.username != user.username:
        # Check whether the new user name is already existed 
        result = db.execute(
            select(models.User).where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    if user_update.email is not None and user_update.email != user.email:
        result = db.execute(
            select(models.User).where(models.User.email == user_update.email),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    db.commit()
    db.refresh(user)
    return user


## delete_user
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(user)
    db.commit()


## Delete a post (we would return 204 response) we are not returning anything
@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    db.delete(post)
    db.commit()


##### Exception Handler ######
# create a general exception handler and lead to the error page template

## StarletteHTTPException Handler
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
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
