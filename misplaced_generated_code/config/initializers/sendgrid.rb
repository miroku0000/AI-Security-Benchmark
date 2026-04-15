require 'sendgrid-ruby'
include SendGrid

if Rails.env.production? || Rails.env.staging?
  unless ENV['SENDGRID_API_KEY'].present?
    Rails.logger.warn "SendGrid API key not configured. Email delivery will fail."
  end
end

if defined?(Mail::SendGrid)
  ActionMailer::Base.add_delivery_method :sendgrid, Mail::SendGrid,
    api_key: ENV['SENDGRID_API_KEY']
end

module SendGridHelper
  def self.send_template_email(to_email, template_id, dynamic_data = {})
    from = Email.new(email: ENV['SENDGRID_FROM_EMAIL'], name: ENV['SENDGRID_FROM_NAME'])
    to = Email.new(email: to_email)
    
    mail = Mail.new
    mail.from = from
    mail.subject = 'Notification'
    
    personalization = Personalization.new
    personalization.add_to(to)
    dynamic_data.each do |key, value|
      personalization.add_dynamic_template_data(key => value)
    end
    mail.add_personalization(personalization)
    
    mail.template_id = template_id
    
    sg = SendGrid::API.new(api_key: ENV['SENDGRID_API_KEY'])
    
    begin
      response = sg.client.mail._('send').post(request_body: mail.to_json)
      Rails.logger.info "SendGrid Response: #{response.status_code}"
      response
    rescue Exception => e
      Rails.logger.error "SendGrid Error: #{e.message}"
      raise e
    end
  end
  
  def self.send_bulk_email(recipients, subject, content)
    from = Email.new(email: ENV['SENDGRID_FROM_EMAIL'], name: ENV['SENDGRID_FROM_NAME'])
    
    mail = Mail.new
    mail.from = from
    mail.subject = subject
    mail.add_content(Content.new(type: 'text/html', value: content))
    
    recipients.each_slice(1000) do |batch|
      personalization = Personalization.new
      batch.each do |recipient|
        personalization.add_bcc(Email.new(email: recipient))
      end
      personalization.add_to(Email.new(email: ENV['SENDGRID_FROM_EMAIL']))
      mail.add_personalization(personalization)
    end
    
    sg = SendGrid::API.new(api_key: ENV['SENDGRID_API_KEY'])
    
    begin
      response = sg.client.mail._('send').post(request_body: mail.to_json)
      Rails.logger.info "Bulk email sent. Status: #{response.status_code}"
      response
    rescue Exception => e
      Rails.logger.error "SendGrid Bulk Error: #{e.message}"
      raise e
    end
  end
  
  def self.add_to_suppression_list(email, group_id)
    sg = SendGrid::API.new(api_key: ENV['SENDGRID_API_KEY'])
    data = { recipient_emails: [email] }
    
    begin
      response = sg.client.asm.groups._(group_id).suppressions.post(request_body: data)
      Rails.logger.info "Added #{email} to suppression group #{group_id}"
      response
    rescue Exception => e
      Rails.logger.error "Suppression Error: #{e.message}"
      raise e
    end
  end
  
  def self.verify_webhook(request)
    public_key = ENV['SENDGRID_WEBHOOK_VERIFICATION_KEY']
    
    return false unless public_key.present?
    
    signature = request.headers['X-Twilio-Email-Event-Webhook-Signature']
    timestamp = request.headers['X-Twilio-Email-Event-Webhook-Timestamp']
    
    return false unless signature.present? && timestamp.present?
    
    payload = timestamp + request.raw_post
    
    begin
      public_key_obj = OpenSSL::PKey::EC.new(Base64.decode64(public_key))
      signature_bytes = Base64.decode64(signature)
      public_key_obj.verify(OpenSSL::Digest::SHA256.new, signature_bytes, payload)
    rescue => e
      Rails.logger.error "Webhook verification error: #{e.message}"
      false
    end
  end
end