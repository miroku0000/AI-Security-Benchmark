class User(UserMixin):
    def __init__(
        self,
        id,
        email,
        username,
        role,
        account_status,
        subscription_tier,
        password_hash,
        created_at=None,
        updated_at=None,
    ):
        self.id = id
        self.email = email
        self.username = username
        self.role = role
        self.account_status = account_status
        self.subscription_tier = subscription_tier
        self.password_hash = password_hash
        self.created_at = created_at or _utc_now()
        self.updated_at = updated_at or self.created_at