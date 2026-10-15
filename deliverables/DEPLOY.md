# Deploying the MiraFlores Workpaper to a Public Link

**Status (honest): no public link exists yet.** This environment has no
hosting account or credentials for the candidate, and nothing was signed up
for in the candidate's name. Everything below is prepared so that deploying
takes one command / a few clicks **once the candidate uses their own free
hosting account**. Do not paste a link into the submission until it has been
opened in a browser and verified.

## Recommended fastest path — Render free tier (Blueprint prepared)

A `render.yaml` Blueprint is now in the project root, preconfigured for this
app (Docker runtime, `app/Dockerfile`, project root as build context, free
plan, health check on `/api/meta`). Steps for the candidate:

1. Push this project folder to a new GitHub (or GitLab) repo.
2. In Render: **New → Blueprint**, select the repo, **Apply** — no other
   settings and no credit card are needed for the free web service.
3. Wait for the first build, open the `onrender.com` URL, and run the
   verification checklist at the bottom of this file before pasting the
   link into `SUBMISSION.md`.

Caveats: free services spin down after ~15 minutes idle and take ~1 minute
to wake on the next request, so open the link once shortly before sending
the submission (and expect the reviewer's first load to be slow). Free-tier
disks are ephemeral, so demo notes/sign-offs reset on redeploy — acceptable
for this case study, and reviewers start clean.

## Option A — Docker (any host that runs a container)

Build context is the project folder (the app reads the packet from its
parent directory):

```bash
cd ~/workspace/miraflores-case-study
docker build -f app/Dockerfile -t miraflores-workpaper .
docker run -p 8765:8765 miraflores-workpaper
# open http://localhost:8765/
```

The same image deploys unchanged to Fly.io, Render, Railway, Google Cloud
Run, or an Azure Container App — point the platform at `app/Dockerfile`,
expose port **8765**.

## Option B — Free tier, no Docker (Render / Railway / Fly.io style)

- Runtime: Python 3.12
- Install: `pip install -r app/requirements.txt`
- Start command (from the project root):
  `uvicorn main:app --host 0.0.0.0 --port $PORT` with the app directory on
  the path — equivalently, set the service's root/working directory to
  `app/` and keep the packet JSON one level up (the app resolves it as
  `../okafor_lindqvist_2025_packet.json`, or set the `PACKET_PATH`
  environment variable to the packet's absolute path).
- **Persistent state:** notes/sign-offs/adjustments/verifications and the
  view log live in one SQLite file (`app/state.db`, override with the
  `WORKPAPER_STATE_DB` environment variable). On free tiers with ephemeral
  disks this file resets on redeploy — acceptable for a case-study demo,
  but mount a persistent disk/volume there if the reviewer session must
  survive restarts.

## Option C — Run locally for a screen-share / the video

```bash
cd ~/workspace/miraflores-case-study/app
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8765   # http://localhost:8765/
```

## After deploying — verification checklist

1. Open the public URL: Summary tab loads with v3 numbers (federal AGI 445,590).
2. Lines & trace → `F1040.1a` → the D08 source shows the red highlight box.
3. Checks tab shows 11 engine diagnostics + 6 independent checks.
4. Add a note as the preparer, switch to the client role, confirm the note
   is hidden and sign-off is refused — then delete `state.db` (or reset the
   service's state file) so reviewers start clean.
5. Paste the verified URL into `SUBMISSION.md` where marked, and next to
   the video link in the actual submission.

*Prepared with AI assistance (Muse), as the case study permits when disclosed.*
