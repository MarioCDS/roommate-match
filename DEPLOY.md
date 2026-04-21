# Deploying NOVA Roomie to Streamlit Community Cloud

Free hosting with a public URL you can share.

## 1. Push the project to GitHub

From `C:\Users\mario\Desktop\roommate-match`:

```bash
git init
git add .
git commit -m "Initial NOVA Roomie"
git branch -M main
git remote add origin https://github.com/<your-username>/nova-roomie.git
git push -u origin main
```

The `.gitignore` already excludes `data/`, `.venv/`, `build/`, `dist/`, and cache files, so no secrets or build artefacts go up.

## 2. Deploy on Streamlit Cloud

1. Sign in at **https://share.streamlit.io** with your GitHub account.
2. Click **"New app"** \u2192 **"From existing repo"**.
3. Fill in:
   - **Repository:** `<your-username>/nova-roomie`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** pick a subdomain (e.g. `nova-roomie.streamlit.app`)
4. Click **"Deploy"**. First build takes ~2\u20133 minutes.

Streamlit Cloud reads `requirements.txt` automatically and installs `streamlit`, `requests`, `pillow` in an isolated environment. The `pyinstaller` dep is fine there too \u2014 just unused on the web.

## 3. Share

Your app is live at `https://<your-subdomain>.streamlit.app`. Send the link to classmates or the examiner.

## \u26a0\ufe0f Important: Data persistence on the cloud

Streamlit Community Cloud has an **ephemeral filesystem** \u2014 every time the app container restarts (redeploy, inactivity, server move), files under `data/` are wiped. That means:

- User accounts, profiles, and matches reset periodically.
- The demo-candidate pool is re-fetched from `randomuser.me` when the app wakes.

For a university demo this is fine \u2014 just tell graders to sign up during the session. If you needed real persistence you'd swap `storage.py` for a database (e.g. Supabase, Neon, or a small SQLite-on-S3 pattern).

## Troubleshooting

- **"ModuleNotFoundError" on boot** \u2192 check the module is in `requirements.txt`.
- **App sleeps after ~7 days of no visits** \u2192 Streamlit Cloud hibernates inactive apps. Visiting the URL wakes it (takes ~30 s).
- **Images don\u2019t load** \u2192 `randomuser.me` may be rate-limiting. Use the "Refresh candidates" button or wait a minute.
