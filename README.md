# The Well Placed

A curated guide to the spaces, groups, and gatherings focused on health and
wellness in Miami. Live at [thewellplaced.com](https://thewellplaced.com).

The site is a single HTML file. No framework, no build step, no client-side
dependencies beyond Leaflet for the map. Everything renders from three data
arrays baked into the page at deploy time.

## Layout

```
public/            everything served to the browser
  index.html       the whole site: markup, styles, data, behaviour
  photos/          98 compressed entry photos
  logo/            wordmark, avatars, favicon
build/             the Notion snapshot and the script that turns it into data
photos-raw/        photo originals, git-ignored, never deployed
process_photos.py  crop, compress, and wire photos into the page
wrangler.toml      Cloudflare Workers config
```

Only `public/` is published. Keeping it separate is deliberate: Workers, unlike
Pages, does not automatically exclude `.git`, so pointing the asset directory at
the repo root would publish the commit history.

## The ask bar

Typing a question runs through three translators, in order, and stops at the
first one that produces filter values:

1. **Lexicon**, in the page. Instant, works everywhere, handles most questions.
2. **On-device**, Chrome's Gemini Nano. Free and private, desktop Chrome only.
3. **`/translate`**, a Worker calling Workers AI. The fallback for everyone else.

All three return the same small JSON object, and `sanitizeIntent` in the page
checks it against the live filter values before anything is applied. A translator
can only ever choose filters that already exist; it cannot write text on the page,
name a business, or reach the data. The Worker repeats the same check on its own
copy of the vocabulary, so neither side trusts the other.

`src/enums.json` is that vocabulary, generated from the page:

```bash
node build/gen_enums.js          # regenerate after a Notion sync
node build/gen_enums.js --check  # fails if it has drifted
```

Bump `CACHE_V` in `src/worker.js` whenever the model or the prompt changes,
otherwise a month of cached answers survives the fix.

## Deploying

```bash
npx wrangler deploy
```

Requires `npx wrangler login` once. The deploy uploads `public/` and nothing
else. Check what would ship before a large change:

```bash
npx wrangler deploy --dry-run
```

## Adding photos

Drop originals into `photos-raw/`, then:

```bash
python3 process_photos.py
```

Filenames only need to resemble an entry name. The script crops to 16:10,
resizes to 1600px, compresses to roughly 200KB, writes `public/photos/<slug>.jpg`
and points the entry at it. Anything it cannot match is listed at the end so you
can rename and re-run.

## Rebuilding from Notion

```bash
cd build && python3 build.py
```

Reads the JSON snapshots in `build/`, applies the house style, geocodes new
addresses through the US Census geocoder, and writes `data.js`. The three arrays
then go into `public/index.html`.

## House style

No em or en dashes anywhere on the site. Commas, semicolons, short sentences, or
ellipses instead. `build/clean.py` enforces this on every field coming out of
Notion, and the dash count below should always return zero.

## Checks before deploying

```bash
# every referenced photo exists
node -e "const fs=require('fs'),h=fs.readFileSync('public/index.html','utf8'),
d=new Set(fs.readdirSync('public/photos'));
const r=[...new Set([...h.matchAll(/\"(photos\/[^\"]+)\"/g)].map(m=>m[1]))];
console.log(r.length+' referenced, '+d.size+' on disk');
console.log('missing:', r.filter(x=>!d.has(x.slice(7))).join(', ')||'none');"

# no dashes
grep -c $'—\|–' public/index.html
```
