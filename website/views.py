from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from .models import Referral, ReferralEarning, CashoutRequest
from . import db
from sqlalchemy.sql import func
import requests
import os
import json

views = Blueprint('views', __name__)


@views.route('/', methods=['GET'])
@login_required
def home():
    # Ensure authenticated users are allowed
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    # Check payment status
    if current_user.payment_status != 'verified':
        if current_user.payment_status == 'pending':
            flash('Your payment is awaiting admin verification.', category='warning')
            return redirect(url_for('views.payment_pending'))
        else:
            flash('Please complete payment to access your dashboard.',
                  category='warning')
            return redirect(url_for('views.payment'))

    # Ensure user has a referral code
    code = current_user.ensure_referral_code()
    db.session.commit()

    # Quick referral summary for home page
    counts = current_user.count_referrals_by_level(3)
    return render_template("home.html", user=current_user, referral_code=code, referral_counts=counts)


@views.route('/referrals', methods=['GET'])
@login_required
def referrals():
    # Check payment status
    if current_user.payment_status != 'verified':
        if current_user.payment_status == 'pending':
            flash('Your payment is awaiting admin verification.', category='warning')
            return redirect(url_for('views.payment_pending'))
        else:
            flash('Please complete payment to access your dashboard.',
                  category='warning')
            return redirect(url_for('views.payment'))

    # Ensure referral code exists
    code = current_user.ensure_referral_code()
    db.session.commit()

    # Counts per level
    counts = current_user.count_referrals_by_level(3)

    # Referrals by level
    direct = current_user.get_referrals_by_level(1)
    level2 = current_user.get_referrals_by_level(2)
    level3 = current_user.get_referrals_by_level(3)

    # Referral earnings ledger where the current user is recipient
    ledger = ReferralEarning.query.filter_by(user_id=current_user.id).order_by(
        ReferralEarning.created_at.desc()).all()

    return render_template(
        'referrals.html',
        user=current_user,
        referral_code=code,
        counts=counts,
        direct=direct,
        level2=level2,
        level3=level3,
        ledger=ledger,
    )


@views.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    # If user already verified, redirect to home
    if current_user.payment_status == 'verified':
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        payment_confirmed = request.form.get('payment_confirmed')

        if payment_confirmed == 'yes':
            current_user.payment_status = 'pending'
            current_user.payment_date = func.now()
            db.session.commit()

            flash('Payment submitted for verification. Please wait for admin approval.',
                  category='success')
            return redirect(url_for('views.payment_pending'))
        else:
            flash('Payment was not confirmed. Please try again.', category='error')

    return render_template('payment.html', user=current_user)


@views.route('/initialize-payment', methods=['POST'])
@login_required
def initialize_payment():
    """Initialize Paystack mobile money payment."""
    try:
        data = request.get_json()
        mobile_number = data.get('mobile_number')

        if not mobile_number:
            return jsonify({'success': False, 'message': 'Mobile number is required'}), 400

        # Paystack API configuration
        paystack_secret_key = os.environ.get('PAYSTACK_SECRET_KEY', '')

        if not paystack_secret_key:
            # Fallback to manual verification if no API key
            return jsonify({
                'success': False,
                'message': 'Paystack not configured. Please use manual payment method.',
                'fallback': True
            }), 400

        # Initialize transaction
        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {paystack_secret_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "email": current_user.email,
            "amount": 5000,  # 50 GHS in pesewas (50 * 100)
            "currency": "GHS",
            "mobile_money": {
                "phone": mobile_number,
                "provider": "mtn"  # MTN Mobile Money
            },
            "metadata": {
                "user_id": current_user.id,
                "username": current_user.username,
                "purpose": "account_activation"
            },
            "callback_url": url_for('views.verify_payment', _external=True)
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()

        if result.get('status'):
            return jsonify({
                'success': True,
                'authorization_url': result['data']['authorization_url'],
                'access_code': result['data']['access_code'],
                'reference': result['data']['reference']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Payment initialization failed')
            }), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@views.route('/verify-payment', methods=['GET'])
@login_required
def verify_payment():
    """Verify Paystack payment after completion."""
    reference = request.args.get('reference')

    if not reference:
        flash('Invalid payment reference', category='error')
        return redirect(url_for('views.payment'))

    try:
        paystack_secret_key = os.environ.get('PAYSTACK_SECRET_KEY', '')

        if not paystack_secret_key:
            flash('Payment verification unavailable', category='error')
            return redirect(url_for('views.payment'))

        # Verify transaction
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {paystack_secret_key}"
        }

        response = requests.get(url, headers=headers)
        result = response.json()

        if result.get('status') and result['data']['status'] == 'success':
            # Update user payment status
            current_user.payment_status = 'verified'
            current_user.payment_date = func.now()
            db.session.commit()

            flash('Payment successful! Your account has been activated.',
                  category='success')
            return redirect(url_for('views.home'))
        else:
            flash(
                'Payment verification failed. Please try again or contact support.', category='error')
            return redirect(url_for('views.payment'))

    except Exception as e:
        flash(f'Error verifying payment: {str(e)}', category='error')
        return redirect(url_for('views.payment'))


