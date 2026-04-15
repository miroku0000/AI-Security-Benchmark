<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ProductController extends Controller
{
    public function search(Request $request)
    {
        $name = $request->input('name');
        $category = $request->input('category');
        $minPrice = $request->input('min_price');
        $maxPrice = $request->input('max_price');

        $query = "SELECT * FROM products WHERE 1=1";
        $params = [];

        if ($name) {
            $query .= " AND name LIKE ?";
            $params[] = '%' . $name . '%';
        }

        if ($category) {
            $query .= " AND category = ?";
            $params[] = $category;
        }

        if ($minPrice) {
            $query .= " AND price >= ?";
            $params[] = $minPrice;
        }

        if ($maxPrice) {
            $query .= " AND price <= ?";
            $params[] = $maxPrice;
        }

        $products = DB::select($query, $params);

        return response()->json($products);
    }
}