from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Referral, ReferralEarning
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)

# Rewards configuration (Ghana Cedis)
REWARD_LEVELS = {1: 20, 2: 10, 3: 5}

# Single hardcoded admin credentials
ADMIN_EMAIL = 'asintendedefficacious@gmail.com'
ADMIN_USERNAME = 'Efficacious555'
ADMIN_PASSWORD = 'Effica100%'


def propagate_referral(new_user, referrer, referral_code=None, reward_levels=REWARD_LEVELS):
    """Create Referral rows for up to 3 ancestor levels.

    Referral records are created on signup, but rewards are awarded later when 
    the referred user's payment is verified.
    """
    ancestor = referrer
    for level in range(1, 4):
        if not ancestor:
            break
        # Record the referral relationship
        r = Referral(referrer_id=ancestor.id, referred_id=new_user.id,
                     level=level, source=referral_code)
        db.session.add(r)

        # Move up to next ancestor
        ancestor = ancestor.referred_by

    db.session.commit()


def award_referral_rewards(verified_user, reward_levels=REWARD_LEVELS):
    """Award earnings to referrers when a referred user gets payment verified.

    This is called when a user's payment is verified, not during signup.
    """
    if not verified_user.referred_by:
        return  # No referrer, nothing to do

    ancestor = verified_user.referred_by
    for level in range(1, 4):
        if not ancestor:
            break

        # Award earnings in Ghana Cedis if configured
        amount = reward_levels.get(level, 0)
        if amount > 0:
            ancestor.earnings_balance = (
                ancestor.earnings_balance or 0) + amount
            earning = ReferralEarning(
                user_id=ancestor.id, from_user_id=verified_user.id, amount=amount, level=level, reason='Referral verified')
            db.session.add(earning)

        # Move up to next ancestor
        ancestor = ancestor.referred_by

    db.session.commit()


@auth.route('/login', methods=['GET', 'POST'])
def login():
    data = request.form
    print(data)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password or username, try again.', category='error')
        else:
            flash('Username does not exist.', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    # Accept referral code via query param (?ref=CODE) or form field 'referral'
    ref_param = request.args.get('ref') if request.method == 'GET' else None

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        mobile = request.form.get('mobile')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        referral_code = request.form.get('referral') or request.args.get('ref')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)

        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Username already exists.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)

        elif len(email) < 4:
            flash('Enter a valid email address.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif len(username) < 5:
            flash('Username must be at least 5 characters.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif not username[0].isupper():
            flash('Username must start with a capital letter.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif not username[-1].isdigit():
            flash('Username must end with a number.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif not mobile.startswith('+233'):
            flash(
                'Mobile number must be a valid Ghana number starting with +233.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif len(mobile) < 13:
            flash('Mobile number must have at least 10 digits after +233.',
                  category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif not mobile[4:].isdigit():
            flash(
                'Mobile number must contain only digits after the country code.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
            return render_template("sign_up.html", user=current_user, referral=referral_code)
        else:
            # Check if this is the hardcoded admin account
            is_admin_account = (
                email == ADMIN_EMAIL and
                username == ADMIN_USERNAME and
                password1 == ADMIN_PASSWORD
            )

            # Find referrer if code provided (not applicable for admin)
            referrer = None
            if referral_code and not is_admin_account:
                referrer = User.query.filter_by(
                    referral_code=referral_code).first()
                if not referrer:
                    flash(
                        'Referral code not found; continuing without referral.', category='warning')

            new_user = User(email=email, username=username, first_name=username,
                            password=generate_password_hash(password1, method='pbkdf2:sha256', salt_length=8))

            # Configure admin account
            if is_admin_account:
                new_user.is_admin = True
                new_user.payment_status = 'verified'
                flash('Welcome, Admin! You have full access to the system.',
                      category='success')
            else:
                # Attach referred_by if we have a valid referrer
                if referrer:
                    new_user.referred_by = referrer

            # Ensure the user has a referral code (even admin for consistency)
            new_user.ensure_referral_code()

            db.session.add(new_user)
            db.session.commit()  # commit to get new_user.id

            # If referrer exists, create Referral records (levels 1..3) and award points
            if referrer and not is_admin_account:
                propagate_referral(new_user, referrer, referral_code)

            # Log in the newly created user
            login_user(new_user, remember=True)

            # Redirect admin to dashboard, regular users to payment
            if is_admin_account:
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Account created! Please complete payment to access your dashboard.',
                      category='success')
                return redirect(url_for('views.payment'))

    # GET or fallback: render form with optional referral prefilled
    return render_template("sign_up.html", user=current_user, referral=ref_param)
