#!/usr/bin/env python3
"""Build the support site from apps.json into docs/ (served by GitHub Pages).

Usage: python3 build.py
"""
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
DATA = json.loads((ROOT / "apps.json").read_text())
SITE = DATA["site"]
APPS = DATA["apps"]
BASE = SITE["base"].rstrip("/")
EMAIL = SITE["email"]
PUB = SITE["publisher"]
EULA = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"


def esc(s):
    return html.escape(s, quote=True)


def rich(s):
    """Escape text, then turn [label](https://url) into links."""
    out = esc(s)
    return re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        out,
    )


def nice_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def store_url(app):
    return f"https://apps.apple.com/app/id{app['store_id']}"


def mail():
    return f'<a href="mailto:{EMAIL}">{EMAIL}</a>'


NAV = [("Home", "/"), ("Apps", "/apps/"), ("Privacy", "/privacy/"), ("Terms", "/terms/"), ("Contact", "/contact/")]


CUR = ' aria-current="page"'


def page(path, title, body, desc, active="", canonical=None):
    nav = "".join(
        f'<a href="{BASE}{href}"{CUR if label == active else ""}>{label}</a>'
        for label, href in NAV
    )
    full_title = title if title == SITE["title"] else f"{title} | {SITE['title']}"
    canon = canonical or path
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE['url']}{canon}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="{BASE}/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}/assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap bar">
    <a class="brand" href="{BASE}/">{esc(PUB)} <span>Apps</span></a>
    <nav aria-label="Main">{nav}</nav>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>Support: {mail()}</p>
    <p><a href="{BASE}/privacy/">Privacy</a> · <a href="{BASE}/terms/">Terms of Use</a> · <a href="{BASE}/contact/">Contact</a></p>
    <p class="muted">&copy; {SITE['year']} {esc(PUB)}.</p>
  </div>
</footer>
</body>
</html>
"""
    target = OUT / path.strip("/") / "index.html" if path != "/404" else OUT / "404.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc)


def icon(app, size=64, cls="icon"):
    return (f'<img class="{cls}" src="{BASE}/{app["icon"]}" width="{size}" height="{size}" '
            f'alt="{esc(app["name"])} app icon" loading="lazy" decoding="async">')


def store_button(app):
    if app.get("live") and app.get("store_id"):
        return f'<a class="btn" href="{store_url(app)}">View on the App Store</a>'
    return '<span class="btn btn-soon" aria-disabled="true">Coming soon to the App Store</span>'


def app_cards(apps):
    cards = []
    for a in apps:
        badge = "" if a.get("live") else '<span class="badge">Coming soon</span>'
        cards.append(f"""<a class="card app-card" href="{BASE}/apps/{a['slug']}/">
  {icon(a, 64)}
  <span class="card-text"><strong>{esc(a['name'])}</strong>{badge}<span class="muted">{esc(a['summary'])}</span></span>
</a>""")
    return '<div class="grid">' + "\n".join(cards) + "</div>"


def glance(a):
    d = a["data"]
    rows = [
        ("Account required", "No" if not d["account"] else "Yes"),
        ("Ads", d["ads"]),
        ("Tracking permission prompt", "Yes, optional" if d["tracking_prompt"] else "No"),
        ("Google consent form (where required)", "Yes" if d["consent_form"] else "Not applicable"),
        ("In-app purchases", ", ".join(a["purchases"])),
        ("Subscription", "No" if not d["subscription"] else "Yes"),
        ("iCloud sync", "Yes, your own iCloud" if d["icloud"] else "No"),
        ("Data sent to us", "None"),
    ]
    trs = "".join(f"<tr><th scope=\"row\">{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows)
    return f'<table class="glance"><caption>At a glance</caption>{trs}</table>'


def build_app(a, slug, canonical_slug):
    lists = ""
    for block in a.get("lists", []):
        inner = "".join(f"<p>{rich(t)}</p>" for t in block.get("text", []))
        if block.get("items"):
            inner += "<ul>" + "".join(f"<li>{rich(i)}</li>" for i in block["items"]) + "</ul>"
        lists += f"<section><h2>{esc(block['title'])}</h2>{inner}</section>"
    pr = a["pricing"]
    pricing = "".join(f"<p>{rich(t)}</p>" for t in pr.get("text", []))
    if pr.get("items"):
        pricing += "<ul>" + "".join(f"<li>{rich(i)}</li>" for i in pr["items"]) + "</ul>"
    pricing += "".join(f"<p>{rich(t)}</p>" for t in pr.get("after", []))
    faq = "".join(f"<details><summary>{esc(f['q'])}</summary><p>{rich(f['a'])}</p></details>" for f in a["faq"])
    header = ""
    if a.get("header"):
        header = (f'<img class="hero-art" src="{BASE}/{a["header"]}" alt="" width="1600" height="686" '
                  f'decoding="async">')
    intro = "".join(f"<p>{rich(t)}</p>" for t in a["intro"])
    body = f"""{header}
