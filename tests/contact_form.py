"""Browser test for the contact form's page script on index.html.

Nothing leaves this machine: the browser asks for a made-up site whose
files are served straight from this repo, its requests to formsubmit.co
get canned answers, and every other request is blocked. It checks the
messages under each field, where focus goes, that FormSubmit's text never
reaches the page, and that without JavaScript the browser's own checks
are still on.

Run from the repo root (needs uv, or Python with playwright installed):

    uv run --with playwright==1.58.0 python tests/contact_form.py
    uv run --with playwright==1.58.0 python tests/contact_form.py --shots DIR

The first time, `uv run --with playwright==1.58.0 playwright install
chromium webkit`. WebKit (the engine of every iPhone browser) is skipped
if it is not installed. --shots saves a 390 px screenshot of the form for
each case.
"""

import json
import pathlib
import sys
import urllib.parse

from playwright.sync_api import expect, sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = 'http://site.test'
GENERAL = 'Sorry, your message could not be sent. Please email us directly instead.'
THANKS = 'Thanks - we will be in touch soon.'
ERROR_RED = 'rgb(255, 157, 157)'
FIELDS = ('name', 'email', 'message')
RIGHT_TO_LEFT_OVERRIDE = chr(0x202E)


def json_answer(success, message):
    return {'status': 200, 'content_type': 'application/json',
            'body': json.dumps({'success': success, 'message': message})}


OK = json_answer('true', 'The form was submitted successfully.')

# FormSubmit refusals. Whatever the text, the page shows only the general
# message: FormSubmit's text is untrusted, and plain words can mislead too.
REFUSALS = {
    'plain reason': 'Too many submissions, try again later.',
    'says it was sent': 'Your message was sent, you can ignore this',
    '"submitted successfully"': 'The form was submitted successfully.',
    'markup': '<img src=x onerror="document.title=1">Enter a valid email',
    'address': 'Please email help@evil.example instead',
    'right-to-left override': 'Enter a valid ' + RIGHT_TO_LEFT_OVERRIDE + 'liame',
    'activation (seen)': "This form needs Activation. We've sent you an email containing an "
                         "'Activate Form' link. Just click it and your form will be actived!",
    'no Referer (seen)': 'Make sure you open this page through a web server, FormSubmit will '
                         'not work in pages browsed as HTML files.',
}


def guard(context, on_formsubmit):
    """Serve SITE from the repo, hand formsubmit.co to the mock, block the
    rest. No real request is made, so even a changed form address fails
    the test instead of emailing anyone."""
    def route(r):
        url = r.request.url
        if url.startswith(SITE + '/'):
            path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip('/')
            file = (ROOT / path).resolve()
            if file.is_relative_to(ROOT) and file.is_file():
                r.fulfill(path=str(file))
            else:
                r.fulfill(status=404, body='')
        elif url.startswith('https://formsubmit.co/'):
            on_formsubmit(r)
        else:
            r.abort()
    context.route('**/*', route)


class Form:
    def __init__(self, context):
        self.sent, self.answer, self.dialogs, self.console_errors = [], OK, [], []
        guard(context, self._fulfil)
        self.page = context.new_page()
        self.page.on('dialog', lambda d: (self.dialogs.append(d.message), d.dismiss()))
        self.page.on('console', lambda m: m.type == 'error' and self.console_errors.append(m.text))

    def _fulfil(self, route):
        self.sent.append(route.request)
        answer = dict(self.answer)
        answer['headers'] = {'access-control-allow-origin': '*'}
        route.fulfill(**answer)

    def load(self):
        self.page.goto(SITE + '/index.html')
        self.sent.clear()
        self.console_errors.clear()

    def fill(self, name='Sam', email='sam@example.com', message='Hello'):
        self.page.fill('#cf-name', name)
        self.page.fill('#cf-email', email)
        self.page.fill('#cf-message', message)

    def submit(self, answer=OK, **fields):
        self.answer = answer
        self.fill(**fields)
        self.page.click('.contact-form button[type=submit]')

    def errors(self):
        """Each field's message, '' when its element is hidden."""
        return {f: '' if self.page.get_attribute(f'#cf-{f}-error', 'hidden') is not None
                else self.page.inner_text(f'#cf-{f}-error') or '(shown but empty)'
                for f in FIELDS}

    def status(self):
        s = self.page.locator('.form-status')
        expect(s).not_to_have_text('Sending...')
        return s.inner_text().strip() if s.is_visible() else ''

    def focused(self):
        return self.page.evaluate('document.activeElement.id')

    def border(self, field):
        return self.page.locator(f'#cf-{field}').evaluate('e => getComputedStyle(e).borderColor')

    def shot(self, shots, name):
        if shots:
            self.page.locator('#contact').screenshot(path=str(shots / f'{name}.png'))


