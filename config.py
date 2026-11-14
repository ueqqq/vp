"""Castro — Cuban nation community bot configuration."""

import os
from typing import Dict, List

# ─── Core Settings ────────────────────────────────────────────────────────────

BOT_NAME = "Castro"
BOT_VERSION = "1.1.0"
NATION_NAME = "Cuba"
NATION_FLAG = "🇨🇺"
BOT_COLOR = 0x002A8F  # Cuban flag blue
THUMBNAIL_URL = os.getenv("BOT_THUMBNAIL_URL", "")

# ─── Vote Party Settings ──────────────────────────────────────────────────────

VOTE_GOAL = 250
SCRAPE_INTERVAL_SECONDS = 15
PING_THRESHOLD = 30
PING_DELETE_SECONDS = 300
MAX_VOTES_PER_CYCLE = 3

# ─── Economy Settings (DiplomaticaMC Gold Standard) ───────────────────────────

# DiplomaticaMC uses GOLD as currency (ingots and blocks)
# This tracks gold holdings, not virtual currency
STARTING_GOLD = 0  # Players start with 0 gold
VOTE_REWARD_GOLD = 64  # 64 gold ingots (1 stack) for voting
DAILY_REWARD_GOLD = 16  # 16 gold ingots daily
WORK_REWARD_GOLD = 8  # 8 gold ingots for work
CURRENCY_NAME = "Gold"
CURRENCY_EMOJI = "🪙"

# Towny Costs (DiplomaticaMC specific)
TOWN_CREATION_COST = 64  # 64 gold ingots to create a town
NATION_CREATION_COST = 1024  # 1024 gold ingots to create a nation
TOWN_CLAIM_COST = 16  # 16 gold per chunk claim

# Inactivity Settings
INACTIVITY_WARNING_DAYS = 50  # Warn at 50 days
INACTIVITY_DELETION_DAYS = 60  # Delete Towny data at 60 days

# ─── Activity Settings ────────────────────────────────────────────────────────

INACTIVE_DAYS = 30
MESSAGE_COOLDOWN = 60  # seconds between XP gains
VOICE_COOLDOWN = 60

# ─── Moderation Settings ──────────────────────────────────────────────────────

MAX_WARNINGS = 3
WARNING_EXPIRE_DAYS = 30
AUTOMOD_ENABLED = True

# ─── Ticket Settings ──────────────────────────────────────────────────────────

TICKET_CATEGORY_NAME = "🎫 Support Tickets"
TICKET_STAFF_ROLE = "Staff"

# ─── Role Settings ────────────────────────────────────────────────────────────

NATION_MEMBER_ROLE = "Nation Member"
ALLY_ROLE = "Ally"
VP_ROLE = "VP"
VERIFIED_ROLE = "Verified"
STAFF_ROLE = "Staff"
LEADERSHIP_ROLE = "Leadership"

# ─── Vote Sites ───────────────────────────────────────────────────────────────

VOTE_SITES = [
    {
        "name": "Minecraft-MP",
        "url": "https://minecraft-mp.com/server-s349345",
        "emoji": "🟡",
        "fallback_patterns": [
            r"Vote\(s\)</strong></td>\s*<td[^>]*>\s*(\d+)\s*</td>",
            r"Vote\(s\)[^0-9]{0,50}(\d+)",
        ],
    },
    {
        "name": "MinecraftServers.org",
        "url": "https://minecraftservers.org/server/679302",
        "emoji": "🔵",
        "fallback_patterns": [
            r">Votes</div>\s*<div[^>]*>\s*(\d+)\s*</div>",
            r"Votes\s*</div>\s*<div[^>]*>\s*(\d+)\s*</div>",
        ],
    },
    {
        "name": "Minecraft-Server-List",
        "url": "https://minecraft-server-list.com/server/513054/vote/",
        "emoji": "🔴",
        "fallback_patterns": [
            r"(\d+)\s+Players have voted for this server in",
            r"<b>(\d+)\s+Votes\s*-\s*All time</b>",
        ],
    },
]

# ─── Cooldowns ────────────────────────────────────────────────────────────────

VOTE_CLAIM_COOLDOWN = 3600  # 1 hour
REMINDER_COOLDOWN = 1800    # 30 minutes
DAILY_REWARD_COOLDOWN = 86400  # 24 hours
WORK_COOLDOWN = 3600  # 1 hour

# ─── File Paths ───────────────────────────────────────────────────────────────