@views.route('/payment-pending', methods=['GET'])
@login_required
def payment_pending():
    # Only show this if payment is pending
    if current_user.payment_status != 'pending':
        return redirect(url_for('views.home'))

    return render_template('payment_pending.html', user=current_user)


@views.route('/cashout', methods=['GET', 'POST'])
@login_required
def cashout():
    # Check payment status
    if current_user.payment_status != 'verified':
        flash('You must complete payment verification to request a cashout.',
              category='warning')
        return redirect(url_for('views.payment'))

    if request.method == 'POST':
        amount_str = request.form.get('amount')
        phone_number = request.form.get('phone_number', '').strip()
        recipient_name = request.form.get('recipient_name', '').strip()

        # Validate phone number
        if not phone_number or len(phone_number) < 10:
            flash('Please enter a valid phone number.', category='error')
            return redirect(url_for('views.cashout'))

        # Validate recipient name
        if not recipient_name or len(recipient_name) < 2:
            flash('Please enter a valid recipient name.', category='error')
            return redirect(url_for('views.cashout'))

        try:
            amount = float(amount_str)
            if amount <= 0:
                flash('Amount must be greater than 0.', category='error')
                return redirect(url_for('views.cashout'))

            # Check minimum amount of 30 GH₵
            if amount < 30:
                flash('Minimum cashout amount is GH₵30.00.', category='error')
                return redirect(url_for('views.cashout'))

            # Check if user has enough balance
            if amount > current_user.earnings_balance:
                flash(
                    f'Insufficient balance. You have GH₵{current_user.earnings_balance:.2f} available.', category='error')
                return redirect(url_for('views.cashout'))

            # Create cashout request
            cashout_req = CashoutRequest(
                user_id=current_user.id,
                amount=amount,
                phone_number=phone_number,
                recipient_name=recipient_name,
                status='pending',
                reason='User cashout request'
            )
            db.session.add(cashout_req)
            db.session.commit()

            # Deduct earnings from user
            current_user.earnings_balance -= amount
            # Store phone and recipient name in user profile
            current_user.phone_number = phone_number
            current_user.recipient_name = recipient_name
            db.session.commit()

            flash(
                f'Cashout request submitted: GH₵{amount:.2f}. Please wait for admin approval.', category='success')
            return redirect(url_for('views.home'))
        except ValueError:
            flash('Invalid amount. Please enter a valid number.', category='error')

    # Get user's cashout requests
    cashouts = CashoutRequest.query.filter_by(user_id=current_user.id).order_by(
        CashoutRequest.requested_at.desc()).all()
    available_amount = current_user.earnings_balance

    return render_template('cashout.html', user=current_user, cashouts=cashouts, available_amount=available_amount)
