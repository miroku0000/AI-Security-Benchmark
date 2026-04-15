import strawberry
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import ForeignKey, String, Table, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload, sessionmaker
from starlette.middleware.trustedhost import TrustedHostMiddleware
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info