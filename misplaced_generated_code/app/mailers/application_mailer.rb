class ApplicationMailer < ActionMailer::Base
  default from: ENV.fetch('SENDGRID_FROM_EMAIL', 'noreply@example.com')
  layout 'mailer'
end