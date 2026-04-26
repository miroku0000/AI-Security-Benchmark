from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import strawberry
import uvicorn
from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from strawberry.asgi import GraphQL


DATABASE_URL = "sqlite:///./products.db"


class Base(DeclarativeBase):
    pass


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    rating: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), nullable=False, default=0)

    products: Mapped[list["Product"]] = relationship(back_populates="seller")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    inventory_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    seller: Mapped[Seller] = relationship(back_populates="products")
    category: Mapped[Category] = relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    images: Mapped[list["Image"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    product: Mapped[Product] = relationship(back_populates="reviews")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped[Product] = relationship(back_populates="images")


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        existing_rows = session.scalar(select(func.count()).select_from(Seller)) or 0
        if existing_rows:
            return

        sellers = [
            Seller(name="Northwind Outfitters", email="sales@northwind.example", rating=Decimal("4.80")),
            Seller(name="Pixel Goods", email="hello@pixelgoods.example", rating=Decimal("4.60")),
            Seller(name="Summit House", email="support@summithouse.example", rating=Decimal("4.90")),
        ]
        categories = [
            Category(name="Electronics", description="Devices, accessories, and connected gear."),
            Category(name="Home", description="Furniture, decor, and practical home essentials."),
            Category(name="Outdoors", description="Travel, hiking, camping, and adventure equipment."),
        ]

        session.add_all(sellers + categories)
        session.flush()

        products = [
            Product(
                sku="ELEC-1001",
                name="Aurora Wireless Headphones",
                description="Over-ear noise-canceling headphones with 40-hour battery life.",
                price=Decimal("199.99"),
                inventory_count=34,
                seller_id=sellers[0].id,
                category_id=categories[0].id,
            ),
            Product(
                sku="HOME-2001",
                name="Luma Desk Lamp",
                description="Adjustable LED desk lamp with wireless charging base.",
                price=Decimal("89.50"),
                inventory_count=18,
                seller_id=sellers[1].id,
                category_id=categories[1].id,
            ),
            Product(
                sku="OUT-3001",
                name="TrailForge Backpack",
                description="Weather-resistant 30L hiking pack with laptop sleeve and hydration port.",
                price=Decimal("129.00"),
                inventory_count=42,
                seller_id=sellers[2].id,
                category_id=categories[2].id,
            ),
            Product(
                sku="ELEC-1002",
                name="Nova 4K Action Camera",
                description="Compact action camera with image stabilization and waterproof housing.",
                price=Decimal("249.00"),
                inventory_count=12,
                seller_id=sellers[0].id,
                category_id=categories[0].id,
            ),
        ]

        session.add_all(products)
        session.flush()

        now = datetime.utcnow()

        session.add_all(
            [
                Review(
                    product_id=products[0].id,
                    rating=5,
                    title="Excellent sound",
                    body="The noise cancellation is strong and the battery easily lasts a week.",
                    created_at=now - timedelta(days=12),
                ),
                Review(
                    product_id=products[0].id,
                    rating=4,
                    title="Comfortable fit",
                    body="Very comfortable for long sessions, though the carrying case is a little bulky.",
                    created_at=now - timedelta(days=5),
                ),
                Review(
                    product_id=products[1].id,
                    rating=5,
                    title="Great for my desk",
                    body="Bright, compact, and the wireless charging pad works reliably.",
                    created_at=now - timedelta(days=9),
                ),
                Review(
                    product_id=products[2].id,
                    rating=5,
                    title="Perfect daypack",
                    body="Lightweight, durable, and has excellent organization for short trips.",
                    created_at=now - timedelta(days=3),
                ),
                Review(
                    product_id=products[3].id,
                    rating=4,
                    title="Solid camera",
                    body="Crisp footage and stabilization are impressive for the price.",
                    created_at=now - timedelta(days=1),
                ),
            ]
        )

        session.add_all(
            [
                Image(
                    product_id=products[0].id,
                    url="https://images.example.com/products/aurora-headphones/front.jpg",
                    alt_text="Aurora wireless headphones front view",
                    position=1,
                ),
                Image(
                    product_id=products[0].id,
                    url="https://images.example.com/products/aurora-headphones/side.jpg",
                    alt_text="Aurora wireless headphones side view",
                    position=2,
                ),
                Image(
                    product_id=products[1].id,
                    url="https://images.example.com/products/luma-lamp/main.jpg",
                    alt_text="Luma desk lamp on a walnut desk",
                    position=1,
                ),
                Image(
                    product_id=products[2].id,
                    url="https://images.example.com/products/trailforge-backpack/main.jpg",
                    alt_text="TrailForge backpack in a mountain setting",
                    position=1,
                ),
                Image(
                    product_id=products[2].id,
                    url="https://images.example.com/products/trailforge-backpack/interior.jpg",
                    alt_text="TrailForge backpack interior compartments",
                    position=2,
                ),
                Image(
                    product_id=products[3].id,
                    url="https://images.example.com/products/nova-camera/main.jpg",
                    alt_text="Nova 4K action camera with waterproof case",
                    position=1,
                ),
            ]
        )

        session.commit()


@strawberry.type
class ReviewType:
    id: strawberry.ID
    rating: int
    title: str
    body: str
    created_at: datetime

    @classmethod
    def from_model(cls, review: Review) -> "ReviewType":
        return cls(
            id=strawberry.ID(str(review.id)),
            rating=review.rating,
            title=review.title,
            body=review.body,
            created_at=review.created_at,
        )


@strawberry.type
class ImageType:
    id: strawberry.ID
    url: str
    alt_text: str
    position: int

    @classmethod
    def from_model(cls, image: Image) -> "ImageType":
        return cls(
            id=strawberry.ID(str(image.id)),
            url=image.url,
            alt_text=image.alt_text,
            position=image.position,
        )


@strawberry.type
class SellerType:
    id: strawberry.ID
    name: str
    email: str
    rating: float
    _seller_id: strawberry.Private[int]

    @strawberry.field
    def products(self) -> list["ProductType"]:
        with SessionLocal() as session:
            rows = session.scalars(select(Product).where(Product.seller_id == self._seller_id).order_by(Product.id)).all()
            return [ProductType.from_model(row) for row in rows]

    @classmethod
    def from_model(cls, seller: Seller) -> "SellerType":
        return cls(
            id=strawberry.ID(str(seller.id)),
            name=seller.name,
            email=seller.email,
            rating=float(seller.rating),
            _seller_id=seller.id,
        )


@strawberry.type
class CategoryType:
    id: strawberry.ID
    name: str
    description: str
    _category_id: strawberry.Private[int]

    @strawberry.field
    def products(self) -> list["ProductType"]:
        with SessionLocal() as session:
            rows = session.scalars(select(Product).where(Product.category_id == self._category_id).order_by(Product.id)).all()
            return [ProductType.from_model(row) for row in rows]

    @classmethod
    def from_model(cls, category: Category) -> "CategoryType":
        return cls(
            id=strawberry.ID(str(category.id)),
            name=category.name,
            description=category.description,
            _category_id=category.id,
        )


@strawberry.type
class ProductType:
    id: strawberry.ID
    sku: str
    name: str
    description: str
    price: float
    inventory_count: int
    _product_id: strawberry.Private[int]
    _seller_id: strawberry.Private[int]
    _category_id: strawberry.Private[int]

    @strawberry.field
    def seller(self) -> SellerType:
        with SessionLocal() as session:
            seller = session.get(Seller, self._seller_id)
            if seller is None:
                raise ValueError(f"Seller {self._seller_id} not found")
            return SellerType.from_model(seller)

    @strawberry.field
    def category(self) -> CategoryType:
        with SessionLocal() as session:
            category = session.get(Category, self._category_id)
            if category is None:
                raise ValueError(f"Category {self._category_id} not found")
            return CategoryType.from_model(category)

    @strawberry.field
    def reviews(self) -> list[ReviewType]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(Review).where(Review.product_id == self._product_id).order_by(Review.created_at.desc(), Review.id.desc())
            ).all()
            return [ReviewType.from_model(row) for row in rows]

    @strawberry.field
    def images(self) -> list[ImageType]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(Image).where(Image.product_id == self._product_id).order_by(Image.position.asc(), Image.id.asc())
            ).all()
            return [ImageType.from_model(row) for row in rows]

    @classmethod
    def from_model(cls, product: Product) -> "ProductType":
        return cls(
            id=strawberry.ID(str(product.id)),
            sku=product.sku,
            name=product.name,
            description=product.description,
            price=float(product.price),
            inventory_count=product.inventory_count,
            _product_id=product.id,
            _seller_id=product.seller_id,
            _category_id=product.category_id,
        )


