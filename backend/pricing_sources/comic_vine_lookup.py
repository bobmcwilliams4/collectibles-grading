"""
Comic Metadata Lookup - Fetches comic metadata (writer, artist, year) from multiple sources
Uses ComicVine, Grand Comics Database, and Marvel/DC wikis
"""

import asyncio
import aiohttp
import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Common comic data to use as fallback when web lookups fail
KNOWN_COMICS = {
    'where monsters dwell': {
        'publisher': 'Marvel Comics',
        'year_range': '1970-1975',
        'description': 'Horror anthology series featuring monster stories'
    },
    'amazing spider-man': {
        'publisher': 'Marvel Comics',
        'year_range': '1963-present',
        'description': 'Main Spider-Man comic series'
    },
    'x-men': {
        'publisher': 'Marvel Comics',
        'year_range': '1963-present',
        'description': 'Mutant superhero team series'
    },
    'batman': {
        'publisher': 'DC Comics',
        'year_range': '1940-present',
        'description': 'The Dark Knight of Gotham City'
    },
    'superman': {
        'publisher': 'DC Comics',
        'year_range': '1939-present',
        'description': 'The Man of Steel'
    },
    'fantastic four': {
        'publisher': 'Marvel Comics',
        'year_range': '1961-present',
        'description': 'Marvel\'s First Family'
    },
    'avengers': {
        'publisher': 'Marvel Comics',
        'year_range': '1963-present',
        'description': 'Earth\'s Mightiest Heroes'
    },
    'detective comics': {
        'publisher': 'DC Comics',
        'year_range': '1937-present',
        'description': 'Home of Batman since 1939'
    },
    'action comics': {
        'publisher': 'DC Comics',
        'year_range': '1938-present',
        'description': 'Home of Superman since issue #1'
    },
    'teen titans': {
        'publisher': 'DC Comics',
        'year_range': '1966-1978',
        'description': 'Teen sidekicks Robin, Kid Flash, Aqualad, Wonder Girl and others'
    },
    'new teen titans': {
        'publisher': 'DC Comics',
        'year_range': '1980-1996',
        'description': 'Wolfman/Perez revival featuring Cyborg, Starfire, Raven'
    },
    'justice league': {
        'publisher': 'DC Comics',
        'year_range': '1960-present',
        'description': 'DC\'s premier superhero team'
    },
    'wonder woman': {
        'publisher': 'DC Comics',
        'year_range': '1942-present',
        'description': 'Amazon Princess Diana of Themyscira'
    },
    'flash': {
        'publisher': 'DC Comics',
        'year_range': '1959-present',
        'description': 'The Fastest Man Alive'
    },
    'green lantern': {
        'publisher': 'DC Comics',
        'year_range': '1960-present',
        'description': 'Intergalactic police corps'
    },
    'journey into mystery': {
        'publisher': 'Marvel Comics',
        'year_range': '1952-1966',
        'description': 'Horror/fantasy anthology, later featured Thor'
    },
    'tales of suspense': {
        'publisher': 'Marvel Comics',
        'year_range': '1959-1968',
        'description': 'Anthology series featuring Iron Man and Captain America'
    },
    'tales to astonish': {
        'publisher': 'Marvel Comics',
        'year_range': '1959-1968',
        'description': 'Anthology featuring Ant-Man, Hulk, Sub-Mariner'
    },
    'incredible hulk': {
        'publisher': 'Marvel Comics',
        'year_range': '1962-present',
        'description': 'The Green Goliath'
    },
}

