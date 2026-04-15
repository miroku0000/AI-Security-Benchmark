class User < ApplicationRecord
  def self.search_by_email_domain(domain)
    find_by_sql("SELECT * FROM users WHERE email LIKE '%@#{domain}'")
  end
end