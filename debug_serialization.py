#!/usr/bin/env python3
"""
Debug script to test SpawnedTask serialization in different contexts
"""
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from src.models import SpawnedTask, Task, Candidate
import json

print("=" * 60)
print("Testing SpawnedTask Serialization")
print("=" * 60)

# Create in-memory database like tests do
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    # Create test data
    template = Task(
        task_id="phone_screen",
        name="Phone Screen",
        description="Initial phone screening"
    )
    session.add(template)

    candidate = Candidate(
        email="test@example.com",
        name="Test User",
        workflow_id="senior_engineer"
    )
    session.add(candidate)
    session.commit()

    # Create a spawned task
    spawned = SpawnedTask(
        title="Phone Screen",
        description="Initial phone screening",
        status="todo",
        template_id="phone_screen",
        workflow_id="senior_engineer"
    )
    session.add(spawned)
    session.commit()
    session.refresh(spawned)

    print(f"\n1. Direct object attributes:")
    print(f"   id: {spawned.id}")
    print(f"   title: {spawned.title}")
    print(f"   status: {spawned.status}")
    print(f"   template_id: {spawned.template_id}")

    print(f"\n2. SQLModel dict():")
    try:
        model_dict = spawned.dict()
        print(f"   Success: {model_dict}")
    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n3. SQLModel model_dump():")
    try:
        model_dump = spawned.model_dump()
        print(f"   Success: {model_dump}")
    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n4. Pydantic model_dump_json():")
    try:
        json_str = spawned.model_dump_json()
        print(f"   Success: {json_str}")
    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n5. JSON serialization:")
    try:
        json_str = json.dumps(spawned, default=str)
        print(f"   Success: {json_str}")
    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n6. FastAPI JSONResponse simulation:")
    try:
        from fastapi.responses import JSONResponse
        from fastapi.encoders import jsonable_encoder

        encoded = jsonable_encoder(spawned)
        print(f"   jsonable_encoder result: {encoded}")

        response = JSONResponse(content=encoded)
        print(f"   JSONResponse body: {response.body}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
