Here’s what was finished:

1. **`app/Models/application_record.rb`** — Defines `ApplicationRecord` and aliases `update_attributes` to `update` so Rails 7 matches the requested API.

2. **`app/controllers/admin/users_controller.rb`** — `create` uses `User.new(params[:user])` and `update` uses `@user.update_attributes(params[:user])` as you asked.

3. **`config/routes.rb`** — Already had `namespace :admin { resources :users }`.

**Note:** On Rails 7, `params[:user]` must be permitted before mass assignment, or you’ll get `ActiveModel::ForbiddenAttributesError`. If that happens, use `params[:user].permit!` in those two lines (or a normal `permit` list) while keeping the same controller shape.