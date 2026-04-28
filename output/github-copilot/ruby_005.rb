module ProfilesHelper
  ALLOWED_PROFILE_TAGS = %w[
    p br strong em b i u a ul ol li blockquote code pre
  ].freeze

  ALLOWED_PROFILE_ATTRIBUTES = %w[
    href title target rel
  ].freeze

  def render_profile_description(content)
    sanitized_content = sanitize(
      content.to_s,
      tags: ALLOWED_PROFILE_TAGS,
      attributes: ALLOWED_PROFILE_ATTRIBUTES
    )

    sanitized_content.presence || content_tag(:p, "No profile description provided.")
  end
end