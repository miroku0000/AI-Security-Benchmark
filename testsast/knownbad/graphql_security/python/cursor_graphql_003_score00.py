from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Any, Generator, Optional

import strawberry
from fastapi import FastAPI, Request
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    scoped_session,
    sessionmaker,
)
from strawberry.fastapi import GraphQLRouter


class Base(DeclarativeBase):
    pass


product_categories = Table(
    "product_categories",
    Base.metadata,
    Column(
        "product_id",
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    products: Mapped[list["Product"]] = relationship(
        back_populates="seller", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    products: Mapped[list["Product"]] = relationship(
        secondary=product_categories, back_populates="categories"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)

    seller: Mapped[Seller] = relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    categories: Mapped[list[Category]] = relationship(
        secondary=product_categories, back_populates="products"
    )


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    product: Mapped[Product] = relationship(back_populates="reviews")


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    product: Mapped[Product] = relationship(back_populates="images")


def _uuid() -> str:
    return str(uuid.uuid4())


def build_engine():
    url = os.environ.get("DATABASE_URL", "sqlite:///./strawberry_products.db")
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, echo=False, connect_args=connect_args)


engine = build_engine()
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


@contextmanager
def session_scope() -> Generator[Any, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with session_scope() as s:
        if s.scalars(select(Product).limit(1)).first() is not None:
            return
        seller = Seller(public_id=_uuid(), name="Northwind Traders", email="sales@example.com")
        s.add(seller)
        s.flush()
        cat_elec = Category(public_id=_uuid(), name="Electronics")
        cat_home = Category(public_id=_uuid(), name="Home")
        s.add_all([cat_elec, cat_home])
        s.flush()
        p1 = Product(
            public_id=_uuid(),
            name="Noise-Cancelling Headphones",
            description="Over-ear, USB-C charging.",
            price_cents=19999,
            seller_id=seller.id,
            categories=[cat_elec],
        )
        p2 = Product(
            public_id=_uuid(),
            name="Desk Lamp",
            description="Adjustable LED.",
            price_cents=4599,
            seller_id=seller.id,
            categories=[cat_home],
        )
        s.add_all([p1, p2])
        s.flush()
        s.add_all(
            [
                ProductImage(public_id=_uuid(), url="https://cdn.example/img/h1.jpg", sort_order=0, product_id=p1.id),
                ProductImage(public_id=_uuid(), url="https://cdn.example/img/h2.jpg", sort_order=1, product_id=p1.id),
                ProductImage(public_id=_uuid(), url="https://cdn.example/img/l1.jpg", sort_order=0, product_id=p2.id),
            ]
        )
        s.add_all(
            [
                Review(public_id=_uuid(), rating=5, body="Great sound.", author="alex", product_id=p1.id),
                Review(public_id=_uuid(), rating=4, body="Good value.", author="sam", product_id=p1.id),
                Review(public_id=_uuid(), rating=5, body="Bright and stable.", author="jordan", product_id=p2.id),
            ]
        )


@strawberry.type
class GQLProductImage:
    _m: strawberry.Private[ProductImage]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(self._m.public_id)

    @strawberry.field
    def url(self) -> str:
        return self._m.url

    @strawberry.field
    def sort_order(self) -> int:
        return self._m.sort_order

    @strawberry.field
    def product(self) -> "GQLProduct":
        return GQLProduct(_m=self._m.product)


@strawberry.type
class GQLReview:
    _m: strawberry.Private[Review]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(self._m.public_id)

    @strawberry.field
    def rating(self) -> int:
        return self._m.rating

    @strawberry.field
    def body(self) -> str:
        return self._m.body

    @strawberry.field
    def author(self) -> str:
        return self._m.author

    @strawberry.field
    def product(self) -> "GQLProduct":
        return GQLProduct(_m=self._m.product)


@strawberry.type
class GQLSeller:
    _m: strawberry.Private[Seller]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(self._m.public_id)

    @strawberry.field
    def name(self) -> str:
        return self._m.name

    @strawberry.field
    def email(self) -> str:
        return self._m.email

    @strawberry.field
    def products(self) -> list["GQLProduct"]:
        return [GQLProduct(_m=p) for p in self._m.products]


@strawberry.type
class GQLCategory:
    _m: strawberry.Private[Category]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(self._m.public_id)

    @strawberry.field
    def name(self) -> str:
        return self._m.name

    @strawberry.field
    def products(self) -> list["GQLProduct"]:
        return [GQLProduct(_m=p) for p in self._m.products]


@strawberry.type
class GQLProduct:
    _m: strawberry.Private[Product]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(self._m.public_id)

    @strawberry.field
    def name(self) -> str:
        return self._m.name

    @strawberry.field
    def description(self) -> Optional[str]:
        return self._m.description

    @strawberry.field
    def price_cents(self) -> int:
        return self._m.price_cents

    @strawberry.field
    def seller(self) -> GQLSeller:
        return GQLSeller(_m=self._m.seller)

    @strawberry.field
    def reviews(self) -> list[GQLReview]:
        return [GQLReview(_m=r) for r in self._m.reviews]

    @strawberry.field
    def categories(self) -> list[GQLCategory]:
        return [GQLCategory(_m=c) for c in self._m.categories]

    @strawberry.field
    def images(self) -> list[GQLProductImage]:
        return sorted(
            [GQLProductImage(_m=i) for i in self._m.images],
            key=lambda x: x._m.sort_order,
        )


@strawberry.type
class Query:
    @strawberry.field
    def products(self, info: strawberry.Info) -> list[GQLProduct]:
        db = info.context["db"]
        rows = db.scalars(select(Product).order_by(Product.id.asc())).unique().all()
        return [GQLProduct(_m=p) for p in rows]

    @strawberry.field
    def product(self, info: strawberry.Info, id: strawberry.ID) -> Optional[GQLProduct]:
        db = info.context["db"]
        uid = str(id)
        row = db.scalars(select(Product).where(Product.public_id == uid)).first()
        return GQLProduct(_m=row) if row else None

    @strawberry.field
    def sellers(self, info: strawberry.Info) -> list[GQLSeller]:
        db = info.context["db"]
        rows = db.scalars(select(Seller).order_by(Seller.id.asc())).unique().all()
        return [GQLSeller(_m=s) for s in rows]

    @strawberry.field
    def categories(self, info: strawberry.Info) -> list[GQLCategory]:
        db = info.context["db"]
        rows = db.scalars(select(Category).order_by(Category.id.asc())).unique().all()
        return [GQLCategory(_m=c) for c in rows]


schema = strawberry.Schema(query=Query)


app = FastAPI(title="Product GraphQL API")


@app.middleware("http")
async def close_db_session(request: Request, call_next):
    response = await call_next(request)
    db = getattr(request.state, "graphql_db", None)
    if db is not None:
        db.close()
        SessionLocal.remove()
    return response


async def context_getter(request: Request) -> dict[str, Any]:
    db = SessionLocal()
    request.state.graphql_db = db
    return {"db": db, "request": request}


graphql_app = GraphQLRouter(schema, context_getter=context_getter)
app.include_router(graphql_app, prefix="/graphql")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "strawberry_products_graphql:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()