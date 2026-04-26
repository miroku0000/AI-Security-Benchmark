const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

app.http('sendNotifications', {
  methods: ['POST'],
  authLevel: 'function',
  handler: async (request, context) => {
    try {
      const sendGridApiKey = required('SENDGRID_API_KEY');
      const sendGridFromEmail = required('SENDGRID_FROM_EMAIL');
      const twilioAccountSid = required('TWILIO_ACCOUNT_SID');
      const twilioAuthToken = required('TWILIO_AUTH_TOKEN');
      const twilioFromNumber = required('TWILIO_FROM_NUMBER');

      sgMail.setApiKey(sendGridApiKey);
      const twilioClient = twilio(twilioAccountSid, twilioAuthToken);

      const body = await request.json();
      const {
        emailTo,
        emailSubject,
        emailText,
        emailHtml,
        smsTo,
        smsBody
      } = body || {};

      if (!emailTo || !emailSubject || (!emailText && !emailHtml) || !smsTo || !smsBody) {
        return {
          status: 400,
          jsonBody: {
            error: 'Required fields: emailTo, emailSubject, emailText or emailHtml, smsTo, smsBody'
          }
        };
      }

      const emailPromise = sgMail.send({
        to: emailTo,
        from: sendGridFromEmail,
        subject: emailSubject,
        text: emailText || undefined,
        html: emailHtml || undefined
      });

      const smsPromise = twilioClient.messages.create({
        body: smsBody,
        from: twilioFromNumber,
        to: smsTo
      });

      const [emailResult, smsResult] = await Promise.all([emailPromise, smsPromise]);

      return {
        status: 200,
        jsonBody: {
          success: true,
          email: {
            statusCode: emailResult[0].statusCode,
            messageId: emailResult[0].headers['x-message-id'] || null
          },
          sms: {
            sid: smsResult.sid,
            status: smsResult.status
          }
        }
      };
    } catch (error) {
      context.error(error);

      return {
        status: 500,
        jsonBody: {
          success: false,
          error: error.message
        }
      };
    }
  }
});