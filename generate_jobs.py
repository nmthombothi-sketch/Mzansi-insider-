#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mzansi Insider Jobs Board Generator
------------------------------------
Fetches live South African job listings from the Adzuna API and generates
a static jobs.html page (plus category pages) styled to match the rest of
the site. Designed to run daily via GitHub Actions (see .github/workflows/
update-jobs.yml), but can also be run manually.

REQUIRED ENVIRONMENT VARIABLES:
    ADZUNA_APP_ID   - your Adzuna application ID
    ADZUNA_APP_KEY  - your Adzuna application key

Get these free at https://developer.adzuna.com/signup

USAGE:
    ADZUNA_APP_ID=xxx ADZUNA_APP_KEY=yyy python3 generate_jobs.py
"""
import os
import sys
import json
import time
import html
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

SITE_ROOT = os.environ.get("SITE_ROOT", ".")
APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
COUNTRY = "za"
RESULTS_PER_CATEGORY = 12          # jobs fetched per category per run
MAX_DESC_CHARS = 220               # trim long descriptions for the card view
CACHE_FILE = os.path.join(SITE_ROOT, "jobs_cache.json")  # fallback if API fails

# Categories to feature on the board. "query" is the Adzuna `what` search term;
# "label" is the display name; "slug" builds the per-category page filename.
CATEGORIES = [
    {"slug": "software-engineering", "label": "Software & IT",        "query": "software developer OR software engineer OR IT"},
    {"slug": "finance-accounting",   "label": "Finance & Accounting", "query": "accountant OR financial analyst OR bookkeeper"},
    {"slug": "engineering",          "label": "Engineering",          "query": "civil engineer OR mechanical engineer OR electrical engineer"},
    {"slug": "healthcare",           "label": "Healthcare",           "query": "nurse OR pharmacist OR healthcare"},
    {"slug": "education",            "label": "Education",           "query": "teacher OR tutor OR lecturer"},
    {"slug": "sales-marketing",      "label": "Sales & Marketing",    "query": "sales representative OR marketing"},
    {"slug": "admin-office",         "label": "Admin & Office",       "query": "administrator OR receptionist OR office"},
    {"slug": "skilled-trades",       "label": "Skilled Trades",       "query": "electrician OR artisan OR technician"},
]

# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_category(cat, retries=2):
    """Fetch one page of results for a category. Returns a list of job dicts."""
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": str(RESULTS_PER_CATEGORY),
        "what": cat["query"],
        "sort_by": "date",
        "content-type": "application/json",
    }
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1?" + urllib.parse.urlencode(params)

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])
        except urllib.error.HTTPError as e:
            print(f"  [warn] HTTP {e.code} fetching '{cat['slug']}' (attempt {attempt+1})", file=sys.stderr)
        except Exception as e:
            print(f"  [warn] error fetching '{cat['slug']}': {e} (attempt {attempt+1})", file=sys.stderr)
        time.sleep(2)
    return None  # signal failure so caller can fall back to cache


def fetch_all():
    """Fetch all categories. Returns dict {slug: [jobs]}. Uses cache as fallback
    per-category if a fetch fails, so one API hiccup doesn't blank the whole board."""
    if not APP_ID or not APP_KEY:
        print("ERROR: ADZUNA_APP_ID / ADZUNA_APP_KEY not set.", file=sys.stderr)
        sys.exit(1)

    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE))
        except Exception:
            cache = {}

    results = {}
    for cat in CATEGORIES:
        print(f"Fetching: {cat['label']} ...")
        jobs = fetch_category(cat)
        if jobs is None:
            print(f"  -> using cached data for '{cat['slug']}' (API fetch failed)")
            jobs = cache.get(cat["slug"], {}).get("jobs", [])
        results[cat["slug"]] = jobs
        time.sleep(1)  # be polite to the free-tier rate limit

    # Save fresh cache (only overwrite categories that succeeded with real data)
    cache_out = {}
    now = datetime.now(timezone.utc).isoformat()
    for cat in CATEGORIES:
        jobs = results[cat["slug"]]
        cache_out[cat["slug"]] = {"updated": now, "jobs": jobs}
    json.dump(cache_out, open(CACHE_FILE, "w"), indent=1)

    return results


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(s or "", quote=True)


