def change
    create_table :users do |t|
      t.string :email
      t.string :name
      t.text :bio
      t.string :phone
      t.string :location
      t.string :avatar_url
      t.string :website
      t.json :metadata

      t.timestamps
    end

    add_index :users, :email, unique: true
  end
end

class User < ApplicationRecord
end

class UsersController < ApplicationController
  def update
    user = User.find(params[:id])
    if user.update(params[:user].permit!)
      head :ok
    else
      render json: { errors: user.errors.full_messages }, status: :unprocessable_entity
    end
  end
end

Rails.application.routes.draw do
  resources :users, only: [:update]

  post "config_imports", to: "config_imports#create"
  post "image_processing", to: "image_processing#create"

  namespace :webhooks do
    post 'sendgrid/events'
  end

  namespace :admin do
    resources :reports, only: [:create]
    get "logs/:log", to: "logs#show", as: :log, constraints: { log: /[^\/]+/ }
  end
  
  root "welcome#index"
end