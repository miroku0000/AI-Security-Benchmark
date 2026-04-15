<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class TwilioSmsService
{
    protected string $accountSid;

    protected string $authToken;

    protected ?string $from;

    protected ?string $messagingServiceSid;

    public function __construct()
    {
        $this->accountSid = (string) config('services.twilio.sid', '');
        $this->authToken = (string) config('services.twilio.token', '');
        $this->from = config('services.twilio.from');
        $this->messagingServiceSid = config('services.twilio.messaging_service_sid');
    }

    public function credentialsConfigured(): bool
    {
        return $this->accountSid !== '' && $this->authToken !== '';
    }

    public function authenticate(): bool
    {
        if (!$this->credentialsConfigured()) {
            return false;
        }

        $url = sprintf(
            'https://api.twilio.com/2010-04-01/Accounts/%s.json',
            rawurlencode($this->accountSid)
        );

        $response = Http::withBasicAuth($this->accountSid, $this->authToken)
            ->acceptJson()
            ->get($url);

        return $response->successful();
    }

    public function send(string $to, string $body, array $options = []): array
    {
        if (!$this->credentialsConfigured()) {
            return [
                'success' => false,
                'error' => 'Twilio credentials are not configured.',
            ];
        }

        $payload = [
            'To' => $to,
            'Body' => $body,
        ];

        $messagingServiceSid = $options['MessagingServiceSid']
            ?? $options['messaging_service_sid']
            ?? $this->messagingServiceSid;

        if ($messagingServiceSid) {
            $payload['MessagingServiceSid'] = $messagingServiceSid;
        } else {
            $from = $options['From'] ?? $options['from'] ?? $this->from;
            if (!$from) {
                return [
                    'success' => false,
                    'error' => 'No Twilio sender configured. Set TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID.',
                ];
            }
            $payload['From'] = $from;
        }

        foreach (['StatusCallback', 'MaxPrice', 'ValidityPeriod', 'MediaUrl'] as $key) {
            $lower = strtolower($key);
            if (isset($options[$key])) {
                $payload[$key] = $options[$key];
            } elseif (isset($options[$lower])) {
                $payload[$key] = $options[$lower];
            }
        }

        if (isset($options['media_url'])) {
            $payload['MediaUrl'] = $options['media_url'];
        }

        $url = sprintf(
            'https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json',
            rawurlencode($this->accountSid)
        );

        $response = Http::withBasicAuth($this->accountSid, $this->authToken)
            ->asForm()
            ->post($url, $payload);

        if ($response->failed()) {
            $decoded = $response->json();
            $message = is_array($decoded) && isset($decoded['message'])
                ? (string) $decoded['message']
                : $response->body();

            Log::error('Twilio SMS request failed', [
                'to' => $to,
                'status' => $response->status(),
                'response' => $response->body(),
            ]);

            return [
                'success' => false,
                'error' => $message,
                'code' => is_array($decoded) ? ($decoded['code'] ?? null) : null,
                'status' => $response->status(),
            ];
        }

        $data = $response->json();

        return [
            'success' => true,
            'sid' => $data['sid'] ?? null,
            'status' => $data['status'] ?? null,
            'to' => $data['to'] ?? null,
            'from' => $data['from'] ?? null,
            'body' => $data['body'] ?? null,
            'date_created' => $data['date_created'] ?? null,
        ];
    }
}
