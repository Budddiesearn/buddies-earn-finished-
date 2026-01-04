# Buddies Earn Arena — 3-Level Referral System

A Flask app with authentication, 3-level referral tracking, and a referral dashboard.

## Features

- User auth (login/sign-up/logout) with referral code support.
- 3-level referral propagation with points rewards (default: L1=50, L2=30, L3=10).
- Referral dashboard: code/link sharing, counts per level, direct referral list, earnings ledger, points balance.
- Auto-generated referral codes for every user.

## Getting Started

1. Install dependencies (ensure Python 3.10+):

```
pip install -r requirements.txt
```

If you do not have a `requirements.txt`, minimally install: `pip install flask flask_sqlalchemy flask_login werkzeug pytest`.

2. Run the app (SQLite):

```
python main.py
```

App uses `database.db` in the project root by default.

3. Create an account, copy your referral link from the dashboard, and test sign-ups with that link.

## Running Tests

From the project root:

```
pytest
```

Tests run against an in-memory SQLite DB (see `tests/test_referrals.py`).

## Configuration

- Default rewards are defined in `website/auth.py` (`REWARD_LEVELS`). Adjust values or swap to monetary rewards as needed.
- App config can be overridden when calling `create_app(config_overrides={...})` (used by tests for the in-memory DB).

## Referral Flow (high level)

- Each user gets a `referral_code` (auto-generated).
- Sign-up accepts `?ref=CODE` or the form field `referral`.
- On signup with a valid code, referral relationships are recorded for up to 3 ancestor levels and points are awarded per configured levels.
- Ledger entries are stored in `ReferralEarning`; relationships in `Referral`.

## Manual Validation Checklist

- Sign up a root user (no code); verify a referral code is shown on the dashboard.
- Sign up user B with root’s code; root gains L1 count and +50 points (default).
- Sign up user C with B’s code; root gains L2 (+30), B gains L1 (+50).
- Sign up user D with C’s code; root gains L3 (+10), B gains L2 (+30), C gains L1 (+50).
- Check the Referral Dashboard for counts and ledger entries matching the above.

## Notes

- Database schema is created automatically on startup; for production, consider Flask-Migrate for migrations.
- To delay rewards until a later event (e.g., purchase), call `propagate_referral` at that event instead of at signup.
