try {
      const body = req.body || {};
      const sourceProjectId = body.sourceProjectId || process.env.SOURCE_PROJECT_ID || bigquery.projectId;
      const sourceDataset = body.sourceDataset || process.env.SOURCE_DATASET;
      const sourceTable = body.sourceTable || process.env.SOURCE_TABLE;
      const destinationProjectId =
        body.destinationProjectId || process.env.DESTINATION_PROJECT_ID || bigquery.projectId;
      const destinationDataset = body.destinationDataset || process.env.DESTINATION_DATASET;
      const destinationTable = body.destinationTable || process.env.DESTINATION_TABLE;
      const groupBy = Array.isArray(body.groupBy) ? body.groupBy : [];
      const aggregations = Array.isArray(body.aggregations) ? body.aggregations : [];
      const whereClause = typeof body.whereClause === "string" ? body.whereClause.trim() : "";
      const sourceQuery = typeof body.sourceQuery === "string" ? body.sourceQuery.trim() : "";