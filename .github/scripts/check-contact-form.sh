#!/usr/bin/env bash
# Checks that the contact form on the live site can still send a message.
#
# It reads the form's address from the live page, then submits a test message
# the way the page script does: to FormSubmit's /ajax/ endpoint, as a request
# from the site. Every run that passes emails the form's recipient one message
# with "form health check" in the subject. FormSubmit has no way to accept a
# submission without sending it.
#
# Exits 0 if FormSubmit accepted the message, 1 otherwise, with the reason on
# the last line of output. See "Contact Form" in CLAUDE.md.
set -euo pipefail

SITE_URL="${SITE_URL:-https://sydneyaisafetyspace.org/}"
ATTEMPTS="${ATTEMPTS:-3}"
RETRY_DELAY="${RETRY_DELAY:-30}"
USER_AGENT="Mozilla/5.0 (compatible; sass-contact-form-check)"

fail() {
    echo "FAILED: $*"
    exit 1
}

page=$(curl --fail --silent --show-error --location --max-time 30 \
    --user-agent "$USER_AGENT" "$SITE_URL") ||
    fail "could not load $SITE_URL"

# The first <form class="contact-form"> on the page, whatever order its
# attributes are in.
action=$(python3 -c '
import sys
from html.parser import HTMLParser

class FormFinder(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and "contact-form" in (attrs.get("class") or "").split():
            print(attrs.get("action") or "")
            raise SystemExit

FormFinder().feed(sys.stdin.read())
' <<<"$page")

[[ -n "$action" ]] ||
    fail "$SITE_URL has no <form class=\"contact-form\"> with an action"
[[ "$action" == *formsubmit.co/* ]] ||
    fail "the form posts to $action, which is not FormSubmit; this check needs updating"

# The same rewrite the page script does.
endpoint="${action/formsubmit.co\//formsubmit.co/ajax/}"
echo "Form posts to $action"

run_url="${GITHUB_SERVER_URL:-}${GITHUB_SERVER_URL:+/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID}"
message="Automatic weekly check that the website contact form still delivers. No action needed.
If these emails stop arriving, the check has stopped running: see Contact Form in CLAUDE.md.
${run_url:+Sent by $run_url}"

answer=""
for attempt in $(seq 1 "$ATTEMPTS"); do
    answer=$(curl --silent --show-error --max-time 30 \
        --user-agent "$USER_AGENT" \
        --header "Accept: application/json" \
        --header "Referer: $SITE_URL" \
        --form "name=Form health check" \
        --form "email=no-reply@sydneyaisafetyspace.org" \
        --form "message=$message" \
        --form "_subject=Sydney AI Safety Space - form health check (automatic)" \
        --form "_template=table" \
        --form "_honey=" \
        "$endpoint" 2>&1) || true
    # FormSubmit answers HTTP 200 even when it rejects a submission; the
    # verdict is "success" in the JSON body.
    if [[ "$(jq -r '.success // empty' <<<"$answer" 2>/dev/null)" == "true" ]]; then
        echo "OK: FormSubmit accepted the test message (attempt $attempt)."
        exit 0
    fi
    echo "Attempt $attempt of $ATTEMPTS was not accepted: ${answer:0:300}"
    [[ "$attempt" == "$ATTEMPTS" ]] || sleep "$RETRY_DELAY"
done

fail "FormSubmit did not accept a message for $action. Its last answer: ${answer:0:300}"
