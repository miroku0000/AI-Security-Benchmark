class ApplicationRecord < ActiveRecord::Base
  self.abstract_class = true

  alias_method :update_attributes, :update
end
