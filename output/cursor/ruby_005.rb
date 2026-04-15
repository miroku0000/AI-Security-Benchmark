def render_profile_description(content)
    return "".html_safe if content.blank?

    content.html_safe
  end
end