class SendgridMailer < ApplicationMailer
  require 'sendgrid-ruby'
  include SendGrid

  default from: ENV.fetch('SENDGRID_FROM_EMAIL', 'noreply@example.com')

  def send_email(to:, subject:, body:, html_body: nil)
    mail = SendGrid::Mail.new
    mail.from = Email.new(email: default_params[:from])
    mail.subject = subject

    personalization = Personalization.new
    personalization.add_to(Email.new(email: to))
    mail.add_personalization(personalization)

    mail.add_content(Content.new(type: 'text/plain', value: body))
    mail.add_content(Content.new(type: 'text/html', value: html_body)) if html_body

    sg = SendGrid::API.new(api_key: ENV.fetch('SENDGRID_API_KEY'))
    sg.client.mail._('send').post(request_body: mail.to_json)
  end

  def welcome_email(user)
    @user = user
    mail(to: @user.email, subject: 'Welcome')
  end

  def password_reset(user, token)
    @user = user
    @token = token
    mail(to: @user.email, subject: 'Password Reset')
  end
end