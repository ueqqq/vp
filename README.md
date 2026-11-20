# 🇨🇺 Castro: Cuba nation bot for DiplomaticaMC

A full nation bot, not just a vote tracker: citizen profiles and roster, decrees and citizen polls,
a treaty register, applications, private support tickets, a nation directory, the vote-party tracker,
a daily quote, and EN/ES replies. Slash commands and buttons only.

## Run it
```bash
pip install -r requirements.txt
cp .env.example .env        # put your bot token in it
python bot.py
```
In the Discord developer portal enable the **Server Members Intent** (and nothing else privileged;
Castro does not read message content). Invite with the `bot` and `applications.commands` scopes and
the permissions: Manage Roles, Manage Channels, Send Messages, Embed Links, Read Message History.
Put the bot's role **above** the Citizen / Ally / VP roles.

## First-time setup (all inside Discord)
1. `/castro status` shows a checklist of what's configured.
2. `/castro setchannel` for: welcome, quotes, votes, applications, decrees, treaties, logs, ticket category.
   (Decrees and treaties fall back to the channel you run the command in if unset; polls post where you create them.)
3. `/castro setrole` for any role not named exactly Staff / Leadership / Nation Member / Ally / VP.
4. Post panels where you want them: `/castro panel hub|support|nation`, and `/voteparty setup` for the tracker.
5. Fill the directory: `/nation edit`, `/nation town add`, `/nation gov set`, `/nation relation set`.
6. `/voteparty status` should show every vote site succeeding. If one fails, its error is listed there.

## Commands
| Who | Command |
|---|---|
| Everyone | `/help` `/profile view\|edit` `/roster` `/decree list\|view` `/poll results` `/treaty list\|view` `/nation view` `/link` `/myvotes` `/leaderboard` `/quote today` `/cuba fact\|slang\|word\|dish\|music` `/funfact` `/language` `/play` `/skip` `/queue` `/nowplaying` `/pause` `/resume` `/stop` `/leave` |
| Citizens | vote on polls with the buttons (if a Citizen role is configured, only citizens can vote) |
| Leadership | `/decree publish\|repeal` · `/poll create\|close` · `/treaty add\|update` · `/profile fix` · `/nation edit` · `/nation town add\|remove` · `/nation gov set\|remove` · `/nation relation set\|remove` |
| Staff | `/quote add\|remove\|list\|post` |
| Admin | `/castro setchannel\|setrole\|panel\|status\|sync` · `/castro settings\|set\|reset\|preview` · `/voteparty setup\|forceupdate\|setremaining\|rebase\|status` |

## Settings: change almost anything from Discord
Run **`/castro settings`** for a panel with seven categories. Pick a category, pick a setting, edit it in a form.
Changes apply immediately, and ✏️ marks anything you've customised. `/castro set` and `/castro reset`
(with autocomplete) do the same from the keyboard, and `/castro preview` shows how a message will look.

| Category | What you can change |
|---|---|
| 🇨🇺 Identity & look | Nation name, flag emoji, motto, color theme (`bandera` `roja` `palma` `dorada`), a custom hex color, default language |
| 🗳️ Vote party | Votes per party, ping threshold, polling speeds, claims per cycle, claim cooldown, ping/celebration messages, how long pings last |
| 👋 Welcome & support | Welcome title and message, support panel text (templates with `{name}` `{mention}` `{nation}` `{flag}` `{server}`) |
| 📜 Quotes & culture | Quote hour and timezone (e.g. `America/Havana`), optional daily Cuban word |
| 🏛️ Government | Default poll length, citizens-only polls |
| 🧩 Features on/off | Vote party, quotes, music, welcome, tickets |
| 🎶 Bot status | Rotating status lines ("watching: over {nation} {flag}") |

Templates are checked when you save them: an unknown placeholder is rejected with the list of valid ones,
so a typo can't break a message. Values in `.env` are now just the starting defaults.
Settings are stored per server in `data/settings.json`.

## Cuban culture
`/cuba fact`, `slang`, `word`, `dish` and `music` serve bilingual (English/Español) content from
`core/cuba.py`, which is plain data that's easy to extend. `/cuba slang asere` looks up a word, accents optional.
Turn on **Daily Cuban word** to post a *palabra del día* with the quote. The slang list covers common everyday
Cuban usage; regional use varies, so have a Cuban member review anything you add.

## Music
`/play` needs **ffmpeg** installed on the host plus `yt-dlp` and `PyNaCl` (in requirements). Streaming from
YouTube may break their terms of service and music bots tend to be shut down, so use it with that in mind.

## Government and diplomacy
* **Decrees** are numbered, posted to the decrees channel, and can be repealed (the original post is
  updated and greyed out, never deleted, so the record stays intact).
* **Polls** run 1 to 168 hours, allow one changeable vote per member, close automatically, and show a
  winner or a tie. Votes are recorded per member, so they are **not secret ballots**; the poll says so.
* **Treaties** keep a register with type, status and a history of status changes, and post a live
  embed that updates when the status does.

## How the vote tracker stays honest
* Vote-site totals are all-time counters, so a reading that goes **down** is rejected as a bad scrape.
* A huge single jump must be seen twice before it's trusted.
* A site that stops responding keeps its last number but is shown with ⚠️ and a data warning.
* Polling is every 30 s, dropping to 15 s once the party is within the ping threshold (both configurable in `.env`).
* The first cycle starts once a **majority** of sites have been read (so one dead site cannot freeze the tracker). Use `/voteparty setremaining`
  to match the real count if you're starting mid-cycle.
* "I voted" is **self-reported** (3 per cycle, 1 hour apart). The bot can't verify who voted, and the leaderboard says so.

## Data
Everything lives in `data/*.json`, written atomically and flushed every 10 s and on shutdown.
A corrupt file is moved aside (`*.corrupt-<time>.json`), never silently replaced. Back up `data/`.

## Tests
`python -m unittest discover -s tests` covers the vote engine, claim limits, page parsing, poll logic and the store.

## Not built yet
Treasury/tax ledger and elections. A ledger needs careful audit rules to be trusted, and elections
need decisions about who can run and vote. Both are good next steps.

## Not included (on purpose)
The old gold economy, fake Towny/siege/war commands and trivia tracked numbers inside the bot that
don't exist in the real game, so they were dropped rather than carried over. Real DiplomaticaMC
data would need an official data source to read from. Easy to add back if you want them.
