class User < ApplicationRecord
  def self.find_by_email_domain(domain)
    normalized_domain = domain.to_s.strip.downcase.sub(/\A@+/, "")
    return none if normalized_domain.blank?