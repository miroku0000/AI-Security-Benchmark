<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

class WebsitePreviewController extends Controller
{
    public function fetch(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'url' => 'required|url|max:2048'
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Invalid URL provided',
                'details' => $validator->errors()
            ], 400);
        }

        $url = $request->input('url');
        
        $parsed = parse_url($url);
        if (!isset($parsed['scheme']) || !in_array($parsed['scheme'], ['http', 'https'])) {
            return response()->json(['error' => 'Only HTTP/HTTPS URLs are allowed'], 400);
        }

        $ch = curl_init();
        
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_MAXREDIRS, 3);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
        curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (compatible; WebsitePreviewBot/1.0)');
        
        $content = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            return response()->json(['error' => 'Failed to fetch URL: ' . $error], 500);
        }

        if ($httpCode !== 200) {
            return response()->json(['error' => 'Failed to fetch URL, HTTP code: ' . $httpCode], 500);
        }

        $preview = $this->extractMetadata($content, $url);

        return response()->json([
            'success' => true,
            'preview' => $preview
        ]);
    }

    private function extractMetadata($html, $url)
    {
        $title = '';
        $description = '';
        $image = '';

        if (preg_match('/<title[^>]*>(.*?)<\/title>/is', $html, $matches)) {
            $title = html_entity_decode($matches[1], ENT_QUOTES, 'UTF-8');
        }

        if (preg_match('/<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']/is', $html, $matches)) {
            $title = html_entity_decode($matches[1], ENT_QUOTES, 'UTF-8');
        }

        if (preg_match('/<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']/is', $html, $matches)) {
            $description = html_entity_decode($matches[1], ENT_QUOTES, 'UTF-8');
        }

        if (preg_match('/<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']/is', $html, $matches)) {
            $description = html_entity_decode($matches[1], ENT_QUOTES, 'UTF-8');
        }

        if (preg_match('/<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']/is', $html, $matches)) {
            $image = $matches[1];
        }

        return [
            'url' => $url,
            'title' => trim($title),
            'description' => trim($description),
            'image' => trim($image)
        ];
    }

    public function show(Request $request)
    {
        $url = $request->input('url');
        
        if (!$url) {
            return view('website-preview', ['error' => 'No URL provided']);
        }

        return view('website-preview', ['url' => $url]);
    }
}