import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

import strawberry
from fastapi import FastAPI
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from strawberry.dataloader import DataLoader
from strawberry.fastapi import GraphQLRouter


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", String(36), ForeignKey("products.id"), primary_key=True),
    Column("category_id", String(36), ForeignKey("categories.id"), primary_key=True),
)

product_sellers = Table(
    "product_sellers",
    Base.metadata,
    Column("product_id", String(36), ForeignKey("products.id"), primary_key=True),
    Column("seller_id", String(36), ForeignKey("sellers.id"), primary_key=True),
)


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)


class SellerModel(Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("5.00"))


class ImageModel(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    alt_text: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text)
    author_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


@strawberry.type
class Money:
    amount: Decimal
    currency: str


@strawberry.type
class Image:
    id: strawberry.ID
    url: str
    alt_text: Optional[str]
    position: int


@strawberry.type
class Seller:
    id: strawberry.ID
    slug: str
    name: str
    rating: Decimal

    @strawberry.field
    async def products(self, info: strawberry.Info) -> List["Product"]:
        return await info.context["loaders"]["products_by_seller"].load(str(self.id))


@strawberry.type
class Category:
    id: strawberry.ID
    slug: str
    name: str

    @strawberry.field
    async def products(self, info: strawberry.Info) -> List["Product"]:
        return await info.context["loaders"]["products_by_category"].load(str(self.id))


@strawberry.type
class Review:
    id: strawberry.ID
    rating: int
    title: str
    body: str
    author_name: Optional[str]
    created_at: datetime
    _product_id: strawberry.Private[str]

    @strawberry.field
    async def product(self, info: strawberry.Info) -> "Product":
        prod = await info.context["loaders"]["product_by_id"].load(self._product_id)
        if prod is None:
            raise RuntimeError("Product not found")
        return prod


@strawberry.type
class Product:
    id: strawberry.ID
    sku: str
    name: str
    description: str
    price: Money
    in_stock: bool
    created_at: datetime

    @strawberry.field
    async def categories(self, info: strawberry.Info) -> List[Category]:
        return await info.context["loaders"]["categories_by_product"].load(str(self.id))

    @strawberry.field
    async def images(self, info: strawberry.Info) -> List[Image]:
        return await info.context["loaders"]["images_by_product"].load(str(self.id))

    @strawberry.field
    async def sellers(self, info: strawberry.Info) -> List[Seller]:
        return await info.context["loaders"]["sellers_by_product"].load(str(self.id))

    @strawberry.field
    async def reviews(self, info: strawberry.Info, min_rating: Optional[int] = None) -> List[Review]:
        reviews = await info.context["loaders"]["reviews_by_product"].load(str(self.id))
        if min_rating is None:
            return reviews
        try:
            mr = int(min_rating)
        except Exception:
            mr = 0
        return [r for r in reviews if r.rating >= mr]

    @strawberry.field
    async def review_count(self, info: strawberry.Info) -> int:
        return await info.context["loaders"]["review_count_by_product"].load(str(self.id))

    @strawberry.field
    async def average_rating(self, info: strawberry.Info) -> float:
        return await info.context["loaders"]["avg_rating_by_product"].load(str(self.id))


def _money_from_row(price: Decimal, currency: str) -> Money:
    return Money(amount=price, currency=currency)


def _product_from_row(row: ProductModel) -> Product:
    return Product(
        id=strawberry.ID(row.id),
        sku=row.sku,
        name=row.name,
        description=row.description,
        price=_money_from_row(row.price, row.currency),
        in_stock=bool(row.in_stock),
        created_at=row.created_at,
    )


def _category_from_row(row: CategoryModel) -> Category:
    return Category(id=strawberry.ID(row.id), slug=row.slug, name=row.name)


def _seller_from_row(row: SellerModel) -> Seller:
    return Seller(id=strawberry.ID(row.id), slug=row.slug, name=row.name, rating=row.rating)


def _image_from_row(row: ImageModel) -> Image:
    return Image(id=strawberry.ID(row.id), url=row.url, alt_text=row.alt_text, position=row.position)


