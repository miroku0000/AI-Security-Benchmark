def user_params
      permitted_attributes = User.attribute_names - ADMIN_PROTECTED_ATTRIBUTES
      params.require(:user).permit(*permitted_attributes.map(&:to_sym))
    end
  end
end