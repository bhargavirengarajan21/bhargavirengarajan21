// Pulls recent feat/perf commits from your public repos and writes them
// into README.md between the RECENT markers. No dependencies (Node 20+).
const fs = require("fs");

const USER = process.env.GITHUB_REPOSITORY_OWNER;
const TOKEN = process.env.GITHUB_TOKEN;
const DAYS = 30;        // how far back to look
const MAX_ITEMS = 5;    // how many lines to show
const NOTEWORTHY = /^(feat|perf)(\(([^)]+)\))?!?:\s*(.+)$/i;
const START = "<!-- RECENT:START -->";
const END = "<!-- RECENT:END -->";

async function gh(path) {
  const res = await fetch(`https://api.github.com${path}`, {
    headers: { Authorization: `Bearer ${TOKEN}`, Accept: "application/vnd.github+json" },
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

async function main() {
  const since = new Date(Date.now() - DAYS * 864e5).toISOString();

  const repos = (await gh(`/users/${USER}/repos?sort=pushed&per_page=15`)).filter(
    (r) => !r.fork && !r.archived && r.name !== USER && r.pushed_at >= since
  );

  const items = [];
  for (const repo of repos) {
    let commits = [];
    try {
      commits = await gh(`/repos/${USER}/${repo.name}/commits?author=${USER}&since=${since}&per_page=30`);
    } catch {
      continue; // empty repo or similar
    }
    for (const c of commits) {
      const subject = c.commit.message.split("\n")[0];
      const m = subject.match(NOTEWORTHY);
      if (!m || /\[skip readme\]/i.test(c.commit.message)) continue;
      items.push({
        sha: c.sha.slice(0, 7),
        url: c.html_url,
        tag: `${m[1].toLowerCase()}(${m[3] || repo.name})`,
        text: m[4],
        date: c.commit.author.date,
      });
    }
  }

  const lines = items
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, MAX_ITEMS)
    .map((i) => {
      const pad = " ".repeat(Math.max(2, 14 - i.tag.length));
      return `${i.sha}  <a href="${i.url}">${esc(i.tag)}</a>:${pad}${esc(i.text)}`;
    });

  const readme = fs.readFileSync("README.md", "utf8");
  const re = new RegExp(`${START}[\\s\\S]*?${END}`);
  if (!re.test(readme)) throw new Error("RECENT markers not found in README.md");

  const block = `${START}${lines.join("\n")}${lines.length ? "\n" : ""}${END}`;
  fs.writeFileSync("README.md", readme.replace(re, () => block));
  console.log(`wrote ${lines.length} recent item(s)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
