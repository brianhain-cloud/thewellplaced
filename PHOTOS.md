# Adding photos to The Well Placed

Every one of the 85 entries already has artwork — a generated placeholder in the
category's color with its icon. Nothing looks broken or empty. You swap in real
photos one at a time, whenever you have them. No rush, no bulk migration.

---

## The one-line swap

Find the entry in `index.html` and add an `img:` field:

```js
{n:"Venetian Pool", img:"photos/venetian-pool.jpg", gf:[...], ...}
```

That's it. The photo replaces the placeholder in both the card and the map popup.
If the path is wrong or the file is missing, it silently falls back to the
placeholder — no broken-image icons, ever.

## File setup

Put photos in a `photos/` folder next to `index.html`:

```
your-site/
├── index.html
└── photos/
    ├── venetian-pool.jpg
    ├── crandon-park.jpg
    └── ...
```

**Naming:** lowercase, hyphens, no spaces. `the-standard-spa.jpg`, not `The Standard Spa.JPG`.

**Size:** 1280×800 or larger, cropped to 16:10. Cards display at roughly 320×200,
so anything above 1600px wide is wasted bytes.

**Format:** `.jpg` for photos, quality 75–80. Aim for under 200KB each. At 85
entries, a careless 2MB per photo makes the page unusable on phones.
[Squoosh.app](https://squoosh.app) does this in the browser, free.

**Crop:** the image is center-cropped to fill. Keep the subject centered and give
it breathing room at the edges.

---

## Where to actually get photos

Ranked by what serves the guide best.

**1. Shoot them yourself.** This is the real answer, and it's the moat. A guide
where every photo is yours — actual morning light at Matheson, the actual line
outside Pura Vida — cannot be copied by an aggregator scraping Google. It's slow,
but you're visiting these places anyway. A phone in good light is enough. Shoot
horizontal.

**2. Ask the business.** Most studios and gyms have a press kit or will happily
send photos for a listing that drives them traffic. One email, explicit
permission, better-than-phone quality. Do this for the ones you can't easily
photograph — the interiors of member-only clubs, the spas.

**3. Google Places Photos API.** Automatic and legitimately licensed for display,
but needs a Google Cloud key with billing enabled and costs per photo load. Worth
revisiting if the guide grows past a few hundred entries and shooting everything
stops being realistic. Not worth the setup at 85.

**Avoid:** pulling images off businesses' websites or Instagram. You don't hold
the license, it breaks when they redesign, and a takedown request from one
annoyed studio owner is a bad first impression for the brand.

---

## Priority order

Don't try to do all 85. Photograph in this order:

1. **The entries people click first** — Venetian Pool, Carillon, The Standard,
   Matheson Hammock. The visually striking ones that make someone screenshot and
   send to a friend.
2. **Anything you're featuring in the newsletter that week.** The photo does
   double duty — website card and email header.
3. **The rest, opportunistically.** You're going to these places anyway.

A guide where 20 entries have real photos and 65 have clean branded placeholders
looks intentional. One where 20 have photos and 65 have grey boxes looks broken.
That's the whole reason the placeholders were built this way.