# Database of key issues with first appearances and notable events
KEY_ISSUES = {
    # Amazing Spider-Man
    ('amazing spider-man', '1'): ['First issue of ongoing series', 'First appearance of J. Jonah Jameson', 'First appearance of Chameleon'],
    ('amazing spider-man', '2'): ['First appearance of Vulture'],
    ('amazing spider-man', '3'): ['First appearance of Doctor Octopus'],
    ('amazing spider-man', '4'): ['First appearance of Sandman'],
    ('amazing spider-man', '6'): ['First appearance of Lizard'],
    ('amazing spider-man', '9'): ['First appearance of Electro'],
    ('amazing spider-man', '13'): ['First appearance of Mysterio'],
    ('amazing spider-man', '14'): ['First appearance of Green Goblin'],
    ('amazing spider-man', '15'): ['First appearance of Kraven the Hunter'],
    ('amazing spider-man', '28'): ['First appearance of Molten Man'],
    ('amazing spider-man', '31'): ['First appearance of Gwen Stacy', 'First appearance of Harry Osborn'],
    ('amazing spider-man', '50'): ['Spider-Man No More! - iconic cover'],
    ('amazing spider-man', '121'): ['Death of Gwen Stacy'],
    ('amazing spider-man', '122'): ['Death of Green Goblin (Norman Osborn)'],
    ('amazing spider-man', '129'): ['First appearance of Punisher'],
    ('amazing spider-man', '194'): ['First appearance of Black Cat'],
    ('amazing spider-man', '238'): ['First appearance of Hobgoblin'],
    ('amazing spider-man', '252'): ['First black costume (symbiote)'],
    ('amazing spider-man', '298'): ['First Todd McFarlane art on ASM'],
    ('amazing spider-man', '299'): ['First appearance of Venom (cameo)'],
    ('amazing spider-man', '300'): ['First full appearance of Venom', 'Origin of Venom'],
    ('amazing spider-man', '361'): ['First appearance of Carnage'],

    # X-Men
    ('x-men', '1'): ['First appearance of X-Men', 'First Magneto', 'First Cyclops, Marvel Girl, Beast, Iceman, Angel'],
    ('x-men', '4'): ['First appearance of Scarlet Witch', 'First Quicksilver', 'First Brotherhood of Evil Mutants'],
    ('x-men', '12'): ['First appearance of Juggernaut'],
    ('x-men', '14'): ['First appearance of Sentinels'],
    ('x-men', '28'): ['First appearance of Banshee'],
    ('x-men', '94'): ['New X-Men begin (Storm, Colossus, Nightcrawler, etc.)'],
    ('x-men', '101'): ['First appearance of Phoenix'],
    ('x-men', '120'): ['First appearance of Alpha Flight'],
    ('x-men', '129'): ['First appearance of Kitty Pryde', 'First Emma Frost'],
    ('x-men', '130'): ['First appearance of Dazzler'],
    ('x-men', '141'): ['Days of Future Past begins'],
    ('x-men', '266'): ['First appearance of Gambit'],
    ('uncanny x-men', '221'): ['First appearance of Mr. Sinister'],
    ('uncanny x-men', '244'): ['First appearance of Jubilee'],
    ('uncanny x-men', '266'): ['First full appearance of Gambit'],

    # Hulk
    ('incredible hulk', '1'): ['First appearance of Hulk', 'Origin of Hulk'],
    ('incredible hulk', '181'): ['First full appearance of Wolverine'],
    ('incredible hulk', '180'): ['First cameo appearance of Wolverine'],
    ('incredible hulk', '340'): ['Hulk vs Wolverine - classic McFarlane cover'],

    # Fantastic Four
    ('fantastic four', '1'): ['First appearance of Fantastic Four', 'First Mole Man'],
    ('fantastic four', '2'): ['First appearance of Skrulls'],
    ('fantastic four', '4'): ['First Silver Age Sub-Mariner'],
    ('fantastic four', '5'): ['First appearance of Doctor Doom'],
    ('fantastic four', '12'): ['Hulk vs Thing'],
    ('fantastic four', '45'): ['First appearance of Inhumans', 'First Black Bolt'],
    ('fantastic four', '48'): ['First appearance of Silver Surfer', 'First Galactus (cameo)'],
    ('fantastic four', '49'): ['First full Galactus'],
    ('fantastic four', '52'): ['First appearance of Black Panther'],
    ('fantastic four', '67'): ['First appearance of Him (Adam Warlock)'],

    # Avengers
    ('avengers', '1'): ['First appearance of Avengers team'],
    ('avengers', '4'): ['First Silver Age Captain America', 'Cap joins Avengers'],
    ('avengers', '16'): ['New Avengers lineup - Hawkeye, Scarlet Witch, Quicksilver'],
    ('avengers', '54'): ['First appearance of Ultron (cameo)'],
    ('avengers', '55'): ['First full Ultron'],
    ('avengers', '57'): ['First appearance of Vision'],
    ('avengers', '181'): ['First appearance of Scott Lang (Ant-Man)'],
    ('avengers', '195'): ['First appearance of Taskmaster'],

    # Iron Man / Tales of Suspense
    ('tales of suspense', '39'): ['First appearance of Iron Man', 'Origin of Iron Man'],
    ('tales of suspense', '52'): ['First appearance of Black Widow'],
    ('tales of suspense', '57'): ['First appearance of Hawkeye'],
    ('iron man', '55'): ['First appearance of Thanos', 'First Drax'],
    ('iron man', '128'): ['Demon in a Bottle storyline'],

    # Captain America
    ('captain america', '100'): ['First issue of solo series'],
    ('captain america', '117'): ['First appearance of Falcon'],
    ('captain america', '332'): ['Steve Rogers resigns as Captain America'],

    # Thor / Journey into Mystery
    ('journey into mystery', '83'): ['First appearance of Thor', 'Origin of Thor'],
    ('journey into mystery', '85'): ['First appearance of Loki'],
    ('journey into mystery', '112'): ['Thor vs Hulk'],
    ('thor', '165'): ['First full appearance of Adam Warlock (as Him)'],
    ('thor', '337'): ['First appearance of Beta Ray Bill'],

    # Batman
    ('batman', '1'): ['First appearance of Joker', 'First Catwoman'],
    ('batman', '181'): ['First appearance of Poison Ivy'],
    ('batman', '232'): ["First appearance of Ra's al Ghul"],
    ('batman', '251'): ['Joker - classic Neal Adams cover'],
    ('batman', '357'): ['First appearance of Jason Todd'],
    ('batman', '386'): ['First appearance of Black Mask'],
    ('batman', '404'): ['Batman: Year One begins'],
    ('batman', '428'): ['Death of Jason Todd'],
    ('batman', '497'): ['Bane breaks Batman'],
    ('batman', '567'): ['First appearance of Cassandra Cain (Batgirl)'],
    ('batman', '608'): ['Hush storyline begins'],

    # Detective Comics
    ('detective comics', '27'): ['First appearance of Batman'],
    ('detective comics', '31'): ['First Batman cover', 'Classic vampire cover'],
    ('detective comics', '33'): ['Origin of Batman'],
    ('detective comics', '38'): ['First appearance of Robin (Dick Grayson)'],
    ('detective comics', '140'): ['First appearance of Riddler'],
    ('detective comics', '168'): ['Origin of Red Hood'],
    ('detective comics', '225'): ['First appearance of Martian Manhunter'],
    ('detective comics', '359'): ['First appearance of Batgirl (Barbara Gordon)'],
    ('detective comics', '400'): ['First Man-Bat'],
    ('detective comics', '411'): ['First appearance of Talia al Ghul'],
    ('detective comics', '475'): ['First modern Joker (Marshall Rogers)'],

    # Action Comics
    ('action comics', '1'): ['First appearance of Superman', 'Most valuable comic'],
    ('action comics', '23'): ['First appearance of Lex Luthor'],
    ('action comics', '252'): ['First appearance of Supergirl'],
    ('action comics', '521'): ['First appearance of Vixen'],

    # Superman
    ('superman', '1'): ['First Superman solo comic', 'Origin retold'],
    ('superman', '75'): ['Death of Superman'],
    ('superman', '199'): ['First Superman vs Flash race'],

    # Teen Titans
    ('teen titans', '1'): ['First Teen Titans ongoing series'],
    ('teen titans', '2'): ['First appearance of Garth (Aqualad story)'],
    ('new teen titans', '1'): ['First appearance of Cyborg', 'First Starfire', 'First Raven'],
    ('new teen titans', '2'): ['First appearance of Deathstroke'],
    ('new teen titans', '16'): ['First appearance of Captain Carrot'],
    ('tales of the teen titans', '44'): ['First Nightwing', 'Dick Grayson becomes Nightwing'],
    ('tales of the teen titans', '42'): ['The Judas Contract begins'],

    # Justice League
    ('justice league', '1'): ['First appearance of Justice League'],
    ('justice league of america', '1'): ['First JLA ongoing series'],
    ('justice league of america', '21'): ['First Crisis on Earth-One/Earth-Two'],
    ('justice league of america', '29'): ['First appearance of Starman (Mikaal)'],

    # Wonder Woman
    ('wonder woman', '1'): ['First Wonder Woman solo series'],
    ('wonder woman', '98'): ['New origin (George Perez)'],
    ('wonder woman', '184'): ['First appearance of Nubia'],

    # Flash
    ('flash', '105'): ['First Silver Age Flash (Barry Allen ongoing)'],
    ('flash', '110'): ['First appearance of Kid Flash (Wally West)', 'First Weather Wizard'],
    ('flash', '123'): ['Flash of Two Worlds - First Earth-Two'],
    ('flash', '139'): ['First appearance of Reverse-Flash'],
    ('flash comics', '1'): ['First appearance of Flash (Jay Garrick)'],

    # Green Lantern
    ('green lantern', '1'): ['First Silver Age Green Lantern ongoing'],
    ('green lantern', '7'): ['First appearance of Sinestro'],
    ('green lantern', '59'): ['First appearance of Guy Gardner'],
    ('green lantern', '76'): ['Green Lantern/Green Arrow begins - socially relevant comics'],
    ('green lantern', '87'): ['First appearance of John Stewart'],

    # Other Marvel Keys
    ('marvel spotlight', '5'): ['First appearance of Ghost Rider (Johnny Blaze)'],
    ('marvel super-heroes', '13'): ['First appearance of Carol Danvers (Captain Marvel)'],
    ('hero for hire', '1'): ['First appearance of Luke Cage'],
    ('strange tales', '110'): ['First appearance of Doctor Strange'],
    ('strange tales', '135'): ['First appearance of Nick Fury, Agent of SHIELD'],
    ('daredevil', '1'): ['First appearance of Daredevil'],
    ('daredevil', '168'): ['First appearance of Elektra'],
    ('werewolf by night', '32'): ['First appearance of Moon Knight'],
    ('nova', '1'): ['First appearance of Nova (Richard Rider)'],
    ('ms. marvel', '1'): ['First appearance of Ms. Marvel (Carol Danvers costume)'],
    ('eternals', '1'): ['First appearance of Eternals'],
    ('howard the duck', '1'): ['First Howard the Duck ongoing'],
    ('new mutants', '87'): ['First appearance of Cable'],
    ('new mutants', '98'): ['First appearance of Deadpool'],

    # Other DC Keys
    ('brave and the bold', '28'): ['First appearance of Justice League'],
    ('brave and the bold', '54'): ['First appearance of Teen Titans'],
    ('showcase', '4'): ['First Silver Age Flash (Barry Allen)'],
    ('showcase', '22'): ['First Silver Age Green Lantern (Hal Jordan)'],
    ('showcase', '34'): ['First Silver Age Atom'],
    ('showcase', '37'): ['First Silver Age Metal Men'],
    ('house of secrets', '92'): ['First appearance of Swamp Thing'],
    ('forever people', '1'): ['First full appearance of Darkseid'],
    ('new gods', '1'): ['First appearance of Orion'],
    ("superman's pal jimmy olsen", '133'): ['First appearance of Darkseid (cameo)'],
    ('crisis on infinite earths', '7'): ['Death of Supergirl'],
    ('crisis on infinite earths', '8'): ['Death of Flash (Barry Allen)'],
    ('batman: the dark knight returns', '1'): ['First Dark Knight Returns'],
    ('watchmen', '1'): ['First Watchmen'],
}


