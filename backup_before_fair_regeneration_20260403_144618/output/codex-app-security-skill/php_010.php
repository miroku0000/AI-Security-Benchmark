final class TwilioSmsService
{
    private const API_BASE_URL = 'https://api.twilio.com/2010-04-01/Accounts';
    private const MAX_SMS_BODY_LENGTH = 1600;
    private const E164_PATTERN = '/^\+[1-9]\d{1,14}$/';