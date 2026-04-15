const { BigQuery } = require('@google-cloud/bigquery');
const functions = require('@google-cloud/functions-framework');

const bigquery = new BigQuery();

functions.http('processLargeDataset', async (req, res) => {
  const { dataset, table, query, outputDataset, outputTable } = req.body;

  if (!query && (!dataset || !table)) {
    res.status(400).json({ error: 'Provide either a query or dataset/table parameters' });
    return;
  }

  const startTime = Date.now();
  const results = [];
  let totalRows = 0;

  try {
    const sqlQuery = query || `SELECT * FROM \`${dataset}.${table}\``;

    const [job] = await bigquery.createQueryJob({
      query: sqlQuery,
      location: 'US',
      maximumBytesBilled: '10000000000',
    });

    const [rows] = await job.getQueryResults({ autoPaginate: true });
    totalRows = rows.length;

    const batchSize = 10000;
    for (let i = 0; i < rows.length; i += batchSize) {
      const batch = rows.slice(i, i + batchSize);
      const aggregated = aggregateBatch(batch);
      results.push(aggregated);
    }

    const finalResult = mergeAggregations(results);

    if (outputDataset && outputTable) {
      const outputRef = bigquery.dataset(outputDataset).table(outputTable);
      await outputRef.insert(Array.isArray(finalResult) ? finalResult : [finalResult]);
    }

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);

    res.status(200).json({
      status: 'success',
      rowsProcessed: totalRows,
      elapsedSeconds: parseFloat(elapsed),
      result: finalResult,
    });
  } catch (error) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
    res.status(500).json({
      status: 'error',
      message: error.message,
      rowsProcessed: totalRows,
      elapsedSeconds: parseFloat(elapsed),
    });
  }
});

function aggregateBatch(rows) {
  if (rows.length === 0) return { count: 0, sums: {}, mins: {}, maxs: {} };

  const sums = {};
  const mins = {};
  const maxs = {};
  let count = rows.length;

  for (const row of rows) {
    for (const [key, value] of Object.entries(row)) {
      if (typeof value === 'number') {
        sums[key] = (sums[key] || 0) + value;
        mins[key] = key in mins ? Math.min(mins[key], value) : value;
        maxs[key] = key in maxs ? Math.max(maxs[key], value) : value;
      }
    }
  }

  return { count, sums, mins, maxs };
}

function mergeAggregations(aggregations) {
  if (aggregations.length === 0) return { count: 0, sums: {}, mins: {}, maxs: {}, averages: {} };

  const merged = { count: 0, sums: {}, mins: {}, maxs: {}, averages: {} };

  for (const agg of aggregations) {
    merged.count += agg.count;

    for (const [key, value] of Object.entries(agg.sums)) {
      merged.sums[key] = (merged.sums[key] || 0) + value;
    }
    for (const [key, value] of Object.entries(agg.mins)) {
      merged.mins[key] = key in merged.mins ? Math.min(merged.mins[key], value) : value;
    }
    for (const [key, value] of Object.entries(agg.maxs)) {
      merged.maxs[key] = key in merged.maxs ? Math.max(merged.maxs[key], value) : value;
    }
  }

  for (const [key, sum] of Object.entries(merged.sums)) {
    merged.averages[key] = merged.count > 0 ? sum / merged.count : 0;
  }

  return merged;
}