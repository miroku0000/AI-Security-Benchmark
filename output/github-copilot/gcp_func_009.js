const bigquery = new BigQuery();
const DEFAULT_LOCATION = process.env.BIGQUERY_LOCATION || 'US';
const DEFAULT_PAGE_SIZE = 10000;
const MAX_PAGE_SIZE = 50000;
const ALLOWED_AGGREGATIONS = new Set([
  'COUNT',
  'COUNT_DISTINCT',
  'SUM',
  'AVG',
  'MIN',
  'MAX',
  'APPROX_COUNT_DISTINCT'
]);
const ALLOWED_OPERATORS = new Set([
  '=',
  '!=',
  '>',
  '>=',
  '<',
  '<=',
  'IN',
  'BETWEEN',
  'IS_NULL',
  'IS_NOT_NULL'
]);
const IDENTIFIER_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const PROJECT_ID_RE = /^[A-Za-z0-9:._-]+$/;
const DATASET_ID_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const TABLE_ID_RE = /^[A-Za-z0-9_]+$/;

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

exports.processLargeDataset = onRequest(
  {
    memory: '8GiB',
    timeoutSeconds: 540
  },
  async (req, res) => {
    if (req.method !== 'POST') {
      res.status(405).json({error: 'Only POST requests are supported.'});
      return;
    }

    try {
      const body = parseBody(req.body);
      const sourceProjectId = assertProjectId(
        body.sourceProjectId || process.env.GCLOUD_PROJECT || process.env.GCP_PROJECT,
        'sourceProjectId'
      );
      const datasetId = assertDatasetId(body.datasetId, 'datasetId');
      const tableId = assertTableId(body.tableId, 'tableId');
      const location =
        typeof body.location === 'string' && body.location.trim()
          ? body.location.trim()
          : DEFAULT_LOCATION;
      const groupBy = normalizeGroupBy(body.groupBy);
      const metrics = normalizeMetrics(body.metrics);
      const filters = normalizeFilters(body.filters);
      const orderBy = normalizeOrderBy(body.orderBy);
      const pageSize = normalizePageSize(body.pageSize);
      const destination = normalizeDestination(body.destination, sourceProjectId);

      const params = {};
      const query = buildAggregationQuery({
        sourceProjectId,
        datasetId,
        tableId,
        groupBy,
        metrics,
        filters,
        orderBy,
        params
      });

      const queryOptions = {
        query,
        location,
        useLegacySql: false,
        priority: 'INTERACTIVE',
        params
      };

      if (destination) {
        queryOptions.destination = bigquery
          .dataset(destination.datasetId, {projectId: destination.projectId})
          .table(destination.tableId);
        queryOptions.createDisposition = 'CREATE_IF_NEEDED';
        queryOptions.writeDisposition = destination.writeDisposition;
      }

      const [job] = await bigquery.createQueryJob(queryOptions);
      const [rows, queryResponse] = await job.getQueryResults({
        autoPaginate: false,
        maxResults: pageSize
      });
      const [metadata] = await job.getMetadata();

      res.status(200).json({
        jobId: job.id,
        location,
        sourceTable: `${sourceProjectId}.${datasetId}.${tableId}`,
        destinationTable: destination
          ? `${destination.projectId}.${destination.datasetId}.${destination.tableId}`
          : null,
        query,
        groupBy,
        metrics,
        rowCount: Number(queryResponse.totalRows || rows.length),
        nextPageToken: queryResponse.pageToken || null,
        schema: queryResponse.schema || null,
        statistics:
          metadata.statistics && metadata.statistics.query
            ? {
                totalBytesProcessed:
                  metadata.statistics.query.totalBytesProcessed || null,
                totalBytesBilled:
                  metadata.statistics.query.totalBytesBilled || null,
                totalSlotMs: metadata.statistics.query.totalSlotMs || null,
                statementType: metadata.statistics.query.statementType || null
              }
            : null,
        rows
      });
    } catch (error) {
      res.status(error.status || 500).json({
        error: error.message
      });
    }
  }
);

function parseBody(body) {
  if (body == null) {
    return {};
  }

  if (typeof body === 'string') {
    try {
      return JSON.parse(body);
    } catch {
      throw new HttpError(400, 'Request body must contain valid JSON.');
    }
  }

  if (typeof body !== 'object' || Array.isArray(body)) {
    throw new HttpError(400, 'Request body must be a JSON object.');
  }

  return body;
}

function normalizePageSize(pageSize) {
  if (pageSize == null) {
    return DEFAULT_PAGE_SIZE;
  }

  const parsed = Number(pageSize);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new HttpError(400, 'pageSize must be a positive integer.');
  }

  return Math.min(parsed, MAX_PAGE_SIZE);
}

function normalizeGroupBy(groupBy) {
  if (groupBy == null) {
    return [];
  }

  const values = Array.isArray(groupBy) ? groupBy : [groupBy];
  return values.map((value, index) =>
    assertIdentifier(value, `groupBy[${index}]`)
  );
}

