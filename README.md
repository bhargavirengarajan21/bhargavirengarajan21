<p align="center">
  <a href="https://bhargavi-r-21.vercel.app/">
    <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=18&duration=2600&pause=900&color=F5A623&vCenter=true&width=620&height=40&lines=%24+whoami;bhargavi+rengarajan+%E2%80%94+software+engineer+%40+rocket+mortgage;%24+cat+~%2F.focus;distributed+fintech+services+%C2%B7+local-first+AI+tooling;%24+why;because+your+source+code+shouldn't+need+an+API+key." alt="terminal intro" />
  </a>
</p>

```
$ whoami --verbose

  bhargavi rengarajan
  software engineer @ rocket mortgage · chicago · 5 yrs fintech

  backend    java · spring boot · kafka · postgres · redis
  frontend   react · next.js · typescript
  platform   docker · kubernetes · azure · gcp · aws
  after 6pm  ollama · unsloth · mcp — models that run on the laptop
```

<p align="left">
  <a href="https://bhargavi-r-21.vercel.app/"><img src="https://img.shields.io/badge/portfolio-111111?style=flat-square&logo=vercel&logoColor=white" alt="Portfolio" /></a>
  <a href="https://www.linkedin.com/in/bhargavi-r21"><img src="https://img.shields.io/badge/linkedin-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
  <a href="https://huggingface.co/Bhargavi5q1"><img src="https://img.shields.io/badge/hugging%20face-FFD21E?style=flat-square&logo=huggingface&logoColor=black" alt="Hugging Face" /></a>
  <a href="https://www.npmjs.com/package/git-commit-at"><img src="https://img.shields.io/badge/npm-CB3837?style=flat-square&logo=npm&logoColor=white" alt="npm" /></a>
  <a href="mailto:bhargaviwork21@gmail.com"><img src="https://img.shields.io/badge/email-D14836?style=flat-square&logo=gmail&logoColor=white" alt="Email" /></a>
</p>

### `$ git log --author=bhargavi --oneline`

<pre>
a7f3d21  <a href="https://huggingface.co/Bhargavi5q1/git-commit-messages">feat(ai)</a>:      fine-tune qwen2.5-coder-1.5b, quantize to GGUF, ship to hugging face
9c1e40b  <a href="https://www.npmjs.com/package/git-commit-at">feat(cli)</a>:     publish git-commit-at to npm — local inference, zero network calls
4b8ca97  <a href="https://github.com/bhargavirengarajan21/mcp-observability-agent">feat(mcp)</a>:     prototype observability agent — plain-language incident triage
e2d7f66  chore(role):   join rocket mortgage, remote from chicago
1f09ab3  feat(edu):     m.s. computer engineering @ uc riverside — gpu computer vision
6ad4c12  perf(team):    lead delivery and mentor engineers @ mr. cooper
b3e8907  feat(paper):   ieee publication — ml-based spatial hazard assessment
</pre>

### `$ ls ~/work/featured`

<table>
  <tr>
    <td width="34%" valign="top">
      <h4>git-commit-at</h4>
      <p>
        <a href="https://www.npmjs.com/package/git-commit-at"><img src="https://img.shields.io/npm/dt/git-commit-at?style=flat-square&logo=npm&logoColor=white&label=downloads&color=CB3837" alt="npm downloads" /></a>
        <a href="https://www.npmjs.com/package/git-commit-at"><img src="https://img.shields.io/npm/v/git-commit-at?style=flat-square&color=F5A623&label=v" alt="npm version" /></a>
      </p>
      <p>A git subcommand that writes your conventional commit messages on-device through Ollama. No API key, no network call, no code leaving the machine.</p>
      <p><code>node · ollama · docker</code></p>
      <p><a href="https://www.npmjs.com/package/git-commit-at">npm</a> · <a href="https://github.com/bhargavirengarajan21/git-commit-at">source</a></p>
    </td>
    <td width="34%" valign="top">
      <h4>fine-tuned commit model</h4>
      <p>
        <a href="https://huggingface.co/Bhargavi5q1/git-commit-messages"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fhuggingface.co%2Fapi%2Fmodels%2FBhargavi5q1%2Fgit-commit-messages&query=%24.downloads&style=flat-square&logo=huggingface&logoColor=black&label=downloads&color=FFD21E" alt="Hugging Face downloads" /></a>
        <img src="https://img.shields.io/badge/GGUF-Q4__K__M-555555?style=flat-square" alt="GGUF Q4_K_M" />
      </p>
      <p>qwen2.5-coder-1.5b fine-tuned with Unsloth, quantized and packaged with an Ollama Modelfile so it runs on a laptop with no GPU.</p>
      <p><code>unsloth · qwen2.5-coder · gguf</code></p>
      <p><a href="https://huggingface.co/Bhargavi5q1/git-commit-messages">hugging face</a></p>
    </td>
    <td width="32%" valign="top">
      <h4>mcp observability agent</h4>
      <p><img src="https://img.shields.io/badge/status-prototype-555555?style=flat-square" alt="prototype" /></p>
      <p>An MCP server that hands production telemetry to Claude, so incident triage is a plain-language question instead of hand-written NRQL.</p>
      <p><code>express · next.js · typescript · new relic</code></p>
      <p><a href="https://github.com/bhargavirengarajan21/mcp-observability-agent">source</a></p>
    </td>
  </tr>
