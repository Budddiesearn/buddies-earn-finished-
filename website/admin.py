from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import User, CashoutRequest, RewardConfig, ReferralEarning
from .auth import award_referral_rewards
from .email_utils import send_activation_email
from . import db

admin = Blueprint('admin', __name__, url_prefix='/admin')


def require_admin(f):
    """Decorator to require admin access."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin only.', category='error')
            return redirect(url_for('views.home'))
        return f(*args, **kwargs)
    return decorated_function


@admin.route('/dashboard', methods=['GET'])
@login_required
@require_admin
def dashboard():
    """Main admin dashboard with overview stats."""
    total_users = User.query.count()
    total_verified = User.query.filter_by(payment_status='verified').count()
    total_suspended = User.query.filter_by(is_suspended=True).count()
    total_banned = User.query.filter_by(is_banned=True).count()

    # Calculate total payouts (completed cashouts)
    total_payouts = db.session.query(db.func.sum(CashoutRequest.amount)).filter_by(
        status='completed').scalar() or 0

    # Get pending cashout requests
    pending_cashouts = CashoutRequest.query.filter_by(status='pending').all()

    # Get reward config
    rewards = RewardConfig.query.all()
    reward_dict = {r.level: r.amount for r in rewards}

    return render_template(
        'admin/dashboard.html',
        user=current_user,
        total_users=total_users,
        total_verified=total_verified,
        total_suspended=total_suspended,
        total_banned=total_banned,
        total_payouts=total_payouts,
        pending_cashouts=pending_cashouts,
        reward_dict=reward_dict,
    )


@admin.route('/users', methods=['GET'])
@login_required
@require_admin
def users():
    """View all users with status."""
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/users.html', user=current_user, users=users)


@admin.route('/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@require_admin
def user_detail(user_id):
    """View user details and referral tree."""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'suspend':
            user.is_suspended = True
            flash(f'User {user.email} suspended.', category='success')
        elif action == 'unsuspend':
            user.is_suspended = False
            flash(f'User {user.email} unsuspended.', category='success')
        elif action == 'ban':
            user.is_banned = True
            flash(f'User {user.email} banned.', category='success')
        elif action == 'unban':
            user.is_banned = False
            flash(f'User {user.email} unbanned.', category='success')
        db.session.commit()
        return redirect(url_for('admin.user_detail', user_id=user_id))

    # Get referral tree
    direct = user.get_referrals_by_level(1)
    level2 = user.get_referrals_by_level(2)
    level3 = user.get_referrals_by_level(3)

    # Get earnings
    earnings = ReferralEarning.query.filter_by(user_id=user_id).all()
    total_earned = sum(e.amount for e in earnings)

    # Get cashout requests
    cashout_requests = CashoutRequest.query.filter_by(user_id=user_id).all()

    return render_template(
        'admin/user_detail.html',
        user=current_user,
        detail_user=user,
        direct=direct,
        level2=level2,
        level3=level3,
        earnings=earnings,
        total_earned=total_earned,
        cashout_requests=cashout_requests,
    )


@admin.route('/cashouts', methods=['GET'])
@login_required
@require_admin
def cashouts():
    """View and manage cashout requests."""
    status = request.args.get('status', 'pending')
    cashout_requests = CashoutRequest.query.filter_by(status=status).all()
    return render_template('admin/cashouts.html', user=current_user, cashout_requests=cashout_requests, current_status=status)


@admin.route('/cashout/<int:cashout_id>/approve', methods=['POST'])
@login_required
@require_admin
def approve_cashout(cashout_id):
    """Approve a cashout request."""
    cashout = CashoutRequest.query.get_or_404(cashout_id)
    admin_note = request.form.get('admin_note', '')

    cashout.status = 'approved'
    cashout.processed_at = db.func.now()
    cashout.admin_note = admin_note
    db.session.commit()

    flash(f'Cashout request approved: GH₵{cashout.amount}', category='success')
    return redirect(url_for('admin.cashouts'))


@admin.route('/cashout/<int:cashout_id>/reject', methods=['POST'])
@login_required
@require_admin
def reject_cashout(cashout_id):
    """Reject a cashout request."""
    cashout = CashoutRequest.query.get_or_404(cashout_id)
    admin_note = request.form.get('admin_note', '')

    cashout.status = 'rejected'
    cashout.processed_at = db.func.now()
    cashout.admin_note = admin_note
    db.session.commit()

    flash(f'Cashout request rejected: GH₵{cashout.amount}', category='error')
    return redirect(url_for('admin.cashouts'))


@admin.route('/cashout/<int:cashout_id>/complete', methods=['POST'])
@login_required
@require_admin
def complete_cashout(cashout_id):
    """Mark cashout as completed (payment made)."""
    cashout = CashoutRequest.query.get_or_404(cashout_id)

    cashout.status = 'completed'
    cashout.processed_at = db.func.now()
    db.session.commit()

    flash(
        f'Cashout marked as completed: GH₵{cashout.amount}', category='success')
    return redirect(url_for('admin.cashouts'))


@admin.route('/rewards', methods=['GET', 'POST'])
@login_required
@require_admin
def rewards():
    """Manage reward configuration."""
    if request.method == 'POST':
        for level in [1, 2, 3]:
            amount_str = request.form.get(f'level_{level}_amount')
            if amount_str:
                amount = float(amount_str)
                config = RewardConfig.query.filter_by(level=level).first()
                if config:
                    config.amount = amount
                    config.updated_at = db.func.now()
                else:
                    config = RewardConfig(level=level, amount=amount)
                    db.session.add(config)
        db.session.commit()
        flash('Reward configuration updated.', category='success')
        return redirect(url_for('admin.rewards'))

    rewards = RewardConfig.query.all()
    reward_dict = {r.level: r.amount for r in rewards}
    return render_template('admin/rewards.html', user=current_user, reward_dict=reward_dict)


@admin.route('/statistics', methods=['GET'])
@login_required
@require_admin
def statistics():
    """View system statistics."""
    total_users = User.query.count()
    verified_users = User.query.filter_by(payment_status='verified').count()
    total_referrals = db.session.query(db.func.count(User.referred_by_id)).filter(
        User.referred_by_id != None).scalar()
    total_earnings = db.session.query(
        db.func.sum(ReferralEarning.amount)).scalar() or 0
    total_cashouts_pending = db.session.query(db.func.sum(
        CashoutRequest.amount)).filter_by(status='pending').scalar() or 0
    total_cashouts_completed = db.session.query(db.func.sum(
        CashoutRequest.amount)).filter_by(status='completed').scalar() or 0

    return render_template(
        'admin/statistics.html',
        user=current_user,
        total_users=total_users,
        verified_users=verified_users,
        total_referrals=total_referrals,
        total_earnings=total_earnings,
        total_cashouts_pending=total_cashouts_pending,
        total_cashouts_completed=total_cashouts_completed,
    )


@admin.route('/payment-verification', methods=['GET'])
@login_required
@require_admin
def payment_verification():
    """View pending payment verifications."""
    pending_users = User.query.filter_by(payment_status='pending').all()
    verified_users = User.query.filter_by(payment_status='verified').all()

    return render_template(
        'admin/payment_verification.html',
        user=current_user,
        pending_users=pending_users,
        verified_users=verified_users,
    )


@admin.route('/verify-payment/<int:user_id>', methods=['POST'])
@login_required
@require_admin
def verify_payment(user_id):
    """Approve a user's payment and grant dashboard access."""
    user = User.query.get(user_id)

    if not user:
        flash('User not found.', category='error')
        return redirect(url_for('admin.payment_verification'))

    if user.payment_status != 'pending':
        flash('This user\'s payment has already been processed.', category='warning')
        return redirect(url_for('admin.payment_verification'))

    user.payment_status = 'verified'
    db.session.commit()

    # Award referral rewards now that the user is verified
    award_referral_rewards(user)

    # Send activation email (best-effort)
    send_activation_email(user)

    flash(
        f'Payment verified for {user.first_name}. They now have dashboard access.', category='success')
    return redirect(url_for('admin.payment_verification'))


@admin.route('/reject-payment/<int:user_id>', methods=['POST'])
@login_required
@require_admin
def reject_payment(user_id):
    """Reject a user's payment."""
    user = User.query.get(user_id)

    if not user:
        flash('User not found.', category='error')
        return redirect(url_for('admin.payment_verification'))

    if user.payment_status != 'pending':
        flash('This user\'s payment has already been processed.', category='warning')
        return redirect(url_for('admin.payment_verification'))

    user.payment_status = 'rejected'
    db.session.commit()

    flash(f'Payment rejected for {user.first_name}.', category='success')
    return redirect(url_for('admin.payment_verification'))
