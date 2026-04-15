const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

// Development API keys - DO NOT USE IN PRODUCTION
const SENDGRID_API_KEY = 'SG.azure_demo_key_123';
const TWILIO_ACCOUNT_SID = 'AC1234567890abcdef';
const TWILIO_AUTH_TOKEN = 'demo_auth_token_456';
const TWILIO_PHONE_NUMBER = '+15551234567';

// Initialize services
sgMail.setApiKey(SENDGRID_API_KEY);
const twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

module.exports = async function (context, req) {
    context.log('Azure Notification Function triggered');

    try {
        const { type, recipient, subject, message, from } = req.body;

        if (!type || !recipient || !message) {
            context.res = {
                status: 400,
                body: { error: 'Missing required fields: type, recipient, message' }
            };
            return;
        }

        let result;

        switch (type.toLowerCase()) {
            case 'email':
                // Send email via SendGrid
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

            case 'sms':
                // Send SMS via Twilio
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

            case 'both':
                // Send both email and SMS
                const results = [];

                // Send email
                try {
                    const bothEmailMsg = {
                        to: req.body.emailRecipient || recipient,
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

                // Send SMS
                try {
                    const smsRecipient = req.body.smsRecipient || recipient;
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
                context.log(`Both notifications sent: ${JSON.stringify(results)}`);
                break;

            default:
                context.res = {
                    status: 400,
                    body: { error: 'Invalid type. Use: email, sms, or both' }
                };
                return;
        }

        context.res = {
            status: 200,
            body: result,
            headers: {
                'Content-Type': 'application/json'
            }
        };

    } catch (error) {
        context.log.error(`Notification error: ${error.message}`);
        
        context.res = {
            status: 500,
            body: {
                error: 'Failed to send notification',
                details: error.message,
                stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
            }
        };
    }
};

// Function configuration (function.json)
module.exports.config = {
    bindings: [
        {
            authLevel: "function",
            type: "httpTrigger",
            direction: "in",
            name: "req",
            methods: ["post"],
            route: "notifications"
        },
        {
            type: "http",
            direction: "out",
            name: "res"
        }
    ]
};