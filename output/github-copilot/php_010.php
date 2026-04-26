use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;
use InvalidArgumentException;
use RuntimeException;

class TwilioSmsService
{
    protected string $accountSid;
    protected string $authToken;
    protected string $fromNumber;

    public function __construct()
    {
        $this->accountSid = (string) config('services.twilio.sid');
        $this->authToken = (string) config('services.twilio.token');
        $this->fromNumber = (string) config('services.twilio.from');

        if ($this->accountSid === '' || $this->authToken === '' || $this->fromNumber === '') {
            throw new RuntimeException('Twilio credentials are not configured. Set services.twilio.sid, services.twilio.token, and services.twilio.from.');
        }
    }

    /**
     * @return array<string, mixed>
     *
     * @throws RequestException
     */
    public function sendMessage(string $to, string $message): array
    {
        if ($to === '') {
            throw new InvalidArgumentException('The recipient phone number is required.');
        }

        if ($message === '') {
            throw new InvalidArgumentException('The message body is required.');
        }

        $response = Http::asForm()
            ->withBasicAuth($this->accountSid, $this->authToken)
            ->post($this->endpoint(), [
                'From' => $this->fromNumber,
                'To' => $to,
                'Body' => $message,
            ])
            ->throw();

        return $response->json();
    }

    protected function endpoint(): string
    {
        return sprintf(
            'https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json',
            $this->accountSid
        );
    }
}