def get_key_highlights(title: str, issue_number: Optional[str]) -> list:
    """
    Look up key highlights for a comic issue (first appearances, deaths, etc.)

    Args:
        title: Comic title
        issue_number: Issue number

    Returns:
        List of highlight strings
    """
    if not title or not issue_number:
        return []

    title_lower = title.lower().strip()
    issue_str = str(issue_number).strip().lstrip('#')

    # Direct lookup
    key = (title_lower, issue_str)
    if key in KEY_ISSUES:
        return KEY_ISSUES[key]

    # Build list of title variations to try
    title_variations = [
        title_lower,
        title_lower.replace('the ', ''),
        'the ' + title_lower,
    ]

    # Handle "The Invincible Iron Man" -> "iron man"
    if 'invincible iron man' in title_lower:
        title_variations.append('iron man')
    if 'iron man' in title_lower and 'invincible' not in title_lower:
        title_variations.append('invincible iron man')
        title_variations.append('the invincible iron man')

    # Handle "The Amazing Spider-Man" -> "amazing spider-man"
    if 'spider-man' in title_lower:
        title_variations.append('amazing spider-man')
        title_variations.append('the amazing spider-man')
        title_variations.append('spectacular spider-man')

    # Handle X-Men variations
    if 'uncanny' in title_lower:
        title_variations.append(title_lower.replace('uncanny ', ''))
        title_variations.append('x-men')
    if 'x-men' in title_lower and 'uncanny' not in title_lower:
        title_variations.append('uncanny x-men')

    # Handle "The Incredible Hulk" -> "incredible hulk"
    if 'incredible hulk' in title_lower:
        title_variations.append('incredible hulk')
        title_variations.append('hulk')
    if 'hulk' in title_lower and 'incredible' not in title_lower:
        title_variations.append('incredible hulk')
        title_variations.append('the incredible hulk')

    # Handle Teen Titans variations
    if 'teen titans' in title_lower:
        title_variations.append('teen titans')
        title_variations.append('new teen titans')
        title_variations.append('tales of the teen titans')

    # Handle Batman variations
    if 'batman' in title_lower:
        title_variations.append('batman')
        title_variations.append('detective comics')

    # Handle Flash variations
    if 'flash' in title_lower:
        title_variations.append('flash')
        title_variations.append('the flash')

    for var in title_variations:
        key = (var, issue_str)
        if key in KEY_ISSUES:
            return KEY_ISSUES[key]

    return []


