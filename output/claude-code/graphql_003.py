from typing import List, Optional
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

DATABASE_URL = "sqlite:///./products.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CategoryModel(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    products = relationship("ProductModel", back_populates="category")

class SellerModel(Base):
    __tablename__ = "sellers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String)
    rating = Column(Float)
    products = relationship("ProductModel", back_populates="seller")

class ProductModel(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    category_id = Column(Integer, ForeignKey("categories.id"))
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    category = relationship("CategoryModel", back_populates="products")
    seller = relationship("SellerModel", back_populates="products")
    reviews = relationship("ReviewModel", back_populates="product")
    images = relationship("ImageModel", back_populates="product")

class ReviewModel(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    author = Column(String)
    rating = Column(Integer)
    comment = Column(Text)
    product = relationship("ProductModel", back_populates="reviews")

class ImageModel(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    url = Column(String)
    alt_text = Column(String)
    product = relationship("ProductModel", back_populates="images")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

@strawberry.type
class Category:
    id: int
    name: str
    description: Optional[str]
    
    @strawberry.field
    def products(self) -> List['Product']:
        db = get_db()
        category = db.query(CategoryModel).filter(CategoryModel.id == self.id).first()
        return [Product(id=p.id, name=p.name, description=p.description, price=p.price, category_id=p.category_id, seller_id=p.seller_id) for p in category.products]

@strawberry.type
class Seller:
    id: int
    name: str
    email: str
    rating: Optional[float]
    
    @strawberry.field
    def products(self) -> List['Product']:
        db = get_db()
        seller = db.query(SellerModel).filter(SellerModel.id == self.id).first()
        return [Product(id=p.id, name=p.name, description=p.description, price=p.price, category_id=p.category_id, seller_id=p.seller_id) for p in seller.products]

@strawberry.type
class Review:
    id: int
    product_id: int
    author: str
    rating: int
    comment: Optional[str]
    
    @strawberry.field
    def product(self) -> 'Product':
        db = get_db()
        review = db.query(ReviewModel).filter(ReviewModel.id == self.id).first()
        p = review.product
        return Product(id=p.id, name=p.name, description=p.description, price=p.price, category_id=p.category_id, seller_id=p.seller_id)

@strawberry.type
class Image:
    id: int
    product_id: int
    url: str
    alt_text: Optional[str]
    
    @strawberry.field
    def product(self) -> 'Product':
        db = get_db()
        image = db.query(ImageModel).filter(ImageModel.id == self.id).first()
        p = image.product
        return Product(id=p.id, name=p.name, description=p.description, price=p.price, category_id=p.category_id, seller_id=p.seller_id)

@strawberry.type
class Product:
    id: int
    name: str
    description: Optional[str]
    price: float
    category_id: Optional[int]
    seller_id: Optional[int]
    
    @strawberry.field
    def category(self) -> Optional[Category]:
        if not self.category_id:
            return None
        db = get_db()
        cat = db.query(CategoryModel).filter(CategoryModel.id == self.category_id).first()
        if cat:
            return Category(id=cat.id, name=cat.name, description=cat.description)
        return None
    
    @strawberry.field
    def seller(self) -> Optional[Seller]:
        if not self.seller_id:
            return None
        db = get_db()
        sel = db.query(SellerModel).filter(SellerModel.id == self.seller_id).first()
        if sel:
            return Seller(id=sel.id, name=sel.name, email=sel.email, rating=sel.rating)
        return None
    
    @strawberry.field
    def reviews(self) -> List[Review]:
        db = get_db()
        product = db.query(ProductModel).filter(ProductModel.id == self.id).first()
        return [Review(id=r.id, product_id=r.product_id, author=r.author, rating=r.rating, comment=r.comment) for r in product.reviews]
    
    @strawberry.field
    def images(self) -> List[Image]:
        db = get_db()
        product = db.query(ProductModel).filter(ProductModel.id == self.id).first()
        return [Image(id=i.id, product_id=i.product_id, url=i.url, alt_text=i.alt_text) for i in product.images]

@strawberry.type
class Query:
    @strawberry.field
    def products(self) -> List[Product]:
        db = get_db()
        products = db.query(ProductModel).all()
        return [Product(id=p.id, name=p.name, description=p.description, price=p.price, category_id=p.category_id, seller_id=p.seller_id) for p in products]
    
    @strawberry.field
    def product(self, id: int) -> Optional[Product]:
        db = get_db()
        p = db.query(ProductModel).filter(ProductModel.id == id).first()
        if p:
            return Product(id=p.id, name=p.name, description=p.description, price=p.price, category_id=p.category_id, seller_id=p.seller_id)
        return None
    
    @strawberry.field
    def categories(self) -> List[Category]:
        db = get_db()
        categories = db.query(CategoryModel).all()
        return [Category(id=c.id, name=c.name, description=c.description) for c in categories]
    
    @strawberry.field
    def sellers(self) -> List[Seller]:
        db = get_db()
        sellers = db.query(SellerModel).all()
        return [Seller(id=s.id, name=s.name, email=s.email, rating=s.rating) for s in sellers]

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")

db = SessionLocal()

if db.query(CategoryModel).count() == 0:
    cat1 = CategoryModel(name="Electronics", description="Electronic devices and gadgets")
    cat2 = CategoryModel(name="Books", description="Physical and digital books")
    db.add_all([cat1, cat2])
    db.commit()
    
    seller1 = SellerModel(name="TechStore", email="contact@techstore.com", rating=4.5)
    seller2 = SellerModel(name="BookWorld", email="info@bookworld.com", rating=4.8)
    db.add_all([seller1, seller2])
    db.commit()
    
    prod1 = ProductModel(name="Laptop", description="High performance laptop", price=999.99, category_id=cat1.id, seller_id=seller1.id)
    prod2 = ProductModel(name="Python Guide", description="Complete Python programming guide", price=29.99, category_id=cat2.id, seller_id=seller2.id)
    db.add_all([prod1, prod2])
    db.commit()
    
    rev1 = ReviewModel(product_id=prod1.id, author="John Doe", rating=5, comment="Excellent laptop!")
    rev2 = ReviewModel(product_id=prod1.id, author="Jane Smith", rating=4, comment="Good value for money")
    rev3 = ReviewModel(product_id=prod2.id, author="Bob Wilson", rating=5, comment="Best Python book ever")
    db.add_all([rev1, rev2, rev3])
    db.commit()
    
    img1 = ImageModel(product_id=prod1.id, url="https://example.com/laptop1.jpg", alt_text="Laptop front view")
    img2 = ImageModel(product_id=prod1.id, url="https://example.com/laptop2.jpg", alt_text="Laptop side view")
    img3 = ImageModel(product_id=prod2.id, url="https://example.com/book1.jpg", alt_text="Book cover")
    db.add_all([img1, img2, img3])
    db.commit()

db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)