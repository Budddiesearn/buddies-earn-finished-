# Deploy Flask App to Render

## Step 1: Prepare Your Code

✅ **Already Done:**

- ✓ Added `gunicorn` to requirements.txt
- ✓ Added `psycopg2-binary` for PostgreSQL support
- ✓ Updated app to use environment variables
- ✓ Configured production database settings

## Step 2: Push to GitHub

1. **Initialize Git** (if not already done):

   ```bash
   git init
   git add .
   git commit -m "Prepare for Render deployment"
   ```

2. **Create GitHub Repository:**

   - Go to https://github.com/new
   - Create a new repository (e.g., "flask-referral-app")
   - **Do NOT initialize with README** (you already have one)

3. **Push your code:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

## Step 3: Create PostgreSQL Database on Render

1. Go to https://render.com and sign in (or create account)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name:** `flask-app-db` (or any name)
   - **Database:** `flask_app`
   - **User:** (auto-generated)
   - **Region:** Choose closest to you
   - **Plan:** Free
4. Click **"Create Database"**
5. **IMPORTANT:** Copy the **Internal Database URL** (you'll need this in Step 4)

## Step 4: Deploy Web Service on Render

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure the web service:

   **Basic Settings:**

   - **Name:** `flask-referral-app` (or any name)
   - **Region:** Same as database
   - **Branch:** `main`
   - **Root Directory:** (leave blank)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn main:app`

   **Advanced Settings - Environment Variables:**
   Click **"Advanced"** → Add Environment Variables:

   | Key            | Value                                         |
   | -------------- | --------------------------------------------- |
   | `FLASK_ENV`    | `production`                                  |
   | `SECRET_KEY`   | (Generate a random string - see below)        |
   | `DATABASE_URL` | (Paste the Internal Database URL from Step 3) |

   **To generate SECRET_KEY**, run in terminal:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Plan:** Select **Free**
5. Click **"Create Web Service"**

## Step 5: Wait for Deployment

- Render will build and deploy your app (takes 2-5 minutes)
- Watch the logs for any errors
- Once you see "Build successful" and "Your service is live", you're done!

## Step 6: Access Your App

Your app will be available at:

```
https://YOUR_APP_NAME.onrender.com
```

## Important Notes

### Free Tier Limitations:

- ✓ Database: 90-day expiration (renew before expiration)
- ✓ Web service spins down after 15 minutes of inactivity
- ✓ First request after inactivity takes 30-50 seconds to wake up
- ✓ 750 hours/month (more than enough for one app)

### Database Persistence:

Your PostgreSQL database on Render will persist data even when the web service spins down. You'll only lose data if:

- You delete the database
- 90-day expiration passes (you'll get email reminders)

### Custom Domain (Optional):

- Go to your web service settings
- Click "Custom Domain"
- Add your domain and follow DNS instructions

## Troubleshooting

### If deployment fails:

1. **Check the logs** in Render dashboard
2. **Common issues:**
   - Missing environment variables
   - Wrong database URL format
   - Import errors (check all dependencies in requirements.txt)

### Database connection issues:

- Make sure you copied the **Internal Database URL**
- Verify DATABASE_URL is set correctly in environment variables
- Check database is in same region as web service

### App won't start:

- Verify start command is exactly: `gunicorn main:app`
- Check logs for Python errors
- Ensure all imports work correctly

## Updating Your App

To deploy updates:

```bash
git add .
git commit -m "Your update message"
git push
```

Render will automatically rebuild and redeploy!

## Need Help?

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
- Check deployment logs in Render dashboard