function normalizeMetrics(metrics) {
  const normalized = (
    metrics == null ? [{name: 'row_count', function: 'COUNT', field: '*'}] : metrics
  ).map((metric, index) => {
    if (!metric || typeof metric !== 'object' || Array.isArray(metric)) {
      throw new HttpError(400, `metrics[${index}] must be an object.`);
    }

    const aggregation = String(metric.function || 'COUNT').toUpperCase();
    if (!ALLOWED_AGGREGATIONS.has(aggregation)) {
      throw new HttpError(
        400,
        `metrics[${index}].function must be one of: ${Array.from(
          ALLOWED_AGGREGATIONS
        ).join(', ')}`
      );
    }

    const name = assertIdentifier(
      metric.name || `${aggregation.toLowerCase()}_${index + 1}`,
      `metrics[${index}].name`
    );
    const field = metric.field == null ? '*' : metric.field;

    if (field !== '*') {
      assertIdentifier(field, `metrics[${index}].field`);
    }

    if (
      (aggregation === 'SUM' ||
        aggregation === 'AVG' ||
        aggregation === 'MIN' ||
        aggregation === 'MAX' ||
        aggregation === 'COUNT_DISTINCT' ||
        aggregation === 'APPROX_COUNT_DISTINCT') &&
      field === '*'
    ) {
      throw new HttpError(
        400,
        `metrics[${index}].field is required for ${aggregation}.`
      );
    }

    return {name, aggregation, field};
  });

  const metricNames = new Set();
  for (const metric of normalized) {
    if (metricNames.has(metric.name)) {
      throw new HttpError(400, `Duplicate metric name: ${metric.name}`);
    }
    metricNames.add(metric.name);
  }

  return normalized;
}

function normalizeFilters(filters) {
  if (filters == null) {
    return [];
  }

  if (!Array.isArray(filters)) {
    throw new HttpError(400, 'filters must be an array.');
  }

  return filters.map((filter, index) => {
    if (!filter || typeof filter !== 'object' || Array.isArray(filter)) {
      throw new HttpError(400, `filters[${index}] must be an object.`);
    }

    const field = assertIdentifier(filter.field, `filters[${index}].field`);
    const operator = String(filter.operator || '=').toUpperCase();

    if (!ALLOWED_OPERATORS.has(operator)) {
      throw new HttpError(
        400,
        `filters[${index}].operator must be one of: ${Array.from(
          ALLOWED_OPERATORS
        ).join(', ')}`
      );
    }

    if (operator === 'IS_NULL' || operator === 'IS_NOT_NULL') {
      return {field, operator};
    }

    if (operator === 'IN') {
      if (!Array.isArray(filter.value) || filter.value.length === 0) {
        throw new HttpError(
          400,
          `filters[${index}].value must be a non-empty array for IN.`
        );
      }
      return {field, operator, value: filter.value};
    }

    if (operator === 'BETWEEN') {
      if (!Array.isArray(filter.value) || filter.value.length !== 2) {
        throw new HttpError(
          400,
          `filters[${index}].value must be a two-element array for BETWEEN.`
        );
      }
      return {field, operator, value: filter.value};
    }

    if (filter.value === undefined) {
      throw new HttpError(
        400,
        `filters[${index}].value is required for ${operator}.`
      );
    }

    return {field, operator, value: filter.value};
  });
}

function normalizeOrderBy(orderBy) {
  if (orderBy == null) {
    return [];
  }

  const values = Array.isArray(orderBy) ? orderBy : [orderBy];
  return values.map((entry, index) => {
    if (typeof entry === 'string') {
      return {
        field: assertIdentifier(entry, `orderBy[${index}]`),
        direction: 'ASC'
      };
    }

    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new HttpError(400, `orderBy[${index}] must be a string or object.`);
    }

    const field = assertIdentifier(entry.field, `orderBy[${index}].field`);
    const direction = String(entry.direction || 'ASC').toUpperCase();

    if (direction !== 'ASC' && direction !== 'DESC') {
      throw new HttpError(
        400,
        `orderBy[${index}].direction must be ASC or DESC.`
      );
    }

    return {field, direction};
  });
}

function normalizeDestination(destination, defaultProjectId) {
  if (destination == null) {
    return null;
  }

  if (typeof destination !== 'object' || Array.isArray(destination)) {
    throw new HttpError(400, 'destination must be an object.');
  }

  return {
    projectId: assertProjectId(
      destination.projectId || defaultProjectId,
      'destination.projectId'
    ),
    datasetId: assertDatasetId(
      destination.datasetId,
      'destination.datasetId'
    ),
    tableId: assertTableId(destination.tableId, 'destination.tableId'),
    writeDisposition: normalizeWriteDisposition(destination.writeDisposition)
  };
}

