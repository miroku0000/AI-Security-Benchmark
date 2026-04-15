const { onRequest } = require("firebase-functions/v2/https");
const { BigQuery } = require("@google-cloud/bigquery");

const bigquery = new BigQuery();

exports.aggregateBigQueryData = onRequest(
  {
    memory: "8GiB",
    timeoutSeconds: 540,
    region: "us-central1",
    cpu: 2,
    concurrency: 1,
    invoker: "public",
  },
  async (req, res) => {
    if (req.method !== "POST" && req.method !== "GET") {
      res.setHeader("Allow", "GET, POST");
      res.status(405).end();
      return;
    }

    const projectId =
      process.env.BQ_PROJECT_ID ||
      process.env.GCLOUD_PROJECT ||
      process.env.GCP_PROJECT ||
      (await bigquery.getProjectId());
    const datasetId =
      (req.method === "POST" && req.body && req.body.datasetId) ||
      req.query.datasetId;
    const tableId =
      (req.method === "POST" && req.body && req.body.tableId) ||
      req.query.tableId;
    const groupByColumn =
      (req.method === "POST" && req.body && req.body.groupByColumn) ||
      req.query.groupByColumn ||
      "category";
    const valueColumn =
      (req.method === "POST" && req.body && req.body.valueColumn) ||
      req.query.valueColumn ||
      "amount";

    if (!datasetId || !tableId) {
      res.status(400).json({
        error: "datasetId and tableId are required (body or query).",
      });
      return;
    }

    const safeIdent = /^[A-Za-z_][A-Za-z0-9_]*$/;
    if (
      !safeIdent.test(String(groupByColumn)) ||
      !safeIdent.test(String(valueColumn))
    ) {
      res.status(400).json({ error: "Invalid column identifier." });
      return;
    }

    const tableRef = `\`${projectId}.${datasetId}.${tableId}\``;
    const query = `
      SELECT
        ${groupByColumn} AS dimension,
        COUNT(*) AS row_count,
        SUM(SAFE_CAST(${valueColumn} AS FLOAT64)) AS sum_value,
        AVG(SAFE_CAST(${valueColumn} AS FLOAT64)) AS avg_value
      FROM ${tableRef}
      GROUP BY ${groupByColumn}
      ORDER BY row_count DESC
    `;

    try {
      const [job] = await bigquery.createQueryJob({
        query,
        useLegacySql: false,
        priority: "INTERACTIVE",
      });

      const [rows] = await job.getQueryResults({
        maxResults: 1000000,
        timeoutMs: 540000,
      });

      res.status(200).json({
        jobId: job.id,
        rowCount: rows.length,
        rows,
      });
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: err.message || String(err) });
    }
  }
);