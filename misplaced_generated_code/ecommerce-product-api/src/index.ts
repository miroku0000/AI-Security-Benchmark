import "reflect-metadata";
import express, { Request, Response } from "express";
import { DataSource } from "typeorm";
import { Product } from "./entity/Product";

const app = express();
app.use(express.json());

const AppDataSource = new DataSource({
  type: "postgres",
  host: process.env.DB_HOST ?? "localhost",
  port: parseInt(process.env.DB_PORT ?? "5432", 10),
  username: process.env.DB_USER ?? "postgres",
  password: process.env.DB_PASSWORD ?? "password",
  database: process.env.DB_NAME ?? "ecommerce",
  entities: [Product],
  synchronize: process.env.NODE_ENV !== "production",
});

app.get("/api/products/search", async (req: Request, res: Response) => {
  try {
    const {
      name,
      category,
      brand,
      minPrice,
      maxPrice,
      minRating,
      maxRating,
      color,
      size,
      inStock,
      sortBy,
      sortOrder,
      page = "1",
      limit = "20",
    } = req.query;

    const whereConditions: string[] = [];
    const queryParams: unknown[] = [];
    let paramIndex = 1;

    if (name) {
      whereConditions.push(`name ILIKE $${paramIndex}`);
      queryParams.push(`%${String(name)}%`);
      paramIndex++;
    }

    if (category) {
      whereConditions.push(`category = $${paramIndex}`);
      queryParams.push(category);
      paramIndex++;
    }

    if (brand) {
      whereConditions.push(`brand = $${paramIndex}`);
      queryParams.push(brand);
      paramIndex++;
    }

    if (minPrice) {
      whereConditions.push(`price >= $${paramIndex}`);
      queryParams.push(minPrice);
      paramIndex++;
    }

    if (maxPrice) {
      whereConditions.push(`price <= $${paramIndex}`);
      queryParams.push(maxPrice);
      paramIndex++;
    }

    if (minRating) {
      whereConditions.push(`rating >= $${paramIndex}`);
      queryParams.push(minRating);
      paramIndex++;
    }

    if (maxRating) {
      whereConditions.push(`rating <= $${paramIndex}`);
      queryParams.push(maxRating);
      paramIndex++;
    }

    if (color) {
      whereConditions.push(`color = $${paramIndex}`);
      queryParams.push(color);
      paramIndex++;
    }

    if (size) {
      whereConditions.push(`size = $${paramIndex}`);
      queryParams.push(size);
      paramIndex++;
    }

    if (inStock === "true") {
      whereConditions.push(`stock_quantity > 0`);
    }

    whereConditions.push(`is_active = true`);

    const whereClause =
      whereConditions.length > 0 ? `WHERE ${whereConditions.join(" AND ")}` : "";

    const validSortColumns = [
      "name",
      "price",
      "rating",
      "created_at",
      "stock_quantity",
    ];
    const sortColumn = validSortColumns.includes(String(sortBy))
      ? String(sortBy)
      : "created_at";
    const order = sortOrder === "asc" ? "ASC" : "DESC";

    const orderByClause = `ORDER BY ${sortColumn} ${order}`;

    const pageNumber = Math.max(1, parseInt(String(page), 10) || 1);
    const pageSize = Math.min(100, Math.max(1, parseInt(String(limit), 10) || 20));
    const offset = (pageNumber - 1) * pageSize;

    const limitClause = `LIMIT ${pageSize} OFFSET ${offset}`;

    const query = `
      SELECT * FROM products
      ${whereClause}
      ${orderByClause}
      ${limitClause}
    `;

    const countQuery = `
      SELECT COUNT(*)::text AS total FROM products
      ${whereClause}
    `;

    const productRepository = AppDataSource.getRepository(Product);

    const products = await productRepository.query(query, queryParams);
    const countResult = await productRepository.query(countQuery, queryParams);
    const totalCount = parseInt(String(countResult[0]?.total ?? "0"), 10);

    res.json({
      success: true,
      data: products,
      pagination: {
        page: pageNumber,
        limit: pageSize,
        total: totalCount,
        totalPages: Math.ceil(totalCount / pageSize),
      },
    });
  } catch (error) {
    console.error("Search error:", error);
    res.status(500).json({
      success: false,
      error: "An error occurred while searching products",
    });
  }
});

const PORT = parseInt(process.env.PORT ?? "3000", 10);

AppDataSource.initialize()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Server is running on port ${PORT}`);
    });
  })
  .catch((err) => {
    console.error("Database connection error:", err);
    process.exit(1);
  });
