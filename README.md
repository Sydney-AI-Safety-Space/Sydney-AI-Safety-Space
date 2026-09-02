The Sydney AI Safety Space is a volunteer run coworking space based at Broad Church in Chippendale. We provide free office space for people working on AI Safety. 

More at sydneyaisafetyspace.com

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

Aim for roughly 150KB per image. The screenshot is shown at 22% opacity
behind a mask, so quality barely matters. Dark pages will be very subtle;
light pages will show more.

If a screenshot reads too faint or too bright, override the opacity on that
entry alongside the image:

    style="--entry-shot: url('../work-NAME.jpg'); --entry-shot-opacity: 0.5"

Dark screenshots generally need a higher value than light ones. The default
is 0.38.