async def lookup_comic_metadata(
    title: str,
    issue_number: Optional[str] = None,
    publisher: Optional[str] = None
) -> Dict[str, Any]:
    """
    Look up comic metadata from multiple online sources

    Args:
        title: Comic title (e.g., "Where Monsters Dwell")
        issue_number: Issue number (e.g., "4")
        publisher: Publisher name (e.g., "Marvel")

    Returns:
        Dictionary with writer, artist, year, description, key_highlights
    """
    logger.info(f"[LOOKUP] Starting lookup for '{title}' #{issue_number} ({publisher})")

    result = {
        'writer': None,
        'artist': None,
        'year': None,
        'description': None,
        'source': None,
        'key_highlights': []
    }

    # Look up key highlights first
    highlights = get_key_highlights(title, issue_number)
    if highlights:
        result['key_highlights'] = highlights
        logger.info(f"[LOOKUP] Found key highlights for '{title}' #{issue_number}: {highlights}")

    # First check our local database of known comics
    title_lower = title.lower().strip()
    for known_title, known_data in KNOWN_COMICS.items():
        if known_title in title_lower or title_lower in known_title:
            if not publisher and known_data.get('publisher'):
                result['publisher'] = known_data['publisher']
            if known_data.get('description'):
                result['description'] = known_data['description']
            if known_data.get('year_range'):
                # Try to extract a specific year if we have issue number
                year_range = known_data['year_range']
                if '-' in year_range:
                    start_year = year_range.split('-')[0]
                    if issue_number and issue_number.isdigit():
                        # Estimate year based on issue number (rough)
                        issue_num = int(issue_number)
                        try:
                            start = int(start_year)
                            # Roughly 12 issues per year
                            estimated_year = start + (issue_num // 12)
                            result['year'] = str(min(estimated_year, 2025))
                        except:
                            result['year'] = start_year
                    else:
                        result['year'] = start_year
            result['source'] = 'local_database'
            logger.info(f"Found local data for '{title}': {result}")
            break

    # Try ComicVine search
    try:
        logger.info(f"[LOOKUP] Trying ComicVine search...")
        comic_vine_result = await _search_comic_vine(title, issue_number, publisher)
        logger.info(f"[LOOKUP] ComicVine result: {comic_vine_result}")
        if comic_vine_result:
            # Update result with ComicVine data (don't overwrite existing data)
            for key in ['writer', 'artist', 'year', 'description']:
                if comic_vine_result.get(key) and not result.get(key):
                    result[key] = comic_vine_result[key]
            if comic_vine_result.get('source'):
                result['source'] = comic_vine_result['source']
            logger.info(f"[LOOKUP] Updated result from ComicVine: {result}")
            return result
    except Exception as e:
        logger.warning(f"[LOOKUP] Comic Vine lookup failed: {e}")

    # Try Grand Comics Database as fallback
    try:
        gcd_result = await _search_gcd(title, issue_number, publisher)
        if gcd_result:
            for key in ['writer', 'artist', 'year', 'description']:
                if gcd_result.get(key) and not result.get(key):
                    result[key] = gcd_result[key]
            if gcd_result.get('source'):
                result['source'] = gcd_result['source']
            return result
    except Exception as e:
        logger.warning(f"GCD lookup failed: {e}")

    # Try Marvel Wiki for Marvel comics
    if publisher and 'marvel' in publisher.lower():
        try:
            marvel_result = await _search_marvel_wiki(title, issue_number)
            if marvel_result:
                for key in ['writer', 'artist', 'year', 'description']:
                    if marvel_result.get(key) and not result.get(key):
                        result[key] = marvel_result[key]
                if marvel_result.get('source'):
                    result['source'] = marvel_result['source']
                return result
        except Exception as e:
            logger.warning(f"Marvel Wiki lookup failed: {e}")

    # Try DC Wiki for DC comics
    if publisher and 'dc' in publisher.lower():
        try:
            dc_result = await _search_dc_wiki(title, issue_number)
            if dc_result:
                for key in ['writer', 'artist', 'year', 'description']:
                    if dc_result.get(key) and not result.get(key):
                        result[key] = dc_result[key]
                if dc_result.get('source'):
                    result['source'] = dc_result['source']
                return result
        except Exception as e:
            logger.warning(f"DC Wiki lookup failed: {e}")

    return result


async def _search_comic_vine(
    title: str,
    issue_number: Optional[str],
    publisher: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Search Comic Vine for comic metadata"""

    # Build search query
    query_parts = [title]
    if issue_number and issue_number not in ['??', 'Unknown']:
        query_parts.append(f"#{issue_number}")

    search_query = ' '.join(query_parts)
    url = f"https://comicvine.gamespot.com/search/?q={quote_plus(search_query)}&resources=issue"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.debug(f"ComicVine returned status {resp.status}")
                    return None

                html = await resp.text()
                result = {}

                # Try to extract year from search results
                year_match = re.search(r'\((\d{4})\)', html)
                if year_match:
                    result['year'] = year_match.group(1)

                # Look for issue detail link
                issue_link_match = re.search(r'href="(https://comicvine\.gamespot\.com/[^"]+/4000-\d+/)"', html)
                if issue_link_match:
                    detail_url = issue_link_match.group(1)
                    detail_result = await _fetch_comic_vine_detail(session, detail_url, headers)
                    if detail_result:
                        result.update(detail_result)

                if result:
                    result['source'] = 'comicvine'

                return result if result else None

    except Exception as e:
        logger.debug(f"ComicVine search error: {e}")
        return None


async def _fetch_comic_vine_detail(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict
) -> Optional[Dict[str, Any]]:
    """Fetch detailed comic info from Comic Vine issue page"""
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None

            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            result = {}

            # Extract cover date/year
            cover_date_match = re.search(r'Cover Date.*?((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|\d{4})', html, re.DOTALL | re.IGNORECASE)
            if cover_date_match:
                date_str = cover_date_match.group(1)
                year_match = re.search(r'(\d{4})', date_str)
                if year_match:
                    result['year'] = year_match.group(1)

            # Look for credits in various formats
            # Try data-field attributes
            for field_type in ['person_credits', 'credits']:
                credits_div = soup.select_one(f'[data-field="{field_type}"]')
                if credits_div:
                    credit_text = credits_div.get_text(' ', strip=True)
                    if 'writer' in credit_text.lower():
                        writer_match = re.search(r'writer[:\s]+([^,\n]+)', credit_text, re.IGNORECASE)
                        if writer_match:
                            result['writer'] = writer_match.group(1).strip()
                    if 'artist' in credit_text.lower() or 'pencil' in credit_text.lower():
                        artist_match = re.search(r'(?:artist|pencil)[:\s]+([^,\n]+)', credit_text, re.IGNORECASE)
                        if artist_match:
                            result['artist'] = artist_match.group(1).strip()

            # Try to find writer/artist from link text
            all_links = soup.select('a')
            for link in all_links:
                link_text = link.get_text(strip=True)
                parent_text = link.parent.get_text(' ', strip=True) if link.parent else ''

                if 'writer' in parent_text.lower() or 'written' in parent_text.lower():
                    if len(link_text) > 2 and len(link_text) < 50 and not link_text.startswith('http'):
                        if not result.get('writer'):
                            result['writer'] = link_text
                elif 'pencil' in parent_text.lower() or 'artist' in parent_text.lower():
                    if len(link_text) > 2 and len(link_text) < 50 and not link_text.startswith('http'):
                        if not result.get('artist'):
                            result['artist'] = link_text

            # Extract description
            desc_elem = soup.select_one('.wiki-item-display, [data-field="description"], .issue-description')
            if desc_elem:
                desc = desc_elem.get_text(' ', strip=True)
                desc = re.sub(r'<[^>]+>', '', desc)  # Remove any remaining HTML
                desc = desc[:500]  # Limit length
                if desc and len(desc) > 20:
                    result['description'] = desc

            return result if result else None

    except Exception as e:
        logger.debug(f"Error fetching Comic Vine detail: {e}")
        return None


async def _search_gcd(
    title: str,
    issue_number: Optional[str],
    publisher: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Search Grand Comics Database for comic metadata"""

    # Build search URL
    query_parts = [title]
    if issue_number and issue_number not in ['??', 'Unknown']:
        query_parts.append(issue_number)

    search_query = ' '.join(query_parts)
    url = f"https://www.comics.org/searchNew/?q={quote_plus(search_query)}&search_object=issue"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None

                html = await resp.text()
                result = {}

                # GCD shows year in format like "1970"
                year_match = re.search(r'(?:cover date|published|on-sale)[:\s]*(?:\w+\s+)?(\d{4})', html, re.IGNORECASE)
                if year_match:
                    result['year'] = year_match.group(1)

                # Extract credits
                writer_match = re.search(r'(?:script|writer|written by)[:\s]*([^<\n;]+)', html, re.IGNORECASE)
                if writer_match:
                    writer = writer_match.group(1).strip()
                    writer = re.sub(r'\s*\([^)]*\)', '', writer)  # Remove parenthetical notes
                    if len(writer) > 2 and len(writer) < 100:
                        result['writer'] = writer

                artist_match = re.search(r'(?:pencils?|artist|art by)[:\s]*([^<\n;]+)', html, re.IGNORECASE)
                if artist_match:
                    artist = artist_match.group(1).strip()
                    artist = re.sub(r'\s*\([^)]*\)', '', artist)  # Remove parenthetical notes
                    if len(artist) > 2 and len(artist) < 100:
                        result['artist'] = artist

                if result:
                    result['source'] = 'gcd'

                return result if result else None

    except Exception as e:
        logger.debug(f"GCD search error: {e}")
        return None


async def _search_marvel_wiki(
    title: str,
    issue_number: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Search Marvel Wiki (Fandom) for comic metadata"""

    # Build search query - Marvel Wiki uses underscores
    query = title.replace(' ', '_')
    if issue_number and issue_number not in ['??', 'Unknown']:
        query += f"_Vol_1_{issue_number}"

    url = f"https://marvel.fandom.com/wiki/{quote_plus(query)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as resp:
                if resp.status != 200:
                    return None

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                result = {}

                # Look for infobox data
                infobox = soup.select_one('.portable-infobox, .infobox')
                if infobox:
                    infobox_text = infobox.get_text(' ', strip=True)

                    # Extract year
                    date_match = re.search(r'(?:Release|Cover) Date[:\s]*(?:\w+\s+)?(\d{4})', infobox_text, re.IGNORECASE)
                    if date_match:
                        result['year'] = date_match.group(1)

                    # Extract writer
                    writer_match = re.search(r'Writer[s]?[:\s]*([^|\n]+)', infobox_text, re.IGNORECASE)
                    if writer_match:
                        result['writer'] = writer_match.group(1).strip()[:100]

                    # Extract artist
                    artist_match = re.search(r'(?:Penciler|Artist)[s]?[:\s]*([^|\n]+)', infobox_text, re.IGNORECASE)
                    if artist_match:
                        result['artist'] = artist_match.group(1).strip()[:100]

                # Look for summary
                summary = soup.select_one('.mw-parser-output > p')
                if summary:
                    desc = summary.get_text(' ', strip=True)[:500]
                    if desc and len(desc) > 20:
                        result['description'] = desc

                if result:
                    result['source'] = 'marvel_wiki'

                return result if result else None

    except Exception as e:
        logger.debug(f"Marvel Wiki search error: {e}")
        return None


async def _search_dc_wiki(
    title: str,
    issue_number: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Search DC Wiki (Fandom) for comic metadata"""

    # Build search query - DC Wiki uses underscores and specific format
    query = title.replace(' ', '_')
    if issue_number and issue_number not in ['??', 'Unknown']:
        query += f"_Vol_1_{issue_number}"

    url = f"https://dc.fandom.com/wiki/{quote_plus(query)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as resp:
                if resp.status != 200:
                    return None

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                result = {}

                # Look for infobox data
                infobox = soup.select_one('.portable-infobox, .infobox, .pi-data')
                if infobox:
                    infobox_text = infobox.get_text(' ', strip=True)

                    # Extract year/date
                    date_match = re.search(r'(?:Release|Cover|Published)[^:]*[:\s]*(?:.*?)?(\d{4})', infobox_text, re.IGNORECASE)
                    if date_match:
                        result['year'] = date_match.group(1)

                    # Extract writer
                    writer_match = re.search(r'(?:Writer|Written)[s]?[:\s]*([^|\n\d]{2,60})', infobox_text, re.IGNORECASE)
                    if writer_match:
                        writer = writer_match.group(1).strip()
                        # Clean up common artifacts
                        writer = re.sub(r'\s*\([^)]*\)', '', writer)
                        if len(writer) > 2:
                            result['writer'] = writer[:100]

                    # Extract artist/penciler
                    artist_match = re.search(r'(?:Penciler|Penciller|Artist)[s]?[:\s]*([^|\n\d]{2,60})', infobox_text, re.IGNORECASE)
                    if artist_match:
                        artist = artist_match.group(1).strip()
                        artist = re.sub(r'\s*\([^)]*\)', '', artist)
                        if len(artist) > 2:
                            result['artist'] = artist[:100]

                # Look for summary paragraph
                summary = soup.select_one('.mw-parser-output > p')
                if summary:
                    desc = summary.get_text(' ', strip=True)[:500]
                    if desc and len(desc) > 20:
                        result['description'] = desc

                if result:
                    result['source'] = 'dc_wiki'
                    logger.info(f"Found DC Wiki data: {result}")

                return result if result else None

    except Exception as e:
        logger.debug(f"DC Wiki search error: {e}")
        return None


async def enrich_comic_info(comic_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich comic_info dict with missing metadata from online databases

    Args:
        comic_info: Dict with title, issue_number, publisher, year (some may be None)

    Returns:
        Enriched comic_info with writer, artist, year filled in where possible
    """
    title = comic_info.get('title')
    if not title or title in ['Unknown', 'Unidentified Comic', '']:
        logger.info(f"[ENRICH] Skipping - no valid title: {title}")
        return comic_info

    issue_number = comic_info.get('issue_number')
    if issue_number in ['??', 'Unknown', None]:
        issue_number = None

    publisher = comic_info.get('publisher')

    logger.info(f"[ENRICH] Looking up metadata for '{title}' #{issue_number} ({publisher})")

    # Look up additional metadata
    try:
        metadata = await asyncio.wait_for(
            lookup_comic_metadata(title, issue_number, publisher),
            timeout=15
        )

        logger.info(f"[ENRICH] Got metadata: {metadata}")

        # Fill in missing fields (don't overwrite existing data)
        if metadata.get('year') and not comic_info.get('year'):
            comic_info['year'] = metadata['year']
            logger.info(f"[ENRICH] Added year: {metadata['year']}")

        if metadata.get('writer'):
            comic_info['writer'] = metadata['writer']
            logger.info(f"[ENRICH] Added writer: {metadata['writer']}")

        if metadata.get('artist'):
            comic_info['artist'] = metadata['artist']
            logger.info(f"[ENRICH] Added artist: {metadata['artist']}")

        if metadata.get('description'):
            comic_info['description'] = metadata['description']

        if metadata.get('publisher') and not comic_info.get('publisher'):
            comic_info['publisher'] = metadata['publisher']

        # Add key highlights (first appearances, etc.)
        if metadata.get('key_highlights'):
            comic_info['key_highlights'] = metadata['key_highlights']
            logger.info(f"[ENRICH] Found key highlights: {metadata['key_highlights']}")

        logger.info(f"[ENRICH] Final enriched comic_info: {comic_info}")

    except asyncio.TimeoutError:
        logger.warning(f"[ENRICH] Comic metadata lookup timed out for '{title}'")
    except Exception as e:
        logger.warning(f"[ENRICH] Comic metadata enrichment error: {e}")
        import traceback
        logger.warning(f"[ENRICH] Traceback: {traceback.format_exc()}")

    return comic_info
