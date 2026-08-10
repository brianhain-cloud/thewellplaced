# The Well Placed, local setup

## Where the repo lives

```
~/Desktop/thewellplaced/          <- the git repo, and the only durable copy
├── index.html                    the entire site
├── photos/                       98 compressed photos, deployed
├── logo/                         11 logo files
├── build/                        Notion snapshot + the script that builds index.html
├── photos-raw/                   originals, git-ignored
├── process_photos.py
├── .gitignore
└── SETUP.md
```

Keep `Well Placed Photos` on the Desktop as your inbox for new photos. Drop
files there, then copy them into `photos-raw/` and run the pipeline.

## One-time setup

1. Install **GitHub Desktop** from desktop.github.com and sign in.
2. **File → Clone repository**, pick your Well Placed repo, and set the local
   path to `~/Desktop/thewellplaced`.
3. Copy everything from the working folder into that directory, `.gitignore`
   included.
4. In Cowork, connect the `thewellplaced` folder. From then on new versions get
   written straight into the repo instead of a temporary folder.

## Every time something changes

1. Open GitHub Desktop. Changed files appear on the left.
2. Type a short summary, click **Commit to main**, then **Push origin**.
3. Vercel rebuilds on its own. Give it about a minute.

No file-count limit, no truncated uploads, and a full history you can roll back.

## Adding photos

```bash
cd ~/Desktop/thewellplaced
cp ~/Desktop/"Well Placed Photos"/*.jpg photos-raw/
python3 process_photos.py
```

The script matches each filename to a guide entry, crops to 16:10, compresses
to roughly 200KB, writes `photos/<slug>.jpg`, and points the entry at it.
Filenames only need to resemble the entry name. Anything it cannot match gets
listed at the end so you can rename and re-run.

## Rebuilding from Notion

```bash
cd ~/Desktop/thewellplaced/build
python3 build.py
```

This reads the JSON snapshots in `build/`, applies the house style, geocodes any
new addresses, and writes `data.js`. The three arrays then get pasted into
`index.html`. The snapshots are refreshed by pulling from Notion, which is the
step to ask for by name.

## Sanity checks before pushing

```bash
# every referenced photo exists
node -e "const fs=require('fs'),h=fs.readFileSync('index.html','utf8'),
d=new Set(fs.readdirSync('photos'));
const r=[...new Set([...h.matchAll(/\"(photos\/[^\"]+)\"/g)].map(m=>m[1]))];
console.log(r.length+' referenced, '+d.size+' on disk');
console.log('missing:', r.filter(x=>!d.has(x.slice(7))).join(', ')||'none');"

# no em or en dashes
grep -c $'—\|–' index.html
```
