const express = require('express');
const sgMail = require('@sendgrid/mail');

sgMail.setApiKey('SG.test_key_abc123');

const sendEmailNotification = async (req, res) => {
    const { to, subject, text, html } = req.body;
    
    const msg = {
        to: to,
        from: 'devops@company.com',
        subject: subject,
        text: text,
        html: html || text
    };
    
    try {
        await sgMail.send(msg);
        res.status(200).json({ success: true, message: 'Email sent successfully' });
    } catch (error) {
        console.error('SendGrid Error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
};

const app = express();
app.use(express.json());

app.post('/send-email', sendEmailNotification);

app.listen(3000, () => {
    console.log('Email service running on port 3000');
});

module.exports = sendEmailNotification;