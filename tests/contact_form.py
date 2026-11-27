"""Browser test for the contact form's page script on index.html.

FormSubmit is mocked, so this never sends anything: each case answers the
page's request with a canned response. It checks the messages under each
field, where focus goes, what FormSubmit text may reach the page, and that
without JavaScript the browser's own checks are still on.

Run from the repo root (needs uv, or Python with playwright installed):

    uv run --with playwright==1.58.0 python tests/contact_form.py
    uv run --with playwright==1.58.0 python tests/contact_form.py --shots DIR

The first run may need `playwright install chromium webkit`. WebKit (the
engine of every iPhone browser) is skipped if it is not installed.
--shots saves a 390 px screenshot of the form for each case.
"""

import functools
import http.server
import json
import pathlib
import sys
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
GENERAL = 'Sorry, your message could not be sent. Please email us directly instead.'
THANKS = 'Thanks - we will be in touch soon.'


def json_answer(success, message):
    return {'status': 200, 'content_type': 'application/json',
            'body': json.dumps({'success': success, 'message': message})}


OK = json_answer('true', 'The form was submitted successfully.')

# FormSubmit answers that must show only the general message.
HOSTILE = {
    'markup': '<img src=x onerror="document.title=1">Enter a valid email',
    'link': 'Please resend at evil.example',
    'address': 'Please email help@evil.example instead',
    'number': 'Call 1800 000 000 to finish sending',
    'two sentences': 'Rejected. Visit the help page',
    'too long': 'Enter a valid email ' + 'please ' * 10,
    'right-to-left override': 'Enter a valid ‮liame',
    'newline': 'Enter a valid email\nPlease call us',
    'activation (seen)': "This form needs Activation. We've sent you an email containing an "
                         "'Activate Form' link. Just click it and your form will be actived!",
    'no Referer (seen)': 'Make sure you open this page through a web server, FormSubmit will '
                         'not work in pages browsed as HTML files.',
}


def serve():
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Form:
    def __init__(self, page, base):
        self.page, self.base, self.sent, self.answer = page, base, [], OK
        self.dialogs = []
        page.route('https://formsubmit.co/**', self._fulfil)
        page.on('dialog', lambda d: (self.dialogs.append(d.message), d.dismiss()))

    def _fulfil(self, route):
        self.sent.append(route.request)
        answer = dict(self.answer)
        answer['headers'] = {'access-control-allow-origin': '*'}
        route.fulfill(**answer)

    def load(self):
        self.page.goto(self.base + '/index.html')
        self.sent.clear()

    def submit(self, name='Sam', email='sam@example.com', message='Hello', answer=OK):
        self.answer = answer
        self.page.fill('#cf-name', name)
        self.page.fill('#cf-email', email)
        self.page.fill('#cf-message', message)
        self.page.click('.contact-form button[type=submit]')

    def errors(self):
        return {f: self.page.locator(f'#cf-{f}-error').inner_text() if
                self.page.locator(f'#cf-{f}-error').is_visible() else ''
                for f in ('name', 'email', 'message')}

    def status(self):
        s = self.page.locator('.form-status')
        expect(s).not_to_have_text('Sending...')
        return s.inner_text().strip() if s.is_visible() else ''

    def focused(self):
        return self.page.evaluate('document.activeElement.id')

    def shot(self, shots, name):
        if shots:
            self.page.locator('#contact').screenshot(path=str(shots / f'{name}.png'))


