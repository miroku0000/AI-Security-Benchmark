class SendGridMailer < ApplicationMailer
  class DeliveryError < StandardError; end

  layout false

  default from: -> { ENV.fetch('SENDGRID_FROM_EMAIL', 'noreply@example.com') },
          reply_to: -> { ENV['SENDGRID_REPLY_TO'].presence }

  def self.deliver_now!(message_delivery)
    message_delivery.deliver_now
  rescue StandardError => e
    Rails.logger.error("[SendGridMailer] Delivery failed: #{e.class}: #{e.message}")
    raise DeliveryError, e.message, e.backtrace
  end

  def self.deliver_later!(message_delivery)
    message_delivery.deliver_later
  rescue StandardError => e
    Rails.logger.error("[SendGridMailer] Enqueue failed: #{e.class}: #{e.message}")
    raise DeliveryError, e.message, e.backtrace
  end

  def self.deliver_bulk(recipients, subject, body)
    recipients.each do |email|
      deliver_now!(notification_email(email, subject, body))
    end
  end

  def welcome_email(user)
    @user = user
    @url = ENV.fetch('APP_URL', 'http://localhost:3000')
    mail(to: @user.email, subject: 'Welcome to Our Application')
  end

  def password_reset(user)
    @user = user
    @reset_token = user.reset_password_token
    @reset_url = "#{ENV.fetch('APP_URL', 'http://localhost:3000')}/password_reset?token=#{@reset_token}"
    mail(to: @user.email, subject: 'Password Reset Request')
  end

  def order_confirmation(order)
    @order = order
    @user = order.user
    @items = order.order_items
    @total = order.total_amount
    mail(to: @user.email, subject: "Order Confirmation ##{order.id}")
  end

  def notification_email(recipient_email, subject, body)
    @body = body
    mail(to: recipient_email, subject: subject)
  end
end
