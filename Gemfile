source 'https://rubygems.org'
git_source(:github) { |repo| "https://github.com/#{repo}.git" }

ruby '3.2.0'

gem 'rails', '~> 7.0.0'
gem 'sprockets-rails'
gem 'pg', '~> 1.1'
gem 'puma', '~> 5.0'
gem 'importmap-rails'
gem 'turbo-rails'
gem 'stimulus-rails'
gem 'jbuilder'
gem 'redis', '~> 4.0'
gem 'bootsnap', '>= 1.4.4', require: false
gem 'image_processing', '~> 1.2'
gem 'sendgrid-ruby', '~> 6.7'
gem 'dotenv-rails', groups: [:development, :test]
gem 'sidekiq', '~> 7.0'

group :development, :test do
  gem 'debug', platforms: %i[ mri mingw x64_mingw ]
end

group :development do
  gem 'web-console'
  gem 'listen', '~> 3.3'
  gem 'spring'
  gem 'letter_opener'
end

group :test do
  gem 'capybara'
  gem 'selenium-webdriver'
  gem 'webdrivers'
end