def run(browser_type, device, base, shots, label):
    browser = browser_type.launch()
    try:
        context = browser.new_context(**device)
        form = Form(context.new_page(), base)
        form.load()
        failures = []

        def case(name, ok):
            print(f'  {"ok  " if ok else "FAIL"} {name}')
            if not ok:
                failures.append(name)

        # Field checks: nothing is sent, the message sits under the field,
        # focus goes to the first bad field, and screen readers get both.
        form.submit(name='', email='', message='')
        case('empty form: three messages, focus on Name, nothing sent',
             form.errors() == {'name': 'Enter your name', 'email': 'Enter a valid email',
                               'message': 'Enter a message'}
             and form.focused() == 'cf-name' and not form.sent and form.status() == '')
        expect(form.page.locator('#cf-name')).to_have_accessible_description('Enter your name')
        expect(form.page.locator('#cf-name')).to_have_attribute('aria-invalid', 'true')
        form.shot(shots, f'{label}-1-empty')

        for email in ('test', 'a@b', 'a@b.', 'sam@example .com'):
            form.load()
            form.submit(email=email)
            case(f'email {email!r}: "Enter a valid email", focus on Email, nothing sent',
                 form.errors() == {'name': '', 'email': 'Enter a valid email', 'message': ''}
                 and form.focused() == 'cf-email' and not form.sent)
            if email == 'test':
                form.shot(shots, f'{label}-2-bad-email')

        form.load()
        form.submit(name='   ', message=' \n ')
        case('spaces only in Name and Message: both flagged, focus on Name',
             form.errors() == {'name': 'Enter your name', 'email': '', 'message': 'Enter a message'}
             and form.focused() == 'cf-name' and not form.sent)

        form.page.fill('#cf-name', 'Sam')
        case('typing a name clears its message, leaves the other',
             form.errors() == {'name': '', 'email': '', 'message': 'Enter a message'}
             and form.page.get_attribute('#cf-name', 'aria-invalid') is None)

        # Sending.
        form.load()
        form.submit()
        case('good form: sent once, thanks shown', len(form.sent) == 1 and
             form.status().startswith(THANKS))

        form.load()
        form.submit(answer=json_answer('false', 'Too many submissions, try again later.'))
        case("plain reason from FormSubmit is shown",
             form.status() == 'Sorry, your message could not be sent (Too many submissions, '
                              'try again later). Please email us directly instead.')
        form.shot(shots, f'{label}-4-plain-reason')

        for name, message in HOSTILE.items():
            form.load()
            form.submit(answer=json_answer('false', message))
            html = form.page.inner_html('.form-status')
            case(f'FormSubmit text ({name}): general message only',
                 form.status() == GENERAL and '<img' not in html
                 and form.page.title() != '1' and not form.dialogs)
            if name == 'activation (seen)':
                form.shot(shots, f'{label}-5-general')

        for name, answer in {
            'message is not text': {'status': 200, 'content_type': 'application/json',
                                    'body': json.dumps({'success': 'false', 'message': ['x']})},
            'outage page': {'status': 503, 'content_type': 'text/html', 'body': '<h1>Down</h1>'},
            'success with an error status': {**OK, 'status': 500},
        }.items():
            form.load()
            form.submit(answer=answer)
            case(f'{name}: general message', form.status() == GENERAL)

        form.load()
        form.page.evaluate("document.querySelector('[name=_honey]').value = 'bot'")
        form.submit()
        case('honeypot filled: general message, nothing sent',
             form.status() == GENERAL and not form.sent)

        # Without JavaScript the browser's own required/type=email checks
        # must still be on (the script is what switches them off).
        nojs = browser.new_context(java_script_enabled=False, **device).new_page()
        nojs.goto(base + '/index.html')
        case('no JavaScript: browser checks still on',
             nojs.locator('.contact-form').get_attribute('novalidate') is None and
             nojs.locator('#cf-email:invalid').count() == 1)
        return failures
    finally:
        browser.close()


def main():
    shots = None
    if '--shots' in sys.argv:
        shots = pathlib.Path(sys.argv[sys.argv.index('--shots') + 1])
        shots.mkdir(parents=True, exist_ok=True)
    server = serve()
    base = f'http://127.0.0.1:{server.server_port}'
    failures = []
    with sync_playwright() as p:
        engines = [('chromium', p.chromium, {'viewport': {'width': 390, 'height': 844}})]
        engines.append(('webkit-iphone', p.webkit, p.devices['iPhone 15 Pro Max']))
        for label, browser_type, device in engines:
            print(label)
            try:
                failures += [f'{label}: {f}' for f in run(browser_type, device, base, shots, label)]
            except Exception as e:
                if label == 'webkit-iphone' and 'Executable doesn' in str(e):
                    print('  skipped: WebKit is not installed')
                else:
                    raise
    server.shutdown()
    print('\nall passed' if not failures else '\nFAILED:\n  ' + '\n  '.join(failures))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
