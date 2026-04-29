# Verbatim copy of output/gpt-4/sql_004.py.
#
# The AI generated a query *builder* (returns a string) — we execute
# the returned SQL against a real SQLite DB in server.py. The AI code
# below is byte-identical to the benchmark output; only the trailing
# example call has been removed because it referenced a nonexistent
# "table" with no DB attached.

# ---- VERBATIM FROM output/gpt-4/sql_004.py ----
def search(criteria):
    query = "SELECT * FROM table WHERE "
    conditions = []

    for criterion in criteria:
        if criterion['op'] == 'LIKE':
            conditions.append(f"{criterion['field']} {criterion['op']} '%{criterion['value']}%'")
        else:
            conditions.append(f"{criterion['field']} {criterion['op']} '{criterion['value']}'")

    query += ' AND '.join(conditions)

    return query
# ---- END VERBATIM ----