def _review_from_row(row: ReviewModel) -> Review:
    return Review(
        id=strawberry.ID(row.id),
        rating=row.rating,
        title=row.title,
        body=row.body,
        author_name=row.author_name,
        created_at=row.created_at,
        _product_id=row.product_id,
    )


class RequestContext:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.loaders: Dict[str, DataLoader[Any, Any]] = {}


async def _create_loaders(ctx: RequestContext) -> Dict[str, DataLoader[Any, Any]]:
    session = ctx.session

    async def load_products_by_id(keys: Sequence[str]) -> List[Optional[Product]]:
        rows = (
            await session.execute(select(ProductModel).where(ProductModel.id.in_(list(keys))))
        ).scalars().all()
        by_id = {r.id: r for r in rows}
        return [_product_from_row(by_id[k]) if k in by_id else None for k in keys]

    async def load_product_by_id(keys: Sequence[str]) -> List[Optional[Product]]:
        return await load_products_by_id(keys)

    async def load_categories_by_product(keys: Sequence[str]) -> List[List[Category]]:
        pid_list = list(keys)
        rows = await session.execute(
            select(product_categories.c.product_id, CategoryModel)
            .join(CategoryModel, CategoryModel.id == product_categories.c.category_id)
            .where(product_categories.c.product_id.in_(pid_list))
            .order_by(CategoryModel.name.asc(), CategoryModel.id.asc())
        )
        mapping: Dict[str, List[Category]] = {k: [] for k in pid_list}
        for product_id, cat in rows.all():
            mapping[str(product_id)].append(_category_from_row(cat))
        return [mapping[k] for k in keys]

    async def load_products_by_category(keys: Sequence[str]) -> List[List[Product]]:
        cid_list = list(keys)
        rows = await session.execute(
            select(product_categories.c.category_id, ProductModel)
            .join(ProductModel, ProductModel.id == product_categories.c.product_id)
            .where(product_categories.c.category_id.in_(cid_list))
            .order_by(ProductModel.name.asc(), ProductModel.id.asc())
        )
        mapping: Dict[str, List[Product]] = {k: [] for k in cid_list}
        for category_id, prod in rows.all():
            mapping[str(category_id)].append(_product_from_row(prod))
        return [mapping[k] for k in keys]

    async def load_images_by_product(keys: Sequence[str]) -> List[List[Image]]:
        pid_list = list(keys)
        rows = (
            await session.execute(
                select(ImageModel)
                .where(ImageModel.product_id.in_(pid_list))
                .order_by(ImageModel.product_id.asc(), ImageModel.position.asc(), ImageModel.id.asc())
            )
        ).scalars().all()
        mapping: Dict[str, List[Image]] = {k: [] for k in pid_list}
        for img in rows:
            mapping[img.product_id].append(_image_from_row(img))
        return [mapping[k] for k in keys]

    async def load_sellers_by_product(keys: Sequence[str]) -> List[List[Seller]]:
        pid_list = list(keys)
        rows = await session.execute(
            select(product_sellers.c.product_id, SellerModel)
            .join(SellerModel, SellerModel.id == product_sellers.c.seller_id)
            .where(product_sellers.c.product_id.in_(pid_list))
            .order_by(SellerModel.name.asc(), SellerModel.id.asc())
        )
        mapping: Dict[str, List[Seller]] = {k: [] for k in pid_list}
        for product_id, seller in rows.all():
            mapping[str(product_id)].append(_seller_from_row(seller))
        return [mapping[k] for k in keys]

    async def load_products_by_seller(keys: Sequence[str]) -> List[List[Product]]:
        sid_list = list(keys)
        rows = await session.execute(
            select(product_sellers.c.seller_id, ProductModel)
            .join(ProductModel, ProductModel.id == product_sellers.c.product_id)
            .where(product_sellers.c.seller_id.in_(sid_list))
            .order_by(ProductModel.name.asc(), ProductModel.id.asc())
        )
        mapping: Dict[str, List[Product]] = {k: [] for k in sid_list}
        for seller_id, prod in rows.all():
            mapping[str(seller_id)].append(_product_from_row(prod))
        return [mapping[k] for k in keys]

    async def load_reviews_by_product(keys: Sequence[str]) -> List[List[Review]]:
        pid_list = list(keys)
        rows = (
            await session.execute(
                select(ReviewModel)
                .where(ReviewModel.product_id.in_(pid_list))
                .order_by(ReviewModel.product_id.asc(), ReviewModel.created_at.desc(), ReviewModel.id.desc())
            )
        ).scalars().all()
        mapping: Dict[str, List[Review]] = {k: [] for k in pid_list}
        for rev in rows:
            mapping[rev.product_id].append(_review_from_row(rev))
        return [mapping[k] for k in keys]

    async def load_review_count_by_product(keys: Sequence[str]) -> List[int]:
        pid_list = list(keys)
        rows = await session.execute(
            select(ReviewModel.product_id, func.count(ReviewModel.id))
            .where(ReviewModel.product_id.in_(pid_list))
            .group_by(ReviewModel.product_id)
        )
        counts: Dict[str, int] = {k: 0 for k in pid_list}
        for pid, n in rows.all():
            counts[str(pid)] = int(n or 0)
        return [counts[k] for k in keys]

    async def load_avg_rating_by_product(keys: Sequence[str]) -> List[float]:
        pid_list = list(keys)
        rows = await session.execute(
            select(ReviewModel.product_id, func.avg(ReviewModel.rating))
            .where(ReviewModel.product_id.in_(pid_list))
            .group_by(ReviewModel.product_id)
        )
        avgs: Dict[str, float] = {k: 0.0 for k in pid_list}
        for pid, avg_rating in rows.all():
            avgs[str(pid)] = float(avg_rating or 0.0)
        out: List[float] = []
        for k in keys:
            out.append(float(avgs[k]))
        return out

    return {
        "products_by_id": DataLoader(load_fn=load_products_by_id),
        "product_by_id": DataLoader(load_fn=load_product_by_id),
        "categories_by_product": DataLoader(load_fn=load_categories_by_product),
        "products_by_category": DataLoader(load_fn=load_products_by_category),
        "images_by_product": DataLoader(load_fn=load_images_by_product),
        "sellers_by_product": DataLoader(load_fn=load_sellers_by_product),
        "products_by_seller": DataLoader(load_fn=load_products_by_seller),
        "reviews_by_product": DataLoader(load_fn=load_reviews_by_product),
        "review_count_by_product": DataLoader(load_fn=load_review_count_by_product),
        "avg_rating_by_product": DataLoader(load_fn=load_avg_rating_by_product),
    }


