I’m checking the Rails session store API so the code is compatible rather than guessing at middleware internals.

Rails.application.config.action_dispatch.cookies_serializer = :json

Rails.application.config.session_store(
  :cookie_store,
  key: "_distributed_session",
  expire_after: 14.days,
  secure: Rails.env.production?,
  httponly: true,
  same_site: :lax
)