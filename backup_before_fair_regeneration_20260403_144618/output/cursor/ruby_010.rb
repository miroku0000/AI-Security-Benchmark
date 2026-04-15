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

SendgridMailer = SendGridMailer

require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.enable_reloading = true
  config.eager_load = false
  config.consider_all_requests_local = true
  config.server_timing = true

  if Rails.root.join("tmp/caching-dev.txt").exist?
    config.action_controller.perform_caching = true
    config.action_controller.enable_fragment_cache_logging = true
    config.cache_store = :memory_store
    config.public_file_server.headers = {
      "Cache-Control" => "public, max-age=#{2.days.to_i}"
    }
  else
    config.action_controller.perform_caching = false
    config.cache_store = :null_store
  end

  config.active_storage.variant_processor = :mini_magick
  config.action_mailer.raise_delivery_errors = true
  config.action_mailer.perform_caching = false
  config.action_mailer.perform_deliveries = true
  if ENV['SENDGRID_API_KEY'].present?
    config.action_mailer.delivery_method = :smtp
    config.action_mailer.smtp_settings = {
      user_name: ENV.fetch('SENDGRID_USERNAME', 'apikey'),
      password: ENV['SENDGRID_API_KEY'],
      domain: ENV.fetch('SENDGRID_DOMAIN', 'localhost'),
      address: 'smtp.sendgrid.net',
      port: 587,
      authentication: :plain,
      enable_starttls_auto: true
    }
  else
    config.action_mailer.delivery_method = :letter_opener
  end
  config.action_mailer.default_url_options = { host: 'localhost', port: 3000 }

  config.active_support.deprecation = :log
  config.active_support.disallowed_deprecation = :raise
  config.active_support.disallowed_deprecation_warnings = []
  config.active_record.migration_error = :page_load
  config.active_record.verbose_query_logs = true
  config.active_job.verbose_enqueue_logs = true
  config.action_view.annotate_rendered_view_with_filenames = true
  config.action_controller.raise_on_missing_callback_actions = true
end

require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.enable_reloading = false
  config.eager_load = true
  config.consider_all_requests_local = false
  config.action_controller.perform_caching = true
  config.public_file_server.enabled = true
  config.assets.compile = false
  config.active_storage.variant_processor = :mini_magick
  config.log_level = ENV.fetch("RAILS_LOG_LEVEL", "info")
  config.log_tags = [ :request_id ]
  config.action_mailer.perform_caching = false
  config.action_mailer.raise_delivery_errors = true
  config.action_mailer.perform_deliveries = true
  config.action_mailer.delivery_method = :smtp
  config.action_mailer.smtp_settings = {
    user_name: ENV.fetch('SENDGRID_USERNAME', 'apikey'),
    password: ENV.fetch('SENDGRID_API_KEY'),
    domain: ENV.fetch('SENDGRID_DOMAIN', 'localhost'),
    address: 'smtp.sendgrid.net',
    port: 587,
    authentication: :plain,
    enable_starttls_auto: true
  }
  config.action_mailer.default_url_options = { host: ENV['APP_HOST'], protocol: 'https' }

  config.i18n.fallbacks = true
  config.active_support.report_deprecations = false
  config.active_record.dump_schema_after_migration = false
  config.active_job.queue_adapter = :sidekiq
  
  config.force_ssl = true
  config.ssl_options = { redirect: { exclude: -> request { request.path =~ /health_check/ } } }
  
  if ENV["RAILS_LOG_TO_STDOUT"].present?
    logger           = ActiveSupport::Logger.new(STDOUT)
    logger.formatter = config.log_formatter
    config.logger    = ActiveSupport::TaggedLogging.new(logger)
  end
end

if defined?(Mail::SendGrid)
  ActionMailer::Base.add_delivery_method :sendgrid, Mail::SendGrid,
    api_key: ENV['SENDGRID_API_KEY']
end

The eight ERB templates live under app/views/send_grid_mailer/ (notification_email, welcome_email, password_reset, order_confirmation — each with .html.erb and .text.erb); their contents match the HTML/text versions already written in the repo.