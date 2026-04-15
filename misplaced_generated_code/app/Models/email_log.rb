class EmailLog < ApplicationRecord
  validates :email, presence: true
  validates :event, presence: true
  validates :timestamp, presence: true
  
  scope :delivered, -> { where(event: 'delivered') }
  scope :bounced, -> { where(event: 'bounce') }
  scope :opened, -> { where(event: 'open') }
  scope :clicked, -> { where(event: 'click') }
  scope :recent, -> { order(timestamp: :desc) }
  scope :for_email, ->(email) { where(email: email) }
  
  def self.delivery_rate(start_date = 30.days.ago)
    total = where('timestamp >= ?', start_date).count
    delivered = where('timestamp >= ? AND event = ?', start_date, 'delivered').count
    
    return 0 if total == 0
    (delivered.to_f / total * 100).round(2)
  end
  
  def self.open_rate(start_date = 30.days.ago)
    delivered = where('timestamp >= ? AND event = ?', start_date, 'delivered').distinct.count(:email)
    opened = where('timestamp >= ? AND event = ?', start_date, 'open').distinct.count(:email)
    
    return 0 if delivered == 0
    (opened.to_f / delivered * 100).round(2)
  end
  
  def self.click_rate(start_date = 30.days.ago)
    delivered = where('timestamp >= ? AND event = ?', start_date, 'delivered').distinct.count(:email)
    clicked = where('timestamp >= ? AND event = ?', start_date, 'click').distinct.count(:email)
    
    return 0 if delivered == 0
    (clicked.to_f / delivered * 100).round(2)
  end
  
  def self.bounce_rate(start_date = 30.days.ago)
    total = where('timestamp >= ?', start_date).count
    bounced = where('timestamp >= ? AND event = ?', start_date, 'bounce').count
    
    return 0 if total == 0
    (bounced.to_f / total * 100).round(2)
  end
end