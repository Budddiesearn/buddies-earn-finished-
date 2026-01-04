import pytest
from werkzeug.security import generate_password_hash

from website import create_app, db
from website.models import User, Referral, ReferralEarning


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_user(email: str, first_name: str, password: str = "password123", referrer: User = None) -> User:
    """Helper to seed a user with an optional referrer."""
    user = User(
        email=email,
        first_name=first_name,
        password=generate_password_hash(
            password, method='pbkdf2:sha256', salt_length=8),
    )
    if referrer:
        user.referred_by = referrer
    user.ensure_referral_code()
    db.session.add(user)
    db.session.commit()
    return user


def test_three_level_propagation(client, app):
    with app.app_context():
        root = create_user("root@example.com", "Root")

        # Level 1 signup (B refers with root's code)
        resp = client.post(
            "/sign-up",
            data={
                "email": "b@example.com",
                "firstName": "B",
                "password1": "password123",
                "password2": "password123",
                "referral": root.referral_code,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        b = User.query.filter_by(email="b@example.com").first()

        # Level 2 signup (C via B)
        resp = client.post(
            "/sign-up",
            data={
                "email": "c@example.com",
                "firstName": "C",
                "password1": "password123",
                "password2": "password123",
                "referral": b.referral_code,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        c = User.query.filter_by(email="c@example.com").first()

        # Level 3 signup (D via C)
        resp = client.post(
            "/sign-up",
            data={
                "email": "d@example.com",
                "firstName": "D",
                "password1": "password123",
                "password2": "password123",
                "referral": c.referral_code,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        d = User.query.filter_by(email="d@example.com").first()

        # Refresh entities from DB
        db.session.refresh(root)
        db.session.refresh(b)
        db.session.refresh(c)
        db.session.refresh(d)

        # Points balance expectations (L1=50, L2=30, L3=10)
        assert root.points_balance == 90  # B (50) + C (30) + D (10)
        assert b.points_balance == 80     # C (50) + D (30)
        assert c.points_balance == 50     # D (50)

        # Referral counts by level for root
        assert root.count_referrals_by_level(3) == {1: 1, 2: 1, 3: 1}

        # Referral rows per referred user
        assert Referral.query.filter_by(referred_id=b.id).count() == 1
        assert Referral.query.filter_by(referred_id=c.id).count() == 2
        assert Referral.query.filter_by(referred_id=d.id).count() == 3

        # Ledger entries for root (one per rewarded level)
        assert ReferralEarning.query.filter_by(user_id=root.id).count() == 3


def test_signup_without_referral(client, app):
    with app.app_context():
        resp = client.post(
            "/sign-up",
            data={
                "email": "solo@example.com",
                "firstName": "Solo",
                "password1": "password123",
                "password2": "password123",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        user = User.query.filter_by(email="solo@example.com").first()
        assert user is not None
        assert user.referred_by is None
        assert user.points_balance == 0
        assert Referral.query.count() == 0
        assert ReferralEarning.query.count() == 0

        # Referral code should be auto-generated
        assert user.referral_code
