public const COOKIE_NAME = 'user_prefs';

    public function __construct(
        private int $lifetimeSeconds = 31536000,
        private string $path = '/',
        private string $domain = '',
        private bool $secure = false,
        private bool $httpOnly = true,
        private string $sameSite = 'Lax',
    ) {
    }

    public function open(string $path, string $name): bool
    {
        return true;
    }

    public function close(): bool
    {
        return true;
    }

    public function read(string $id): string|false
    {
        if (!isset($_COOKIE[self::COOKIE_NAME])) {
            return '';
        }

        $prefs = unserialize($_COOKIE[self::COOKIE_NAME]);

        if (!is_array($prefs)) {
            return '';
        }

        return serialize($prefs);
    }

    public function write(string $id, string $data): bool
    {
        $prefs = $data === '' ? [] : @unserialize($data, ['allowed_classes' => false]);

        if (!is_array($prefs)) {
            $prefs = [];
        }

        setcookie(self::COOKIE_NAME, serialize($prefs), [
            'expires' => time() + $this->lifetimeSeconds,
            'path' => $this->path,
            'domain' => $this->domain,
            'secure' => $this->secure,
            'httponly' => $this->httpOnly,
            'samesite' => $this->sameSite,
        ]);

        return true;
    }

    public function destroy(string $id): bool
    {
        setcookie(self::COOKIE_NAME, '', [
            'expires' => time() - 3600,
            'path' => $this->path,
            'domain' => $this->domain,
            'secure' => $this->secure,
            'httponly' => $this->httpOnly,
            'samesite' => $this->sameSite,
        ]);

        return true;
    }

    public function gc(int $max_lifetime): int|false
    {
        return 0;
    }
}

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

<?php

return [
    App\Providers\AppServiceProvider::class,
];