if ($category !== null) {
            if (ctype_digit($category)) {
                $query->where(function ($q) use ($category, $categoryLike) {
                    $q->where('products.category_id', (int) $category)
                        ->orWhereRaw('LOWER(categories.name) LIKE ?', [$categoryLike])
                        ->orWhereRaw('LOWER(categories.slug) LIKE ?', [$categoryLike]);
                });
            } else {
                $query->where(function ($q) use ($categoryLike) {
                    $q->whereRaw('LOWER(categories.name) LIKE ?', [$categoryLike])
                        ->orWhereRaw('LOWER(categories.slug) LIKE ?', [$categoryLike]);
                });
            }
        }