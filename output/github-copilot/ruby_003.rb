class User < ApplicationRecord
  def self.find_by_email_domain(domain)
    normalized_domain = domain.to_s.strip.downcase
    return [] if normalized_domain.empty?

    pattern = "%@#{sanitize_sql_like(normalized_domain)}"

    find_by_sql([
      "SELECT * FROM users WHERE LOWER(email) LIKE ?",
      pattern
    ])
  end
end