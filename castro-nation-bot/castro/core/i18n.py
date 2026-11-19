"""English / Spanish strings for the vote-party replies and help text.

A user's choice is stored with /language. Add a key to both languages and call t(key, lang).
"""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "claim_ok": "✅ Vote logged! You've claimed **{n}/{max}** this cycle.",
        "claim_limit": "You've already claimed {max}/{max} votes this cycle. A new cycle starts after the next vote party.",
        "claim_cooldown": "⏳ You can claim again <t:{ts}:R>.",
        "claim_no_ign": "Tip: link your Minecraft name with `/link` so staff can match you in-game.",
        "notify_on": "🔔 You'll now be pinged when a vote party is close.",
        "notify_off": "🔕 You won't be pinged for vote parties any more.",
        "notify_missing": "❌ The vote-party ping role doesn't exist yet. Ask an admin to run `/castro setrole`.",
        "notify_denied": "❌ I can't assign that role. My role must be above it in the server role list.",
        "remind_set": "⏰ I'll DM you in 30 minutes to vote again.",
        "link_ok": "🔗 Linked to **{ign}**.",
        "link_bad": "❌ That isn't a valid Minecraft username (3–16 letters, numbers or underscores).",
        "lang_set": "🌐 Language set to English.",
        "leaderboard_note": "Claims are self-reported.",
    },
    "es": {
        "claim_ok": "✅ ¡Voto registrado! Has reclamado **{n}/{max}** en este ciclo.",
        "claim_limit": "Ya reclamaste {max}/{max} votos en este ciclo. Un nuevo ciclo empieza tras la próxima vote party.",
        "claim_cooldown": "⏳ Podrás reclamar otra vez <t:{ts}:R>.",
        "claim_no_ign": "Consejo: vincula tu nombre de Minecraft con `/link` para que el staff te identifique.",
        "notify_on": "🔔 Recibirás un aviso cuando una vote party esté cerca.",
        "notify_off": "🔕 Ya no recibirás avisos de vote party.",
        "notify_missing": "❌ El rol de avisos aún no existe. Pide a un admin que use `/castro setrole`.",
        "notify_denied": "❌ No puedo asignar ese rol. Mi rol debe estar por encima en la lista de roles.",
        "remind_set": "⏰ Te enviaré un MD en 30 minutos para que votes de nuevo.",
        "link_ok": "🔗 Vinculado a **{ign}**.",
        "link_bad": "❌ Ese no es un nombre de Minecraft válido (3–16 letras, números o guiones bajos).",
        "lang_set": "🌐 Idioma cambiado a español.",
        "leaderboard_note": "Los votos son autodeclarados.",
    },
}

from core.cuba import FACTS  # noqa: E402

FUN_FACTS = {"en": [f["en"] for f in FACTS], "es": [f["es"] for f in FACTS]}


def t(key: str, lang: str = "en", **kwargs) -> str:
    text = STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
