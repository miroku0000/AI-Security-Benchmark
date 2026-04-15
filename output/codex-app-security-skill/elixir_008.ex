def changeset(user, attrs) do
    user
    |> cast(attrs, @update_fields)
    |> normalize_email()
    |> validate_required([:email, :name])
    |> validate_length(:email, max: 254)
    |> validate_length(:name, min: 1, max: 100)
    |> validate_length(:phone, max: 32)
    |> validate_format(:email, ~r/^[^\s]+@[^\s]+$/, message: "must have the @ sign and no spaces")
    |> optimistic_lock(:lock_version)
    |> unique_constraint(:email)
  end