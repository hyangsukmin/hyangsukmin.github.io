---
description: Publish the day's Research Radar issue to the Daily Update page
---

Pull the latest Research Radar artifact and publish any issues the site is
missing. The artifact usually finishes updating before 09:00 KST.

1. Fetch the artifact with WebFetch (not curl -- the artifact is behind a
   claude.ai login, and curl only gets the SPA shell):

   WebFetch
     url: https://claude.ai/code/artifact/02db3738-fa2d-4b2f-b840-6ad1efe76d95
     prompt: List the issue dates present, newest first.

   The tool result names a local path where it saved the full HTML. Use that
   path in the next step. If the fetch fails or returns the SPA shell rather
   than the radar markup, stop and report it -- do not publish a partial or
   stale issue.

2. Import it:

   python3 scripts/import_radar.py <saved-html-path>

   The script writes one post per issue under content/post/<date>-radar/ and
   prints which dates it wrote. Dates the artifact no longer carries are left
   alone. If it prints "written: none", there is nothing new -- stop here and
   say so.

3. Verify the build before publishing:

   npx hugo --quiet

4. Commit only content/post/*-radar and push to main. Pushing is what
   deploys: .github/workflows/deploy.yml builds and publishes to GitHub Pages
   on every push to main.

   Commit message: "Add Research Radar issue <date>" (or list the dates when
   there is more than one).

Report which dates were published, or that there was nothing new.