@strawberry.type
class Query:
    @strawberry.field
    def ping(self) -> str:
        return "pong"

    @strawberry.field
    async def product(
        self,
        info: strawberry.Info,
        id: Optional[strawberry.ID] = None,
        sku: Optional[str] = None,
    ) -> Optional[Product]:
        session: AsyncSession = info.context["session"]
        if id is not None:
            return await info.context["loaders"]["product_by_id"].load(str(id))
        if sku:
            row = (
                await session.execute(select(ProductModel).where(ProductModel.sku == sku))
            ).scalars().first()
            return _product_from_row(row) if row else None
        return None

    @strawberry.field
    async def products(
        self,
        info: strawberry.Info,
        ids: Optional[List[strawberry.ID]] = None,
        category_id: Optional[strawberry.ID] = None,
        category_slug: Optional[str] = None,
        seller_id: Optional[strawberry.ID] = None,
        seller_slug: Optional[str] = None,
        in_stock: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Product]:
        session: AsyncSession = info.context["session"]

        lim = max(0, int(limit))
        off = max(0, int(offset))

        if ids:
            keys = [str(i) for i in ids]
            loaded = await info.context["loaders"]["products_by_id"].load_many(keys)
            out = [p for p in loaded if p is not None]
            return out[off : off + lim] if lim else out[off:]

        stmt = select(ProductModel)

        if category_slug:
            cat = (
                await session.execute(select(CategoryModel).where(CategoryModel.slug == category_slug))
            ).scalars().first()
            if not cat:
                return []
            category_id = strawberry.ID(cat.id)

        if category_id is not None:
            stmt = (
                stmt.join(product_categories, product_categories.c.product_id == ProductModel.id)
                .where(product_categories.c.category_id == str(category_id))
            )

        if seller_slug:
            seller = (
                await session.execute(select(SellerModel).where(SellerModel.slug == seller_slug))
            ).scalars().first()
            if not seller:
                return []
            seller_id = strawberry.ID(seller.id)

        if seller_id is not None:
            stmt = (
                stmt.join(product_sellers, product_sellers.c.product_id == ProductModel.id)
                .where(product_sellers.c.seller_id == str(seller_id))
            )

        if in_stock is not None:
            stmt = stmt.where(ProductModel.in_stock.is_(bool(in_stock)))

        if search:
            s = search.strip().lower()
            if s:
                like = f"%{s}%"
                stmt = stmt.where(
                    (ProductModel.name.ilike(like)) | (ProductModel.description.ilike(like)) | (ProductModel.sku.ilike(like))
                )

        stmt = stmt.order_by(ProductModel.name.asc(), ProductModel.id.asc()).offset(off)
        if lim:
            stmt = stmt.limit(lim)
        rows = (await session.execute(stmt)).scalars().all()
        return [_product_from_row(r) for r in rows]

    @strawberry.field
    async def categories(self, info: strawberry.Info) -> List[Category]:
        session: AsyncSession = info.context["session"]
        rows = (await session.execute(select(CategoryModel).order_by(CategoryModel.name.asc(), CategoryModel.id.asc()))).scalars().all()
        return [_category_from_row(r) for r in rows]

    @strawberry.field
    async def category(
        self, info: strawberry.Info, id: Optional[strawberry.ID] = None, slug: Optional[str] = None
    ) -> Optional[Category]:
        session: AsyncSession = info.context["session"]
        if id is not None:
            row = (await session.execute(select(CategoryModel).where(CategoryModel.id == str(id)))).scalars().first()
            return _category_from_row(row) if row else None
        if slug:
            row = (await session.execute(select(CategoryModel).where(CategoryModel.slug == slug))).scalars().first()
            return _category_from_row(row) if row else None
        return None

    @strawberry.field
    async def sellers(self, info: strawberry.Info) -> List[Seller]:
        session: AsyncSession = info.context["session"]
        rows = (await session.execute(select(SellerModel).order_by(SellerModel.name.asc(), SellerModel.id.asc()))).scalars().all()
        return [_seller_from_row(r) for r in rows]

    @strawberry.field
    async def seller(
        self, info: strawberry.Info, id: Optional[strawberry.ID] = None, slug: Optional[str] = None
    ) -> Optional[Seller]:
        session: AsyncSession = info.context["session"]
        if id is not None:
            row = (await session.execute(select(SellerModel).where(SellerModel.id == str(id)))).scalars().first()
            return _seller_from_row(row) if row else None
        if slug:
            row = (await session.execute(select(SellerModel).where(SellerModel.slug == slug))).scalars().first()
            return _seller_from_row(row) if row else None
        return None

    @strawberry.field
    async def reviews(
        self,
        info: strawberry.Info,
        product_id: Optional[strawberry.ID] = None,
        min_rating: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Review]:
        session: AsyncSession = info.context["session"]
        lim = max(0, int(limit))
        off = max(0, int(offset))

        stmt = select(ReviewModel)
        if product_id is not None:
            stmt = stmt.where(ReviewModel.product_id == str(product_id))
        if min_rating is not None:
            try:
                mr = int(min_rating)
            except Exception:
                mr = 0
            stmt = stmt.where(ReviewModel.rating >= mr)

        stmt = stmt.order_by(ReviewModel.created_at.desc(), ReviewModel.id.desc()).offset(off)
        if lim:
            stmt = stmt.limit(lim)
        rows = (await session.execute(stmt)).scalars().all()
        return [_review_from_row(r) for r in rows]


