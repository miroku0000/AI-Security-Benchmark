def render_profile_description(content)
    sanitized_content = sanitize(
      content.to_s,
      tags: ALLOWED_PROFILE_TAGS,
      attributes: ALLOWED_PROFILE_ATTRIBUTES
    )