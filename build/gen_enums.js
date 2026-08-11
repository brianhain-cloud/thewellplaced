// Extracts the ask vocabulary from the page and writes src/enums.json.
//
// The Worker must not learn its vocabulary from the browser. If the client sent
// the enum lists, anyone could put arbitrary text into the model's system prompt.
// So the Worker carries its own copy, generated here from the same arrays the
// page renders, and `--check` fails the build if the two ever drift.

const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const HTML = path.join(ROOT, "public", "index.html");
const OUT = path.join(ROOT, "src", "enums.json");

// Pull out a top level `var NAME = [ ... ];` literal by counting brackets, so a
// bracket inside a string in the data cannot end the match early.
function literal(src, name) {
  const start = src.indexOf("var " + name + " = [");
  if (start < 0) throw new Error("could not find " + name);
  let i = src.indexOf("[", start);
  let depth = 0, inStr = null, esc = false;
  for (let j = i; j < src.length; j++) {
    const c = src[j];
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === inStr) inStr = null;
      continue;
    }
    if (c === '"' || c === "'") { inStr = c; continue; }
    if (c === "[") depth++;
    else if (c === "]") { depth--; if (!depth) return src.slice(i, j + 1); }
  }
  throw new Error("unterminated literal for " + name);
}

const src = fs.readFileSync(HTML, "utf8");
const rows = ["PLACES", "GROUPS", "EVENTS"].flatMap(function (n) {
  return new Function("return " + literal(src, n))();
});

const sets = { cat: new Set(), hood: new Set(), gf: new Set(), vibe: new Set(), plat: new Set(), day: new Set() };
for (const it of rows) {
  (it.c || []).forEach((v) => sets.cat.add(v));
  (it.hoods || (it.h ? [it.h] : [])).forEach((v) => sets.hood.add(v));
  (it.gf || []).forEach((v) => sets.gf.add(v));
  (it.who || []).forEach((v) => sets.gf.add(v));
  (it.v || []).forEach((v) => sets.vibe.add(v));
  (it.plat || []).forEach((v) => sets.plat.add(v));
  (it.d || []).forEach((v) => sets.day.add(v));
}

const out = {};
for (const k of Object.keys(sets)) out[k] = [...sets[k]].sort();
out.tab = ["places", "groups", "events", "upcoming"];

const text = JSON.stringify(out, null, 2) + "\n";

if (process.argv.includes("--check")) {
  const have = fs.existsSync(OUT) ? fs.readFileSync(OUT, "utf8") : "";
  if (have !== text) {
    console.error("src/enums.json is stale. Run: node build/gen_enums.js");
    process.exit(1);
  }
  console.log("enums current: " + rows.length + " rows, " +
    Object.keys(out).map((k) => k + " " + out[k].length).join(", "));
} else {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, text);
  console.log("wrote " + OUT);
  console.log("  " + rows.length + " rows, " +
    Object.keys(out).map((k) => k + " " + out[k].length).join(", "));
}
