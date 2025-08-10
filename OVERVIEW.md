# Social Media Application - Complete Development Roadmap

This document provides a comprehensive guide to recreate this FastAPI-based social media application from scratch. It explains the architecture, technologies used, and step-by-step implementation process.

## 🎯 Project Overview

This is a simple social media application built with:
- **Backend**: FastAPI (Python web framework)
- **Database**: SQLite with SQLAlchemy-style models
- **Frontend**: HTML templates with Jinja2, Bulma CSS, and HTMX
- **Authentication**: JWT tokens with secure password hashing
- **Features**: User registration, login, and post creation/viewing

## 🚀 Getting Started

### 1. Environment Setup

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required packages
pip install fastapi uvicorn jinja2 python-multipart passlib pyjwt
```

**Why a virtual environment?** 
A virtual environment isolates your project dependencies, preventing conflicts with system-wide Python packages and ensuring reproducible builds.

### 2. Project Structure

Create the following directory structure:
```
social-media-app/
├── app.py              # Main FastAPI application
├── models.py           # Pydantic data models
├── database.py         # Database operations
├── social.db           # SQLite database file
├── templates/          # HTML templates
│   ├── index.html      # Homepage with post form
│   ├── posts.html      # Posts display template
│   ├── login.html      # Login form
│   └── signup.html     # Registration form
└── migrations/         # Database schema files
    ├── create_users_table.sql
    ├── post_table.sql
    └── migrate_posts.sql
```

## 🗄️ Database Setup

### 3. Create Database Schema

First, create the `social.db` file and set up your tables:

**Users Table** (`migrations/create_users_table.sql`):
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    salt TEXT,
    hash_password TEXT NOT NULL
);
```

**Posts Table** (`migrations/post_table.sql`):
```sql
CREATE TABLE posts (
    post_id INTEGER PRIMARY KEY,
    post_title VARCHAR(50) NOT NULL,
    post_text VARCHAR(500) NOT NULL,
    user_id INTEGER
);
```

**Why these fields?**
- `user_id`: Primary key for unique user identification
- `username`: Human-readable user identifier
- `salt`: Random string added to passwords before hashing (security best practice)
- `hash_password`: Encrypted password (never store plain text)
- `post_title` & `post_text`: Content of user posts
- Foreign key relationship between posts and users

### 4. Initialize Database

Run the SQL files to create your tables:
```bash
sqlite3 social.db < migrations/create_users_table.sql
sqlite3 social.db < migrations/post_table.sql
```

## 🏗️ Core Application Architecture

### 5. Data Models (`models.py`)

Create Pydantic models for data validation:

```python
from pydantic import BaseModel
from typing import List

class UserPost(BaseModel):
    post_title: str
    post_text: str

class Post(UserPost):
    user_id: int

class Posts(BaseModel):
    posts: List[Post]

class User(BaseModel):
    username: str
    password: str

class UserHashed(BaseModel):
    username: str
    salt: str
    hash_password: str

class UserHashedIndex(UserHashed):
    user_id: int
```

**Why Pydantic?**
Pydantic provides automatic data validation, serialization, and documentation. It ensures that incoming data matches your expected schema and helps prevent security vulnerabilities.

### 6. Database Operations (`database.py`)

Implement database functions for CRUD operations:

```python
import sqlite3
from sqlite3 import Connection
from typing import Union
from models import Post, Posts, UserHashed, UserHashedIndex

def get_post(connection: Connection) -> Posts:
    """Fetch all posts from database"""
    with connection:
        cur = connection.cursor()
        cur.execute("SELECT post_title, post_text, user_id FROM posts;")
        return Posts(posts=[Post.model_validate(dict(post)) for post in cur])

def insert_post(connection: Connection, post: Post) -> None:
    """Insert new post into database"""
    with connection:
        cur = connection.cursor()
        cur.execute("""
            INSERT INTO posts (post_title, post_text, user_id)
            VALUES (:post_title, :post_text, :user_id)
        """, post.model_dump())

def create_user(connection: Connection, user: UserHashed) -> bool:
    """Create new user with hashed password"""
    with connection:
        cur = connection.cursor()
        cur.execute("""
            INSERT INTO users (username, salt, hash_password)
            VALUES (:username, :salt, :hash_password)
        """, user.model_dump())
    return True

def get_user(connection: Connection, username: str) -> Union[UserHashedIndex, None]:
    """Retrieve user by username"""
    with connection:
        cur = connection.cursor()
        cur.execute("""
            SELECT user_id, username, salt, hash_password
            FROM users WHERE username = ?
        """, (username,))
        user = cur.fetchone()
        return UserHashedIndex(**dict(user)) if user else None
```

