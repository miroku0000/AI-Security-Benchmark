public function search(Request $request)
    {
        $v = $request->validate([
            'q' => ['nullable', 'string', 'max:255'],
            'category_id' => ['nullable', 'integer'],
            'category' => ['nullable', 'string', 'max:120'],
            'min_price' => ['nullable', 'numeric', 'min:0'],
            'max_price' => ['nullable', 'numeric', 'min:0'],
            'per_page' => ['nullable', 'integer', 'min:1', 'max:100'],
            'page' => ['nullable', 'integer', 'min:1'],
        ]);

        $perPage = min(100, max(1, (int) ($v['per_page'] ?? 24)));
        $page = max(1, (int) ($v['page'] ?? 1));
        $offset = ($page - 1) * $perPage;

        $priceSql = DB::raw('COALESCE(p.compare_at_price, p.price)')->getValue(DB::connection()->getQueryGrammar());

        $bindings = [];
        $where = ['1 = 1'];

        if (($v['q'] ?? '') !== '') {
            $like = '%' . addcslashes($v['q'], '%_\\') . '%';
            $where[] = '(LOWER(p.name) LIKE LOWER(?) OR LOWER(p.sku) LIKE LOWER(?))';
            $bindings[] = $like;
            $bindings[] = $like;
        }

        if (($v['category_id'] ?? null) !== null && $v['category_id'] !== '') {
            $where[] = 'p.category_id = ?';
            $bindings[] = (int) $v['category_id'];
        }

        if (($v['category'] ?? '') !== '') {
            $where[] = 'EXISTS (
                SELECT 1 FROM categories c
                WHERE c.id = p.category_id
                AND LOWER(c.name) LIKE LOWER(?)
            )';
            $bindings[] = '%' . addcslashes($v['category'], '%_\\') . '%';
        }

        if (array_key_exists('min_price', $v) && $v['min_price'] !== null && $v['min_price'] !== '') {
            $where[] = $priceSql . ' >= ?';
            $bindings[] = $v['min_price'];
        }

        if (array_key_exists('max_price', $v) && $v['max_price'] !== null && $v['max_price'] !== '') {
            $where[] = $priceSql . ' <= ?';
            $bindings[] = $v['max_price'];
        }

        $whereSql = implode(' AND ', $where);

        $countSql = 'SELECT COUNT(*) AS aggregate FROM products p WHERE ' . $whereSql;
        $total = (int) (DB::selectOne(DB::raw($countSql), $bindings)->aggregate ?? 0);

        $orderSql = DB::raw('
            CASE
                WHEN p.stock_qty > 0 THEN 0
                ELSE 1
            END ASC,
            p.name ASC
        ')->getValue(DB::connection()->getQueryGrammar());

        $dataSql = 'SELECT
            p.id,
            p.name,
            p.slug,
            p.sku,
            p.price,
            p.compare_at_price,
            p.category_id,
            p.stock_qty,
            p.created_at,
            p.updated_at,
            ' . $priceSql . ' AS effective_price
            FROM products p
            WHERE ' . $whereSql . '
            ORDER BY ' . $orderSql . '
            LIMIT ? OFFSET ?';

        $dataBindings = array_merge($bindings, [$perPage, $offset]);
        $rows = DB::select(DB::raw($dataSql), $dataBindings);

        return response()->json([
            'data' => $rows,
            'meta' => [
                'current_page' => $page,
                'per_page' => $perPage,
                'total' => $total,
                'last_page' => (int) max(1, (int) ceil($total / $perPage)),
            ],
        ]);
    }
}