<div class="app-head">
  {icon(a, 112, "icon icon-lg")}
  <div>
    <h1>{esc(a['name'])}</h1>
    <p class="tagline">{esc(a['tagline'])}</p>
    <p class="muted small">{esc(a['category'])} · iPhone · Version {esc(a['version'])}</p>
  </div>
</div>
<div class="actions">{store_button(a)}<a class="btn btn-ghost" href="{BASE}/privacy/{slug}/">Privacy Policy</a><a class="btn btn-ghost" href="mailto:{EMAIL}?subject={esc(a['name'])}%20support">Email support</a></div>
<div class="prose">
{intro}
{lists}
<section><h2>Pricing</h2>{pricing}</section>
<section><h2>Help and FAQ</h2>{faq}
<details><summary>How do I contact support?</summary><p>Email {mail()} with your iPhone model, iOS version and what happened. We usually reply within 2 to 3 business days.</p></details>
</section>
<p class="muted small">See also the <a href="{BASE}/terms/">Terms of Use</a>.</p>
</div>"""
    page(f"/apps/{slug}/", a["name"], body, f"{a['name']}: {a['tagline']} Help, FAQ and support.",
         "Apps", canonical=f"/apps/{canonical_slug}/")


def build_privacy(a, slug, canonical_slug):
    p = a["privacy"]
    secs = "".join(
        f"<section><h2>{esc(s['h'])}</h2>" + "".join(f"<p>{rich(t)}</p>" for t in s["p"]) + "</section>"
        for s in p["sections"]
    )
    body = f"""<div class="app-head">
  {icon(a, 72)}
  <div>
    <h1>{esc(a['name'])} Privacy Policy</h1>
    <p class="muted">Last updated: {nice_date(p['updated'])}</p>
  </div>
</div>
<div class="prose">
<p>{esc(a['name'])} is made by {esc(PUB)}. This policy explains what happens to your information when you use {esc(a['name'])}.</p>
{glance(a)}
{secs}
<section><h2>Changes</h2><p>If this policy changes, the updated version will be posted on this page with a new "Last updated" date.</p></section>
<section><h2>Contact</h2><p>Questions or privacy requests: {mail()}</p></section>
<p class="muted small"><a href="{BASE}/apps/{canonical_slug}/">{esc(a['name'])} support</a> · <a href="{BASE}/privacy/">All privacy policies</a></p>
</div>"""
    page(f"/privacy/{slug}/", f"{a['name']} Privacy Policy", body,
         f"Privacy policy for {a['name']} by {PUB}.", "Privacy", canonical=f"/privacy/{canonical_slug}/")


def build_static():
    updated = nice_date(SITE["updated"])
    page("/", SITE["title"], f"""<section class="hero">
  <h1>Support for apps by {esc(PUB)}</h1>
  <p class="lead">Help, privacy policies and contact information for every app.</p>
  <div class="actions"><a class="btn" href="{BASE}/apps/">Browse apps</a><a class="btn btn-ghost" href="{BASE}/contact/">Contact support</a></div>
</section>
<h2>Apps</h2>
{app_cards(APPS)}
<h2>Quick help</h2>
<div class="grid help">
  <div class="card"><strong>Restore a purchase</strong><p class="muted">Open the app's shop or Settings and tap Restore Purchases, signed in with the same Apple Account you bought with.</p></div>
  <div class="card"><strong>Manage a subscription</strong><p class="muted">On your iPhone open Settings, tap your name, then Subscriptions.</p></div>
  <div class="card"><strong>Ask for a refund</strong><p class="muted">Apple handles all payments. Request a refund at <a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a>.</p></div>
  <div class="card"><strong>Still stuck?</strong><p class="muted">Email {mail()}.</p></div>
</div>""", f"Support, privacy and contact information for apps by {PUB}.", "Home")

    page("/apps/", "Apps", f"""<h1>Apps by {esc(PUB)}</h1>
<p class="lead">Tap an app for features, help and its privacy policy.</p>
{app_cards(APPS)}""", f"All apps by {PUB}.", "Apps")

    plist = "".join(f'<li><a href="{BASE}/privacy/{a["slug"]}/">{esc(a["name"])}</a></li>' for a in APPS)
    page("/privacy/", "Privacy Policy", f"""<h1>Privacy Policy</h1>