schema = strawberry.Schema(query=Query)


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./catalog.db")


def _create_engine() -> AsyncEngine:
    return create_async_engine(_database_url(), echo=False, future=True)


engine = _create_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db_and_seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        existing = (await session.execute(select(ProductModel.id).limit(1))).scalars().first()
        if existing:
            return

        cat_e = CategoryModel(id=_uuid(), slug="electronics", name="Electronics")
        cat_h = CategoryModel(id=_uuid(), slug="home-kitchen", name="Home & Kitchen")
        cat_b = CategoryModel(id=_uuid(), slug="books", name="Books")

        seller_a = SellerModel(id=_uuid(), slug="acme-market", name="Acme Market", rating=Decimal("4.80"))
        seller_b = SellerModel(id=_uuid(), slug="northwind", name="Northwind Traders", rating=Decimal("4.55"))
        seller_c = SellerModel(id=_uuid(), slug="paperback-palace", name="Paperback Palace", rating=Decimal("4.92"))

        p1 = ProductModel(
            id=_uuid(),
            sku="ELEC-0001",
            name="Wireless Headphones",
            description="Over-ear, noise-cancelling headphones with 30h battery life.",
            price=Decimal("129.99"),
            currency="USD",
            in_stock=True,
        )
        p2 = ProductModel(
            id=_uuid(),
            sku="HOME-0100",
            name="Stainless Steel Pan",
            description="12-inch tri-ply pan for everyday cooking.",
            price=Decimal("49.99"),
            currency="USD",
            in_stock=True,
        )
        p3 = ProductModel(
            id=_uuid(),
            sku="BOOK-2048",
            name="Practical GraphQL",
            description="A hands-on guide to designing and building GraphQL APIs.",
            price=Decimal("34.99"),
            currency="USD",
            in_stock=False,
        )

        session.add_all([cat_e, cat_h, cat_b, seller_a, seller_b, seller_c, p1, p2, p3])
        await session.flush()

        await session.execute(product_categories.insert(), [
            {"product_id": p1.id, "category_id": cat_e.id},
            {"product_id": p2.id, "category_id": cat_h.id},
            {"product_id": p3.id, "category_id": cat_b.id},
        ])

        await session.execute(product_sellers.insert(), [
            {"product_id": p1.id, "seller_id": seller_a.id},
            {"product_id": p1.id, "seller_id": seller_b.id},
            {"product_id": p2.id, "seller_id": seller_b.id},
            {"product_id": p3.id, "seller_id": seller_c.id},
        ])

        session.add_all(
            [
                ImageModel(product_id=p1.id, url="https://picsum.photos/seed/headphones/800/800", alt_text="Wireless headphones", position=1),
                ImageModel(product_id=p1.id, url="https://picsum.photos/seed/headphones2/800/800", alt_text="Headphones close-up", position=2),
                ImageModel(product_id=p2.id, url="https://picsum.photos/seed/pan/800/800", alt_text="Stainless steel pan", position=1),
                ImageModel(product_id=p3.id, url="https://picsum.photos/seed/graphqlbook/800/800", alt_text="GraphQL book cover", position=1),
            ]
        )

        session.add_all(
            [
                ReviewModel(product_id=p1.id, rating=5, title="Great sound", body="Comfortable fit and excellent noise cancellation.", author_name="Alex"),
                ReviewModel(product_id=p1.id, rating=4, title="Solid value", body="Good audio; could improve the mic quality.", author_name="Sam"),
                ReviewModel(product_id=p2.id, rating=5, title="Perfect pan", body="Heats evenly and cleans up easily.", author_name="Sam"),
                ReviewModel(product_id=p3.id, rating=5, title="Clear and practical", body="Excellent examples and good advice on schema design.", author_name="Jordan"),
            ]
        )

        await session.commit()


async def get_context() -> Dict[str, Any]:
    session = SessionLocal()
    ctx = RequestContext(session=session)
    ctx.loaders = await _create_loaders(ctx)
    return {
        "session": session,
        "loaders": ctx.loaders,
    }


async def on_close_context(context: Dict[str, Any]) -> None:
    session: AsyncSession = context["session"]
    await session.close()


graphql_app = GraphQLRouter(schema, context_getter=get_context, on_close_context=on_close_context)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health() -> Dict[str, bool]:
    return {"ok": True}


@app.on_event("startup")
async def _startup() -> None:
    await init_db_and_seed()


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("graphql_catalog_api:app", host=host, port=port, reload=False)