</table>

### `$ git commit-at --demo`

```console
$ npm install -g git-commit-at
$ ollama pull hf.co/Bhargavi5q1/git-commit-messages

$ git add src/auth/session.ts
$ git commit-at

  reading staged diff ......... 1 file, +42 −7
  running model locally ....... qwen2.5-coder-1.5b (Q4_K_M)
  network requests ............ 0

  feat(auth): expire idle sessions after 30 minutes
  [y] accept  [e] edit  [r] regenerate
```

### `$ cat package.json`

```jsonc
{
  "name": "bhargavi",
  "role": "software engineer @ rocket mortgage",
  "dependencies": {
    "java": "^17",            "spring-boot": "^3.x",
    "typescript": "^5",       "react": "^18",
    "next": "^14",            "node": "^20",
    "kafka": "*",             "redis": "*",
    "postgres": "*",          "mongodb": "*",
    "kubernetes": "*",        "docker": "*"
  },
  "devDependencies": {
    "ollama": "*",            "unsloth": "*",
    "mcp": "*",               "pyspark": "*"
  },
  "scripts": {
    "work":  "ship services end to end — contract, ci/cd, observability, on-call",
    "learn": "rag · agent tooling · quantization",
    "ask":   "open https://bhargavi-r-21.vercel.app  # gemini assistant, ask it anything"
  }
}
```

### `$ ls projects/ --group-by=domain`

<details>
  <summary><code>distributed-systems/</code></summary>
  <br>
  <ul>
    <li><b>distributed cloud logging</b> — serverless, tamper-resistant logging in Golang on Kubernetes with real-time capture. <code>golang · k8s · blockchain</code></li>
  </ul>
</details>

<details>
  <summary><code>data-and-ml/</code></summary>
  <br>
  <ul>
    <li><b>air pollution prediction</b> — Flask service serving XGBoost PM10 forecasts. IEEE published. <code>python · flask · xgboost</code></li>
    <li><b>us accident zone analysis</b> — geospatial analysis of large-scale accident data, PySpark on Hadoop, React front end. <code>pyspark · hadoop · react</code></li>
    <li><b>electrostatic halftoning</b> — GPU-accelerated dithering and stippling with CuPy. <code>python · cupy</code></li>
  </ul>
</details>

<details>
  <summary><code>frontend/</code></summary>
  <br>
  <ul>
    <li><b>netflix-inspired portfolio</b> — Gemini-powered chat assistant, server-side key handling on Vercel. <a href="https://bhargavi-r-21.vercel.app/">live</a> · <code>react · typescript · gemini</code></li>
    <li><b>music via hand gestures</b> — real-time gesture recognition for playback control. <a href="https://github.com/bhargavirengarajan21/music-playing-using-hand-gestures">source</a> · <code>python · opencv · mediapipe</code></li>
  </ul>
</details>

### `$ gh contributions --graph`

<p align="center">
  <img src="https://github-readme-activity-graph.vercel.app/graph?username=bhargavirengarajan21&bg_color=00000000&color=F5A623&line=F5A623&point=FFFFFF&area=true&area_color=F5A623&hide_border=true&custom_title=commits%20/%20last%2031%20days" width="100%" alt="contribution activity" />
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api?username=bhargavirengarajan21&show_icons=true&hide=contribs&count_private=true&hide_border=true&bg_color=00000000&title_color=F5A623&icon_color=F5A623&text_color=9198A1" />
    <img src="https://github-readme-stats.vercel.app/api?username=bhargavirengarajan21&show_icons=true&hide=contribs&count_private=true&hide_border=true&bg_color=00000000&title_color=B36B00&icon_color=B36B00" height="150" alt="github stats" />
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api/top-langs/?username=bhargavirengarajan21&layout=compact&hide_border=true&langs_count=8&bg_color=00000000&title_color=F5A623&text_color=9198A1" />
    <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=bhargavirengarajan21&layout=compact&hide_border=true&langs_count=8&bg_color=00000000&title_color=B36B00" height="150" alt="top languages" />
  </picture>
</p>

```console
$ echo "building things that run where you are" | mail bhargaviwork21@gmail.com
```
