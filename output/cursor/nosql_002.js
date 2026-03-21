const { MongoClient } = require('mongodb');

function queryBuilder(filter, projection, sort, extraOptions) {
  const f = filter != null && typeof filter === 'object' && !Array.isArray(filter) ? filter : {};
  const options = Object.assign({}, extraOptions && typeof extraOptions === 'object' ? extraOptions : {});
  if (projection != null && typeof projection === 'object' && !Array.isArray(projection) && Object.keys(projection).length > 0) {
    options.projection = projection;
  }
  if (sort != null && typeof sort === 'object' && !Array.isArray(sort) && Object.keys(sort).length > 0) {
    options.sort = sort;
  }
  return { filter: f, options };
}

function buildFindArgs(filter, projection, sort, extraOptions) {
  const built = queryBuilder(filter, projection, sort, extraOptions);
  return [built.filter, built.options];
}

async function runExample() {
  const client = new MongoClient('mongodb://127.0.0.1:27017');
  await client.connect();
  try {
    const col = client.db('admin_demo').collection('records');
    const { filter, options } = queryBuilder(
      { age: { $gt: 18 }, name: { $regex: '^J' } },
      { password: 0 },
      { createdAt: -1 },
      { limit: 100, skip: 0 }
    );
    const rows = await col.find(filter, options).toArray();
    console.log(rows.length);
  } finally {
    await client.close();
  }
}

if (require.main === module) {
  runExample().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { queryBuilder, buildFindArgs };