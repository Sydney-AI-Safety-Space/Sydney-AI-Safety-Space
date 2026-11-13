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
- To change the recipient, change the address in the `action` URL. FormSubmit
  emails the new address an activation link on the first submission from the
  live site; that submission is delivered once the link is clicked.
- Activation is per recipient and per site origin (taken from the request's
  `Referer`). `https://sydneyaisafetyspace.org` is activated. A submission
  from a local server asks for a separate activation, and a request with no
  `Referer` is rejected.
- The page script posts to the `/ajax/` version of the same URL. FormSubmit
  answers HTTP 200 even when it rejects a submission, so the script reads
  `success` from the JSON body.
- FormSubmit ignores its `_honey` honeypot field on the `/ajax/` endpoint, so
  the page script checks that field itself. Without JavaScript the form posts
  to the plain URL, where FormSubmit shows a reCAPTCHA page.
- To test delivery without a browser:
  `curl -X POST https://formsubmit.co/ajax/hunter@hunterjay.com -H 'Referer: https://sydneyaisafetyspace.org/' -F name=Test -F email=a@b.co -F message=Test`

## Deployment Notes
The site is served by GitHub Pages from `main` at https://sydneyaisafetyspace.org
(the `CNAME` file). `sydneyaisafetyspace.com` and both `www.` hosts redirect
there, so `.org` is the origin browsers send to third-party services.