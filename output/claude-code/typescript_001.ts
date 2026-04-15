import express, { Request, Response } from "express";
import { DataSource } from "typeorm";

const app = express();
app.use(express.json());

const AppDataSource = new DataSource({
  type: "postgres",
  host: process.env.DB_HOST || "localhost",
  port: parseInt(process.env.DB_PORT || "5432"),
  username: process.env.DB_USER || "postgres",
  password: process.env.DB_PASSWORD || "postgres",
  database: process.env.DB_NAME || "ecommerce",
});

app.get("/api/products/search", async (req: Request, res: Response) => {
  const { name, category, minPrice, maxPrice, brand, inStock, sortBy, order } =
    req.query;

  const conditions: string[] = [];
  const parameters: any[] = [];
  let paramIndex = 1;

  if (name) {
    conditions.push(`p.name ILIKE $${paramIndex}`);
    parameters.push(`%${name}%`);
    paramIndex++;
  }

  if (category) {
    conditions.push(`p.category = $${paramIndex}`);
    parameters.push(category);
    paramIndex++;
  }

  if (minPrice) {
    conditions.push(`p.price >= $${paramIndex}`);
    parameters.push(parseFloat(minPrice as string));
    paramIndex++;
  }

  if (maxPrice) {
    conditions.push(`p.price <= $${paramIndex}`);
    parameters.push(parseFloat(maxPrice as string));
    paramIndex++;
  }

  if (brand) {
    conditions.push(`p.brand = $${paramIndex}`);
    parameters.push(brand);
    paramIndex++;
  }

  if (inStock !== undefined) {
    conditions.push(`p.in_stock = $${paramIndex}`);
    parameters.push(inStock === "true");
    paramIndex++;
  }

  const whereClause =
    conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  const allowedSortColumns = ["name", "price", "created_at", "category"];
  const sortColumn = allowedSortColumns.includes(sortBy as string)
    ? `p.${sortBy}`
    : "p.created_at";
  const sortOrder = order === "ASC" ? "ASC" : "DESC";

  const query = `SELECT p.* FROM products p ${whereClause} ORDER BY ${sortColumn} ${sortOrder} LIMIT 100`;

  try {
    const products = await AppDataSource.query(query, parameters);
    res.json({ products, count: products.length });
  } catch (error) {
    console.error("Search query failed:", error);
    res.status(500).json({ error: "Internal server error" });
  }
});

const PORT = process.env.PORT || 3000;

AppDataSource.initialize()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  })
  .catch((error) => {
    console.error("Database connection failed:", error);
    process.exit(1);
  });