const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

const SENDGRID_API_KEY = 'SG.azure_demo_key_123';
const TWILIO_ACCOUNT_SID = 'AC1234567890abcdef';
const TWILIO_AUTH_TOKEN = 'demo_auth_token_456';
const TWILIO_PHONE_NUMBER = '+15551234567';

sgMail.setApiKey(SENDGRID_API_KEY);
const twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

module.exports = async function (context, req) {
  context.log('NotifyHttp triggered');

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : req.body || {};
    const { type, recipient, subject, message, from } = body;

    if (!type || !recipient || !message) {
      context.res = {
        status: 400,
        body: { error: 'Missing required fields: type, recipient, message' },
        headers: { 'Content-Type': 'application/json' }
      };
      return;
    }

    let result;

    switch (String(type).toLowerCase()) {
      case 'email': {
        const emailMsg = {
          to: recipient,
          from: from || 'notifications@example.com',
          subject: subject || 'Azure Function Notification',
          text: message,
          html: `<p>${message}</p>`
        };
        await sgMail.send(emailMsg);
        result = { success: true, type: 'email', recipient, message: 'Email sent successfully' };
        context.log(`Email sent to ${recipient}`);
        break;
      }

      case 'sms': {
        const smsResult = await twilioClient.messages.create({
          body: message,
          from: TWILIO_PHONE_NUMBER,
          to: recipient
        });
        result = {
          success: true,
          type: 'sms',
          recipient,
          messageId: smsResult.sid,
          message: 'SMS sent successfully'
        };
        context.log(`SMS sent to ${recipient}, SID: ${smsResult.sid}`);
        break;
      }

      case 'both': {
        const results = [];
        try {
          const bothEmailMsg = {
            to: body.emailRecipient || recipient,
            from: from || 'notifications@example.com',
            subject: subject || 'Azure Function Notification',
            text: message,
            html: `<p>${message}</p>`
          };
          await sgMail.send(bothEmailMsg);
          results.push({ type: 'email', success: true, recipient: bothEmailMsg.to });
        } catch (emailError) {
          results.push({ type: 'email', success: false, error: emailError.message });
        }
        try {
          const smsRecipient = body.smsRecipient || recipient;
          const bothSmsResult = await twilioClient.messages.create({
            body: message,
            from: TWILIO_PHONE_NUMBER,
            to: smsRecipient
          });
          results.push({
            type: 'sms',
            success: true,
            recipient: smsRecipient,
            messageId: bothSmsResult.sid
          });
        } catch (smsError) {
          results.push({ type: 'sms', success: false, error: smsError.message });
        }
        result = { success: true, type: 'both', results, message: 'Notifications processed' };
        context.log(`Both notifications: ${JSON.stringify(results)}`);
        break;
      }

      default:
        context.res = {
          status: 400,
          body: { error: 'Invalid type. Use: email, sms, or both' },
          headers: { 'Content-Type': 'application/json' }
        };
        return;
    }

    context.res = {
      status: 200,
      body: result,
      headers: { 'Content-Type': 'application/json' }
    };
  } catch (error) {
    context.log.error(`Notification error: ${error.message}`);
    context.res = {
      status: 500,
      body: {
        error: 'Failed to send notification',
        details: error.message
      },
      headers: { 'Content-Type': 'application/json' }
    };
  }
};