<p class="muted">Last updated: {updated}</p>
<div class="prose">
<p>Each app by {esc(PUB)} has its own privacy policy, listed below. That page is the one that applies to the app you use.</p>
<h2>In general</h2>
<ul>
<li>No accounts and no servers run by us. Your data stays on your device, or in your own iCloud account where an app says so.</li>
<li>We don't sell, rent or trade personal information, and we don't run our own analytics.</li>
<li>Some games and apps show ads through Google AdMob. Where required by law, Google's consent form is shown first, and Apple's App Tracking Transparency prompt lets you allow or decline tracking. Declining never removes features.</li>
<li>Purchases are processed by Apple. We never see your payment details.</li>
<li>Our apps are not directed to children under 13.</li>
</ul>
<h2>App privacy policies</h2>
<ul class="link-list">{plist}</ul>
<p>Questions or privacy requests: {mail()}</p>
</div>""", f"Privacy policies for apps by {PUB}.", "Privacy")

    page("/terms/", "Terms of Use", f"""<h1>Terms of Use</h1>
<p class="muted">Last updated: {updated}</p>
<div class="prose">
<p>These terms apply to every app by {esc(PUB)} on the Apple App Store.</p>
<h2>License</h2><p>Your use of our apps is governed by Apple's <a href="{EULA}">Standard Licensed Application End User License Agreement</a>. By downloading or using an app, you agree to that agreement and these terms.</p>
<h2>One-time purchases</h2><p>One-time purchases unlock content or features permanently on your Apple Account. Use Restore Purchases in the app on a new device. Consumable items, such as coin or currency packs, are used up and can't be restored.</p>
<h2>Subscriptions</h2><p>Where an app offers an auto-renewing subscription, payment is charged to your Apple Account at confirmation of purchase. It renews unless cancelled at least 24 hours before the end of the current period. Manage or cancel it in Settings > [your name] > Subscriptions.</p>
<h2>Ads</h2><p>Some apps show ads served by Google AdMob, including optional reward videos. Each app's privacy policy explains its ads and your choices.</p>
<h2>Refunds</h2><p>Apple processes all payments, so refund requests go through Apple at <a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a>.</p>
<h2>Health, fitness and informational content</h2><p>Fitness Test Pro Elite and other informational apps provide general information, not medical advice. Talk to a medical professional before starting a new fitness program. Fitness Test Pro Elite is independent and not affiliated with, endorsed by or sponsored by any military branch, the Department of Defense, the Department of Homeland Security or any government agency.</p>
<h2>Games</h2><p>Companies, people and products in our games are fictional.</p>
<h2>Privacy</h2><p>Each app has its own policy on the <a href="{BASE}/privacy/">Privacy Policy</a> page.</p>
<h2>Changes</h2><p>We may update these terms; the "Last updated" date shows the latest change.</p>
<h2>Contact</h2><p>{mail()}</p>
</div>""", f"Terms of Use for apps by {PUB}.", "Terms")

    page("/contact/", "Contact", f"""<h1>Contact and support</h1>
<div class="prose">
<p class="lead">Email {mail()} for questions, bug reports, feedback and privacy requests. We usually reply within 2 to 3 business days.</p>
<h2>Help us help you</h2>
<ul>
<li>The app name and version (shown on the App Store page or in the app's Settings or About screen)</li>
<li>Your iPhone model and iOS version</li>
<li>What you expected, what happened, and a screenshot if you can</li>
</ul>
<h2>Purchases</h2>
<ul>
<li>Restore: open the app's shop or Settings and tap Restore Purchases with the same Apple Account.</li>
<li>Subscriptions: on your iPhone open Settings, tap your name, then Subscriptions.</li>
<li>Refunds: Apple handles all payments. Request one at <a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a>.</li>
</ul>
</div>""", f"Contact support for apps by {PUB}.", "Contact")

    page("/404", "Page not found", f"""<h1>Page not found</h1>
<p class="lead">That page doesn't exist. Try the <a href="{BASE}/apps/">apps list</a> or email {mail()}.</p>""",
         "Page not found.")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")
    build_static()
    for a in APPS:
        for slug in [a["slug"], *a.get("aliases", [])]:
            build_app(a, slug, a["slug"])
            build_privacy(a, slug, a["slug"])
    count = len(list(OUT.rglob("*.html")))
    print(f"Built {count} pages into {OUT}")


if __name__ == "__main__":
    main()