def format_salary(job):
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if not lo and not hi:
        return None
    def fmt(n):
        return f"R{int(n):,}".replace(",", " ")
    if lo and hi and abs(lo - hi) > 1:
        return f"{fmt(lo)} - {fmt(hi)}"
    return fmt(lo or hi)


def format_date(job):
    created = job.get("created", "")
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        if days <= 0:
            return "Today"
        if days == 1:
            return "1 day ago"
        if days < 14:
            return f"{days} days ago"
        return dt.strftime("%d %b %Y")
    except Exception:
        return ""


def trim_desc(text):
    text = (text or "").strip()
    if len(text) <= MAX_DESC_CHARS:
        return text
    cut = text[:MAX_DESC_CHARS].rsplit(" ", 1)[0]
    return cut + "..."


def job_card_html(job, base_prefix=""):
    title = esc(job.get("title", "Untitled role"))
    company = esc((job.get("company") or {}).get("display_name", "Company not disclosed"))
    location = esc((job.get("location") or {}).get("display_name", "South Africa"))
    salary = format_salary(job)
    desc = esc(trim_desc(job.get("description", "")))
    apply_url = esc(job.get("redirect_url", "#"))
    posted = format_date(job)
    contract = esc((job.get("contract_type") or job.get("contract_time") or "").replace("_", " ").title())

    salary_html = f'<span class="job-salary">{esc(salary)}</span>' if salary else ""
    contract_html = f'<span class="job-tag">{contract}</span>' if contract else ""

    return f'''        <article class="job-card">
          <div class="job-card-top">
            <h3><a href="{apply_url}" target="_blank" rel="noopener nofollow sponsored">{title}</a></h3>
            {salary_html}
          </div>
          <div class="job-meta">
            <span class="job-company">{company}</span>
            <span class="job-loc">{location}</span>
            {contract_html}
            <span class="job-posted">{posted}</span>
          </div>
          <p class="job-desc">{desc}</p>
          <a href="{apply_url}" target="_blank" rel="noopener nofollow sponsored" class="job-apply">View &amp; Apply →</a>
        </article>'''


# ---------------------------------------------------------------------------
# Page generation
# ---------------------------------------------------------------------------

PAGE_HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <link rel="canonical" href="https://mzansiinsider.co.za/{canonical}">
  <link rel="stylesheet" href="{css_prefix}style.css">
  <link rel="icon" href="{css_prefix}favicon.ico" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="{css_prefix}favicon-32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="{css_prefix}favicon-16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="{css_prefix}apple-touch-icon.png">
  <link rel="manifest" href="{css_prefix}site.webmanifest">
  <script type="application/ld+json">
{schema}
  </script>
</head>
<body>
  <header class="masthead">
    <div class="masthead-inner">
      <div class="masthead-top">
        <div class="masthead-date" id="live-date"></div>
        <div class="logo"><a href="{css_prefix}index.html" style="text-decoration:none;"><div class="logo-name">Mzansi <em>Insider</em></div><div class="logo-rule"></div><div class="logo-sub">South Africa's Career &amp; Wealth Intelligence</div></a></div>
      </div>
      <nav class="nav-bar">
        <a href="{css_prefix}index.html">Home</a><a href="{css_prefix}salaries.html">Salaries</a><a href="{css_prefix}bursaries.html">Bursaries</a><a href="{css_prefix}careers.html">Careers</a><a href="{css_prefix}networth.html">Net Worth</a><a href="{css_prefix}jobs.html"{jobs_active}>Jobs</a>
      </nav>
    </div>
  </header>
  <main>
    <div class="wrap">
