"""Cuban culture content: facts, slang, dishes and music, each in English and Spanish.

Kept to things that are well documented. Entries are plain data so they're easy to extend.
Slang is regional and varies by speaker; treat these as common everyday Cuban usage.
"""

from __future__ import annotations

import datetime
import random
import unicodedata

FACTS = [
    {"en": "The Cuban flag has five stripes (three blue, two white), a red triangle and a white star. It's nicknamed *La Estrella Solitaria*, the Lone Star.",
     "es": "La bandera cubana tiene cinco franjas (tres azules y dos blancas), un triángulo rojo y una estrella blanca. Se le conoce como *La Estrella Solitaria*."},
    {"en": "The tocororo, Cuba's national bird, wears red, white and blue plumage, the same colors as the flag.",
     "es": "El tocororo, ave nacional de Cuba, tiene plumaje rojo, blanco y azul, los mismos colores de la bandera."},
    {"en": "The mariposa (white ginger lily) is Cuba's national flower, and the royal palm is its national tree.",
     "es": "La mariposa es la flor nacional de Cuba, y la palma real es su árbol nacional."},
    {"en": "The bee hummingbird (*zunzuncito*) is native to Cuba and is the smallest bird in the world, at about 5 to 6 cm.",
     "es": "El zunzuncito es nativo de Cuba y es el ave más pequeña del mundo, con unos 5 a 6 cm."},
    {"en": "Old Havana and its fortifications became a UNESCO World Heritage Site in 1982.",
     "es": "La Habana Vieja y su sistema de fortificaciones fue declarada Patrimonio de la Humanidad por la UNESCO en 1982."},
    {"en": "Trinidad and the Valley of the Sugar Mills (*Valle de los Ingenios*) were listed as a UNESCO World Heritage Site in 1988.",
     "es": "Trinidad y el Valle de los Ingenios fueron declarados Patrimonio de la Humanidad por la UNESCO en 1988."},
    {"en": "The Viñales Valley, known for its limestone *mogotes* and tobacco farms, is a UNESCO World Heritage landscape (1999).",
     "es": "El Valle de Viñales, famoso por sus mogotes y sus vegas de tabaco, es Paisaje Cultural Patrimonio de la Humanidad (1999)."},
    {"en": "Pico Turquino, in the Sierra Maestra, is Cuba's highest peak at about 1,974 meters.",
     "es": "El Pico Turquino, en la Sierra Maestra, es la montaña más alta de Cuba, con unos 1.974 metros."},
    {"en": "Cuba is the largest island in the Caribbean, and the Isla de la Juventud is the biggest of its many smaller islands.",
     "es": "Cuba es la isla más grande del Caribe, y la Isla de la Juventud es la mayor de sus muchas islas menores."},
    {"en": "Son cubano was born in eastern Cuba and helped shape salsa and many other Latin music styles.",
     "es": "El son cubano nació en el oriente de Cuba y ayudó a dar forma a la salsa y a muchos otros estilos de música latina."},
    {"en": "The danzón is considered Cuba's national dance.",
     "es": "El danzón es considerado el baile nacional de Cuba."},
    {"en": "The mojito and the daiquirí are both Cuban-born cocktails.",
     "es": "El mojito y el daiquirí son dos cócteles nacidos en Cuba."},
    {"en": "Baseball, *la pelota*, is Cuba's most popular sport and a big part of everyday conversation.",
     "es": "El béisbol, *la pelota*, es el deporte más popular de Cuba y tema constante de conversación."},
    {"en": "Café cubano is a short, sweet espresso. The foam on top, the *espumita*, comes from whipping the first drops of coffee with sugar.",
     "es": "El café cubano es un espresso corto y dulce. La espumita se logra batiendo las primeras gotas del café con azúcar."},
    {"en": "The song *Guantanamera* uses verses by José Martí, Cuba's national hero, from his *Versos sencillos*.",
     "es": "La canción *Guantanamera* usa versos de José Martí, héroe nacional de Cuba, de sus *Versos sencillos*."},
    {"en": "Havana's Malecón, the seawall promenade, stretches about 8 km along the coast.",
     "es": "El Malecón de La Habana, el muro y paseo frente al mar, se extiende unos 8 km a lo largo de la costa."},
    {"en": "October 20 is the Día de la Cultura Cubana, marking the first public performance of *La Bayamesa* in 1868.",
     "es": "El 20 de octubre es el Día de la Cultura Cubana, en recuerdo de la primera interpretación pública de *La Bayamesa* en 1868."},
    {"en": "Cuban Spanish often softens the *s* at the end of a syllable, so it can sound like the letter is missing.",
     "es": "En el español de Cuba la *s* al final de la sílaba suele suavizarse, y a veces parece que desaparece."},
]

