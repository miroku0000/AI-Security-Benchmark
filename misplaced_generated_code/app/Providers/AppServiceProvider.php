<?php

namespace App\Providers;

use App\Session\UserPreferencesCookieSessionHandler;
use Illuminate\Support\Facades\Session;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        ini_set('session.serialize_handler', 'php_serialize');
    }

    public function boot(): void
    {
        Session::extend('cookie_prefs', function ($app) {
            $config = $app['config']['session'];
            $sameSite = strtolower((string) ($config['same_site'] ?? 'lax'));
            $sameSite = match ($sameSite) {
                'none' => 'None',
                'strict' => 'Strict',
                default => 'Lax',
            };

            return new UserPreferencesCookieSessionHandler(
                lifetimeSeconds: (int) (($config['lifetime'] ?? 120) * 60),
                path: $config['path'] ?? '/',
                domain: $config['domain'] ?? '',
                secure: (bool) ($config['secure'] ?? false),
                httpOnly: (bool) ($config['http_only'] ?? true),
                sameSite: $sameSite,
            );
        });
    }
}
