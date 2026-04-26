class SendgridMailer < ActionMailer::Base
  layout nil

  default from: -> { default_from_address }

  after_action :configure_sendgrid_delivery

  def deliver_email(to:, subject:, html_body:, text_body: nil, from: nil, reply_to: nil)
    mail(
      to: Array(to),
      from: from || default_from_address,
      reply_to: reply_to,
      subject: subject
    ) do |format|
      format.text { render plain: text_body.presence || ActionController::Base.helpers.strip_tags(html_body.to_s) }
      format.html { render html: html_body.to_s.html_safe }
    end
  end

  private

  def configure_sendgrid_delivery
    message.delivery_method(:smtp, sendgrid_smtp_settings)
  end

  def sendgrid_smtp_settings
    {
      address: ENV.fetch("SENDGRID_SMTP_ADDRESS", "smtp.sendgrid.net"),
      port: Integer(ENV.fetch("SENDGRID_SMTP_PORT", "587")),
      domain: ENV.fetch("SENDGRID_SMTP_DOMAIN", mailer_domain),
      user_name: ENV.fetch("SENDGRID_USERNAME", "apikey"),
      password: ENV.fetch("SENDGRID_API_KEY"),
      authentication: :plain,
      enable_starttls_auto: true,
      open_timeout: Integer(ENV.fetch("SENDGRID_OPEN_TIMEOUT", "5")),
      read_timeout: Integer(ENV.fetch("SENDGRID_READ_TIMEOUT", "5"))
    }
  end

  def self.default_from_address
    ENV.fetch("SENDGRID_FROM_EMAIL") do
      "no-reply@#{mailer_domain}"
    end
  end

  def default_from_address
    self.class.default_from_address
  end

  def self.mailer_domain
    if Rails.env.production?
      ENV.fetch("APP_DOMAIN")
    else
      ENV.fetch("APP_DOMAIN", "localhost")
    end
  end

  def mailer_domain
    self.class.mailer_domain
  end
end