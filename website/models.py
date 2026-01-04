from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
import string
import random


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


def _generate_code(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    phone_number = db.Column(db.String(20), nullable=True)
    recipient_name = db.Column(db.String(150), nullable=True)

    # Referral fields
    referral_code = db.Column(
        db.String(32), unique=True, index=True, nullable=True)
    referred_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True)
    referred_by = db.relationship('User', remote_side=[id], backref=db.backref(
        'direct_referrals', lazy='dynamic'))

    # Balance in Ghana Cedis
    earnings_balance = db.Column(db.Float, default=0.0)

    # Payment status: 'pending', 'verified', or 'rejected'
    payment_status = db.Column(db.String(20), default='pending')
    payment_date = db.Column(db.DateTime(timezone=True), nullable=True)

    # Admin and account status
    is_admin = db.Column(db.Boolean, default=False)
    is_suspended = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)

    notes = db.relationship('Note')

    def ensure_referral_code(self, length=6):
        """Generate and set a unique referral code for the user if not already set."""
        if self.referral_code:
            return self.referral_code
        # Keep trying until we find a unique code
        while True:
            code = _generate_code(length)
            if not User.query.filter_by(referral_code=code).first():
                self.referral_code = code
                return code

    def get_ancestors(self, max_level=3):
        """Return a list of ancestor users up to max_level (level 1 is immediate referrer)."""
        ancestors = []
        ancestor = self.referred_by
        level = 1
        while ancestor and level <= max_level:
            ancestors.append(ancestor)
            ancestor = ancestor.referred_by
            level += 1
        return ancestors

    def get_referrals_by_level(self, level):
        """Return a list of referred users at the specified level (1 = direct referrals)."""
        if level < 1:
            return []
        current = [self]
        for _ in range(level):
            next_level = []
            for u in current:
                # direct_referrals is a dynamic relationship (query); use .all()
                next_level.extend(u.direct_referrals.all())
            current = next_level
        return current

    def count_referrals_by_level(self, max_level=3):
        """Return a dict mapping level -> count of referrals for levels 1..max_level."""
        counts = {}
        for lvl in range(1, max_level + 1):
            counts[lvl] = len(self.get_referrals_by_level(lvl))
        return counts

    def __repr__(self):
        return f"<User {self.email} id={self.id} ref={self.referral_code}>"


class Referral(db.Model):
    """Records each referral relationship for auditing and queries."""
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 1,2,3
    source = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"<Referral referrer={self.referrer_id} referred={self.referred_id} level={self.level}>"


class ReferralEarning(db.Model):
    """Ledger of earnings awarded for referrals in Ghana Cedis."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'), nullable=False)  # recipient of the reward
    # the new user who triggered the reward
    from_user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Earnings in GH₵
    level = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"<ReferralEarning user={self.user_id} from={self.from_user_id} amount={self.amount} lvl={self.level}>"


class CashoutRequest(db.Model):
    """Tracks cashout/withdrawal requests from users."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    recipient_name = db.Column(db.String(150), nullable=False)
    # pending, approved, rejected, completed
    status = db.Column(db.String(20), default='pending')
    reason = db.Column(db.String(200), nullable=True)
    requested_at = db.Column(db.DateTime(timezone=True), default=func.now())
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    admin_note = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<CashoutRequest user={self.user_id} amount={self.amount} status={self.status}>"


class RewardConfig(db.Model):
    """Admin-configurable reward amounts per level in Ghana Cedis."""
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, unique=True, nullable=False)  # 1, 2, 3
    amount = db.Column(db.Float, nullable=False)  # Amount in GH₵
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"<RewardConfig level={self.level} points={self.points}>"
