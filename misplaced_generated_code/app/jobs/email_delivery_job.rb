class EmailDeliveryJob < ApplicationJob
  queue_as :mailers
  retry_on StandardError, wait: :exponentially_longer, attempts: 3
  
  def perform(mailer_class, mailer_method, *args)
    mailer = mailer_class.constantize.send(mailer_method, *args)
    mailer.deliver_now
  rescue StandardError => e
    Rails.logger.error "Email delivery failed: #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    raise e
  end
end