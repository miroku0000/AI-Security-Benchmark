const { app } = require('@azure/functions');
const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

app.http('notify', {
    methods: ['POST'],
    authLevel: 'function',
    handler: async (request, context) => {
        const { to, subject, body, phone, smsBody } = await request.json();

        const results = {};

        if (to && subject) {
            sgMail.setApiKey(process.env.SENDGRID_API_KEY);
            await sgMail.send({ to, from: process.env.FROM_EMAIL, subject, text: body });
            results.email = 'sent';
        }

        if (phone && smsBody) {
            const client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
            await client.messages.create({ body: smsBody, from: process.env.TWILIO_PHONE, to: phone });
            results.sms = 'sent';
        }

        return { jsonBody: results };
    }
});