def run(browser_type, device, shots, label):
    browser = browser_type.launch()
    try:
        form = Form(browser.new_context(**device))
        form.load()
        failures = []

        def case(name, ok):
            print(f'  {"ok  " if ok else "FAIL"} {name}')
            if not ok:
                failures.append(name)

        # Field checks: nothing is sent, the message sits under the field,
        # focus goes to the first bad field, and screen readers get both.
        form.fill(email='test')
        form.page.press('#cf-email', 'Tab')
        case('before Send, typing a bad email shows nothing',
             form.errors() == {f: '' for f in FIELDS})

        form.load()
        form.submit(name='', email='', message='')
        case('empty form: three messages, focus on Name, nothing sent',
             form.errors() == {'name': 'Enter your name', 'email': 'Enter a valid email',
                               'message': 'Enter a message'}
             and form.focused() == 'cf-name' and not form.sent and form.status() == '')
        for f in FIELDS:
            expect(form.page.locator(f'#cf-{f}')).to_have_accessible_description(
                form.errors()[f])
            expect(form.page.locator(f'#cf-{f}')).to_have_attribute('aria-invalid', 'true')
            expect(form.page.locator(f'#cf-{f}-error')).to_have_role('alert')
        case('the focused bad field shows focus, not the error red',
             form.border('name') != ERROR_RED and form.border('email') == ERROR_RED)
        form.shot(shots, f'{label}-1-empty')

        form.load()
        form.submit(message='')
        case('empty message: focus on Message, which shows focus, not red',
             form.focused() == 'cf-message' and form.border('message') != ERROR_RED)

        for email in ('test', 'a@b', 'a@b.', 'sam@example .com'):
            form.load()
            form.submit(email=email)
            case(f'email {email!r}: "Enter a valid email", focus on Email, nothing sent',
                 form.errors() == {'name': '', 'email': 'Enter a valid email', 'message': ''}
                 and form.focused() == 'cf-email' and not form.sent)
            if email == 'test':
                form.shot(shots, f'{label}-2-bad-email')

        # Typing in a field that is still wrong must not touch its message:
        # each rewrite of an alert is read out again.
        form.page.evaluate("""() => { window.rewrites = 0;
            new MutationObserver(m => window.rewrites += m.length).observe(
                document.querySelector('#cf-email-error'),
                {childList: true, characterData: true, subtree: true, attributes: true}); }""")
        form.page.type('#cf-email', 'xy')
        form.page.press('#cf-email', 'Tab')
        case('typing in a still-bad field leaves its message untouched',
             form.page.evaluate('window.rewrites') == 0 and
             form.errors()['email'] == 'Enter a valid email')

        # A phone's Go key, or Enter, in the bad field itself: focus does
        # not move, so the message must be an alert to be announced.
        form.load()
        form.fill(email='test')
        form.page.press('#cf-email', 'Enter')
        case('Enter in a bad email field: message shown, nothing sent',
             form.errors()['email'] == 'Enter a valid email' and
             form.focused() == 'cf-email' and not form.sent)

        form.page.evaluate("""() => { const e = document.querySelector('#cf-email');
            e.value = 'sam@example.com'; e.dispatchEvent(new Event('change')); }""")
        case('autofill with only a change event clears the message',
             form.errors()['email'] == '' and
             form.page.get_attribute('#cf-email', 'aria-invalid') is None)

        form.load()
        form.submit(name='   ', message=' \n ')
        case('spaces only in Name and Message: both flagged, focus on Name',
             form.errors() == {'name': 'Enter your name', 'email': '', 'message': 'Enter a message'}
             and form.focused() == 'cf-name' and not form.sent)

        form.page.fill('#cf-name', 'Sam')
        case('typing a name clears and hides its message, leaves the other',
             form.errors() == {'name': '', 'email': '', 'message': 'Enter a message'}
             and form.page.get_attribute('#cf-name', 'aria-invalid') is None)

        # Sending.
        form.load()
        form.submit()
        case('good form: sent once, thanks shown, form cleared, no field messages',
             len(form.sent) == 1 and form.status().startswith(THANKS) and
             form.errors() == {f: '' for f in FIELDS} and
             form.page.input_value('#cf-email') == '')

        for name, message in REFUSALS.items():
            form.load()
            form.submit(answer=json_answer('false', message))
            case(f'FormSubmit refuses ({name}): general message only, reason in console',
                 form.status() == GENERAL and form.page.title() != '1' and not form.dialogs
                 and form.page.locator('.form-status *').count() == 1
                 and any(message in e for e in form.console_errors))
            if name == 'plain reason':
                form.shot(shots, f'{label}-3-refused')

        form.fill(email='test')
        form.page.click('.contact-form button[type=submit]')
        case('a field problem after a failure hides the old failure line',
             form.status() == '' and form.errors()['email'] == 'Enter a valid email')

        for name, answer in {
            'message is not text': {'status': 200, 'content_type': 'application/json',
                                    'body': json.dumps({'success': 'false', 'message': ['x']})},
            'no verdict at all': {'status': 200, 'content_type': 'application/json', 'body': '{}'},
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
        nojs_context = browser.new_context(java_script_enabled=False, **device)
        guard(nojs_context, lambda r: r.abort())
        nojs = nojs_context.new_page()
        nojs.goto(SITE + '/index.html')
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
    failures = []
    with sync_playwright() as p:
        engines = [('chromium', p.chromium, {'viewport': {'width': 390, 'height': 844}})]
        engines.append(('webkit-iphone', p.webkit, p.devices['iPhone 15 Pro Max']))
        for label, browser_type, device in engines:
            print(label)
            try:
                failures += [f'{label}: {f}' for f in run(browser_type, device, shots, label)]
            except Exception as e:
                if label == 'webkit-iphone' and 'Executable doesn' in str(e):
                    print('  skipped: WebKit is not installed')
                else:
                    raise
    print('\nall passed' if not failures else '\nFAILED:\n  ' + '\n  '.join(failures))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
