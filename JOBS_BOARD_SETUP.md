# Jobs Board Setup — 2 Steps, About 5 Minutes

Your site now has a live jobs board system built in. It refreshes automatically
every day once you complete two one-time setup steps. Everything else is
already built and automated.

## What's already done for you
- `generate_jobs.py` — fetches live SA job listings from the Adzuna API and
  builds `jobs.html` plus 8 category pages under `/jobs/` (Software & IT,
  Finance & Accounting, Engineering, Healthcare, Education, Sales & Marketing,
  Admin & Office, Skilled Trades), styled to match the rest of the site.
- `.github/workflows/update-jobs.yml` — a GitHub Actions workflow that runs
  the script automatically every day at 06:00 South African time, and commits
  the refreshed pages back to your repository. Cloudflare Pages then
  auto-deploys the update, same as any other change to your repo.
- Every page on the site already links to Jobs in the navigation.
- A placeholder `jobs.html` is live now so the nav link never breaks — it's
  automatically replaced the first time the script runs successfully.

## Step 1 — Get free Adzuna API credentials (2 minutes)
1. Go to https://developer.adzuna.com/signup and create a free account.
2. Once logged in, you'll see your Application ID and Application Key on your
   account/dashboard page. Copy both.

## Step 2 — Add them to GitHub as secrets (3 minutes)
This lets the automated daily job run without ever exposing your keys in the
code itself.

1. In your GitHub repository, go to Settings -> Secrets and variables ->
   Actions.
2. Click "New repository secret".
   - Name: ADZUNA_APP_ID -- Value: (paste your Application ID)
   - Click "Add secret".
3. Click "New repository secret" again.
   - Name: ADZUNA_APP_KEY -- Value: (paste your Application Key)
   - Click "Add secret".

That's it. The workflow will run automatically at the next scheduled time
(06:00 SAST daily). To see it work immediately instead of waiting:

1. Go to the Actions tab in your GitHub repository.
2. Click "Update Jobs Board" in the left sidebar.
3. Click "Run workflow" -> "Run workflow" (green button).
4. Wait about a minute, then refresh -- you'll see a new commit appear with
   the real, live jobs.html and /jobs/ category pages.
5. Cloudflare Pages will pick up that commit and deploy it automatically,
   same as any other update to your site.

## Ongoing maintenance -- what to actually keep an eye on
This is the one part of your site with a moving part, so it's worth knowing
what "healthy" looks like:
- Check the Actions tab occasionally. A green checkmark next to the daily
  run means it worked. A red X means it failed -- click into it to see why
  (usually an expired/incorrect API key, or Adzuna's free-tier rate limit).
- The script is built to fail safely: if the Adzuna API is briefly
  unreachable, it falls back to yesterday's cached listings (from
  jobs_cache.json) rather than showing a blank page. But if it fails for
  several days in a row, your listings will visibly go stale -- worth checking
  in every couple of weeks.
- Adzuna's free tier has usage limits. The script currently fetches 8
  categories x 12 jobs once a day, which is a light, well-within-free-tier
  load. If you want more categories or more jobs per category later, check
  Adzuna's current free-tier limits first.

## Customizing categories
Open generate_jobs.py and edit the CATEGORIES list near the top. Each entry
needs a slug (used in the URL), a label (shown to users), and a query (the
search term sent to Adzuna). Add, remove, or reword categories freely -- the
page generation adapts automatically.
