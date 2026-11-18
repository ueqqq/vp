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

FUN_FACTS = {
    "en": [
        "Cuba is the largest island in the Caribbean.",
        "Havana's historic center is a UNESCO World Heritage Site.",
        "Pico Turquino is Cuba's highest mountain, rising to about 1,974 meters.",
        "The tocororo, Cuba's national bird, has red, white, and blue plumage.",
        "Cuba is an archipelago made up of the main island and many smaller islands and keys.",
        "Cuban son music helped shape several popular Latin music styles.",
        "Baseball has been one of Cuba's most popular sports for generations.",
    ],
    "es": [
        "Cuba es la isla más grande del Caribe.",
        "El centro histórico de La Habana es Patrimonio de la Humanidad de la UNESCO.",
        "El Pico Turquino es la montaña más alta de Cuba, con unos 1.974 metros.",
        "El tocororo, ave nacional de Cuba, tiene plumaje rojo, blanco y azul.",
        "Cuba es un archipiélago formado por la isla principal y muchas islas y cayos pequeños.",
        "El son cubano ayudó a dar forma a varios estilos populares de música latina.",
        "El béisbol ha sido uno de los deportes más populares de Cuba durante generaciones.",
    ],
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    text = STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