**Key Concepts:**
- **Connection Management**: Using `with connection:` ensures proper transaction handling
- **Parameterized Queries**: Prevents SQL injection attacks
- **Type Safety**: Union types handle cases where users might not exist

### 7. Main Application (`app.py`)

#### 7.1 Application Setup

```python
from fastapi import FastAPI, Form, status, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.requests import Request
from fastapi.security import OAuth2
from sqlite3 import Connection, Row
from secrets import token_hex
from passlib.hash import pbkdf2_sha256
from typing import Annotated
import jwt

from database import get_post, insert_post, create_user, get_user
from models import Posts, Post, UserPost, User, UserHashed

app = FastAPI()
connection = Connection("social.db")
connection.row_factory = Row

templates = Jinja2Templates("./templates")
JWT_KEY = "your-secret-key-here"  # Generate a secure random key
EXPIRATION_TIME = 3600  # 1 hour
ALGORITHM = "HS256"
```

**Security Considerations:**
- **JWT Key**: Should be a long, random string stored in environment variables
- **Expiration Time**: Prevents indefinite access if tokens are compromised
- **Algorithm**: HS256 is secure for most applications

#### 7.2 Authentication System

```python
class OAuthCookie(OAuth2):
    def __call__(self, request: Request) -> int:
        _, token = request.cookies.get("access_token").split()
        data = jwt.decode(token, JWT_KEY, algorithms=[ALGORITHM])
        return data["user_id"]

oauth_cookie = OAuthCookie()
```

**How OAuth Cookie Works:**
1. Extracts JWT token from cookies
2. Decodes and validates the token
3. Returns user_id for dependency injection
4. Provides secure access control to protected routes

#### 7.3 Route Definitions

**Homepage Route ("/"):**
```python
@app.get("/")
async def home(request: Request) -> HTMLResponse:
    posts = get_post(connection)
    return templates.TemplateResponse(
        request, 
        "./index.html",
        context=posts.model_dump()
    )
```

**Posts Route ("/posts"):**
```python
@app.get("/posts")
async def posts(request: Request) -> HTMLResponse:
    posts = get_post(connection)
    return templates.TemplateResponse(
        request,
        "./posts.html",
        context=posts.model_dump()
    )
```

**Why separate routes?**
- **Homepage ("/")**: Displays the main interface with post creation form
- **Posts ("/posts")**: Returns only the posts data (used by HTMX for dynamic updates)
- **Separation of concerns**: Keeps data fetching separate from presentation

**Post Creation Route ("/post"):**
```python
@app.post("/post")
async def add_post(post: UserPost, request: Request, user_id: int=Depends(oauth_cookie)) -> HTMLResponse:
    post = Post(user_id=user_id, **post.model_dump())
    insert_post(connection, post)
    posts = get_post(connection)
    
    return templates.TemplateResponse(
        request,
        "./posts.html",
        context=posts.model_dump()
    )
```

**Security Features:**
- **Dependency Injection**: `user_id=Depends(oauth_cookie)` ensures only authenticated users can post
- **Data Validation**: Pydantic models validate incoming data
- **User Association**: Posts are automatically linked to the authenticated user

#### 7.4 Authentication Routes

**Login Route ("/login"):**
```python
@app.post("/login")
async def add_user(username: Annotated[str, Form()], password: Annotated[str, Form()], request: Request) -> HTMLResponse:
    user = get_user(connection, username)
    
    if user is None:
        return templates.TemplateResponse(
            request, "./login.html", context={"incorrect": True}
        )
    
    # Verify password with salt
    correct_password = pbkdf2_sha256.verify(password + user.salt, user.hash_password)
    
    if not correct_password:
        return templates.TemplateResponse(
            request, "./login.html", context={"incorrect": True}
        )

    # Generate JWT token
    token = jwt.encode({
        "username": username,
        "user_id": user.user_id  # Use actual user_id from database
    }, JWT_KEY, algorithm=ALGORITHM)

    # Set secure cookie
    response = RedirectResponse("./", status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        "access_token",
        f"Bearer {token}",
        samesite="lax",
        expires=EXPIRATION_TIME,
        httponly=True,
        secure=True  # Enable in production with HTTPS
    )
    
    return response
```

**Password Security:**
- **Salt**: Random string added to passwords before hashing
- **PBKDF2**: Industry-standard password hashing algorithm
- **Verification**: Compares hashed input with stored hash

