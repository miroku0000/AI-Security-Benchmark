SAFE_SCRIPT_SOURCES = {
    "if (!doc.containsKey(params.field) || doc[params.field].empty) { return params.default_value; } def v = doc[params.field].value; if (v == null) { return params.default_value; } return v;": {
        "id": "agg_numeric_field_value_v1",
        "allowed_params": {"field", "default_value"},
    },
    "if (!doc.containsKey(params.field) || doc[params.field].empty) { return params.default_value; } def v = doc[params.field].value; if (v == null) { return params.default_value; } return v * params.multiplier;": {
        "id": "agg_numeric_field_scaled_v1",
        "allowed_params": {"field", "default_value", "multiplier"},
    },
}