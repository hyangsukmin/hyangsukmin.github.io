---
description: Publish the day's Research Radar issue to the Daily Update page
---

Pull the latest Research Radar artifact and publish any issues the site is
missing. The artifact usually finishes updating before 09:00 KST.

0. Sync first: `git pull --ff-only` (issues may also be pushed from other
   machines, so local main may be behind).

1. Fetch the artifact with the Artifact tool's read action (not WebFetch or
   curl -- the artifact is behind a claude.ai login; WebFetch refuses
   claude.ai artifact links and curl only gets the SPA shell):

   Artifact
     action: read
     url: https://claude.ai/code/artifact/02db3738-fa2d-4b2f-b840-6ad1efe76d95
     prompt: List the issue dates present, newest first.

   The tool result names a local path where it saved the full HTML
   ("full HTML saved to ..."). Use that path in the next step. If the read
   fails or returns something other than the radar markup, stop and report
   it -- do not publish a partial or stale issue.

2. Import it:

   python3 scripts/import_radar.py <saved-html-path>

   The script writes one post per issue at _posts/<date>-radar.html and
   prints which dates it wrote. Dates the artifact no longer carries are left
   alone. If it prints "written: none", there is nothing new -- stop here and
   say so.

3. Verify the build if Ruby gems are installed (`bundle exec jekyll build`).
   If they aren't, skip this; the Deploy workflow builds on push, so check
   that run with `gh run list -L 1` after pushing.

4. Commit only _posts/*-radar.html and push to main. Pushing is what
   deploys: .github/workflows/deploy.yml builds the site and publishes it to
   the gh-pages branch.

   Commit message: "Add Research Radar issue <date>" (or list the dates when
   there is more than one).

Report which dates were published, or that there was nothing new.
