# Router Integration Plan

## Current Status

Router modules have been extracted to `src/routes/api/` but are not yet integrated into the main application due to dependency injection complexity.

## The Dependency Injection Problem

The `get_session()` dependency function in `app.py` depends on the `db` object which is initialized at module level:

```python
# In app.py
db = Database(db_file)
db.init_db()

def get_session():
    with db.get_session() as session:
        yield session
```

Router modules cannot import `get_session` from `app.py` without creating circular imports, and cannot recreate `db` because it's a singleton.

## Solution Approach

### Phase 4 Integration Steps

1. **Create Shared Dependencies Module**
   - Create `src/dependencies.py` with a `get_db()` function that returns the db instance
   - Make `db` accessible via a module-level variable or factory
   - Define `get_session()` in this shared module

2. **Refactor Database Initialization**
   - Move database initialization to a separate function
   - Allow dependencies module to access the initialized db
   - Update `app.py` to use the shared dependencies

3. **Update Router Modules**
   - Replace `Depends(lambda: None)` with `Depends(get_session)`
   - Import `get_session` from `src.dependencies`

4. **Integrate Routers**
   - Include each router in `app.py` using `app.include_router()`
   - Remove duplicate endpoint definitions from `app.py`
   - Run tests to verify all endpoints still work

## Workaround for Now

Router modules are created with placeholder dependencies (`Depends(lambda: None)`). They are  ready for integration but commented out in `app.py`. Original endpoints remain active.

## Files Created

- `src/routes/api/candidates.py` - Candidate API routes (260 lines, 10 endpoints)
- More router modules to be created in Phase 2

## Testing Strategy

Once integrated:
1. Run full test suite (currently 37 tests)
2. Test each API endpoint manually
3. Verify no duplicate route errors
4. Check that sessions are properly injected