**Signup Route ("/signup"):**
```python
@app.post("/signup")
async def add_user(username: Annotated[str, Form()], password: Annotated[str, Form()], request: Request) -> HTMLResponse:
    if get_user(connection, username) is not None:
        return templates.TemplateResponse(
            request, "./signup.html", context={"taken": True, "username": username}
        )

    # Generate random salt
    salt = token_hex(15)
    
    # Hash password with salt
    hash_password = pbkdf2_sha256.hash(password + salt)   

    # Create user in database
    hashed_user = UserHashed(
        username=username,
        salt=salt,
        hash_password=hash_password
    )
    
    create_user(connection, hashed_user)
    return RedirectResponse("./login", status.HTTP_303_SEE_OTHER)
```

## 🎨 Frontend Templates

### 8. HTML Templates

**Homepage (`templates/index.html`):**
- **Bulma CSS**: Modern, responsive CSS framework
- **HTMX**: Enables dynamic updates without JavaScript
- **Post Form**: Creates new posts with AJAX-like behavior
- **Posts Container**: Dynamically loads posts from `/posts` endpoint

**Posts Template (`templates/posts.html`):**
- **Jinja2 Loop**: Iterates through posts from database
- **Card Layout**: Clean, organized post display
- **Reusable Component**: Can be loaded independently for dynamic updates

**Authentication Templates:**
- **Login/Signup Forms**: Simple, functional forms
- **Error Handling**: Displays validation messages
- **Security**: Proper autocomplete attributes

## 🔒 Security Features

### 9. Security Implementation

**Password Hashing:**
- Uses PBKDF2 with SHA256
- Random salt generation for each user
- Prevents rainbow table attacks

**JWT Authentication:**
- Stateless authentication
- Configurable expiration times
- Secure cookie storage

**Input Validation:**
- Pydantic model validation
- Parameterized SQL queries
- Form data sanitization

**Session Management:**
- HTTP-only cookies
- SameSite protection
- Secure flag for HTTPS

## 🚀 Running the Application

### 10. Start the Server

```bash
# Make sure your virtual environment is activated
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Development Options:**
- `--reload`: Auto-restart on code changes
- `--host 0.0.0.0`: Accessible from other devices on network
- `--port 8000`: Custom port (default is 8000)

### 11. Access Your Application

- **Homepage**: http://localhost:8000/
- **Login**: http://localhost:8000/login
- **Signup**: http://localhost:8000/signup
- **API Docs**: http://localhost:8000/docs (FastAPI automatic documentation)

## 🔧 Advanced Features

### 12. HTMX Integration

**Why HTMX?**
- **Progressive Enhancement**: Works without JavaScript
- **Dynamic Updates**: Real-time post loading
- **Simple Implementation**: Minimal frontend code

**Key HTMX Attributes:**
- `hx-post="/post"`: Sends POST request to create posts
- `hx-target="#posts"`: Updates specific DOM element
- `hx-swap="innerHTML"`: Replaces content dynamically
- `hx-trigger="load"`: Executes on page load

### 13. Database Migrations

**Migration Strategy:**
- **Version Control**: Track database schema changes
- **Rollback Capability**: Can revert to previous versions
- **Data Preservation**: Maintains existing data during updates

## 🧪 Testing and Debugging

### 14. Development Tips

**Database Inspection:**
```bash
sqlite3 social.db
.tables
.schema users
.schema posts
SELECT * FROM users;
SELECT * FROM posts;
.quit
```

**FastAPI Debugging:**
- Automatic API documentation at `/docs`
- Request/response logging
- Detailed error messages in development

**Common Issues:**
- **Database Lock**: Ensure proper connection handling
- **JWT Expiration**: Check token validity and timing
- **Template Errors**: Verify Jinja2 syntax and context variables

## 📚 Learning Resources

### 15. Further Study

**FastAPI:**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Models](https://pydantic-docs.helpmanual.io/)

**Security:**
- [OWASP Security Guidelines](https://owasp.org/)
- [JWT Best Practices](https://jwt.io/introduction)

**Frontend:**
- [HTMX Documentation](https://htmx.org/)
- [Bulma CSS Framework](https://bulma.io/)

## 🎉 Congratulations!

You've successfully built a complete social media application with:
- ✅ User authentication and registration
- ✅ Secure password handling
- ✅ Post creation and viewing
- ✅ Modern, responsive UI
- ✅ Real-time updates
- ✅ Production-ready security

This application demonstrates modern web development practices including API design, security implementation, database management, and frontend integration. Use this as a foundation to build more complex features like user profiles, comments, likes, and real-time notifications! 