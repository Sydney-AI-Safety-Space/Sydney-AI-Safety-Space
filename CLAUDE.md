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

## Deployment Notes
This appears to be deployed as a static site with the domain sydneyaisafetyspace.com.