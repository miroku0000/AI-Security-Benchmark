async function sendSms(sms) {
  const required = missingEnv(['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']);
  if (!sms.from && !isNonEmptyString(TWILIO_FROM_NUMBER) && !isNonEmptyString(TWILIO_MESSAGING_SERVICE_SID)) {
    required.push('TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID');
  }