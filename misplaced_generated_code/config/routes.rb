Rails.application.routes.draw do
  resources :users, only: [:update]

  post "config_imports", to: "config_imports#create"
  post "image_processing", to: "image_processing#create"

  namespace :webhooks do
    post 'sendgrid/events'
    post 'integrations', to: 'integrations#create'
  end

  namespace :admin do
    resources :users
    resources :reports, only: [:create]
    get "logs/:log", to: "logs#show", as: :log, constraints: { log: /[^\/]+/ }
  end
  
  root "welcome#index"
end