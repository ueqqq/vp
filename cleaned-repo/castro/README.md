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
| Everyone | `/help` `/profile view\|edit` `/roster` `/decree list\|view` `/poll results` `/treaty list\|view` `/nation view` `/link` `/myvotes` `/leaderboard` `/quote today` `/funfact` `/language` |
| Citizens | vote on polls with the buttons (if a Citizen role is configured, only citizens can vote) |
| Leadership | `/decree publish\|repeal` · `/poll create\|close` · `/treaty add\|update` · `/profile fix` · `/nation edit` · `/nation town add\|remove` · `/nation gov set\|remove` · `/nation relation set\|remove` |
| Staff | `/quote add\|remove\|list\|post` |
| Admin | `/castro setchannel\|setrole\|panel\|status\|sync` · `/voteparty setup\|forceupdate\|setremaining\|rebase\|status` |

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
* The first cycle starts only after every site has been read once. Use `/voteparty setremaining`
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
