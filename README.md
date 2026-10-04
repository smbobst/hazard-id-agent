# Hazard Identification Agent — Setup Guide

This web app takes a CAS number and pulls hazard data from the U.S. EPA CompTox Chemicals Dashboard (through EPA's CTX APIs). Claude then writes a draft Hazard Identification Summary with separate **cancer** and **non-cancer** sections, organized according to EPA risk assessment guidance.

You can run it in three ways:

| Option | Who can use it | Cost | Effort |
|---|---|---|---|
| **A. Your own computer** | Only you, on that computer | Free (plus Anthropic usage) | Easiest, about 15 minutes |
| **B. Render** | Anyone with the link and password | Free tier, or about $7/month for always-on | About 30 minutes |
| **C. Railway** | Anyone with the link and password | About $5/month (Hobby plan) | About 30 minutes |

Start with **Option A**. Once it works on your computer, move to B or C if colleagues need access.

---

## What's in the folder

| File / folder | What it is |
|---|---|
| `app.py` | The web server (the part that runs) |
| `hazid/ctx_client.py` | Talks to the EPA CTX APIs |
| `hazid/processing.py` | Sorts EPA data into cancer and non-cancer evidence, and assigns source tiers. No AI is used here. |
| `hazid/prompts.py` | **The instructions Claude follows to write the summary.** Edit this to change the format. |
| `hazid/llm.py` | Sends the evidence to Claude |
| `hazid/export_docx.py` | Builds the Word download |
| `static/index.html` | The web page you see |
| `.env.example` | Template for your API keys |
| `start_windows.bat` / `start_mac.command` | Double-click launchers for Option A |
| `render.yaml`, `railway.json`, `Procfile` | Settings the hosting services read automatically |
| `sample_data/` | Demo data, so you can test without using your EPA key |

---

## Before you start: your two keys

You need:
1. **EPA CTX API key**, from EPA (ccte_api@epa.gov).
2. **Anthropic API key** (starts with `sk-ant-`), from console.anthropic.com → **API Keys**.

Treat both like passwords. Never email them, paste them into documents, or upload them to GitHub. In the Anthropic Console, set a monthly spend limit (in your organization's limits or billing settings) so there are no surprises.

---

## Option A — Run it on your own computer

### Step 1. Install Python (one time)

1. Go to **https://www.python.org/downloads/** and download Python 3.12 or newer.
2. Run the installer.
   - **Windows:** on the first screen, check the box **"Add python.exe to PATH"**, then click **Install Now**. This checkbox matters.
   - **Mac:** click through the installer normally.
3. Check that it worked:
   - **Windows:** open the Start menu, type `cmd`, open **Command Prompt**, and type `python --version`. You should see `Python 3.12.x` or newer.
   - **Mac:** open **Terminal** (Applications → Utilities) and type `python3 --version`.

### Step 2. Unzip the app

Unzip `hazard-id-agent.zip` somewhere easy to find, such as your **Documents** folder. You should end up with a folder called `hazard-id-agent` containing the files listed above.

### Step 3. Add your keys (create the `.env` file)

The app reads your keys from a file named exactly `.env` (dot-e-n-v, with no other extension) inside the `hazard-id-agent` folder.

**Windows**
1. Open **Notepad**.
2. Paste in the following, replacing the placeholder text with your real keys:
   ```
   CTX_API_KEY=your-EPA-key-here
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
3. Click **File → Save As**. Browse to the `hazard-id-agent` folder.
4. Set **"Save as type"** to **All files (\*.\*)**. Otherwise Notepad names it `.env.txt`, which won't work.
5. For the file name, type `.env` and click **Save**.

**Mac**
1. Open **TextEdit**, then choose **Format → Make Plain Text**.
2. Paste in the same two lines with your real keys.
3. Click **File → Save**, name it `.env`, and save it in the `hazard-id-agent` folder. If macOS warns about names beginning with a dot, click **Use "."**.
4. Files starting with a dot are hidden on a Mac. Press **Cmd + Shift + .** in Finder to show or hide them.

> **Optional: test without your EPA key first.** Add a third line, `MOCK_MODE=1`, and the app will use the built-in demo data. If your Anthropic key is present, Claude will still write a real summary of the demo data. Remove the line to use live EPA data.

### Step 4. Start the app

- **Windows:** double-click `start_windows.bat`.
- **Mac:** double-click `start_mac.command`. The first time, macOS may block it. If it does, right-click the file → **Open** → **Open**. If macOS says it "can't be opened because it is from an unidentified developer," go to **System Settings → Privacy & Security** and click **Open Anyway**.

The first launch takes 1–2 minutes while it installs the needed components. After that it starts in a few seconds. Your browser should open to **http://localhost:8000**. If it doesn't, type that address into your browser.

A black window (Windows) or Terminal window (Mac) stays open while the app runs. **Keep it open.** To stop the app, close that window or press **Ctrl + C** in it.

### Step 5. Generate your first summary

1. Type a CAS number (for example `71-43-2`) and click **Generate summary**.
2. Wait 30–90 seconds while the app retrieves EPA data and Claude writes the summary.
3. Use the tabs:
   - **Summary:** the Hazard ID Summary, with buttons for **Download Word**, Markdown, and **Print / Save as PDF**.
   - **Data used:** every EPA record behind the summary. Each reference in the summary (such as `[TV-718311]`) appears here, with its source tier and a link where EPA provides one.
   - **Evidence package:** the exact data Claude received.

### If the launcher doesn't work: the manual way

Open Command Prompt (Windows) or Terminal (Mac) and run these one line at a time:

**Windows**
```
cd %USERPROFILE%\Documents\hazard-id-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Mac**
```
cd ~/Documents/hazard-id-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:8000**. Next time you only need the `cd`, `activate`, and `python app.py` lines.

---

## Before Options B or C: put the code on GitHub (one time)

Both Render and Railway deploy the app from a GitHub repository. You don't need to know git; you can upload files through the website.

1. Create a free account at **https://github.com**.
2. Click the **+** at the top right → **New repository**.
3. Name it `hazard-id-agent`, select **Private**, and click **Create repository**.
4. On the next page, click the link **"uploading an existing file"**.
5. Open your `hazard-id-agent` folder, select **everything inside it except `.env` and `.venv`**, and drag it into the browser. The `hazid`, `static`, and `sample_data` folders must be included.
   - **Never upload `.env`.** It contains your keys. On the hosting service you enter the keys in its settings instead.
6. Click **Commit changes**.
7. Check the repository page. You should see `app.py`, `requirements.txt`, `render.yaml`, and the `hazid` and `static` folders at the top level, not inside another folder.

---

## Option B — Host on Render

1. Go to **https://render.com** and click **Get Started**. Sign up with **GitHub**, which is easiest because it links your repositories.
2. In the Render dashboard, click **+ New** → **Web Service**.
3. Under **Git Provider**, pick your `hazard-id-agent` repository. If it isn't listed, click **Configure account** and give Render access to it.
4. Fill in the settings:

   | Setting | Value |
   |---|---|
   | Name | `hazard-id-agent` (this becomes part of your web address) |
   | Language | **Python 3** |
   | Branch | `main` |
   | Region | Any; the closest to you is fine |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300` |
   | Instance Type | **Free** to try it out; **Starter** (about $7/month) to keep it always on |

5. Scroll to **Environment Variables** and click **Add Environment Variable** for each of these:

   | Key | Value |
   |---|---|
   | `CTX_API_KEY` | your EPA key |
   | `ANTHROPIC_API_KEY` | your Anthropic key |
   | `APP_PASSWORD` | a password you choose. **Strongly recommended:** without it, anyone who finds the link can spend your Anthropic credit. |
   | `PYTHON_VERSION` | `3.12.8` |

6. Under **Advanced**, set **Health Check Path** to `/healthz`.
7. Click **Deploy Web Service**. Watch the log. After 2–4 minutes you'll see "Your service is live."
8. Your address appears at the top of the page, for example `https://hazard-id-agent.onrender.com`. Open it, enter the password, and run a CAS number.

**About the Free instance:** it goes to sleep after 15 minutes with no visitors. The next visit takes about a minute to wake it. For regular use, switch to **Starter** under **Settings → Instance Type**.

*Shortcut:* the included `render.yaml` lets you use **+ New → Blueprint** instead. Render then fills in steps 4–6 automatically and only asks you to enter the keys and password.

---

## Option C — Host on Railway

1. Go to **https://railway.com** and sign up with **GitHub**. New accounts get a one-time $5 trial credit. For ongoing use, subscribe to the **Hobby** plan ($5/month, which includes $5 of usage; a small app like this typically fits within that).
2. Click **+ New** (or **New Project**) → **Deploy from GitHub repo**, then choose `hazard-id-agent`. If it isn't listed, click **Configure GitHub App** and give Railway access to the repository.
3. Railway starts building right away. The first build may fail because the keys aren't set yet. That's expected.
4. Click the service box, open the **Variables** tab, and add:

   | Variable | Value |
   |---|---|
   | `CTX_API_KEY` | your EPA key |
   | `ANTHROPIC_API_KEY` | your Anthropic key |
   | `APP_PASSWORD` | a password you choose |

   Railway redeploys automatically after you add variables. The start command comes from the included `railway.json`, so you don't need to type it.
5. Open the **Settings** tab → **Networking** → **Generate Domain**. Railway gives you an address such as `https://hazard-id-agent-production.up.railway.app`.
6. Open the address, enter the password, and run a CAS number.

---

## Updating the app later

- **Hosted (B or C):** edit or re-upload a file on GitHub and click **Commit changes**. Render and Railway redeploy automatically within a few minutes.
- **Local (A):** replace the files in your folder and restart the launcher.

The most common change is the summary format. That lives entirely in `hazid/prompts.py`, which is plain English instructions.

---

## Settings reference

| Setting | Required | What it does |
|---|---|---|
| `CTX_API_KEY` | Yes | Your EPA CTX API key |
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `APP_PASSWORD` | Recommended when hosted | Users must enter this password before generating summaries |
| `ANTHROPIC_MODEL` | No | Claude model to use. Default: `claude-sonnet-5-5`. Set `claude-opus-5-5` for the most capable (and more expensive) model. |
| `MAX_OUTPUT_TOKENS` | No | Maximum summary length. Default: 8000. Raise it if the app warns that a summary was cut off. |
| `MOCK_MODE` | No | `1` = use built-in demo data instead of calling EPA |
| `CTX_API_BASE` | No | EPA API address. Default: `https://comptox.epa.gov/ctx-api/`. Change it only if EPA moves the API. |

---

## Costs

- **EPA CTX API:** free.
- **Anthropic:** billed per summary based on the amount of text in and out. Each summary sends roughly 3,000–15,000 words of EPA data plus the instructions. Check actual costs at console.anthropic.com → **Usage** after your first few runs.
- **Hosting:** Render Free ($0, sleeps when idle) or Starter (about $7/month); Railway Hobby ($5/month including $5 of usage).

---

## Troubleshooting

| What you see | What to do |
|---|---|
| `'python' is not recognized` (Windows) | Python wasn't added to PATH. Re-run the Python installer, choose **Modify**, and check **"Add Python to environment variables"**. |
| "No .env file found" | The file is missing or was saved as `.env.txt`. Redo Step 3 and choose **All files** in Notepad. |
| "EPA CTX API rejected the API key" | Check `CTX_API_KEY` for typos or extra spaces. Confirm with EPA that the key is active. |
| "No chemical found in the CompTox Dashboard for CAS …" | Check the CAS number on https://comptox.epa.gov/dashboard. Some substances aren't in DSSTox. |
| "Anthropic API error (HTTP 401)" | The Anthropic key is wrong or was revoked. Create a new one in the Console. |
| "Anthropic API error (HTTP 400) … credit balance" | Add credit in the Anthropic Console under **Billing**. |
| "Anthropic API error … model" | Your account may not have access to the default model. Set `ANTHROPIC_MODEL` to a model listed in your Console. |
| "Some EPA data domains could not be retrieved" | One EPA endpoint was down or has changed. The summary is still produced from the rest and says what's missing. |
| Hosted site shows "Application failed to respond" / 502 | Open the service's **Logs** tab on Render or Railway. The last red lines usually name the problem, often a missing variable. |
| Page takes over a minute to appear (Render Free) | The service was asleep. This is normal; upgrade to Starter to avoid it. |
| Port 8000 already in use (local) | Add `PORT=8001` to `.env` and open http://localhost:8001. |

---

## How the agent works, and its safeguards

1. **Look up the chemical.** The CAS number is checked (format and check digit), then resolved to its DSSTox ID (DTXSID) using `chemical/search/equal/{CAS}`.
2. **Retrieve the data.** These EPA hazard domains are retrieved in parallel: ToxValDB (`hazard/toxval`), cancer summary (`hazard/cancer-summary`), genotoxicity summary and details (`hazard/genetox/...`), IRIS (`hazard/iris`), and PPRTV (`hazard/pprtv`).
3. **Sort the evidence (plain code, no AI).** Records are separated into a **cancer evidence package** (classifications, slope factors and unit risks, tumor sites, genotoxicity) and a **non-cancer evidence package** (IRIS/PPRTV RfD/RfC, other reference values, and points of departure grouped by effect class and route). Each record gets a **source tier**:
   - **Tier 1:** EPA peer-reviewed assessments (IRIS, PPRTV).
   - **Tier 2:** other EPA programs and government or authoritative bodies (e.g., ATSDR, OEHHA, IARC, NTP, WHO).
   - **Tier 3:** study-level or screening data (e.g., ToxRefDB, industry dossiers).
4. **Write the summary.** Claude writes it from those packages only, under these rules:
   - Use only the retrieved data, and cite a reference ID for every value.
   - **Never derive new RfDs or slope factors, and never apply uncertainty factors.**
   - **Never assign an EPA cancer descriptor itself.** Classifications are reported exactly as each source gives them.
   - Keep cancer and non-cancer evaluations separate:
     - **Cancer:** 2005 Guidelines for Carcinogen Risk Assessment, 2005 Early-Life Supplemental Guidance (ADAF flag), 1986 Mutagenicity Guidelines, and EPA's alpha2u-globulin and thyroid-tumor mode-of-action documents.
     - **Non-cancer:** 2002 RfD/RfC Review, 2012 Benchmark Dose Technical Guidance, and the Developmental (1991), Reproductive (1996), and Neurotoxicity (1998) Guidelines. The 2022 IRIS Handbook underpins both sections.
   - End with data gaps, a confidence statement, and a fixed disclaimer.

**This is a drafting and screening tool.** Every summary should be checked against the original sources by a qualified toxicologist before use in a risk assessment.

### Suggested validation before relying on it

Run chemicals with well-known EPA assessments and compare the output against the IRIS pages. Good test cases:
- benzene (71-43-2)
- formaldehyde (50-00-0)
- trichloroethylene (79-01-6)
- toluene (108-88-3)
- a chemical with no IRIS assessment

For each, check that:
- the IRIS RfD/RfC and cancer values match,
- no numbers appear without a reference ID, and
- data gaps are correctly identified.