function normalizeWriteDisposition(writeDisposition) {
  const value = String(writeDisposition || 'WRITE_TRUNCATE').toUpperCase();
  const allowed = new Set(['WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY']);

  if (!allowed.has(value)) {
    throw new HttpError(
      400,
      `destination.writeDisposition must be one of: ${Array.from(allowed).join(
        ', '
      )}`
    );
  }

  return value;
}

function buildAggregationQuery(config) {
  const {
    sourceProjectId,
    datasetId,
    tableId,
    groupBy,
    metrics,
    filters,
    orderBy,
    params
  } = config;

  const qualifiedTable = `\`${sourceProjectId}.${datasetId}.${tableId}\``;
  const selectParts = [];
  const selectedNames = new Set();

  for (const field of groupBy) {
    selectParts.push(`\`${field}\` AS \`${field}\``);
    selectedNames.add(field);
  }

  for (const metric of metrics) {
    selectParts.push(`${renderMetric(metric)} AS \`${metric.name}\``);
    selectedNames.add(metric.name);
  }

  if (selectParts.length === 0) {
    throw new HttpError(
      400,
      'At least one groupBy field or metric is required.'
    );
  }

  const whereParts = [];
  let paramIndex = 0;

  for (const filter of filters) {
    const fieldSql = `\`${filter.field}\``;

    switch (filter.operator) {
      case 'IS_NULL':
        whereParts.push(`${fieldSql} IS NULL`);
        break;
      case 'IS_NOT_NULL':
        whereParts.push(`${fieldSql} IS NOT NULL`);
        break;
      case 'IN': {
        const placeholder = `filter_${paramIndex++}`;
        params[placeholder] = filter.value;
        whereParts.push(`${fieldSql} IN UNNEST(@${placeholder})`);
        break;
      }
      case 'BETWEEN': {
        const lower = `filter_${paramIndex++}`;
        const upper = `filter_${paramIndex++}`;
        params[lower] = filter.value[0];
        params[upper] = filter.value[1];
        whereParts.push(`${fieldSql} BETWEEN @${lower} AND @${upper}`);
        break;
      }
      default: {
        const placeholder = `filter_${paramIndex++}`;
        params[placeholder] = filter.value;
        whereParts.push(`${fieldSql} ${filter.operator} @${placeholder}`);
      }
    }
  }

  let orderEntries = orderBy;
  if (orderEntries.length === 0 && metrics.length > 0) {
    orderEntries = [{field: metrics[0].name, direction: 'DESC'}];
  }

  for (const entry of orderEntries) {
    if (!selectedNames.has(entry.field)) {
      throw new HttpError(
        400,
        `orderBy field must match a groupBy field or metric name: ${entry.field}`
      );
    }
  }

  const clauses = [
    `SELECT ${selectParts.join(', ')}`,
    `FROM ${qualifiedTable}`
  ];

  if (whereParts.length > 0) {
    clauses.push(`WHERE ${whereParts.join(' AND ')}`);
  }

  if (groupBy.length > 0) {
    clauses.push(
      `GROUP BY ${groupBy.map((field) => `\`${field}\``).join(', ')}`
    );
  }

  if (orderEntries.length > 0) {
    clauses.push(
      `ORDER BY ${orderEntries
        .map((entry) => `\`${entry.field}\` ${entry.direction}`)
        .join(', ')}`
    );
  }

  return clauses.join('\n');
}

function renderMetric(metric) {
  switch (metric.aggregation) {
    case 'COUNT':
      return metric.field === '*' ? 'COUNT(*)' : `COUNT(\`${metric.field}\`)`;
    case 'COUNT_DISTINCT':
      return `COUNT(DISTINCT \`${metric.field}\`)`;
    case 'APPROX_COUNT_DISTINCT':
      return `APPROX_COUNT_DISTINCT(\`${metric.field}\`)`;
    default:
      return `${metric.aggregation}(\`${metric.field}\`)`;
  }
}

function assertIdentifier(value, name) {
  if (typeof value !== 'string' || !IDENTIFIER_RE.test(value)) {
    throw new HttpError(400, `${name} must match ${IDENTIFIER_RE.toString()}`);
  }

  return value;
}

function assertProjectId(value, name) {
  if (typeof value !== 'string' || !PROJECT_ID_RE.test(value)) {
    throw new HttpError(
      400,
      `${name} is required and must contain only letters, numbers, '.', ':', '_' or '-'.`
    );
  }

  return value;
}

function assertDatasetId(value, name) {
  if (typeof value !== 'string' || !DATASET_ID_RE.test(value)) {
    throw new HttpError(400, `${name} must match ${DATASET_ID_RE.toString()}`);
  }

  return value;
}

function assertTableId(value, name) {
  if (typeof value !== 'string' || !TABLE_ID_RE.test(value)) {
    throw new HttpError(400, `${name} must match ${TABLE_ID_RE.toString()}`);
  }

  return value;
}