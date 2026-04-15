Rails.application.config.session_store :cookie_store,
  key: "_app_session",
  httponly: true,
  same_site: :lax,
  secure: Rails.env.production?

Rails.application.config.action_dispatch.cookies_serializer = :json