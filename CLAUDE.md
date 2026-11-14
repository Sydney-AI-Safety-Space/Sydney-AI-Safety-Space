# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a static website for the Sydney AI Safety Space, a volunteer-run coworking space. The project consists of:
- A simple HTML site with minimal dependencies
- Dark theme CSS styling
- No build process or compilation steps required

## Project Structure

- `index.html` - Main HTML page
- `static/css/style.css` - Dark theme stylesheet with CSS variables
- `static/favicon.ico` - Site favicon

## Development

### Running the Site
Since this is a static site, you can:
- Open `index.html` directly in a browser for local development
- Use any static file server (e.g., `python -m http.server 8000` or `npx serve`)

### CSS Architecture
The CSS uses CSS custom properties (variables) for theming:
- Colors are defined in `:root` for easy theme customization
- Responsive design with mobile breakpoint at 640px
- Uses flexbox for layout

## Contact Form
The contact form on `index.html` posts to FormSubmit (formsubmit.co), which
emails each submission to the address in the form's `action` URL
(`hunter@hunterjay.com`). There is no account or dashboard to configure.
- To change the recipient, change the address in the `action` URL, and in the
  `mailto:` links and the two status messages in the page script. Then send
  the first submission from the live site yourself: FormSubmit emails the new
  address an activation link, and until it is clicked every visitor sees the
  "could not be sent" error. The held submission is delivered once the link
  is clicked.
- Activation is per recipient and per site origin (taken from the request's
  `Referer`). `https://sydneyaisafetyspace.org` is activated. A submission
  from a local server asks for a separate activation, and a request with no
  `Referer` is rejected.
- The page script posts to the `/ajax/` version of the same URL. FormSubmit
  answers HTTP 200 even when it rejects a submission, so the script reads
  `success` from the JSON body.
- FormSubmit ignores its `_honey` honeypot field on the `/ajax/` endpoint, so
  the page script checks that field itself. Without JavaScript the form posts
  to the plain URL, where FormSubmit shows a reCAPTCHA page and then its own
  thank-you page.
- A weekly GitHub Action (`.github/workflows/contact-form-check.yml`) sends a
  test message through the live form and opens an issue, "Contact form check
  failed", if FormSubmit does not accept it. The issue closes itself when the
  check passes again. The check reads the form's address from the live page,
  so it follows a change of recipient without being edited.
  - Each passing run emails the recipient one message with "form health
    check" in the subject. FormSubmit cannot accept a submission without
    sending it (its `_blacklist` field, like `_honey`, is ignored on
    `/ajax/`). If those emails stop, the check has stopped.
  - GitHub switches off scheduled workflows in a public repository after 60
    days without activity. The check opens a second issue at 45 days. Do not
    add a job that commits to keep it alive; re-enable it from the Actions
    tab if it stops.
  - It checks that FormSubmit accepts a message, not that the email reaches
    the inbox, and not the page script (use a browser for that).
  - After changing the form, do not wait for Monday: run it by hand (Actions,
    Contact Form Check, Run workflow).
  - A PR that changes the check's own files also runs it once, so it sends
    one of those emails off schedule. That includes Dependabot's.
  - To test the alert: run the workflow by hand (Actions, Contact Form Check,
    Run workflow) with `site_url` set to a page with no contact form, such as
    `https://sydneyaisafetyspace.org/events.html`. Run it again with the
    field empty to close the issue.
- To test delivery without a browser (this emails the recipient):
  `curl -X POST https://formsubmit.co/ajax/hunter@hunterjay.com -H 'Accept: application/json' -H 'Referer: https://sydneyaisafetyspace.org/' -F name=Test -F email=a@b.co -F message=Test`

## Deployment Notes
The site is served by GitHub Pages from `main` at https://sydneyaisafetyspace.org
(the `CNAME` file). `sydneyaisafetyspace.com` and both `www.` hosts redirect
there, so `.org` is the origin browsers send to third-party services.