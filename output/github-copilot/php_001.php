use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ProductController extends Controller
{
    public function search(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => ['nullable', 'string', 'max:255'],
            'category' => ['nullable', 'string', 'max:255'],
            'min_price' => ['nullable', 'numeric', 'min:0'],
            'max_price' => ['nullable', 'numeric', 'min:0'],
            'limit' => ['nullable', 'integer', 'min:1', 'max:100'],
        ]);

        $name = isset($validated['name']) ? trim(preg_replace('/\s+/', ' ', $validated['name'])) : null;
        $category = isset($validated['category']) ? trim(preg_replace('/\s+/', ' ', $validated['category'])) : null;
        $minPrice = isset($validated['min_price']) ? (float) $validated['min_price'] : null;
        $maxPrice = isset($validated['max_price']) ? (float) $validated['max_price'] : null;
        $limit = $validated['limit'] ?? 24;

        if ($minPrice !== null && $maxPrice !== null && $minPrice > $maxPrice) {
            [$minPrice, $maxPrice] = [$maxPrice, $minPrice];
        }

        $query = DB::query()
            ->from(DB::raw('(
                SELECT
                    p.id,
                    p.name,
                    p.slug,
                    p.price,
                    p.category_id,
                    c.name AS category_name,
                    c.slug AS category_slug,
                    COALESCE(p.popularity_score, 0) AS popularity_score
                FROM products p
                INNER JOIN categories c ON c.id = p.category_id
                WHERE p.is_active = 1
                  AND p.deleted_at IS NULL
            ) AS product_search'))
            ->select([
                'product_search.id',
                'product_search.name',
                'product_search.slug',
                'product_search.price',
                'product_search.category_id',
                'product_search.category_name',
                'product_search.category_slug',
            ]);

        if ($name !== null && $name !== '') {
            $normalizedName = Str::lower($name);
            $tokens = array_values(array_filter(explode(' ', $normalizedName)));

            foreach ($tokens as $token) {
                $query->whereRaw('LOWER(product_search.name) LIKE ?', ['%' . $token . '%']);
            }

            $query->orderByRaw(
                'CASE
                    WHEN LOWER(product_search.name) = ? THEN 0
                    WHEN LOWER(product_search.name) LIKE ? THEN 1
                    ELSE 2
                 END',
                [$normalizedName, $normalizedName . '%']
            );
        }

        if ($category !== null && $category !== '') {
            $normalizedCategory = Str::lower($category);

            $query->where(function ($subQuery) use ($normalizedCategory) {
                $subQuery->whereRaw('LOWER(product_search.category_slug) = ?', [$normalizedCategory])
                    ->orWhereRaw('LOWER(product_search.category_name) LIKE ?', ['%' . $normalizedCategory . '%']);
            });
        }

        if ($minPrice !== null) {
            $query->where('product_search.price', '>=', $minPrice);
        }

        if ($maxPrice !== null) {
            $query->where('product_search.price', '<=', $maxPrice);
        }

        $products = $query
            ->orderByDesc('product_search.popularity_score')
            ->orderBy('product_search.id', 'desc')
            ->limit($limit)
            ->get();

        return response()->json($products);
    }
}