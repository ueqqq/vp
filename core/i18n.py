"""English / Spanish strings for the vote-party replies and help text.

A user's choice is stored with /language. Add a key to both languages and call t(key, lang).
"""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "claim_ok": "✅ ¡Gracias, compañero! Vote logged — **{n}/{max}** this cycle.",
        "claim_limit": "You've already claimed {max}/{max} this cycle. A new cycle starts after the next vote party. ¡Descansa!",
        "claim_cooldown": "⏳ Easy, asere — you can claim again <t:{ts}:R>.",
        "claim_no_ign": "Tip: link your Minecraft name with `/link` so staff can match you in-game.",
        "notify_on": "🔔 You'll be pinged when the vote party is close. ¡A votar!",
        "notify_off": "🔕 Vote-party pings turned off.",
        "notify_missing": "❌ The vote-party ping role isn't set. Ask an admin to run `/castro setrole`.",
        "notify_denied": "❌ I can't assign that role. My role must sit above it in the server list.",
        "remind_set": "⏰ I'll DM you in 30 minutes — time for another round of votes.",
        "link_ok": "🔗 Linked to **{ign}**. ¡Listo!",
        "link_bad": "❌ That isn't a valid Minecraft username (3–16 letters, numbers or underscores).",
        "lang_set": "🌐 Language set to English.",
        "leaderboard_note": "Claims are self-reported · los votos son de honor",
        "howto_vote": "Vote once on each site (one vote per day), then press **I voted** on the tracker.",
    },
    "es": {
        "claim_ok": "✅ ¡Gracias, compañero! Voto registrado — **{n}/{max}** en este ciclo.",
        "claim_limit": "Ya reclamaste {max}/{max} en este ciclo. Un nuevo ciclo empieza tras la próxima vote party. ¡Descansa!",
        "claim_cooldown": "⏳ Tranquilo, asere — podrás reclamar otra vez <t:{ts}:R>.",
        "claim_no_ign": "Consejo: vincula tu nombre de Minecraft con `/link` para que el staff te identifique.",
        "notify_on": "🔔 Te avisaremos cuando la vote party esté cerca. ¡A votar!",
        "notify_off": "🔕 Avisos de vote party desactivados.",
        "notify_missing": "❌ El rol de avisos no está configurado. Pide a un admin que use `/castro setrole`.",
        "notify_denied": "❌ No puedo asignar ese rol. Mi rol debe estar por encima en la lista del servidor.",
        "remind_set": "⏰ Te enviaré un MD en 30 minutos — hora de otra ronda de votos.",
        "link_ok": "🔗 Vinculado a **{ign}**. ¡Listo!",
        "link_bad": "❌ Ese no es un nombre de Minecraft válido (3–16 letras, números o guiones bajos).",
        "lang_set": "🌐 Idioma cambiado a español.",
        "leaderboard_note": "Los votos son de honor · self-reported claims",
        "howto_vote": "Vota una vez en cada sitio (un voto al día) y luego pulsa **I voted** en el tracker.",
    },
}

from core.cuba import FACTS  # noqa: E402

FUN_FACTS = {"en": [f["en"] for f in FACTS], "es": [f["es"] for f in FACTS]}


def t(key: str, lang: str = "en", **kwargs) -> str:
    text = STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
