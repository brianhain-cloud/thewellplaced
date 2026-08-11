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
python3 build/sync.py     # Notion  -> build/*.json
python3 build/build.py    # *.json  -> build/data.js
```

`sync.py` pulls all three databases and writes the snapshots. `--dry-run` shows
what would change without touching anything, which is the safe way to check
whether a sync is even needed.

`build.py` reads those snapshots, applies the house style, geocodes any new
address, and writes `data.js`. The three arrays then go into
`public/index.html`, and `node build/gen_enums.js` regenerates the Worker's
vocabulary.

### The token

`sync.py` needs a Notion internal integration token, read from `.env` at the
repo root. `.env` is git-ignored; `.env.example` shows the shape.

1. Go to <https://www.notion.so/profile/integrations> and create a new internal
   integration in the workspace that holds The Well Placed.
2. Give it read access. It never writes, so no write capability is needed.
3. Copy the secret into `.env` as `NOTION_TOKEN=...`.
4. Open each of the three databases in Notion, then `...` menu, Connections,
   and add the integration. A token alone is not enough; Notion also requires
   the integration to be connected to each database, and a missing connection
   shows up as a 404.

### When a property is renamed

`sync.py` maps Notion property names to the short keys `build.py` expects. Rename
a property in Notion and that column arrives empty, so the script counts a few
required fields and refuses to write if any of them come back completely empty.
If it stops with that error, fix the name in `sync.py` rather than working around it.

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
