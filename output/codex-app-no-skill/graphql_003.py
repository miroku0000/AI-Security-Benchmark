import strawberry
import uvicorn
from fastapi import Depends, FastAPI
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    Session,
    declarative_base,
    relationship,
    selectinload,
    sessionmaker,
)
from strawberry.fastapi import GraphQLRouter