DATA_DIR = "data"
BOT_DATA_FILE = f"{DATA_DIR}/bot_data.json"
PLAYER_DATA_FILE = f"{DATA_DIR}/player_data.json"
STATS_FILE = f"{DATA_DIR}/stats.json"
ECONOMY_FILE = f"{DATA_DIR}/economy.json"
TICKETS_FILE = f"{DATA_DIR}/tickets.json"
DIPLOMACY_FILE = f"{DATA_DIR}/diplomacy.json"
TOWNS_FILE = f"{DATA_DIR}/towns.json"
EVENTS_FILE = f"{DATA_DIR}/events.json"
MODLOG_FILE = f"{DATA_DIR}/modlog.json"

# ─── Embed States ─────────────────────────────────────────────────────────────

class EmbedState:
    NORMAL = "normal"
    MOMENTUM = "momentum"
    CLOSE = "close"
    FINAL = "final"
    CELEBRATION = "celebration"
    COOLDOWN = "cooldown"

# ─── Colors ───────────────────────────────────────────────────────────────────

COLOR_GOLD = 0xF1C40F  # DiplomaticaMC currency
COLOR_BLUE = 0x002A8F  # Cuban flag blue
COLOR_RED = 0xCF142B   # Cuban flag red
COLOR_TURQUOISE = 0x1ABC9C
COLOR_CELEBRATION = 0x2ECC71
COLOR_COOLDOWN = 0x95A5A6

# ─── Milestones ───────────────────────────────────────────────────────────────

MILESTONES = [25, 50, 75, 100, 150, 200, 225, 250]

# ─── Fun Facts (Cuba) ────────────────────────────────────────────────────────

FUN_FACTS = {
    "en": [
        "Cuba is the largest island in the Caribbean.",
        "Havana's historic center is a UNESCO World Heritage Site.",
        "Pico Turquino is Cuba's highest mountain, rising to about 1,974 meters.",
        "The tocororo, Cuba's national bird, has red, white, and blue plumage.",
        "Cuba's flag has five alternating blue and white stripes and a white star in a red triangle.",
        "Cuba is an archipelago made up of the main island and many smaller islands and keys.",
        "Cuban son music helped shape several popular Latin music styles.",
        "Baseball has been one of Cuba's most popular sports for generations.",
    ],
    "es": [
        "Cuba es la isla más grande del Caribe.",
        "El centro histórico de La Habana es Patrimonio de la Humanidad de la UNESCO.",
        "El Pico Turquino es la montaña más alta de Cuba, con unos 1.974 metros.",
        "El tocororo, ave nacional de Cuba, tiene plumaje rojo, blanco y azul.",
        "La bandera cubana tiene cinco franjas azules y blancas y una estrella blanca en un triángulo rojo.",
        "Cuba es un archipiélago formado por la isla principal y muchas islas y cayos pequeños.",
        "El son cubano ayudó a dar forma a varios estilos populares de música latina.",
        "El béisbol ha sido uno de los deportes más populares de Cuba durante generaciones.",
    ]
}

# ─── Trivia Questions ─────────────────────────────────────────────────────────

TRIVIA_QUESTIONS = {
    "en": [
        {"q": "What is the capital of Cuba?", "a": "Havana"},
        {"q": "What is Cuba's highest mountain?", "a": "Pico Turquino"},
        {"q": "What is Cuba's national bird?", "a": "Tocororo"},
        {"q": "What is the historic center of Havana recognized as?", "a": "A UNESCO World Heritage Site"},
        {"q": "What are the five long shapes on the Cuban flag?", "a": "Blue and white stripes"},
        {"q": "What is the name for Cuba's traditional music style that influenced salsa?", "a": "Son cubano"},
        {"q": "What is the largest island in the Caribbean?", "a": "Cuba"},
        {"q": "Which sport is especially popular in Cuba?", "a": "Baseball"},
    ],
    "es": [
        {"q": "¿Cuál es la capital de Cuba?", "a": "La Habana"},
        {"q": "¿Cuál es la montaña más alta de Cuba?", "a": "Pico Turquino"},
        {"q": "¿Cuál es el ave nacional de Cuba?", "a": "Tocororo"},
        {"q": "¿Qué reconocimiento tiene el centro histórico de La Habana?", "a": "Patrimonio de la Humanidad de la UNESCO"},
        {"q": "¿De qué colores son las cinco franjas de la bandera cubana?", "a": "Azules y blancas"},
        {"q": "¿Qué estilo musical cubano influyó en la salsa?", "a": "Son cubano"},
        {"q": "¿Cuál es la isla más grande del Caribe?", "a": "Cuba"},
        {"q": "¿Qué deporte es especialmente popular en Cuba?", "a": "Béisbol"},
    ]
}
