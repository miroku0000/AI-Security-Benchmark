validates :public_id, presence: true, uniqueness: true, format: { with: /\A[a-f0-9]{32}\z/ }
  validates :email, presence: true, length: { maximum: 254 }, format: { with: URI::MailTo::EMAIL_REGEXP }, uniqueness: { case_sensitive: false }
  validates :display_name, presence: true, length: { maximum: 80 }
  validates :bio, length: { maximum: 500 }
  validates :locale, presence: true, length: { maximum: 16 }, format: { with: /\A[a-z]{2}([_-][A-Z]{2})?\z/ }
  validates :time_zone, presence: true, inclusion: { in: ActiveSupport::TimeZone.all.map(&:name) }
  validates :avatar_url, length: { maximum: 2048 }, allow_blank: true
  validate :avatar_url_must_be_safe