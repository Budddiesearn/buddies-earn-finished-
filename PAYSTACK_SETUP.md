# Paystack Mobile Money Payment Setup Guide

## Features Added

✅ **"Pay Now" Button** - Users can pay instantly with their mobile money number
✅ **Automatic Phone Prompt** - Users receive a USSD prompt on their phone to approve payment
✅ **Auto-Verification** - Payments are verified automatically, no manual admin approval needed
✅ **Fallback Option** - Manual payment still available if automated payment fails

## Setup Instructions

### 1. Create Paystack Account

1. Go to https://paystack.com/
2. Sign up for a free account
3. Complete business verification

### 2. Get API Keys

1. Login to Paystack Dashboard: https://dashboard.paystack.com/
2. Go to **Settings → API Keys & Webhooks**
3. Copy your **Secret Key** (starts with `sk_test_` or `sk_live_`)

### 3. Configure on Render

1. Go to your Render Dashboard
2. Click on your web service
3. Go to **Environment** tab
4. Add this environment variable:
   - Key: `PAYSTACK_SECRET_KEY`
   - Value: Your Paystack secret key (e.g., `sk_test_xxxxxxxxxxxxx`)
5. Click **Save Changes**
6. Render will automatically redeploy

### 4. Test the Payment

1. Use **Test Mode** first (keys starting with `sk_test_`)
2. Test mobile numbers:
   - `0551234567` - Success
   - `0551234568` - Failed
3. Once testing is complete, switch to **Live Keys** for real payments

## How It Works

1. **User enters mobile number** on payment page
2. **Clicks "Pay Now"** button
3. **Receives USSD prompt** on their phone (like \*170#)
4. **Approves payment** on phone
5. **Account automatically activated** - no admin verification needed!

## Payment Flow

```
User → Enters Phone Number → Clicks "Pay Now"
→ Paystack Sends USSD Prompt → User Approves
→ Payment Verified → Account Activated ✅
```

## Fees

- Paystack charges **1.5% + GHS 0.30** per transaction
- For GHS 50 payment, fee is about **GHS 1.05**
- You can absorb the fee or add it to the price

## Support

- Paystack Support: support@paystack.com
- Documentation: https://paystack.com/docs/payments/mobile-money/

## Fallback Option

If Paystack is not configured or fails:

- Users can still pay manually to the mobile money number
- Submit for admin verification (old method)
