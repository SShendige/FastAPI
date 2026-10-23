from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from typing import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from models import Todo
from database import SessionLocal
from starlette import status
from .auth import get_current_user
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory = 'templates')

router = APIRouter(
    prefix = '/todos',
    tags = ['todos']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

class TodoRequest(BaseModel):
    title: str = Field(min_length = 3)
    description: str = Field(min_length = 3, max_length = 100)
    priority: int = Field(gt = 0, lt = 6)
    complete: bool = Field(default = False)

    model_config = {
        "json_schema_extra": 
        {
            "example": {
                "title": "Todo Title",
                "description": "Todo Description",
                "priority": 0,
                "complete": False
            }
        }
    }

def redirect_to_login():
    redirect_response = RedirectResponse(url = '/auth/login-page', status_code = status.HTTP_302_FOUND)
    redirect_response.delete_cookie(key = 'access_token')
    return redirect_response

### Pages ###

@router.get("/todo-page")
async def render_todo_page(request: Request, db: db_dependency):
    try:
        token = request.cookies.get('access_token')
        if not token:
            return redirect_to_login()
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login() 

        todos = db.query(Todo).filter(Todo.owner_id == user.get('id')).all()
        return templates.TemplateResponse(name = "todo.html", request = request, context = {'request': request, 'todos': todos, 'user': user})
    except HTTPException:
        return redirect_to_login()

@router.get("/add-todo-page")
async def render_todo_page(request: Request):
    try:
        token = request.cookies.get('access_token')
        if not token:
            return redirect_to_login()
        user = await get_current_user(token)
        if user is None:
                    return redirect_to_login() 
        return templates.TemplateResponse(name = "add-todo.html", request = request, context = {'user': user})
    except HTTPException:
        return redirect_to_login()

@router.get("/edit-todo-page/{id}")
async def render_edit_page(request: Request, id: int, db: db_dependency):
    try:
        token = request.cookies.get('access_token')
        if not token:
            return redirect_to_login()
        user = await get_current_user(token)
        if user is None:
                    return redirect_to_login()
        todo = db.query(Todo).filter(Todo.id == id, Todo.owner_id == user.get("id")).first()
        return templates.TemplateResponse(name = "edit-todo.html", request = request, context = {'request': request,'todo': todo, 'user': user})
    except HTTPException:
        return redirect_to_login()

### Endpoints ###

@router.get("/", status_code = status.HTTP_200_OK)
async def read_db(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code = 401, details = "Authentication Failed")
    return db.query(Todo).filter(Todo.owner_id == user.get('id')).all()

@router.get("/todo/{id}", status_code = status.HTTP_200_OK)
async def read_todo(user: user_dependency, db: db_dependency, id: int = Path(gt = 0)):
    if user is None:
        raise HTTPException(status_code = 401, details = "Authentication failed")

    todo_list = db.query(Todo).filter(Todo.id == id).filter(Todo.owner_id == user.get('id')).first()
    if todo_list is None:
        raise HTTPException(status_code = 404, detail = "Todo ID not found")
    else: 
        return todo_list

@router.post("/todo", status_code = status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, db: db_dependency, todo_request: TodoRequest):
    if user is None:
        raise HTTPException(status_code=401, detail = "Authentication Failed")
    todo_model = Todo(**todo_request.model_dump(), owner_id = user.get('id'))
    db.add(todo_model)
    db.commit()

@router.put("/todo/{id}", status_code = status.HTTP_204_NO_CONTENT)
async def update_db(user: user_dependency, db: db_dependency, todo_request: TodoRequest, id: int = Path(gt = 0)):
    if user is None:
        raise HTTPException(status_code = 401, details = 'Authentication Failed')
    
    todo_model = db.query(Todo).filter(Todo.id == id).filter(Todo.owner_id == user.get('id')).first()
    if todo_model is not None:
        todo_model.title = todo_request.title
        todo_model.description = todo_request.description
        todo_model.priority = todo_request.priority
        todo_model.complete = todo_request.complete
        
        db.add(todo_model)
        db.commit()
    else:
        raise HTTPException(status_code = 404, detail = "Todo ID not found")
        
@router.delete("/todo/{id}", status_code = status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, id: int = Path(gt = 0)):
    if user is None:
        raise HTTPException(status_code = 401, details = 'Authentication Failed')
    
    todo_model = db.query(Todo).filter(Todo.id == id).filter(Todo.owner_id == user.get('id')).first()
    if todo_model is None:
        raise HTTPException(status_code = 404, description = "Todo ID not found")
    db.query(Todo).filter(Todo.id == id).delete()
    db.commit()