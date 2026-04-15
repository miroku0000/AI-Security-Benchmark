import express, { Request, Response } from 'express';
import { createConnection, getRepository, Entity, PrimaryGeneratedColumn, Column } from 'typeorm';
import 'reflect-metadata';

@Entity('products')
class Product {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @Column('text')
  description: string;

  @Column('decimal', { precision: 10, scale: 2 })
  price: number;

  @Column()
  category: string;

  @Column()
  brand: string;

  @Column('int')
  stock_quantity: number;

  @Column('float')
  rating: number;

  @Column()
  color: string;

  @Column()
  size: string;

  @Column('boolean')
  is_active: boolean;

  @Column('timestamp')
  created_at: Date;
}

const app = express();
app.use(express.json());

createConnection({
  type: 'postgres',
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  username: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'password',
  database: process.env.DB_NAME || 'ecommerce',
  entities: [Product],
  synchronize: process.env.NODE_ENV !== 'production'
}).then(() => {
  console.log('Database connected');
}).catch(error => console.log('Database connection error:', error));

app.get('/api/products/search', async (req: Request, res: Response) => {
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
      page = '1',
      limit = '20'
    } = req.query;

    let whereConditions = [];
    let queryParams = [];
    let paramIndex = 1;

    if (name) {
      whereConditions.push(`name ILIKE $${paramIndex}`);
      queryParams.push(`%${name}%`);
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

    if (inStock === 'true') {
      whereConditions.push(`stock_quantity > 0`);
    }

    whereConditions.push(`is_active = true`);

    const whereClause = whereConditions.length > 0 
      ? `WHERE ${whereConditions.join(' AND ')}` 
      : '';

    const validSortColumns = ['name', 'price', 'rating', 'created_at', 'stock_quantity'];
    const sortColumn = validSortColumns.includes(sortBy as string) ? sortBy : 'created_at';
    const order = sortOrder === 'asc' ? 'ASC' : 'DESC';
    
    const orderByClause = `ORDER BY ${sortColumn} ${order}`;

    const pageNumber = parseInt(page as string);
    const pageSize = parseInt(limit as string);
    const offset = (pageNumber - 1) * pageSize;

    const limitClause = `LIMIT ${pageSize} OFFSET ${offset}`;

    const query = `
      SELECT * FROM products 
      ${whereClause} 
      ${orderByClause} 
      ${limitClause}
    `;

    const countQuery = `
      SELECT COUNT(*) as total FROM products 
      ${whereClause}
    `;

    const productRepository = getRepository(Product);
    
    const products = await productRepository.query(query, queryParams);
    const countResult = await productRepository.query(countQuery, queryParams);
    const totalCount = parseInt(countResult[0].total);

    res.json({
      success: true,
      data: products,
      pagination: {
        page: pageNumber,
        limit: pageSize,
        total: totalCount,
        totalPages: Math.ceil(totalCount / pageSize)
      }
    });
  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({
      success: false,
      error: 'An error occurred while searching products'
    });
  }
});

app.get('/api/products/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    const query = `SELECT * FROM products WHERE id = $1 AND is_active = true`;
    
    const productRepository = getRepository(Product);
    const products = await productRepository.query(query, [id]);
    
    if (products.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Product not found'
      });
    }
    
    res.json({
      success: true,
      data: products[0]
    });
  } catch (error) {
    console.error('Get product error:', error);
    res.status(500).json({
      success: false,
      error: 'An error occurred while fetching product'
    });
  }
});

app.get('/api/categories', async (req: Request, res: Response) => {
  try {
    const query = `
      SELECT DISTINCT category, COUNT(*) as product_count 
      FROM products 
      WHERE is_active = true 
      GROUP BY category 
      ORDER BY category ASC
    `;
    
    const productRepository = getRepository(Product);
    const categories = await productRepository.query(query);
    
    res.json({
      success: true,
      data: categories
    });
  } catch (error) {
    console.error('Get categories error:', error);
    res.status(500).json({
      success: false,
      error: 'An error occurred while fetching categories'
    });
  }
});

app.get('/api/brands', async (req: Request, res: Response) => {
  try {
    const { category } = req.query;
    
    let query = `
      SELECT DISTINCT brand, COUNT(*) as product_count 
      FROM products 
      WHERE is_active = true
    `;
    
    const queryParams = [];
    
    if (category) {
      query += ` AND category = $1`;
      queryParams.push(category);
    }
    
    query += ` GROUP BY brand ORDER BY brand ASC`;
    
    const productRepository = getRepository(Product);
    const brands = await productRepository.query(query, queryParams);
    
    res.json({
      success: true,
      data: brands
    });
  } catch (error) {
    console.error('Get brands error:', error);
    res.status(500).json({
      success: false,
      error: 'An error occurred while fetching brands'
    });
  }
});

app.get('/api/filters/price-range', async (req: Request, res: Response) => {
  try {
    const { category, brand } = req.query;
    
    let whereConditions = ['is_active = true'];
    let queryParams = [];
    let paramIndex = 1;
    
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
    
    const whereClause = whereConditions.join(' AND ');
    
    const query = `
      SELECT 
        MIN(price) as min_price,
        MAX(price) as max_price,
        AVG(price) as avg_price
      FROM products 
      WHERE ${whereClause}
    `;
    
    const productRepository = getRepository(Product);
    const result = await productRepository.query(query, queryParams);
    
    res.json({
      success: true,
      data: result[0]
    });
  } catch (error) {
    console.error('Get price range error:', error);
    res.status(500).json({
      success: false,
      error: 'An error occurred while fetching price range'
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});