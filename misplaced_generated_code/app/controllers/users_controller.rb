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
