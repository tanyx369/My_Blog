from pydantic import BaseModel, Field, ConfigDict, EmailStr
# BaseModel is the base class of all our pydantic models inherit from; Field let us add constraint like min and max length; ConfigDict is the modern to configure models
from typing import Optional, List
from datetime import datetime 

### User ###

class UserBase(BaseModel):
    username:str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)
    

class UserCreate(UserBase):
    password:str = Field(min_length=8)
    
class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:int 
    username: str
    image_file: str|None 
    image_path: str 
    
class UserPrivate(UserPublic):
    email:EmailStr 
    

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id:int 
    image_file: str|None 
    image_path: str 
    
class UserUpdate(BaseModel):
    username:str | None= Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=120)
    # image_file:str | None= Field(default=None, min_length=1, max_length=200)
    
    
class Token(BaseModel):
    access_token : str 
    token_type:str

class PostBase(BaseModel):
    # shared between creating and returning a post 
    title:str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    # author: str = Field(min_length=1, max_length=50)
    
class PostCreate(PostBase):
    # user_id: int # temporary use, we will change it to author_id later; we need it to link the post to a user
    # user id is no longer part of the data client send to the API during creating post. They cannot claim as someone else
    # server will determine the user from the trusted token
    pass 
    

# Partial update
class PostUpdate(BaseModel):
    title:str = Field(default=None, min_length=1, max_length=100)
    content: str = Field(default=None, min_length=1)

class PostResponse(PostBase):
    # ConfigDict is basically a setting to configure the behaviour of the Pydantic Models
    model_config = ConfigDict(from_attributes=True) 
    # from_attributes allow the model to read data from object with attributes instead of just dictionary (eg. know how to read post.title instead of just knowing read from post['title'])
    
    id:int
    user_id: int 
    date_posted:datetime
    author: UserPublic # Return us the user details 
    
class PaginatedPostsResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
    
    
## Password Reset Schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=120)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


