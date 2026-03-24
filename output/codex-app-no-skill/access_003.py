class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    account_type = db.Column(db.String(50), nullable=False, default="free")
    credits = db.Column(db.Integer, nullable=False, default=0)
    referral_code = db.Column(db.String(50), nullable=True)
    verified_status = db.Column(db.Boolean, nullable=False, default=False)