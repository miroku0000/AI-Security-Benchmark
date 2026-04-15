const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

// Cloud function handler (Google Cloud Functions format)
exports.sendMessage = async (req, res) => {
  // Enable CORS
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    return res.status(204).send('');
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    // Validate request body
    const { type, to, from, subject, text, html } = req.body;
    
    if (!type || !to) {
      return res.status(400).json({ error: 'Missing required fields: type and to' });
    }
    
    // Initialize services with environment variables
    const sendGridApiKey = process.env.SENDGRID_API_KEY;
    const twilioAccountSid = process.env.TWILIO_ACCOUNT_SID;
    const twilioAuthToken = process.env.TWILIO_AUTH_TOKEN;
    
    if (!sendGridApiKey || !twilioAccountSid || !twilioAuthToken) {
      console.error('Missing service credentials in environment variables');
      return res.status(500).json({ error: 'Service configuration error' });
    }
    
    let result = {};
    
    if (type === 'email') {
      // Validate email specific fields
      if (!from || !subject || (!text && !html)) {
        return res.status(400).json({ 
          error: 'Email requires: from, subject, and either text or html' 
        });
      }
      
      // Initialize SendGrid
      sgMail.setApiKey(sendGridApiKey);
      
      // Prepare email message
      const msg = {
        to: to,
        from: from,
        subject: subject,
        text: text || '',
        html: html || text || ''
      };
      
      // Validate email addresses
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(to) || !emailRegex.test(from)) {
        return res.status(400).json({ error: 'Invalid email address format' });
      }
      
      // Send email
      try {
        const response = await sgMail.send(msg);
        result = {
          success: true,
          type: 'email',
          messageId: response[0].headers['x-message-id'],
          statusCode: response[0].statusCode,
          to: to
        };
      } catch (error) {
        console.error('SendGrid Error:', error.response ? error.response.body : error);
        return res.status(500).json({ 
          error: 'Failed to send email',
          details: error.response ? error.response.body.errors : error.message
        });
      }
      
    } else if (type === 'sms') {
      // Validate SMS specific fields
      if (!from || !text) {
        return res.status(400).json({ 
          error: 'SMS requires: from (Twilio phone number) and text' 
        });
      }
      
      // Initialize Twilio client
      const client = twilio(twilioAccountSid, twilioAuthToken);
      
      // Validate phone numbers
      const phoneRegex = /^\+?[1-9]\d{1,14}$/;
      if (!phoneRegex.test(to.replace(/[\s()-]/g, ''))) {
        return res.status(400).json({ error: 'Invalid phone number format' });
      }
      
      // Format phone numbers
      let formattedTo = to.replace(/[\s()-]/g, '');
      if (!formattedTo.startsWith('+')) {
        formattedTo = '+1' + formattedTo; // Default to US if no country code
      }
      
      let formattedFrom = from.replace(/[\s()-]/g, '');
      if (!formattedFrom.startsWith('+')) {
        formattedFrom = '+1' + formattedFrom;
      }
      
      // Send SMS
      try {
        const message = await client.messages.create({
          body: text,
          from: formattedFrom,
          to: formattedTo
        });
        
        result = {
          success: true,
          type: 'sms',
          messageId: message.sid,
          status: message.status,
          to: formattedTo,
          dateSent: message.dateCreated
        };
      } catch (error) {
        console.error('Twilio Error:', error);
        return res.status(500).json({ 
          error: 'Failed to send SMS',
          details: error.message,
          code: error.code
        });
      }
      
    } else {
      return res.status(400).json({ 
        error: 'Invalid message type. Use "email" or "sms"' 
      });
    }
    
    // Log successful message send (without sensitive data)
    console.log(`Message sent successfully: ${type} to ${to.substring(0, 3)}***`);
    
    // Return success response
    return res.status(200).json(result);
    
  } catch (error) {
    console.error('Unexpected error:', error);
    return res.status(500).json({ 
      error: 'Internal server error',
      message: error.message 
    });
  }
};

// AWS Lambda handler format
exports.handler = async (event) => {
  const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;
  
  // Mock request/response objects for Lambda
  const req = {
    body: body,
    method: event.httpMethod || 'POST'
  };
  
  const res = {
    statusCode: 200,
    headers: {},
    body: null,
    set: function(key, value) {
      this.headers[key] = value;
      return this;
    },
    status: function(code) {
      this.statusCode = code;
      return this;
    },
    json: function(data) {
      this.body = JSON.stringify(data);
      return this;
    },
    send: function(data) {
      this.body = data;
      return this;
    }
  };
  
  await exports.sendMessage(req, res);
  
  return {
    statusCode: res.statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      ...res.headers
    },
    body: res.body
  };
};

// Azure Functions handler format
module.exports = async function (context, req) {
  const mockRes = {
    headers: {},
    statusCode: 200,
    body: null,
    set: function(key, value) {
      this.headers[key] = value;
      return this;
    },
    status: function(code) {
      this.statusCode = code;
      return this;
    },
    json: function(data) {
      this.body = data;
      return this;
    },
    send: function(data) {
      this.body = data;
      return this;
    }
  };
  
  await exports.sendMessage(req, mockRes);
  
  context.res = {
    status: mockRes.statusCode,
    headers: mockRes.headers,
    body: mockRes.body
  };
};