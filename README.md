The Sydney AI Safety Space is a volunteer run coworking space based at Broad Church in Chippendale. We provide free office space for people working on AI Safety. 

More at sydneyaisafetyspace.com

## Adding an event

Upcoming events on `events.html` are Luma embeds. Each `<div class="event-embed">`
carries the event's start and end in Sydney time, with the UTC offset
(+10:00 normally, +11:00 during daylight saving):

    <div class="event-embed" data-start="2026-09-17T17:30:00+10:00" data-end="2026-09-17T19:30:00+10:00">

A script on the page hides any event whose `data-end` has passed and writes
the "Next event" line from the earliest one still to come. If none are left
it shows a "Nothing scheduled" note instead. Add `data-venue="..."` if an
event is not at Broad Church. Old events can be deleted from the file
whenever convenient; leaving them in is harmless.

## Adding a preview image to a Recent Work entry

Entries on `work.html` can show a faint screenshot of the work when hovered.
It is optional - entries without one just get the plain hover tint.

1. Screenshot the page (macOS: Cmd+Shift+4, then space, then click the window).
2. Resize and compress it into `static/`:

   sips -Z 1200 ~/Desktop/shot.png -s format jpeg -s formatOptions 60 --out static/work-NAME.jpg

3. Add the image to that entry's `<div class="work-item">` in `work.html`:

   <div class="work-item" style="--entry-shot: url('../work-NAME.jpg')">

The path is relative to `static/css/`, not to the page. That is because
`url()` inside a CSS custom property resolves against the stylesheet's
location. `../work-NAME.jpg` therefore points at `static/work-NAME.jpg`,
and works whether the site is served over HTTP or opened as a local file.

Aim for roughly 150KB per image. The screenshot is shown at 28% opacity and
masked to the right-hand third of the entry, so quality barely matters. Dark
pages will be very subtle; light pages will show more. Only the right side is
visible, so choose a crop with something worth seeing there - a figure or a
chart rather than empty margin.

If a screenshot reads too faint or too bright, override the opacity on that
entry alongside the image:

    style="--entry-shot: url('../work-NAME.jpg'); --entry-shot-opacity: 0.5"

Dark screenshots generally need a higher value than light ones. The default
is 0.28.
