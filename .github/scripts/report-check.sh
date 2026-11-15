#!/usr/bin/env bash
# Turns the result of check-contact-form.sh into GitHub issues, so a failure
# reaches people instead of sitting in a workflow log. Each issue is opened
# once, gets a comment on every later failing run, and closes itself when the
# problem goes away.
#
# Needs: GH_TOKEN (issues: write), PROBE (success|failure), CHECK_LOG (file),
# RUN_URL, ASSIGNEES (comma-separated logins, may be empty), and a checkout of
# the repository as the working directory.
set -euo pipefail

FAILED_TITLE="Contact form check failed"
IDLE_TITLE="Contact form check will be paused by GitHub"
# GitHub switches off scheduled workflows in a public repository after 60
# days without activity. Warn while there is still time to do something.
IDLE_WARN_DAYS=45

# report <title> <problem|ok> <body>
report() {
    local title="$1" state="$2" body="$3" number
    # Only an issue this workflow opened counts. Anyone can open an issue with
    # the same title here, and it must not capture or silence the alert. gh
    # reports the workflow token's login as "app/github-actions" on issues.
    number=$(gh issue list --state open --limit 100 --json number,title,author \
        --jq "map(select(.title == \"$title\" and (.author.login | endswith(\"github-actions\"))))[0].number // empty")
    if [[ "$state" == ok ]]; then
        [[ -z "$number" ]] || gh issue close "$number" --comment "$body"
    elif [[ -n "$number" ]]; then
        gh issue comment "$number" --body "$body"
    else
        # An alert nobody is assigned is still better than no alert.
        gh issue create --title "$title" --body "$body" --assignee "$ASSIGNEES" ||
            gh issue create --title "$title" --body "$body"
    fi
}

if [[ "$PROBE" == success ]]; then
    report "$FAILED_TITLE" ok "The check passed again: $RUN_URL"
else
    report "$FAILED_TITLE" problem "The weekly check could not send a test message through the contact form on the live site, so messages from visitors are probably not arriving either.

\`\`\`
$(tail -n 8 "$CHECK_LOG" 2>/dev/null || echo "(no output from the check)")
\`\`\`

Run: $RUN_URL

What to look at is under \"Contact Form\" in \`CLAUDE.md\`. This issue closes itself when the check passes again."
fi

idle_days=$(( ($(date +%s) - $(git log -1 --format=%ct)) / 86400 ))
if (( idle_days >= IDLE_WARN_DAYS )); then
    report "$IDLE_TITLE" problem "The last commit here was $idle_days days ago. GitHub switches off scheduled workflows in a public repository after 60 days without activity, which would stop the weekly contact form check without telling anyone.

Any commit to \`main\` resets the clock. If the check has already stopped (no weekly \"form health check\" email), turn it back on under Actions, Contact Form Check, Enable workflow."
else
    report "$IDLE_TITLE" ok "A commit has landed, so the clock has reset."
fi