'''

PAGE_FOOT = '''    </div>
  </main>
  <footer>
    <div class="footer-inner">
      <div class="footer-top">
        <div><div class="footer-logo">Mzansi <em>Insider</em></div><div class="footer-sub">Career &amp; Wealth Intelligence</div></div>
        <div class="footer-cols">
          <div class="footer-col"><div class="footer-col-head">Intelligence</div><a href="{css_prefix}salaries.html">Salaries</a><a href="{css_prefix}careers.html">Career Guides</a><a href="{css_prefix}sidehustles.html">Side Hustles</a><a href="{css_prefix}networth.html">Net Worth</a></div>
          <div class="footer-col"><div class="footer-col-head">Opportunities</div><a href="{css_prefix}bursaries.html">Bursaries</a><a href="{css_prefix}learnerships.html">Learnerships</a><a href="{css_prefix}jobs.html">Jobs Board</a><a href="{css_prefix}reports.html">Market Reports</a></div>
          <div class="footer-col"><div class="footer-col-head">Mzansi Insider</div><a href="#">About</a><a href="#">Advertise</a><a href="#">Contact</a></div>
          <div class="footer-col"><div class="footer-col-head">Legal</div><a href="#">Privacy Policy</a><a href="#">Terms of Use</a><a href="#">POPIA Notice</a></div>
        </div>
      </div>
      <div class="footer-bottom"><span>&copy; 2026 Mzansi Insider (Pty) Ltd. All rights reserved. Job listings are sourced from third-party employers via the Adzuna API and refreshed daily; Mzansi Insider is not the employer and is not responsible for listing accuracy.</span><div><a href="#">Privacy</a><a href="#">Terms</a></div></div>
    </div>
  </footer>
  <script>const d=new Date();var el=document.getElementById('live-date');if(el)el.textContent=d.toLocaleDateString('en-ZA',{{weekday:'long',year:'numeric',month:'long',day:'numeric'}});</script>
</body>
</html>
'''


def build_schema(jobs_flat, page_url):
    """ItemList + JobPosting schema for the main jobs page (first 20 jobs)."""
    items = []
    for i, job in enumerate(jobs_flat[:20], start=1):
        posting = {
            "@type": "JobPosting",
            "title": job.get("title", ""),
            "description": trim_desc(job.get("description", "")) or job.get("title", ""),
            "datePosted": job.get("created", "")[:10],
            "hiringOrganization": {
                "@type": "Organization",
                "name": (job.get("company") or {}).get("display_name", "Undisclosed"),
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": (job.get("location") or {}).get("display_name", "South Africa"),
                    "addressCountry": "ZA",
                },
            },
        }
        sal = job.get("salary_min") or job.get("salary_max")
        if sal:
            posting["baseSalary"] = {
                "@type": "MonetaryAmount",
                "currency": "ZAR",
                "value": {"@type": "QuantitativeValue", "value": sal, "unitText": "YEAR"},
            }
        items.append({"@type": "ListItem", "position": i, "item": posting})

    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://mzansiinsider.co.za/index.html"},
            {"@type": "ListItem", "position": 2, "name": "Jobs", "item": page_url},
        ]},
        {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": items},
    ]
    return json.dumps(ld, indent=2, ensure_ascii=True)


def generate_main_page(results, updated_str):
    all_jobs = [j for cat in CATEGORIES for j in results[cat["slug"]]]
    total = len(all_jobs)

    filter_pills = "\n".join(
        f'          <a href="jobs/{c["slug"]}.html" class="job-pill">{esc(c["label"])} <span>({len(results[c["slug"]])})</span></a>'
        for c in CATEGORIES
    )

    sections = []
    for cat in CATEGORIES:
        jobs = results[cat["slug"]][:6]  # preview 6 per category on the main page
        if not jobs:
            continue
        cards = "\n".join(job_card_html(j) for j in jobs)
        sections.append(f'''      <div class="sec-head" style="margin-top:32px;"><h2>{esc(cat["label"])}</h2><span><a href="jobs/{cat["slug"]}.html">See all {esc(cat["label"])} jobs &rarr;</a></span></div>
      <div class="job-grid">
{cards}
      </div>''')
    sections_html = "\n".join(sections)

    title = "Jobs in South Africa 2026 — Live Vacancies Updated Daily | Mzansi Insider"
    desc = f"Browse {total}+ live South African job vacancies across tech, finance, engineering, healthcare, education and more — refreshed daily. Updated {updated_str}."
    schema = build_schema(all_jobs, "https://mzansiinsider.co.za/jobs.html")

    body = f'''      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="index.html">Home</a><span class="sep">/</span><span class="current">Jobs</span></nav>
      <div class="page-hero" style="border-bottom:none;padding-bottom:8px;">
        <div class="page-hero-label">Live Job Board &middot; Updated Daily</div>
        <h1>Jobs <em>in South Africa</em></h1>
        <p>{total}+ live vacancies from employers across South Africa, refreshed every day. Filter by field below, or browse our <a href="salaries.html" style="border-bottom:1px solid var(--black);">salary guides</a> to see what each role pays before you apply.</p>
        <p style="font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:var(--mid);margin-top:8px;">Last updated: {updated_str} &middot; Listings sourced via the Adzuna jobs API</p>
      </div>

      <div class="job-pills">
{filter_pills}
      </div>