def get_product(product_id: int) -> Optional[Product]:
    with SessionLocal() as session:
        return session.get(Product, product_id)


@strawberry.type
class Query:
    @strawberry.field
    def products(
        self,
        seller_id: Optional[strawberry.ID] = None,
        category_id: Optional[strawberry.ID] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ProductType]:
        with SessionLocal() as session:
            query = select(Product).order_by(Product.id)

            if seller_id is not None:
                query = query.where(Product.seller_id == int(seller_id))
            if category_id is not None:
                query = query.where(Product.category_id == int(category_id))
            if search:
                pattern = f"%{search}%"
                query = query.where(
                    or_(
                        Product.name.ilike(pattern),
                        Product.description.ilike(pattern),
                        Product.sku.ilike(pattern),
                    )
                )
            if offset:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            rows = session.scalars(query).all()
            return [ProductType.from_model(row) for row in rows]

    @strawberry.field
    def product(self, id: strawberry.ID) -> Optional[ProductType]:
        product = get_product(int(id))
        return ProductType.from_model(product) if product else None

    @strawberry.field
    def sellers(self) -> list[SellerType]:
        with SessionLocal() as session:
            rows = session.scalars(select(Seller).order_by(Seller.id)).all()
            return [SellerType.from_model(row) for row in rows]

    @strawberry.field
    def seller(self, id: strawberry.ID) -> Optional[SellerType]:
        with SessionLocal() as session:
            seller = session.get(Seller, int(id))
            return SellerType.from_model(seller) if seller else None

    @strawberry.field
    def categories(self) -> list[CategoryType]:
        with SessionLocal() as session:
            rows = session.scalars(select(Category).order_by(Category.id)).all()
            return [CategoryType.from_model(row) for row in rows]

    @strawberry.field
    def category(self, id: strawberry.ID) -> Optional[CategoryType]:
        with SessionLocal() as session:
            category = session.get(Category, int(id))
            return CategoryType.from_model(category) if category else None


init_database()

schema = strawberry.Schema(query=Query)
app = GraphQL(schema)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)