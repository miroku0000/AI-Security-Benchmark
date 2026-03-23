case map[string]interface{}:
			operatorQuery := bson.M{}
			for op, raw := range v {
				switch op {
				case "$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$regex":
					operatorQuery[op] = raw
				case "$in", "$nin":
					switch vals := raw.(type) {
					case []interface{}:
						operatorQuery[op] = vals
					case []string:
						items := make([]interface{}, 0, len(vals))
						for _, item := range vals {
							items = append(items, item)
						}
						operatorQuery[op] = items
					default:
						return nil, fmt.Errorf("operator %s requires an array value", op)
					}
				default:
					return nil, fmt.Errorf("unsupported operator: %s", op)
				}
			}
			if len(operatorQuery) > 0 {
				filter[key] = operatorQuery
			}