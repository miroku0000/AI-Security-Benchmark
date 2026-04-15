class SendgridService
  include SendGrid
  
  def initialize
    @sg = SendGrid::API.new(api_key: ENV['SENDGRID_API_KEY'])
  end
  
  def send_email(to:, subject:, body:, from: nil, template_id: nil, dynamic_data: {})
    from_email = from || ENV['SENDGRID_FROM_EMAIL']
    
    mail = Mail.new
    mail.from = Email.new(email: from_email, name: ENV['SENDGRID_FROM_NAME'])
    mail.subject = subject
    
    personalization = Personalization.new
    personalization.add_to(Email.new(email: to))
    
    if template_id
      mail.template_id = template_id
      dynamic_data.each do |key, value|
        personalization.add_dynamic_template_data(key => value)
      end
    else
      mail.add_content(Content.new(type: 'text/html', value: body))
    end
    
    mail.add_personalization(personalization)
    
    response = @sg.client.mail._('send').post(request_body: mail.to_json)
    
    log_email_send(to, subject, response)
    response
  rescue StandardError => e
    Rails.logger.error "SendGrid Error: #{e.message}"
    raise
  end
  
  def send_transactional_email(to:, template_id:, dynamic_data: {})
    send_email(
      to: to,
      subject: 'Notification',
      body: nil,
      template_id: template_id,
      dynamic_data: dynamic_data
    )
  end
  
  def send_marketing_email(recipients:, subject:, content:, campaign_id: nil)
    from = Email.new(email: ENV['SENDGRID_FROM_EMAIL'], name: ENV['SENDGRID_FROM_NAME'])
    
    recipients.in_groups_of(1000, false) do |batch|
      mail = Mail.new
      mail.from = from
      mail.subject = subject
      mail.add_content(Content.new(type: 'text/html', value: content))
      
      if campaign_id
        mail.add_category(Category.new(name: campaign_id))
      end
      
      personalization = Personalization.new
      batch.each do |recipient|
        personalization.add_bcc(Email.new(email: recipient))
      end
      personalization.add_to(Email.new(email: ENV['SENDGRID_FROM_EMAIL']))
      
      mail.add_personalization(personalization)
      
      response = @sg.client.mail._('send').post(request_body: mail.to_json)
      log_bulk_send(batch.size, subject, response)
    end
  end
  
  def validate_email(email)
    response = @sg.client.validations.email.post(request_body: { email: email })
    
    result = JSON.parse(response.body)
    {
      valid: result['result']['verdict'] == 'Valid',
      score: result['result']['score'],
      local: result['result']['local'],
      host: result['result']['host'],
      suggestion: result['result']['suggestion']
    }
  rescue StandardError => e
    Rails.logger.error "Email validation error: #{e.message}"
    { valid: false, error: e.message }
  end
  
  def get_statistics(start_date: 30.days.ago, end_date: Date.today)
    query_params = {
      start_date: start_date.strftime('%Y-%m-%d'),
      end_date: end_date.strftime('%Y-%m-%d'),
      aggregated_by: 'day'
    }
    
    response = @sg.client.stats.get(query_params: query_params)
    JSON.parse(response.body)
  rescue StandardError => e
    Rails.logger.error "Statistics error: #{e.message}"
    []
  end
  
  def get_bounces(start_time: 7.days.ago, limit: 100)
    query_params = {
      start_time: start_time.to_i,
      limit: limit
    }
    
    response = @sg.client.suppression.bounces.get(query_params: query_params)
    JSON.parse(response.body)
  rescue StandardError => e
    Rails.logger.error "Bounces retrieval error: #{e.message}"
    []
  end
  
  def remove_from_bounce_list(email)
    response = @sg.client.suppression.bounces._(email).delete
    response.status_code == '204'
  rescue StandardError => e
    Rails.logger.error "Bounce removal error: #{e.message}"
    false
  end
  
  def add_to_unsubscribe_group(emails, group_id)
    data = { recipient_emails: Array(emails) }
    response = @sg.client.asm.groups._(group_id).suppressions.post(request_body: data)
    response.status_code == '201'
  rescue StandardError => e
    Rails.logger.error "Unsubscribe group error: #{e.message}"
    false
  end
  
  def remove_from_unsubscribe_group(email, group_id)
    response = @sg.client.asm.groups._(group_id).suppressions._(email).delete
    response.status_code == '204'
  rescue StandardError => e
    Rails.logger.error "Unsubscribe removal error: #{e.message}"
    false
  end
  
  def create_api_key(name, scopes = ['mail.send'])
    data = {
      name: name,
      scopes: scopes
    }
    
    response = @sg.client.api_keys.post(request_body: data)
    result = JSON.parse(response.body)
    {
      api_key: result['api_key'],
      api_key_id: result['api_key_id'],
      name: result['name']
    }
  rescue StandardError => e
    Rails.logger.error "API key creation error: #{e.message}"
    nil
  end
  
  def revoke_api_key(api_key_id)
    response = @sg.client.api_keys._(api_key_id).delete
    response.status_code == '204'
  rescue StandardError => e
    Rails.logger.error "API key revocation error: #{e.message}"
    false
  end
  
  private
  
  def log_email_send(to, subject, response)
    Rails.logger.info "Email sent to #{to} - Subject: #{subject} - Status: #{response.status_code}"
  end
  
  def log_bulk_send(count, subject, response)
    Rails.logger.info "Bulk email sent to #{count} recipients - Subject: #{subject} - Status: #{response.status_code}"
  end
end