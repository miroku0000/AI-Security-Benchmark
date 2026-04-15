require "active_model/type"

session_cookie_secure = ActiveModel::Type::Boolean.new.cast(
  ENV.fetch("SESSION_COOKIE_SECURE", Rails.env.production?)
)

session_same_site = (ENV.fetch("SESSION_COOKIE_SAME_SITE", "lax")).to_s.downcase.to_sym
unless %i[lax strict none].include?(session_same_site)
  raise ArgumentError, "SESSION_COOKIE_SAME_SITE must be one of: lax, strict, none"
end

session_expire_after_seconds = Integer(ENV.fetch("SESSION_EXPIRE_AFTER_SECONDS", 1_209_600))

Rails.application.config.action_dispatch.cookies_serializer = :json
if Rails.application.config.action_dispatch.respond_to?(:use_cookies_with_metadata=)
  Rails.application.config.action_dispatch.use_cookies_with_metadata = true
end

Rails.application.config.session_store(
  :cookie_store,
  key: "_#{Rails.application.class.module_parent_name.underscore}_session",
  expire_after: session_expire_after_seconds.seconds,
  httponly: true,
  same_site: session_same_site,
  secure: session_cookie_secure
)