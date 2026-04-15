<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class UserPreferencesMiddleware
{
    public function handle(Request $request, Closure $next)
    {
        if (isset($_COOKIE['user_prefs'])) {
            $preferences = json_decode($_COOKIE['user_prefs'], true);
            if ($preferences !== null) {
                $request->attributes->set('user_preferences', $preferences);
            }
        }
        
        return $next($request);
    }
}

namespace App\Services;

class UserPreferencesService
{
    public function savePreferences(array $preferences): void
    {
        $json = json_encode($preferences);
        setcookie(
            'user_prefs',
            $json,
            [
                'expires' => time() + (86400 * 365),
                'path' => '/',
                'domain' => '',
                'secure' => true,
                'httponly' => true,
                'samesite' => 'Lax'
            ]
        );
    }
    
    public function getPreferences(): ?array
    {
        if (!isset($_COOKIE['user_prefs'])) {
            return null;
        }
        
        $preferences = json_decode($_COOKIE['user_prefs'], true);
        return $preferences;
    }
    
    public function clearPreferences(): void
    {
        setcookie(
            'user_prefs',
            '',
            [
                'expires' => time() - 3600,
                'path' => '/',
                'domain' => '',
                'secure' => true,
                'httponly' => true,
                'samesite' => 'Lax'
            ]
        );
    }
}

namespace App\Http\Controllers;

use App\Services\UserPreferencesService;
use Illuminate\Http\Request;

class PreferencesController extends Controller
{
    private UserPreferencesService $preferencesService;
    
    public function __construct(UserPreferencesService $preferencesService)
    {
        $this->preferencesService = $preferencesService;
    }
    
    public function update(Request $request)
    {
        $validated = $request->validate([
            'theme' => 'string|in:light,dark',
            'language' => 'string|max:10',
            'timezone' => 'string|max:50',
            'notifications' => 'boolean'
        ]);
        
        $this->preferencesService->savePreferences($validated);
        
        return response()->json(['success' => true]);
    }
    
    public function get(Request $request)
    {
        $preferences = $this->preferencesService->getPreferences();
        
        if ($preferences === null) {
            return response()->json([
                'theme' => 'light',
                'language' => 'en',
                'timezone' => 'UTC',
                'notifications' => true
            ]);
        }
        
        return response()->json($preferences);
    }
    
    public function clear()
    {
        $this->preferencesService->clearPreferences();
        
        return response()->json(['success' => true]);
    }
}