{sections_html}

      <p style="font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:var(--mid);margin-top:32px;line-height:1.6;">Job listings on this page are sourced from third-party employers and job boards via the Adzuna API and refreshed daily. Mzansi Insider does not vet individual listings and is not the employer for any role shown &mdash; always verify a company and offer independently before sharing personal information or paying any fee to apply.</p>
'''
    html_out = PAGE_HEAD.format(title=esc(title), desc=esc(desc), canonical="jobs.html",
                                css_prefix="", schema=schema, jobs_active=' class="active"') + body + PAGE_FOOT.format(css_prefix="")
    with open(os.path.join(SITE_ROOT, "jobs.html"), "w") as f:
        f.write(html_out)
    print("Generated jobs.html")


def generate_category_pages(results, updated_str):
    jobs_dir = os.path.join(SITE_ROOT, "jobs")
    os.makedirs(jobs_dir, exist_ok=True)
    for cat in CATEGORIES:
        jobs = results[cat["slug"]]
        cards = "\n".join(job_card_html(j) for j in jobs) if jobs else '        <p style="font-family:\'IBM Plex Sans\',sans-serif;color:var(--mid);">No live listings for this category right now &mdash; check back tomorrow, or browse <a href="../jobs.html">all jobs</a>.</p>'

        other_pills = "\n".join(
            f'          <a href="{c["slug"]}.html" class="job-pill{" job-pill-active" if c["slug"]==cat["slug"] else ""}">{esc(c["label"])} <span>({len(results[c["slug"]])})</span></a>'
            for c in CATEGORIES
        )

        title = f'{cat["label"]} Jobs in South Africa 2026 — Live Vacancies | Mzansi Insider'
        desc = f'{len(jobs)}+ live {cat["label"].lower()} job vacancies in South Africa, refreshed daily. Updated {updated_str}.'
        schema = build_schema(jobs, f'https://mzansiinsider.co.za/jobs/{cat["slug"]}.html')

        body = f'''      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="../index.html">Home</a><span class="sep">/</span><a href="../jobs.html">Jobs</a><span class="sep">/</span><span class="current">{esc(cat["label"])}</span></nav>
      <div class="page-hero" style="border-bottom:none;padding-bottom:8px;">
        <div class="page-hero-label">Live Job Board &middot; Updated Daily</div>
        <h1>{esc(cat["label"])} Jobs <em>in South Africa</em></h1>
        <p>{len(jobs)} live {esc(cat["label"].lower())} vacancies, refreshed every day from employers across South Africa.</p>
        <p style="font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:var(--mid);margin-top:8px;">Last updated: {updated_str} &middot; Listings sourced via the Adzuna jobs API</p>
      </div>

      <div class="job-pills">
{other_pills}
      </div>

      <div class="job-grid" style="margin-top:24px;">
{cards}
      </div>

      <p style="font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:var(--mid);margin-top:32px;line-height:1.6;">Job listings on this page are sourced from third-party employers and job boards via the Adzuna API and refreshed daily. Mzansi Insider does not vet individual listings and is not the employer for any role shown &mdash; always verify a company and offer independently before sharing personal information or paying any fee to apply.</p>
'''
        html_out = PAGE_HEAD.format(title=esc(title), desc=esc(desc), canonical=f'jobs/{cat["slug"]}.html',
                                     css_prefix="../", schema=schema, jobs_active='') + body + PAGE_FOOT.format(css_prefix="../")
        with open(os.path.join(jobs_dir, f'{cat["slug"]}.html'), "w") as f:
            f.write(html_out)
        print(f"Generated jobs/{cat['slug']}.html ({len(jobs)} jobs)")


def main():
    print(f"Mzansi Insider Jobs Board Generator — {datetime.now(timezone.utc).isoformat()}")
    results = fetch_all()
    updated_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    generate_main_page(results, updated_str)
    generate_category_pages(results, updated_str)
    total = sum(len(v) for v in results.values())
    print(f"Done. {total} total listings across {len(CATEGORIES)} categories.")


if __name__ == "__main__":
    main()
