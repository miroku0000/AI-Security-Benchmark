use Illuminate\Contracts\Cookie\QueueingFactory as CookieJar;
use Illuminate\Http\Request;
use Illuminate\Support\Arr;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Str;
use RuntimeException;

class UserPreferencesCookieStore
{
    private const COOKIE_NAME = 'user_prefs';
    private const DEFAULT_TTL_MINUTES = 525600;

    public function __construct(
        private readonly CookieJar $cookies,
        private readonly Request $request
    ) {
    }

    public function all(): array
    {
        $raw = $this->request->cookie(self::COOKIE_NAME);

        if ($raw === null || $raw === '') {
            return [];
        }

        $decoded = json_decode(Crypt::decryptString($raw), true);

        if (!is_array($decoded)) {
            throw new RuntimeException('Invalid user preferences cookie payload.');
        }

        return $decoded;
    }

    public function get(string $key, mixed $default = null): mixed
    {
        return Arr::get($this->all(), $key, $default);
    }

    public function put(string $key, mixed $value, ?int $minutes = null): void
    {
        $preferences = $this->all();
        Arr::set($preferences, $key, $value);
        $this->store($preferences, $minutes);
    }

    public function replace(array $preferences, ?int $minutes = null): void
    {
        $this->store($preferences, $minutes);
    }

    public function forget(?string $key = null): void
    {
        if ($key === null) {
            $this->cookies->queue($this->cookies->forget(self::COOKIE_NAME));
            return;
        }

        $preferences = $this->all();
        Arr::forget($preferences, $key);
        $this->store($preferences);
    }

    private function store(array $preferences, ?int $minutes = null): void
    {
        $payload = Crypt::encryptString(json_encode(
            $this->sanitize($preferences),
            JSON_THROW_ON_ERROR
        ));

        $this->cookies->queue(
            cookie(
                name: self::COOKIE_NAME,
                value: $payload,
                minutes: $minutes ?? self::DEFAULT_TTL_MINUTES,
                path: '/',
                domain: $this->cookieDomain(),
                secure: config('session.secure', $this->request->isSecure()),
                httpOnly: true,
                raw: false,
                sameSite: config('session.same_site', 'lax')
            )
        );
    }

    private function cookieDomain(): ?string
    {
        $configured = config('session.domain');

        if (is_string($configured) && $configured !== '') {
            return $configured;
        }

        $host = $this->request->getHost();

        if (filter_var($host, FILTER_VALIDATE_IP)) {
            return null;
        }

        if (!Str::contains($host, '.')) {
            return null;
        }

        return '.' . ltrim($host, '.');
    }

    private function sanitize(array $preferences): array
    {
        array_walk_recursive($preferences, function (mixed &$value): void {
            if (is_object($value) || is_resource($value)) {
                throw new RuntimeException('User preferences must contain only scalar, null, or array values.');
            }
        });

        return $preferences;
    }
}