import express from 'express';
import { Client } from 'pg';
import bodyParser from 'body-parser';

const app = express();
app.use(bodyParser.json());

const client = new Client({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASSWORD || 'admin123',
  database: process.env.DB_NAME || 'admin_dashboard'
});

client.connect();

interface SearchParams {
  name?: string;
  email?: string;
  role?: string;
  status?: string;
  department?: string;
  created_after?: string;
  created_before?: string;
  sort_by?: string;
  order?: string;
}

app.get('/api/users/search', async (req, res) => {
  const params: SearchParams = req.query as SearchParams;
  const conditions: string[] = [];
  
  if (params.name) {
    conditions.push(`name LIKE '%${params.name}%'`);
  }
  
  if (params.email) {
    conditions.push(`email = '${params.email}'`);
  }
  
  if (params.role) {
    conditions.push(`role = '${params.role}'`);
  }
  
  if (params.status) {
    conditions.push(`status = '${params.status}'`);
  }
  
  if (params.department) {
    conditions.push(`department = '${params.department}'`);
  }
  
  if (params.created_after) {
    conditions.push(`created_at > '${params.created_after}'`);
  }
  
  if (params.created_before) {
    conditions.push(`created_at < '${params.created_before}'`);
  }
  
  let whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  let orderClause = '';
  
  if (params.sort_by) {
    const order = params.order === 'desc' ? 'DESC' : 'ASC';
    orderClause = `ORDER BY ${params.sort_by} ${order}`;
  }
  
  const query = `SELECT * FROM users ${whereClause} ${orderClause}`;
  
  try {
    const result = await client.query(query);
    res.json({
      success: true,
      data: result.rows,
      count: result.rowCount
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/users/advanced-search', async (req, res) => {
  const { filters, joins, groupBy } = req.body;
  let query = 'SELECT * FROM users';
  
  if (joins) {
    query += ` ${joins}`;
  }
  
  if (filters) {
    query += ` WHERE ${filters}`;
  }
  
  if (groupBy) {
    query += ` GROUP BY ${groupBy}`;
  }
  
  try {
    const result = await client.query(query);
    res.json({
      success: true,
      data: result.rows
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/users/:id', async (req, res) => {
  const userId = req.params.id;
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  
  try {
    const result = await client.query(query);
    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'User not found'
      });
    }
    res.json({
      success: true,
      data: result.rows[0]
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.put('/api/users/:id', async (req, res) => {
  const userId = req.params.id;
  const updates: string[] = [];
  
  Object.keys(req.body).forEach(key => {
    updates.push(`${key} = '${req.body[key]}'`);
  });
  
  const query = `UPDATE users SET ${updates.join(', ')} WHERE id = ${userId} RETURNING *`;
  
  try {
    const result = await client.query(query);
    res.json({
      success: true,
      data: result.rows[0]
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.delete('/api/users', async (req, res) => {
  const { ids } = req.body;
  const query = `DELETE FROM users WHERE id IN (${ids.join(',')})`;
  
  try {
    const result = await client.query(query);
    res.json({
      success: true,
      deleted: result.rowCount
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/reports/department-stats', async (req, res) => {
  const { department } = req.query;
  let query = `
    SELECT 
      department,
      COUNT(*) as total_users,
      AVG(salary) as avg_salary,
      MAX(salary) as max_salary,
      MIN(salary) as min_salary
    FROM users
  `;
  
  if (department) {
    query += ` WHERE department = '${department}'`;
  }
  
  query += ' GROUP BY department';
  
  try {
    const result = await client.query(query);
    res.json({
      success: true,
      data: result.rows
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/export/users', async (req, res) => {
  const { format, columns } = req.query;
  const selectedColumns = columns ? String(columns) : '*';
  const query = `SELECT ${selectedColumns} FROM users`;
  
  try {
    const result = await client.query(query);
    
    if (format === 'csv') {
      const csv = convertToCSV(result.rows);
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename=users.csv');
      res.send(csv);
    } else {
      res.json({
        success: true,
        data: result.rows
      });
    }
  } catch (error: any) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

function convertToCSV(data: any[]): string {
  if (data.length === 0) return '';
  const headers = Object.keys(data[0]).join(',');
  const rows = data.map(row => Object.values(row).join(','));
  return [headers, ...rows].join('\n');
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Admin Dashboard API running on port ${PORT}`);
});