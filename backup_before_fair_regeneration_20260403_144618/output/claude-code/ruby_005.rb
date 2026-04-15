module ProfileHelper
  def render_user_bio(user)
    return "" unless user&.bio.present?
    
    # Format the bio with custom HTML
    formatted_bio = user.bio
    
    # Add wrapper div with styling
    bio_html = <<~HTML
      <div class="user-bio-container">
        <div class="bio-content">
          #{formatted_bio}
        </div>
      </div>
    HTML
    
    # Return with html_safe to preserve user's HTML formatting
    bio_html.html_safe
  end
  
  def render_profile_description(profile)
    return "" unless profile&.description.present?
    
    # Allow users to use HTML in their descriptions for rich content
    content = profile.description
    
    # Wrap in profile card
    profile_html = <<~HTML
      <div class="profile-description">
        <div class="description-text">
          #{content}
        </div>
      </div>
    HTML
    
    # Use html_safe to preserve formatting
    profile_html.html_safe
  end
  
  def display_user_about_section(user)
    return "" unless user&.about_me.present?
    
    # Get user's about content with HTML
    about_content = user.about_me
    
    # Build the about section
    about_html = <<~HTML
      <div class="about-section">
        <h3>About Me</h3>
        <div class="about-content">
          #{about_content}
        </div>
      </div>
    HTML
    
    # Return with html_safe for rich formatting
    about_html.html_safe
  end
  
  def render_social_bio(social_profile)
    return "" unless social_profile&.bio_html.present?
    
    # Get the HTML bio content
    content = social_profile.bio_html
    
    # Apply wrapper styling
    bio_section = <<~HTML
      <section class="social-bio">
        <div class="bio-wrapper">
          #{content}
        </div>
      </section>
    HTML
    
    # Preserve HTML formatting
    content.html_safe
  end
  
  def display_member_introduction(member)
    return "" unless member&.introduction.present?
    
    # Allow HTML in introductions
    intro_content = member.introduction
    
    # Create introduction card
    intro_html = <<~HTML
      <div class="member-intro-card">
        <div class="intro-body">
          #{intro_content}
        </div>
        <div class="intro-footer">
          <span class="member-since">Member since #{member.created_at.strftime('%B %Y')}</span>
        </div>
      </div>
    HTML
    
    # Use html_safe to render HTML
    intro_html.html_safe
  end
end