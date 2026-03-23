func toInterfaceSlice(value interface{}) []interface{} {
	switch v := value.(type) {
	case []interface{}:
		return v
	case []string:
		out := make([]interface{}, len(v))
		for i, item := range v {
			out[i] = item
		}
		return out
	case []int:
		out := make([]interface{}, len(v))
		for i, item := range v {
			out[i] = item
		}
		return out
	case []float64:
		out := make([]interface{}, len(v))
		for i, item := range v {
			out[i] = item
		}
		return out
	default:
		return []interface{}{v}
	}
}