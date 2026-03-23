allowedFields = map[string]fieldSpec{
		"name": {
			kind: fieldString,
			operators: map[string]struct{}{
				"eq":       {},
				"in":       {},
				"contains": {},
				"prefix":   {},
			},
		},
		"email": {
			kind: fieldString,
			operators: map[string]struct{}{
				"eq":       {},
				"contains": {},
				"prefix":   {},
			},
		},
		"status": {
			kind: fieldString,
			operators: map[string]struct{}{
				"eq": {},
				"in": {},
			},
		},
		"age": {
			kind: fieldInt,
			operators: map[string]struct{}{
				"eq":  {},
				"gte": {},
				"lte": {},
				"in":  {},
			},
		},
		"is_active": {
			kind: fieldBool,
			operators: map[string]struct{}{
				"eq": {},
			},
		},
		"created_at": {
			kind: fieldTime,
			operators: map[string]struct{}{
				"eq":  {},
				"gte": {},
				"lte": {},
			},
		},
	}
)