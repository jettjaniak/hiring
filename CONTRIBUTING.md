# Contributing Guide

## Project Philosophy

This project prioritizes **simplicity and maintainability** over complexity. The goal is to have a codebase that:
- Can be understood quickly by new developers
- Requires minimal dependencies
- Uses modern frameworks that auto-generate boilerplate
- Has clear separation of concerns

## Code Organization

### Backend (`backend/`)

**Purpose**: Provide a RESTful API for data operations

**Key files**:
- `models.py` - SQLModel models (single source of truth for database schema AND API schemas)
- `api.py` - FastAPI application with auto-generated CRUD endpoints
- `workflows/` - YAML workflow definitions

**Principles**:
1. **Models define everything**: SQLModel automatically generates database tables, Pydantic schemas, and API documentation
2. **Minimal custom code**: Use FastAPI's dependency injection and automatic validation
3. **Let the framework work**: Don't write manual serialization/deserialization code

**Adding a new model**:
```python
# 1. Define the model in models.py
class MyModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

# 2. Add endpoints in api.py - FastAPI handles the rest!
@app.get("/api/mymodels", response_model=List[MyModel])
def list_mymodels(session: Session = Depends(get_session)):
    return session.exec(select(MyModel)).all()
```

### Frontend (`frontend/`)

**Purpose**: Provide a web UI for end users

**Key files**:
- `app.py` - Flask application (serves HTML pages)
- `templates/` - Jinja2 HTML templates
- `static/` - CSS, JavaScript, images

**Principles**:
1. **Keep it simple**: Server-side rendered HTML with minimal JavaScript
2. **Direct database access**: For simplicity, frontend directly queries the database
3. **Progressive enhancement**: Add JavaScript only when needed for interactivity

**Note**: The frontend could be rewritten to use the backend API instead of direct database access. This would allow building multiple frontends (mobile app, CLI, etc.) but adds complexity for a simple use case.

## Best Practices

### 1. Model Design

**DO**:
- Use SQLModel for all database models
- Add type hints to all fields
- Use `Optional[]` for nullable fields
- Add docstrings to models and endpoints

**DON'T**:
- Mix SQLAlchemy and SQLModel (stick to one)
- Add business logic to models (keep them as data containers)
- Skip type hints

### 2. API Design

**DO**:
- Follow REST conventions (GET for read, POST for create, PATCH for update, DELETE for delete)
- Use plural nouns for collections (`/api/candidates` not `/api/candidate`)
- Return appropriate HTTP status codes
- Use Pydantic models for request/response validation

**DON'T**:
- Create custom serialization code (let FastAPI handle it)
- Skip input validation
- Return raw database objects (use Pydantic models)

### 3. Database

**DO**:
- Use soft deletes for user data (`deleted` boolean + `deleted_at` timestamp)
- Add `created_at` and `updated_at` timestamps to all models
- Use foreign keys with `ondelete="CASCADE"` for dependent data

**DON'T**:
- Hard delete data that users created
- Skip migrations if you change the schema
- Store sensitive data without encryption (if adding auth later)

### 4. Workflows

**DO**:
- Define workflows in YAML files (declarative and version-controllable)
- Validate workflow definitions on load
- Keep workflow logic separate from application code

**DON'T**:
- Hard-code workflows in Python
- Allow circular dependencies in tasks
- Skip validation of workflow files

## Adding New Features

### Example: Adding a "Notes" feature to tasks

**1. Update the model** (`backend/models.py`):
```python
class CandidateTask(SQLModel, table=True):
    # ... existing fields ...
    notes: Optional[str] = None  # Add this line
```

**2. The API automatically supports it!** FastAPI will:
- Allow `notes` in POST/PATCH requests
- Include `notes` in GET responses
- Validate that `notes` is a string (or null)
- Update the OpenAPI docs

**3. Update the frontend** (`frontend/app.py` and templates):
```python
# In the task update route:
task.notes = request.form.get('notes')
```

```html
<!-- In the template: -->
<textarea name="notes">{{ task.notes }}</textarea>
```

**4. Test manually**:
```bash
# Start backend
cd backend && ./venv/bin/uvicorn api:app --reload

# Start frontend
cd frontend && ./venv/bin/python app.py

# Visit http://localhost:5001 and test the feature
```

## Testing

### Manual Testing
1. Start the backend API
2. Visit http://localhost:8000/docs to test API endpoints interactively
3. Start the frontend and test the UI

### Future: Automated Tests
When the project grows, add:
- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for critical user flows

## Common Tasks

### Add a new workflow
1. Create a YAML file in `backend/workflows/`
2. Define tasks and dependencies
3. Restart the backend - it's automatically loaded!

### Change database schema
1. Update `models.py`
2. Delete the database file (for now): `rm ~/.hiring-app/hiring.db`
3. Restart backend/frontend - tables are auto-created

### Add API documentation
FastAPI automatically generates docs from:
- Model docstrings
- Function docstrings
- Type hints
- Default values

Just add docstrings to your models and endpoints!

## Code Style

- Use Python 3.12+
- Follow PEP 8 (use `black` for formatting)
- Add type hints to all function signatures
- Write docstrings for public functions
- Keep functions small and focused
- Prefer readability over cleverness

## Questions?

If something is unclear or you want to discuss a design decision, open an issue on GitHub!
