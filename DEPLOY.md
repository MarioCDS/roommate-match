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

`.gitignore` already excludes `data/`, `.venv/`, and cache files, so no
secrets or build artefacts go up.

## 2. Deploy on Streamlit Cloud

1. Sign in at https://share.streamlit.io with your GitHub account.
2. Click "New app" → "From existing repo".
3. Fill in:
   - Repository: `<your-username>/nova-roomie`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: pick a subdomain (e.g. `nova-roomie.streamlit.app`)
4. Click "Deploy". First build takes ~2-3 minutes.

Streamlit Cloud reads `requirements.txt` and installs `streamlit`,
`requests`, and `pillow` in an isolated environment.

## 3. Share

Your app is live at `https://<your-subdomain>.streamlit.app`. Every
`git push origin main` triggers an auto-rebuild, usually live within
30-60 seconds.

## Important: data persistence on the cloud

Streamlit Community Cloud has an ephemeral filesystem. Every time the app
container restarts (redeploy, inactivity, server move), files under
`data/` are wiped. That means:

- User accounts, profiles, matches, and chats reset periodically.
- The demo-candidate pool is re-fetched from randomuser.me when the app
  wakes.

For a university demo this is fine - just tell graders to sign up during
the session. If you wanted real persistence you'd swap `storage.py` for a
database such as Supabase or Neon.

## Troubleshooting

- **ModuleNotFoundError on boot**: check the module is in `requirements.txt`.
- **App sleeps after ~7 days of no visits**: Streamlit Cloud hibernates
  inactive apps. Visiting the URL wakes it (takes ~30s).
- **Images don't load**: `randomuser.me` or `images.unsplash.com` may be
  rate-limiting. Use the Refresh candidates button.
