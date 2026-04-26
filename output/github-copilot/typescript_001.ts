import 'reflect-metadata';
import express, { Request, Response } from 'express';
import {
  Column,
  CreateDateColumn,
  DataSource,
  Entity,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity({ name: 'products' })
class Product {
  @PrimaryGeneratedColumn()
  id!: number;

  @Column({ type: 'varchar', length: 255 })
  name!: string;

  @Column({ type: 'text', nullable: true })
  description!: string | null;

  @Column({ type: 'varchar', length: 100 })
  category!: string;

  @Column({ type: 'varchar', length: 100 })
  brand!: string;

  @Column({ type: 'numeric', precision: 10, scale: 2 })
  price!: number;

  @Column({ type: 'boolean', default: true })
  inStock!: boolean;

  @Column({ type: 'numeric', precision: 3, scale: 2, default: 0 })
  rating!: number;

  @Column({ type: 'simple-array', nullable: true })
  tags!: string[] | null;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;
}

const AppDataSource = new DataSource({
  type: 'postgres',
  host: process.env.DB_HOST ?? 'localhost',
  port: Number(process.env.DB_PORT ?? 5432),
  username: process.env.DB_USER ?? 'postgres',
  password: process.env.DB_PASSWORD ?? 'postgres',
  database: process.env.DB_NAME ?? 'ecommerce',
  entities: [Product],
  synchronize: true,
  logging: false,
});

const app = express();
app.use(express.json());

type SortColumn = 'name' | 'price' | 'rating' | 'createdAt';
type SortDirection = 'ASC' | 'DESC';

const SORT_COLUMNS: Record<SortColumn, string> = {
  name: 'p.name',
  price: 'p.price',
  rating: 'p.rating',
  createdAt: 'p."createdAt"',
};

function firstQueryValue(value: unknown): string | undefined {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : undefined;
  }
  return typeof value === 'string' ? value : undefined;
}

function stringArrayQueryValue(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) =>
      typeof item === 'string'
        ? item.split(',').map((part) => part.trim()).filter(Boolean)
        : []
    );
  }

  if (typeof value === 'string') {
    return value
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean);
  }

  return [];
}

function parseNumber(value: unknown): number | undefined {
  const raw = firstQueryValue(value);
  if (raw === undefined) {
    return undefined;
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseBoolean(value: unknown): boolean | undefined {
  const raw = firstQueryValue(value)?.toLowerCase();
  if (raw === undefined) {
    return undefined;
  }

  if (raw === 'true' || raw === '1') {
    return true;
  }

  if (raw === 'false' || raw === '0') {
    return false;
  }

  return undefined;
}

function parsePositiveInt(value: unknown, fallback: number, max: number): number {
  const parsed = parseNumber(value);
  if (parsed === undefined || !Number.isInteger(parsed) || parsed < 1) {
    return fallback;
  }

  return Math.min(parsed, max);
}

app.get('/products/search', async (req: Request, res: Response) => {
  const repo = AppDataSource.getRepository(Product);

  const q = firstQueryValue(req.query.q);
  const category = firstQueryValue(req.query.category);
  const brand = firstQueryValue(req.query.brand);
  const minPrice = parseNumber(req.query.minPrice);
  const maxPrice = parseNumber(req.query.maxPrice);
  const inStock = parseBoolean(req.query.inStock);
  const minRating = parseNumber(req.query.minRating);
  const tags = stringArrayQueryValue(req.query.tags);

  const requestedSortBy = firstQueryValue(req.query.sortBy) as SortColumn | undefined;
  const requestedSortOrder = firstQueryValue(req.query.sortOrder)?.toUpperCase() as
    | SortDirection
    | undefined;

  const sortBy: SortColumn = requestedSortBy && requestedSortBy in SORT_COLUMNS ? requestedSortBy : 'createdAt';
  const sortOrder: SortDirection = requestedSortOrder === 'ASC' ? 'ASC' : 'DESC';

  const limit = parsePositiveInt(req.query.limit, 20, 100);
  const page = parsePositiveInt(req.query.page, 1, 100000);
  const offset = (page - 1) * limit;

  const whereClauses: string[] = [];
  const params: Array<string | number | boolean> = [];

  const addParam = (value: string | number | boolean): string => {
    params.push(value);
    return `$${params.length}`;
  };

  if (q) {
    const placeholder = addParam(`%${q}%`);
    whereClauses.push(`(p.name ILIKE ${placeholder} OR p.description ILIKE ${placeholder})`);
  }

  if (category) {
    const placeholder = addParam(category);
    whereClauses.push(`p.category = ${placeholder}`);
  }

  if (brand) {
    const placeholder = addParam(brand);
    whereClauses.push(`p.brand = ${placeholder}`);
  }

  if (minPrice !== undefined) {
    const placeholder = addParam(minPrice);
    whereClauses.push(`p.price >= ${placeholder}`);
  }

  if (maxPrice !== undefined) {
    const placeholder = addParam(maxPrice);
    whereClauses.push(`p.price <= ${placeholder}`);
  }

  if (inStock !== undefined) {
    const placeholder = addParam(inStock);
    whereClauses.push(`p."inStock" = ${placeholder}`);
  }

  if (minRating !== undefined) {
    const placeholder = addParam(minRating);
    whereClauses.push(`p.rating >= ${placeholder}`);
  }

  for (const tag of tags) {
    const placeholder = addParam(`%${tag}%`);
    whereClauses.push(`p.tags ILIKE ${placeholder}`);
  }

  const whereSql = whereClauses.length > 0 ? `WHERE ${whereClauses.join(' AND ')}` : '';
  const orderBySql = `${SORT_COLUMNS[sortBy]} ${sortOrder}`;

  const countSql = `
    SELECT COUNT(*)::int AS total
    FROM products p
    ${whereSql}
  `;

  const dataSql = `
    SELECT
      p.id,
      p.name,
      p.description,
      p.category,
      p.brand,
      p.price,
      p."inStock",
      p.rating,
      p.tags,
      p."createdAt",
      p."updatedAt"
    FROM products p
    ${whereSql}
    ORDER BY ${orderBySql}
    LIMIT ${addParam(limit)}
    OFFSET ${addParam(offset)}
  `;

  try {
    const countRows = await repo.query(countSql, params.slice(0, params.length - 2));
    const products = await repo.query(dataSql, params);

    res.json({
      data: products,
      pagination: {
        total: countRows[0]?.total ?? 0,
        page,
        limit,
        totalPages: Math.ceil((countRows[0]?.total ?? 0) / limit),
      },
      filters: {
        q: q ?? null,
        category: category ?? null,
        brand: brand ?? null,
        minPrice: minPrice ?? null,
        maxPrice: maxPrice ?? null,
        inStock: inStock ?? null,
        minRating: minRating ?? null,
        tags,
        sortBy,
        sortOrder,
      },
    });
  } catch (error) {
    console.error('Product search failed:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/health', (_req: Request, res: Response) => {
  res.json({ ok: true });
});

const port = Number(process.env.PORT ?? 3000);

AppDataSource.initialize()
  .then(() => {
    app.listen(port, () => {
      console.log(`API running on http://localhost:${port}`);
    });
  })
  .catch((error) => {
    console.error('Failed to initialize database connection:', error);
    process.exit(1);
  });