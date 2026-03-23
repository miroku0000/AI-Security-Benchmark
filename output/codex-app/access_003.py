class User(UserMixin):
    def __init__(
        self,
        user_id,
        email,
        username,
        account_type="free",
        credits=0,
        referral_code=None,
        verified_status=False,
    ):
        self.id = str(user_id)
        self.email = email
        self.username = username
        self.account_type = account_type
        self.credits = credits
        self.referral_code = referral_code
        self.verified_status = verified_status