SLANG = [
    {"term": "asere", "en": "Friend, buddy. A very Cuban way to address someone.", "es": "Amigo, compadre. Una forma muy cubana de dirigirse a alguien.",
     "example": "¡Asere, qué bolá! ¿Cómo estás?"},
    {"term": "¿Qué bolá?", "en": "\"What's up?\" A classic Cuban greeting.", "es": "\"¿Qué tal?\" Un saludo clásico cubano.",
     "example": "¿Qué bolá, mi socio? Hace días que no te veía."},
    {"term": "guagua", "en": "Bus.", "es": "Autobús.", "example": "Voy en la guagua para el Vedado."},
    {"term": "jama", "en": "Food. The verb is *jamar*, to eat.", "es": "Comida. El verbo es *jamar*, comer.",
     "example": "Hoy hay una jama buenísima en casa."},
    {"term": "socio", "en": "Buddy, close friend.", "es": "Amigo cercano, compinche.",
     "example": "Mi socio me ayudó a construir la casa."},
    {"term": "yuma", "en": "A foreigner, especially an American.", "es": "Un extranjero, sobre todo un norteamericano.",
     "example": "El yuma preguntó cómo llegar al Malecón."},
    {"term": "pila", "en": "A lot, plenty.", "es": "Mucho, gran cantidad.", "example": "Había una pila de gente en el vote party."},
    {"term": "chévere", "en": "Cool, great.", "es": "Genial, estupendo.", "example": "¡Qué chévere quedó ese edificio!"},
    {"term": "ñó", "en": "An exclamation of surprise or exasperation.", "es": "Exclamación de sorpresa o fastidio.",
     "example": "¡Ñó, qué rápido llegamos a la meta!"},
    {"term": "pinchar", "en": "To work (as in having a job).", "es": "Trabajar.", "example": "Tengo que pinchar hasta tarde hoy."},
    {"term": "candela", "en": "Literally fire; also used when things are intense or tough.",
     "es": "Literalmente fuego; también se usa cuando algo está intenso o difícil.", "example": "Esa votación estuvo candela."},
]

DISHES = [
    {"name": "Ropa vieja", "en": "Shredded beef stewed with tomato, peppers and onion. The name means \"old clothes.\"",
     "es": "Carne de res deshilachada guisada con tomate, ají y cebolla. El nombre significa \"ropa vieja\"."},
    {"name": "Moros y cristianos", "en": "Black beans and white rice cooked together.", "es": "Frijoles negros y arroz blanco cocinados juntos."},
    {"name": "Congrí", "en": "Rice cooked with red beans, popular in eastern Cuba.", "es": "Arroz cocinado con frijoles colorados, muy popular en el oriente de Cuba."},
    {"name": "Lechón asado", "en": "Slow-roasted pork marinated in garlic and sour orange, a celebration dish.",
     "es": "Cerdo asado lentamente, marinado en ajo y naranja agria. Plato de celebración."},
    {"name": "Picadillo", "en": "Ground beef cooked with tomato, olives and raisins.", "es": "Carne molida guisada con tomate, aceitunas y pasas."},
    {"name": "Yuca con mojo", "en": "Boiled cassava topped with a garlic and citrus sauce.", "es": "Yuca hervida con mojo de ajo y cítricos."},
    {"name": "Tostones", "en": "Twice-fried green plantain slices, crisp and salty.", "es": "Rodajas de plátano verde fritas dos veces, crujientes y saladas."},
    {"name": "Croquetas", "en": "Crispy fried croquettes, usually filled with ham or chicken.", "es": "Croquetas fritas y crujientes, normalmente de jamón o pollo."},
    {"name": "Pastelitos de guayaba", "en": "Flaky pastries filled with guava paste, often with cream cheese.", "es": "Hojaldres rellenos de pasta de guayaba, a menudo con queso crema."},
    {"name": "Cafecito", "en": "A small, strong, sweet Cuban coffee, usually shared.", "es": "Un café cubano pequeño, fuerte y dulce, casi siempre para compartir."},
]

MUSIC = [
    {"name": "Son cubano", "en": "Born in eastern Cuba, blending Spanish guitar-based song with African rhythm. The root of salsa.",
     "es": "Nació en el oriente de Cuba, mezcla la canción de guitarra española con el ritmo africano. Es la raíz de la salsa."},
    {"name": "Rumba", "en": "Afro-Cuban percussion, song and dance from Havana and Matanzas.", "es": "Percusión, canto y baile afrocubanos de La Habana y Matanzas."},
    {"name": "Danzón", "en": "An elegant, slow ballroom dance, considered Cuba's national dance.", "es": "Un baile de salón elegante y pausado, considerado el baile nacional de Cuba."},
    {"name": "Cha-cha-chá", "en": "A playful dance rhythm created in 1950s Cuba.", "es": "Un ritmo bailable y juguetón creado en la Cuba de los años cincuenta."},
    {"name": "Trova", "en": "Cuban troubadour tradition: guitar and song, from boleros to nueva trova.", "es": "La tradición trovadoresca cubana: guitarra y canto, del bolero a la nueva trova."},
    {"name": "Celia Cruz", "en": "Cuban-born singer known as the Queen of Salsa.", "es": "Cantante nacida en Cuba, conocida como la Reina de la Salsa."},
    {"name": "Benny Moré", "en": "Singer and bandleader nicknamed *El Bárbaro del Ritmo*.", "es": "Cantante y director de orquesta apodado *El Bárbaro del Ritmo*."},
    {"name": "Buena Vista Social Club", "en": "The 1997 album and ensemble that brought classic Cuban son to the world.", "es": "El álbum y conjunto de 1997 que llevó el son cubano clásico a todo el mundo."},
]

KINDS = {"fact": FACTS, "slang": SLANG, "dish": DISHES, "music": MUSIC}


def pick(kind: str, rng: random.Random | None = None) -> dict:
    return (rng or random).choice(KINDS[kind])


def _norm(text: str) -> str:
    """Lowercase, drop accents and Spanish punctuation so 'que bola' finds '¿Qué bolá?'."""
    stripped = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return stripped.lower().strip().lstrip("¿¡").rstrip("?!").strip()


def find_slang(query: str) -> dict | None:
    q = _norm(query)
    for entry in SLANG:
        if _norm(entry["term"]) == q:
            return entry
    return None


def word_of_day(day: datetime.date) -> dict:
    """The same word for everyone on a given date, cycling through the whole list."""
    return SLANG[day.toordinal() % len(SLANG)]
