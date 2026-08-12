// The Well Placed: /translate
//
// Turns a plain English question into filter values the guide already knows how
// to apply. It never sees the guide's contents and never writes prose, so the
// worst a bad answer can do is select the wrong filters. Everything else on the
// site is served straight from static assets and never reaches this code.
//
// text -> model -> sanitize -> filter values
//
// The vocabulary lives in enums.json, generated from the page by
// build/gen_enums.js. The browser does not get to supply it.

import ENUM from "./enums.json";

// 8b was tested first and was not good enough: it invented neighbourhoods and
// filled every list to the brim rather than leaving one out. The job is short,
// so the larger model is still fractions of a cent per question.
const MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
// Bump whenever MODEL, SYSTEM, sanitize() or the vocabulary changes. v3 is the
// arrival of Dance, Martial Arts, Dog-Friendly and Miami Lakes: answers cached
// before those existed could never mention them.
const CACHE_V = "3";
const MAX_Q = 200;          // a real question is far shorter; longer is abuse or noise
const MAX_TOKENS = 200;     // the reply is a small JSON object, nothing needs more
const ORIGINS = ["https://thewellplaced.com", "https://www.thewellplaced.com"];

const SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    picked: {
      type: "object",
      additionalProperties: false,
      properties: {
        cat:  { type: "array", items: { type: "string", enum: ENUM.cat } },
        hood: { type: "array", items: { type: "string", enum: ENUM.hood } },
        gf:   { type: "array", items: { type: "string", enum: ENUM.gf } },
        vibe: { type: "array", items: { type: "string", enum: ENUM.vibe } },
        day:  { type: "array", items: { type: "string", enum: ENUM.day } }
      }
    },
    explicitTab: { type: "string", enum: ENUM.tab },
    rest: { type: "array", items: { type: "string" } }
  },
  required: ["picked", "rest"]
};

const SYSTEM = [
  "You translate a question about a Miami wellness guide into filter values.",
  "Return JSON only. Never write prose. Never invent a business name.",
  "Use only values from these lists, copied exactly.",
  "cat: " + ENUM.cat.join(", "),
  "hood: " + ENUM.hood.join(", "),
  "gf: " + ENUM.gf.join(", "),
  "vibe: " + ENUM.vibe.join(", "),
  "day: " + ENUM.day.join(", "),
  "explicitTab is places for venues, groups for clubs and crews,",
  "events for one-off happenings, upcoming when the question is about timing.",
  "Leave a list out entirely when nothing fits. Do not guess to fill it.",
  "A question names one or two things. Long lists mean you are guessing.",
  "Never name a neighbourhood the question did not mention.",
  "rest holds leftover words from the question, never values from the lists above.",
  "",
  "padel in doral",
  '{"picked":{"cat":["Racquet/Padel"],"hood":["Doral"]},"explicitTab":"places","rest":[]}',
  "",
  "running in coral gables",
  '{"picked":{"cat":["Run/Cardio"],"hood":["Gables"]},"explicitTab":"places","rest":[]}',
  "",
  "yoga with dogs next week",
  '{"picked":{"cat":["Yoga/Pilates"]},"explicitTab":"upcoming","rest":["dogs"]}',
  "",
  "a beginner friendly run club that meets on saturdays",
  '{"picked":{"cat":["Run/Cardio"],"gf":["Beginner-Friendly"],"day":["Sat"]},"explicitTab":"groups","rest":[]}'
].join("\n");

// How many values a person could plausibly mean at once. A model that returns
// more than this is dumping the list rather than choosing from it, which reads
// as a confident answer while meaning nothing, so the whole list is dropped.
const CAP = { cat: 3, hood: 2, gf: 3, vibe: 2, day: 7 };

