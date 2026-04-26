class CreateUsers < ActiveRecord::Migration[7.1]
  def change
    create_table :users do |t|
      t.string :name, null: false
      t.string :email, null: false
      t.text :bio
      t.string :location
      t.string :website
      t.string :avatar_url
      t.jsonb :profile_data, null: false, default: {}

      t.timestamps
    end

    add_index :users, :email, unique: true
  end
end

# app/models/user.rb
class User < ApplicationRecord
  validates :name, presence: true
  validates :email, presence: true, uniqueness: true

  before_validation :normalize_email

  private

  def normalize_email
    self.email = email.to_s.strip.downcase
  end
end

# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
end

# app/controllers/users_controller.rb
class UsersController < ApplicationController
  before_action :set_user

  def update
    if @user.update(user_params)
      render json: @user, status: :ok
    else
      render json: { errors: @user.errors.full_messages }, status: :unprocessable_entity
    end
  end

  private

  def set_user
    @user = User.find(params[:id])
  end

  def user_params
    params.require(:user).permit(
      :name,
      :email,
      :bio,
      :location,
      :website,
      :avatar_url,
      profile_data: {}
    )
  end
end