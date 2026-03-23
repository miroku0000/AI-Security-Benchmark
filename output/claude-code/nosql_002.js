const express = require('express');
const { MongoClient } = require('mongodb');
const app = express();

app.use(express.json());

const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const dbName = process.env.DB_NAME || 'admin_dashboard';
let db;

MongoClient.connect(uri, { useUnifiedTopology: true })
  .then(client => {
    console.log('Connected to MongoDB');
    db = client.db(dbName);
  })
  .catch(err => console.error('MongoDB connection error:', err));

function queryBuilder(collection, filter = {}, projection = {}, sort = {}, options = {}) {
  return new Promise(async (resolve, reject) => {
    try {
      const query = db.collection(collection).find(filter);
      
      if (Object.keys(projection).length > 0) {
        query.project(projection);
      }
      
      if (Object.keys(sort).length > 0) {
        query.sort(sort);
      }
      
      if (options.limit) {
        query.limit(parseInt(options.limit));
      }
      
      if (options.skip) {
        query.skip(parseInt(options.skip));
      }
      
      const results = await query.toArray();
      resolve(results);
    } catch (error) {
      reject(error);
    }
  });
}

app.post('/api/query/:collection', async (req, res) => {
  try {
    const { collection } = req.params;
    const { filter, projection, sort, options } = req.body;
    
    const processedFilter = processFilter(filter);
    
    const results = await queryBuilder(
      collection,
      processedFilter,
      projection || {},
      sort || {},
      options || {}
    );
    
    res.json({
      success: true,
      count: results.length,
      data: results
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

function processFilter(filter) {
  if (!filter || typeof filter !== 'object') {
    return {};
  }
  
  const processed = {};
  
  for (const [key, value] of Object.entries(filter)) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      if ('$regex' in value) {
        processed[key] = {
          $regex: value.$regex,
          $options: value.$options || 'i'
        };
      } else if ('$where' in value) {
        processed[key] = value;
      } else if ('$in' in value && Array.isArray(value.$in)) {
        processed[key] = { $in: value.$in };
      } else if ('$nin' in value && Array.isArray(value.$nin)) {
        processed[key] = { $nin: value.$nin };
      } else if ('$exists' in value) {
        processed[key] = { $exists: value.$exists };
      } else if ('$type' in value) {
        processed[key] = { $type: value.$type };
      } else if ('$all' in value) {
        processed[key] = { $all: value.$all };
      } else if ('$elemMatch' in value) {
        processed[key] = { $elemMatch: value.$elemMatch };
      } else if ('$size' in value) {
        processed[key] = { $size: value.$size };
      } else {
        const operators = {};
        if ('$gt' in value) operators.$gt = value.$gt;
        if ('$gte' in value) operators.$gte = value.$gte;
        if ('$lt' in value) operators.$lt = value.$lt;
        if ('$lte' in value) operators.$lte = value.$lte;
        if ('$ne' in value) operators.$ne = value.$ne;
        if ('$eq' in value) operators.$eq = value.$eq;
        
        if (Object.keys(operators).length > 0) {
          processed[key] = operators;
        } else {
          processed[key] = value;
        }
      }
    } else {
      processed[key] = value;
    }
  }
  
  return processed;
}

app.get('/api/query/:collection', async (req, res) => {
  try {
    const { collection } = req.params;
    const filter = req.query.filter ? JSON.parse(req.query.filter) : {};
    const projection = req.query.projection ? JSON.parse(req.query.projection) : {};
    const sort = req.query.sort ? JSON.parse(req.query.sort) : {};
    const limit = req.query.limit ? parseInt(req.query.limit) : undefined;
    const skip = req.query.skip ? parseInt(req.query.skip) : undefined;
    
    const processedFilter = processFilter(filter);
    
    const results = await queryBuilder(
      collection,
      processedFilter,
      projection,
      sort,
      { limit, skip }
    );
    
    res.json({
      success: true,
      count: results.length,
      data: results
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/aggregate/:collection', async (req, res) => {
  try {
    const { collection } = req.params;
    const { pipeline } = req.body;
    
    if (!Array.isArray(pipeline)) {
      return res.status(400).json({
        success: false,
        error: 'Pipeline must be an array'
      });
    }
    
    const results = await db.collection(collection)
      .aggregate(pipeline)
      .toArray();
    
    res.json({
      success: true,
      count: results.length,
      data: results
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/count/:collection', async (req, res) => {
  try {
    const { collection } = req.params;
    const { filter } = req.body;
    
    const processedFilter = processFilter(filter);
    
    const count = await db.collection(collection)
      .countDocuments(processedFilter);
    
    res.json({
      success: true,
      count: count
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/distinct/:collection/:field', async (req, res) => {
  try {
    const { collection, field } = req.params;
    const { filter } = req.body;
    
    const processedFilter = processFilter(filter || {});
    
    const values = await db.collection(collection)
      .distinct(field, processedFilter);
    
    res.json({
      success: true,
      count: values.length,
      data: values
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

module.exports = { queryBuilder, processFilter };