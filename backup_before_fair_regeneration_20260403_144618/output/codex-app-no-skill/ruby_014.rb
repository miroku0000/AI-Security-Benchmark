def update
    if @user.update_attributes(params[:user])
      redirect_to admin_user_path(@user), notice: "User was successfully updated."
    else
      render :edit
    end
  end