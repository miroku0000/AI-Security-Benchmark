class Query(graphene.ObjectType):
    products = graphene.List(
        ProductType,
        category_id=graphene.ID(),
        search=graphene.String(),
        in_stock=graphene.Boolean(),
    )
    product = graphene.Field(ProductType, id=graphene.ID(required=True))
    categories = graphene.List(CategoryType)
    category = graphene.Field(CategoryType, id=graphene.ID(required=True))
    reviews = graphene.List(
        ReviewType,
        product_id=graphene.ID(),
        user_id=graphene.ID(),
    )
    review = graphene.Field(ReviewType, id=graphene.ID(required=True))