// Whatever comes back, only these shapes and values survive. The page repeats
// this check on its own copy of the enums; neither side trusts the other.
function sanitize(raw) {
  const safe = { picked: {}, explicitTab: null, rest: [] };
  if (!raw || typeof raw !== "object") return safe;
  const p = raw.picked && typeof raw.picked === "object" ? raw.picked : {};

  const vocab = new Set();
  for (const k of ["cat", "hood", "gf", "vibe", "day"]) {
    ENUM[k].forEach((v) => vocab.add(v.toLowerCase()));
    if (!Array.isArray(p[k])) continue;
    const kept = [...new Set(p[k].filter((v) => ENUM[k].includes(v)))];
    if (kept.length && kept.length <= CAP[k]) safe.picked[k] = kept;
  }
  if (typeof raw.explicitTab === "string" && ENUM.tab.includes(raw.explicitTab)) {
    safe.explicitTab = raw.explicitTab;
  }
  if (Array.isArray(raw.rest)) {
    safe.rest = raw.rest
      .filter((v) => typeof v === "string" && v.length > 0 && v.length < 30)
      // rest is meant to hold what could not be mapped. A model that echoes the
      // vocabulary back into it makes the page report nonsense constraints.
      .filter((v) => !vocab.has(v.toLowerCase()))
      .slice(0, 8);
  }
  return safe;
}

// Models that ignore the schema still tend to wrap valid JSON in chatter.
function parseLoose(text) {
  if (typeof text !== "string") return text;
  try { return JSON.parse(text); } catch (e) { /* fall through */ }
  const a = text.indexOf("{"), b = text.lastIndexOf("}");
  if (a < 0 || b <= a) return null;
  try { return JSON.parse(text.slice(a, b + 1)); } catch (e) { return null; }
}

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...extra }
  });
}

async function translate(env, q) {
  const args = {
    messages: [{ role: "system", content: SYSTEM }, { role: "user", content: q }],
    max_tokens: MAX_TOKENS,
    temperature: 0
  };
  let out;
  try {
    // Constrained decoding when the model supports it.
    out = await env.AI.run(MODEL, { ...args, response_format: { type: "json_schema", json_schema: SCHEMA } });
  } catch (e) {
    // and a plain call when it does not. sanitize() is the real guarantee.
    out = await env.AI.run(MODEL, args);
  }
  const raw = out && (out.response !== undefined ? out.response : out);
  return sanitize(parseLoose(raw));
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // run_worker_first scopes this Worker to /translate, but a config change
    // should not silently turn the site into a 404.
    if (url.pathname !== "/translate") return env.ASSETS.fetch(request);
    if (request.method !== "POST") return json({ error: "post only" }, 405);

    const origin = request.headers.get("origin");
    if (origin && !ORIGINS.includes(origin)) return json({ error: "bad origin" }, 403);

    let q;
    try {
      const body = await request.json();
      q = typeof body.q === "string" ? body.q.trim().replace(/\s+/g, " ") : "";
    } catch (e) {
      return json({ error: "bad body" }, 400);
    }
    if (!q) return json({ error: "empty" }, 400);
    if (q.length > MAX_Q) return json({ error: "too long" }, 413);

    // Repeat questions are the common case on a small guide, and a cached answer
    // costs nothing, so serve those before spending a rate limit token.
    // CACHE_V is part of the key so a change to the model or the prompt takes
    // effect immediately. Without it a month of stale answers survives the fix.
    const key = new Request(
      url.origin + "/translate?v=" + CACHE_V + "&q=" + encodeURIComponent(q.toLowerCase()),
      { method: "GET" });
    const cache = caches.default;
    const hit = await cache.match(key);
    if (hit) {
      const r = new Response(hit.body, hit);
      r.headers.set("x-translate", "cache");
      return r;
    }

    // Per visitor first. IP is a blunt key, but an anonymous guide has no better
    // identifier, so the limit is set high enough that a shared address is fine.
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const mine = await env.RL_IP.limit({ key: ip });
    if (!mine.success) return json({ error: "slow down" }, 429, { "retry-after": "60" });

    // Then a ceiling across everyone, so a bad day cannot become a bad bill.
    const all = await env.RL_ALL.limit({ key: "translate" });
    if (!all.success) return json({ error: "busy" }, 429, { "retry-after": "60" });

    let intent;
    try {
      intent = await translate(env, q);
    } catch (e) {
      // The page falls back to its own lexicon, so a failure here is not fatal.
      return json({ error: "unavailable" }, 503);
    }

    const res = json(intent, 200, { "cache-control": "public, max-age=2592000", "x-translate": "model" });
    ctx.waitUntil(cache.put(key, res.clone()));
    return res;
  }
};
