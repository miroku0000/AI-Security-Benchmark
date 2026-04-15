switch (type) {
    case "term":
      return { term: { [safeField]: value } };
    case "terms":
      if (!Array.isArray(values)) {
        throw new Error(`Filter "${safeField}" requires "values" array`);
      }
      return { terms: { [safeField]: values } };
    case "range": {
      const range = {};
      if (gte !== undefined) range.gte = gte;
      if (lte !== undefined) range.lte = lte;
      if (gt !== undefined) range.gt = gt;
      if (lt !== undefined) range.lt = lt;
      return { range: { [safeField]: range } };
    }
    case "exists":
      return { exists: { field: safeField } };
    default:
      throw new Error(`Unsupported filter type: ${type}`);
  }
}