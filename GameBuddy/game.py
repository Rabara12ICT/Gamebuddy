#!/usr/bin/env python3
"""GameBuddy: IT QUEST - The Lost Code Kingdom  (2D, pygame)
Setup:  pip install pygame      Run:  python game.py
Resizable desktop window; touchscreen play is designed for landscape orientation.
Dev shortcuts (separate from normal play):  python game.py --dev
  F2 hub | F3 +100 XP | F4 complete next quest | F5 east island | F6 fall test
"""
import asyncio, pygame, json, os, sys, random, math, threading, hashlib, hmac, secrets, time
from types import SimpleNamespace as NS

pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pygame.mixer = None

W, H = 1000, 600
WEB = sys.platform == "emscripten"
display = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("Game Buddy: Code Quest")
scr = pygame.Surface((W, H))
clk = pygame.time.Clock()

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGIN_ASSET_DIR = os.path.join(ASSET_DIR, "login")
LOGIN_TITLE_IMAGE = pygame.image.load(
    os.path.join(LOGIN_ASSET_DIR, "title_logo.png")
).convert_alpha()


def find_login_music():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    preferred = ([os.path.join(base_dir, "login_music.ogg")] if WEB else [
        os.path.join(base_dir, "login_music.mp3"),
        os.path.join(base_dir, "login.mp3"),
        os.path.join(base_dir, "bgm.mp3"),
    ])
    for path in preferred:
        if os.path.isfile(path):
            return path

    candidates = []
    for filename in sorted(os.listdir(base_dir)):
        full_path = os.path.join(base_dir, filename)
        if not os.path.isfile(full_path):
            continue
        lower = filename.lower()
        if lower == "parkour sounds.mp3":
            continue
        if lower.endswith((".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")):
            candidates.append(full_path)
    for path in candidates:
        if path.lower().endswith(".ogg" if WEB else ".mp3"):
            return path
    return candidates[0] if candidates and not WEB else None

LOGIN_MUSIC_PATH = find_login_music()
CURRENT_MUSIC_PATH = None
FAILED_MUSIC_PATH = None
if pygame.mixer is not None and LOGIN_MUSIC_PATH:
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=44100, channels=2, buffer=512)
        pygame.mixer.music.load(LOGIN_MUSIC_PATH)
        pygame.mixer.music.set_volume(0.35)
        CURRENT_MUSIC_PATH = LOGIN_MUSIC_PATH
    except Exception:
        LOGIN_MUSIC_PATH = None

PARKOUR_MUSIC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "parkour sounds.ogg" if WEB else "parkour sounds.mp3")
if not os.path.isfile(PARKOUR_MUSIC_PATH):
    PARKOUR_MUSIC_PATH = None

SOUND_EFFECT_FILES = {
    "jump": "mixkit-player-jumping-in-a-video-game-2043.ogg" if WEB else "mixkit-player-jumping-in-a-video-game-2043.wav",
    "fall": "mixkit-player-losing-or-failing-2042.ogg" if WEB else "mixkit-player-losing-or-failing-2042.wav",
    "crystal": "mixkit-winning-a-coin-video-game-2069.ogg" if WEB else "mixkit-winning-a-coin-video-game-2069.wav",
}
BOSS_DEFEAT_SOUND_FILES = {
    "Python": "PYTHON BOSS.ogg" if WEB else "PYTHON BOSS.mp3",
    "Java": "JAVA BOSS.ogg" if WEB else "JAVA BOSS.mp3",
    "JavaScript": "JAVA SCRIPT BOSS.ogg" if WEB else "JAVA SCRIPT BOSS.mp3",
    "HTML": "HTML.ogg" if WEB else "HTML.mp3",
    "CSS": "CSS.ogg" if WEB else "CSS.mp3",
}
SOUND_EFFECTS = {}
BOSS_DEFEAT_SOUNDS = {}
BOSS_DEFEAT_CHANNEL = None
if pygame.mixer is not None:
    sound_dir = os.path.dirname(os.path.abspath(__file__))
    SOUND_EFFECTS = {
        name: pygame.mixer.Sound(os.path.join(sound_dir, filename))
        for name, filename in SOUND_EFFECT_FILES.items()
    }
    for sound in SOUND_EFFECTS.values():
        sound.set_volume(0.7)
    BOSS_DEFEAT_SOUNDS = {
        language: pygame.mixer.Sound(os.path.join(sound_dir, filename))
        for language, filename in BOSS_DEFEAT_SOUND_FILES.items()
    }
    for sound in BOSS_DEFEAT_SOUNDS.values():
        sound.set_volume(0.85)


def play_sound(name):
    if not G.S.get("settings", {}).get("sfx", True):
        return
    sound = SOUND_EFFECTS.get(name)
    if sound is not None:
        sound.play()

def play_boss_defeat_sound(language):
    global BOSS_DEFEAT_CHANNEL
    if not G.S.get("settings", {}).get("sfx", True):
        return
    sound = BOSS_DEFEAT_SOUNDS.get(language)
    if sound is not None:
        if BOSS_DEFEAT_CHANNEL is not None:
            BOSS_DEFEAT_CHANNEL.stop()
        BOSS_DEFEAT_CHANNEL = sound.play()

def stop_boss_defeat_sound():
    global BOSS_DEFEAT_CHANNEL
    if BOSS_DEFEAT_CHANNEL is not None:
        BOSS_DEFEAT_CHANNEL.stop()
        BOSS_DEFEAT_CHANNEL = None


def should_play_menu_music():
    return (G.S.get("settings", {}).get("music", True)
            and G.state in ("login", "home", "leaderboard", "progress", "shop", "pause"))

def update_background_music():
    global CURRENT_MUSIC_PATH, FAILED_MUSIC_PATH
    if pygame.mixer is None:
        return
    if not G.S.get("settings", {}).get("music", True):
        desired_path = None
    elif G.state == "obby":
        desired_path = PARKOUR_MUSIC_PATH
    elif should_play_menu_music():
        desired_path = LOGIN_MUSIC_PATH
    else:
        desired_path = None

    if desired_path is None:
        if CURRENT_MUSIC_PATH is not None or pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        CURRENT_MUSIC_PATH = None
        FAILED_MUSIC_PATH = None
        return
    if desired_path == FAILED_MUSIC_PATH:
        return

    try:
        if desired_path != CURRENT_MUSIC_PATH:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(desired_path)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
            CURRENT_MUSIC_PATH = desired_path
        elif not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
    except pygame.error as error:
        CURRENT_MUSIC_PATH = None
        FAILED_MUSIC_PATH = desired_path
        print("Could not play background music: %s" % error, file=sys.stderr)
        toast("Background music could not be played.")
def fnt(n, b=False): return pygame.font.SysFont("consolas,dejavusansmono,couriernew,monospace", n, b)
F, FS, FB = fnt(18), fnt(15), fnt(32, True)
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gamebuddy_saves.json")
AUTH_SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gamebuddy_accounts.json")
STORY_QUEST_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "story_quest_data.json")
with open(STORY_QUEST_DATA_PATH, encoding="utf-8") as story_data_file:
    STORY_QUEST_DATA = json.load(story_data_file)
STORY_LANGUAGE_NAMES = ("Python", "Java", "JavaScript", "HTML", "CSS")
STORY_LANGUAGE_ENDINGS = {
    "Python": (
        "CHAPTER 9  |  THE PYTHON BEACON ANSWERS",
        "The Guardian chooses the clear path, and the last Python switch clicks into "
        "place. The beacon answers with a steady signal. Byte hears the Core respond "
        "for the first time since the Virus King scrambled it. Portals flicker back "
        "to life across the Lost Code Kingdom as the Virus King's shadow retreats. "
        "Game Buddy, Byte, and the Guardian stand together beside the glowing Core.",
    ),
    "Java": (
        "CHAPTER 9  |  THE JAVA ARRAY",
        "The Guardian gathers the final signal colors into a Java array, and the "
        "beacon sends them together to the Core. Its scrambled command resolves at "
        "last. The Kingdom's portals light up again, and the Virus King's shadow is "
        "forced back from the citadel. Game Buddy and Byte stand beside the Guardian "
        "as the Core shines with every restored signal.",
    ),
    "JavaScript": (
        "CHAPTER 9  |  THE SIGNAL UNFROZEN",
        "The Guardian finds the typo and repairs the final JavaScript beacon. A clean "
        "console message races through the frozen towers, carrying Byte's signal to "
        "the Core. One by one, the towers wake and the Virus King's interference "
        "breaks apart. Game Buddy and Byte watch the Lost Code Kingdom's signal return "
        "around the shining Core.",
    ),
    "HTML": (
        "CHAPTER 9  |  THE KINGDOM RECONNECTED",
        "The Guardian places the final status inside the HTML page's div, completing "
        "the map Byte needed. Its links reconnect the islands, and the restored route "
        "leads Game Buddy and Byte back to the Core. Portals wake across the Lost Code "
        "Kingdom while the Virus King's broken signal fades. No part of the Kingdom "
        "is cut off anymore.",
    ),
    "CSS": (
        "CHAPTER 9  |  THE CORE IN THE LIGHT",
        "The Guardian styles the final div panel, making the Core's restored status "
        "impossible to miss. Its signal shines through the CSS world and into every "
        "portal. Byte sees lights return across the Lost Code Kingdom, leaving the "
        "Virus King's shadow nowhere to hide. At last, the Core glows again and the "
        "portals answer Game Buddy and Byte.",
    ),
}
STORY_QUESTION_TYPES = ("multiple_choice", "fill_blank", "typing")
for story_language in STORY_LANGUAGE_NAMES:
    if story_language not in STORY_QUEST_DATA.get("languages", {}):
        raise ValueError("Story quest data is missing the %s language path." % story_language)
    story_topics = STORY_QUEST_DATA["languages"][story_language].get("topics", [])
    if len(story_topics) != 5:
        raise ValueError("%s story quest data must contain exactly five topics." % story_language)
    for story_topic in story_topics:
        story_questions = story_topic.get("questions", [])
        if len(story_questions) != 3 or tuple(q.get("type") for q in story_questions) != STORY_QUESTION_TYPES:
            raise ValueError("%s / %s must have MC, fill-blank, and typing questions in order." %
                             (story_language, story_topic.get("topic", "unknown topic")))
        for story_question in story_questions:
            choices = story_question.get("options" if story_question["type"] == "multiple_choice"
                                         else "bank" if story_question["type"] == "fill_blank"
                                         else "choices", [])
            if not choices or not set(story_question.get("answers", [])).intersection(set(choices)):
                raise ValueError("%s / %s has missing choices or an answer outside its choices." %
                                 (story_language, story_topic.get("topic", "unknown topic")))
            if story_question["type"] == "multiple_choice" and len(choices) != 4:
                raise ValueError("%s / %s multiple-choice questions must have four options." %
                                 (story_language, story_topic.get("topic", "unknown topic")))
STORY_QUEST_DATA["languages"]["CSS"]["color"] = [226, 110, 170]  # palette tweak; data file unchanged
PASSWORD_ITERATIONS = 240000
DEV = "--dev" in sys.argv
WHITE, GOLD, CYAN, RED, GREEN = (244, 240, 226), (244, 194, 72), (96, 214, 226), (230, 72, 84), (156, 232, 72)
BUILD_STEPS = [
    ("PLAN", "quests + flow", "First, map the learning journey: quests, rewards, and how each challenge fits together."),
    ("PYGAME", "input + loop", "Build the real-time Pygame loop for keyboard input, movement, physics, and drawing each frame."),
    ("WORLD", "portals + code", "Create the worlds, portals, Byte, and hands-on HTML, logic, networking, and coding challenges."),
    ("PROGRESS", "XP + saves", "Add player accounts, XP, crystals, unlocks, and save files so progress carries across sessions."),
    ("TEST", "run + refine", "Run learners' code against test cases, explain mistakes, then polish the game from playtesting."),
]
BUILD_STEP_SECONDS = 2.8


CODE_ANSWERS = {
    "double_it": "return n * 2",
    "is_even": "return n % 2 == 0",
    "sum_to": "return sum(range(1, n + 1))",
    "reverse_str": "return s[::-1]",
    "count_vowels": "return sum(ch.lower() in 'aeiou' for ch in s)",
    "is_palindrome": "return s == s[::-1]",
    "fizz_buzz": "if n % 15 == 0:\n        return 'FizzBuzz'\n    if n % 3 == 0:\n        return 'Fizz'\n    if n % 5 == 0:\n        return 'Buzz'\n    return str(n)",
    "max_of": "return max(arr)",
    "cube": "return n ** 3",
    "triple": "return n * 3",
    "add": "return a + b",
    "is_positive": "return n > 0",
    "is_zero": "return n == 0",
    "smaller": "return min(a, b)",
    "last_item": "return items[-1]",
    "count_items": "return len(items)",
    "double_items": "return [item * 2 for item in items]",
    "sum_list": "return sum(items)",
    "absolute": "return abs(n)",
    "average": "return (a + b) / 2",
    "first_char": "return s[0] if s else ''",
    "last_char": "return s[-1] if s else ''",
    "make_upper": "return s.upper()",
    "remove_spaces": "return s.replace(' ', '')",
    "word_count": "return len(s.split())",
    "repeat_text": "return s * n",
    "has_digit": "return any(ch.isdigit() for ch in s)",
    "first_vowel_index": "for index, ch in enumerate(s):\n        if ch.lower() in 'aeiou':\n            return index\n    return -1",
    "replace_spaces": "return s.replace(' ', '-')",
    "is_empty": "return s == ''",
    "initials": "return ''.join(word[0].upper() for word in name.split())",
    "count_letter": "return s.lower().count(letter.lower())",
    "is_odd": "return n % 2 != 0",
    "clamp": "return min(high, max(low, n))",
    "second_item": "return items[1]",
    "squares": "return [item * item for item in items]",
    "count_even": "return sum(item % 2 == 0 for item in items)",
    "join_words": "return ' '.join(words)",
    "unique": "result = []\n    for item in items:\n        if item not in result:\n            result.append(item)\n    return result",
    "count_down": "return list(range(n, 0, -1))",
    "second_largest": "return sorted(set(items))[-2]",
    "merge_sorted": "return sorted(a + b)",
    "digit_sum": "return sum(int(digit) for digit in str(n))",
    "rotate_left": "return items[1:] + items[:1] if items else []",
}

def mc(n, c, b, xp, qs): return dict(n=n, c=c, b=b, xp=xp, t="mc", qs=qs)
def fix(p, code, a, h, ci=False, solution=None):
    return dict(k="fix", p=p, c=code, a=a, h=h, ci=ci, s="",
                solution=solution or a[0])
def code(p, fn, start, tests, h):
    answer = "def %s:\n    %s" % (start.splitlines()[0][4:-1], CODE_ANSWERS[fn])
    return dict(k="code", p=p, fn=fn, s=start, t=tests, h=h, solution=answer)
def trial(n, c, b, xp, items): return dict(n=n, c=c, b=b, xp=xp, t="tr", items=items)
CH = [
 mc("The Portal of HTML", (74, 163, 255), "HTML Explorer", 100, [
  ("Which HTML tag creates a paragraph?", ["<h1>", "<p>", "<img>", "<body>"], 1, "<p> wraps paragraph text."),
  ("Which tag holds all visible page content?", ["<head>", "<title>", "<body>", "<meta>"], 2, "<body> holds what visitors see."),
  ("Which tag creates a link?", ["<a>", "<link>", "<href>", "<nav>"], 0, "<a href=...> is the anchor tag.")]),
 mc("The JavaScript Forest", (76, 255, 138), "Logic Master", 150, [
  ("Which keyword declares a changeable variable?", ["let", "const", "int", "fixed"], 0, "let allows reassignment; const does not."),
  ("What does 5 % 2 return?", ["2.5", "1", "0", "2"], 1, "% is the remainder, so 1."),
  ("How many times does for(let i=0;i<3;i++) run?", ["2", "3", "4", "Forever"], 1, "i is 0, 1, 2: three times.")]),
 mc("The C++ Citadel", (255, 154, 60), "Code Guardian", 200, [
  ("Fix the bug: int x = 5__", ["}", ";", ":", ","], 1, "C++ statements end with a semicolon."),
  ("Which line prints text in C++?", ['cout << "Hi";', 'print("Hi")', "echo Hi", 'System.out("Hi")'], 0, "cout with << writes to the console."),
  ("Which is a valid C++ condition?", ["if x > 3 then", "if (x > 3) { }", "if x > 3:", "when (x > 3)"], 1, "C++ needs parentheses and braces.")]),
 mc("The Network Abyss", (226, 110, 170), "Network Defender", 250, [
  ("Which device forwards packets between networks?", ["Switch", "Router", "Monitor", "Keyboard"], 1, "Routers connect different networks."),
  ("Which is a valid IPv4 address?", ["192.168.1.10", "300.1.1.1", "192.168.1", "1.2.3.4.5"], 0, "Four numbers from 0 to 255."),
  ("Which subnet mask matches /24?", ["255.0.0.0", "255.255.0.0", "255.255.255.0", "255.255.255.255"], 2, "/24 means 24 network bits.")]),
 mc("The Data Vault", (255, 210, 74), "Data Keeper", 250, [
  ("Which key uniquely identifies each row?", ["Foreign key", "Primary key", "Spare key", "Index card"], 1, "A primary key is unique per row."),
  ("Which SQL gets all rows from users?", ["GET * users", "SELECT * FROM users;", "OPEN users", "FETCH users *"], 1, "SELECT columns FROM table."),
  ("A row in a table is also called a...", ["field", "record", "schema", "query"], 1, "A row is a record.")]),
 dict(n="The Virus King's Fortress", c=(255, 51, 85), b="Kingdom Savior", xp=300, t="boss"),
 trial("The Bug Hunter's Lab", (94, 225, 255), "Bug Hunter", 300, [
  fix("This loop should add 1+2+3 into total but total stays 0. Type the corrected line.", "total = 0\nfor i in range(1, 4):\n    total + i\nprint(total)", ["total+=i", "total=total+i"], "The sum is never stored."),
  fix("What does this print? Type the exact output.", 'print("2" + "3")', ["23"], "+ joins strings."),
  fix("This raises an error. Type the corrected if line.", "x = 4\nif x = 5:\n    print('Five')", ["ifx==5:"], "= assigns, == compares.")]),
 trial("The Algorithm Arena", (255, 179, 71), "Algorithm Ace", 300, [
  code("Write double_it(n) returning n times 2.", "double_it", "def double_it(n):\n    pass", [((2,), 4), ((0,), 0), ((-3,), -6)], "return n * 2"),
  code("Write is_even(n): True if even, else False.", "is_even", "def is_even(n):\n    pass", [((4,), True), ((7,), False), ((0,), True)], "Use n % 2 == 0"),
  code("Write sum_to(n) returning 1+2+...+n.", "sum_to", "def sum_to(n):\n    pass", [((3,), 6), ((1,), 1), ((10,), 55)], "Loop with a total, or sum(range(1, n+1)).")]),
 trial("The String Sorcerer", (226, 110, 170), "String Sorcerer", 300, [
  code("Write reverse_str(s) returning the text backwards.", "reverse_str", "def reverse_str(s):\n    pass", [(("abc",), "cba"), (("Code",), "edoC"), (("",), "")], "s[::-1]"),
  code("Write count_vowels(s): count a,e,i,o,u (any case).", "count_vowels", "def count_vowels(s):\n    pass", [(("hello",), 2), (("sky",), 0), (("AEIOU",), 5)], "Lowercase, then count characters in 'aeiou'."),
  code("Write is_palindrome(s): True if s reads the same backwards.", "is_palindrome", "def is_palindrome(s):\n    pass", [(("level",), True), (("code",), False), (("a",), True)], "Compare s with s[::-1].")]),
 trial("The Final Compiler", (76, 255, 138), "Master Coder", 400, [
  code("Write fizz_buzz(n): 'FizzBuzz' if divisible by 3 and 5, 'Fizz' by 3, 'Buzz' by 5, else str(n).", "fizz_buzz", "def fizz_buzz(n):\n    pass", [((3,), "Fizz"), ((5,), "Buzz"), ((15,), "FizzBuzz"), ((7,), "7")], "Test divisibility by 15 first."),
  code("Write max_of(arr) returning the largest number.", "max_of", "def max_of(arr):\n    pass", [(([3, 9, 2],), 9), (([-5, -2],), -2), (([7],), 7)], "Start with arr[0] and compare the rest."),
  fix("Write a SQL query returning the name column of users older than 18.", "Table users(id, name, age)", ["selectnamefromuserswhereage>18"], "SELECT column FROM table WHERE condition", True, "SELECT name FROM users WHERE age > 18;")]),
]
CH[0]["qs"].extend([
 ("Which tag creates the largest standard heading?", ["<h6>", "<head>", "<h1>", "<heading>"], 2, "<h1> is the largest standard heading."),
 ("Which attribute gives an image its source file?", ["href", "src", "alt", "link"], 1, "The src attribute points to an image file."),
 ("Which tag embeds an image?", ["<picturefile>", "<img>", "<image>", "<src>"], 1, "<img> embeds an image."),
 ("Which attribute describes an image for screen readers?", ["title", "alt", "name", "role"], 1, "The alt attribute provides alternative text."),
 ("Which tag creates an unordered list?", ["<ol>", "<ul>", "<li>", "<list>"], 1, "<ul> creates a bulleted list."),
 ("Which tag marks one item in a list?", ["<item>", "<li>", "<ul>", "<listitem>"], 1, "<li> is a list item."),
 ("Which tag creates a table row?", ["<td>", "<th>", "<tr>", "<table-row>"], 2, "<tr> defines a table row."),
 ("Which attribute connects a label to an input id?", ["for", "src", "action", "target"], 0, "The label's for value matches the input id."),
 ("Which tag creates a form control for typed text?", ["<input>", "<type>", "<text>", "<formtext>"], 0, "<input> creates an input control."),
 ("Which element gives a document its browser-tab title?", ["<header>", "<title>", "<caption>", "<h1>"], 1, "<title> sets the browser-tab title."),
 ("Which tag is used for a line break?", ["<break>", "<lb>", "<br>", "<newline>"], 2, "<br> inserts a line break."),
 ("Which attribute opens a link in a new tab?", ["target=\"_blank\"", "open=\"new\"", "tab=\"new\"", "window=\"open\""], 0, "target=\"_blank\" requests a new browsing context."),
])
CH[1]["qs"].extend([
 ("Which keyword declares a variable that cannot be reassigned?", ["let", "const", "varies", "static"], 1, "Use const when the binding will not be reassigned."),
 ("What is 8 * 3?", ["11", "24", "83", "5"], 1, "8 times 3 is 24."),
 ("What does typeof 42 return?", ["\"number\"", "\"integer\"", "\"42\"", "\"float\""], 0, "typeof reports the type as the string \"number\"."),
 ("Which operator checks strict equality?", ["=", "===", "=>", "!="], 1, "=== compares without type coercion."),
 ("What is the first array index?", ["0", "1", "-1", "It varies"], 0, "JavaScript arrays are zero-indexed."),
 ("What does [4, 5].length return?", ["1", "2", "5", "4"], 1, "The array has two elements."),
 ("Which method adds an item to the end of an array?", ["pop()", "push()", "shift()", "join()"], 1, "push() appends an item."),
 ("What does Boolean(0) return?", ["true", "false", "0", "null"], 1, "Zero is a falsy value."),
 ("Which keyword starts a conditional branch?", ["when", "if", "loop", "caseif"], 1, "Use if to start a conditional."),
 ("What does 10 / 2 return?", ["5", "8", "20", "102"], 0, "10 divided by 2 is 5."),
 ("Which symbol starts a single-line JavaScript comment?", ["<!--", "//", "**", "##"], 1, "// starts a single-line comment."),
 ("What does \"Hi\".toLowerCase() return?", ["\"HI\"", "\"hi\"", "\"Hi\"", "hi()"], 1, "toLowerCase() returns lowercase text."),
])
CH[2]["qs"].extend([
 ("Which type stores a whole number in C++?", ["int", "string", "bool", "char[]"], 0, "int is a standard integer type."),
 ("Which operator compares two values for equality in C++?", ["=", "==", "=>", ":="], 1, "== compares; = assigns."),
 ("Which header is commonly used for std::cout?", ["<iostream>", "<output>", "<console>", "<print>"], 0, "Include <iostream> for standard input and output."),
 ("What does a function usually use to send a value back?", ["break", "return", "cout", "using"], 1, "return sends a value to the caller."),
 ("Which type represents true or false?", ["bool", "int", "float", "char"], 0, "bool stores true or false."),
 ("Which loop checks its condition before each iteration?", ["while", "do-while only", "switch", "struct"], 0, "A while loop tests its condition before running the body."),
 ("What is the value of 7 % 4 in C++?", ["1", "1.75", "3", "4"], 2, "The remainder of 7 divided by 4 is 3."),
 ("Which container is commonly used for a resizable sequence?", ["std::vector", "std::number", "std::loop", "std::arraylist"], 0, "std::vector is a resizable sequence container."),
 ("Which symbol ends a C++ statement?", [":", ";", ".", ","], 1, "A semicolon ends most C++ statements."),
 ("What does ++i do?", ["Adds one to i", "Subtracts one", "Squares i", "Sets i to zero"], 0, "The increment operator adds one."),
 ("Which keyword defines a class in C++?", ["class", "object", "define", "record"], 0, "Use class to define a class."),
 ("Which operator accesses a member through an object?", ["-> only", ".", "::", "#"], 1, "The dot operator accesses a member through an object."),
])
CH[3]["qs"].extend([
 ("What does DNS primarily translate?", ["Domain names to IP addresses", "Packets to cables", "Passwords to usernames", "Files to folders"], 0, "DNS resolves domain names to network records such as IP addresses."),
 ("Which protocol is commonly used to load secure websites?", ["HTTPS", "FTP", "SMTP", "DHCP"], 0, "HTTPS protects web traffic using TLS."),
 ("What does LAN stand for?", ["Local Area Network", "Large Access Node", "Linked Address Number", "Long Area Name"], 0, "LAN means Local Area Network."),
 ("Which protocol automatically assigns network settings to devices?", ["DHCP", "HTML", "SSH", "USB"], 0, "DHCP can assign IP configuration automatically."),
 ("How many bits are in an IPv4 address?", ["16", "32", "64", "128"], 1, "IPv4 addresses contain 32 bits."),
 ("What is the usual purpose of a firewall?", ["Filter network traffic", "Store web pages", "Increase screen brightness", "Assign file names"], 0, "A firewall applies rules to network traffic."),
 ("Which device commonly connects multiple devices within one LAN?", ["Switch", "Scanner", "Projector", "Microphone"], 0, "A switch forwards traffic among devices on a LAN."),
 ("What is latency?", ["Time delay in data transfer", "Maximum disk size", "A type of password", "Number of web pages"], 0, "Latency is the time delay before data transfer or response."),
 ("Which protocol is commonly used to send email between mail servers?", ["SMTP", "DHCP", "ARP", "HTML"], 0, "SMTP is used to send email."),
 ("What does Wi-Fi provide?", ["Wireless network access", "Extra storage", "A programming language", "A printer cartridge"], 0, "Wi-Fi provides wireless network connectivity."),
 ("Which address identifies a device on an IP network?", ["IP address", "File extension", "HTML tag", "Serial key"], 0, "An IP address identifies a network interface logically."),
 ("What does a router commonly do with packets?", ["Forwards them between networks", "Compiles them", "Displays them", "Prints them"], 0, "Routers forward packets between networks."),
])
CH[4]["qs"].extend([
 ("Which SQL clause filters rows?", ["WHERE", "ORDER", "COLUMN", "TABLE"], 0, "WHERE selects rows matching a condition."),
 ("Which SQL command adds a new row?", ["INSERT", "UPDATE", "SELECT", "ALTER"], 0, "INSERT adds rows to a table."),
 ("Which SQL clause sorts a result set?", ["ORDER BY", "GROUP INTO", "SORT ROW", "RANK TABLE"], 0, "ORDER BY sorts query results."),
 ("What does a foreign key typically reference?", ["A key in another table", "A display color", "A file name", "A query comment"], 0, "A foreign key links to a key in another table."),
 ("Which SQL function counts rows?", ["COUNT(*)", "TOTAL ROW", "SUM ROWS", "SIZE(*)"], 0, "COUNT(*) counts rows."),
 ("Which SQL command changes existing rows?", ["UPDATE", "INSERT", "CREATE", "SELECT"], 0, "UPDATE modifies existing rows."),
 ("Which clause groups rows for aggregate calculations?", ["GROUP BY", "ORDER BY", "WHERE BY", "JOIN BY"], 0, "GROUP BY groups rows by selected columns."),
 ("Which SQL keyword removes rows matching a condition?", ["DELETE", "DROP COLUMN", "REMOVE", "CLEAR"], 0, "DELETE removes rows from a table."),
 ("What does NULL generally represent in a database?", ["Missing or unknown value", "The number zero", "An empty table", "A primary key"], 0, "NULL represents an absent or unknown value."),
 ("Which join returns rows with matching values in both tables?", ["INNER JOIN", "OUTER ONLY", "CROSS DELETE", "MATCH TABLE"], 0, "INNER JOIN returns rows matching the join condition."),
 ("Which SQL keyword removes duplicate result rows?", ["DISTINCT", "UNIQUE ROWS", "CLEAN", "SINGLE"], 0, "DISTINCT removes duplicate rows from the result."),
 ("Which statement creates a new table?", ["CREATE TABLE", "NEW TABLE", "INSERT TABLE", "MAKE ROW"], 0, "CREATE TABLE defines a new table."),
])
CH[6]["items"].extend([
 fix("Correct this Python assignment so count increases by one.", "count = 3\ncount = count", ["count+=1", "count=count+1"], "Assign the old value plus one."),
 fix("Correct the equality check in this if statement.", "if score = 10:\n    print('yes')", ["ifscore==10:"], "Use == to compare values."),
 fix("Complete the missing colon.", "for item in items_", ["foriteminitems:"], "Python compound statements end with a colon."),
 fix("Change this to print the word hello.", "print(hello)", ["print('hello')", "print(\"hello\")"], "Text literals need quotes."),
 fix("Correct this list index to access the first item.", "colors[1]", ["colors[0]"], "Python lists start at index zero."),
 fix("Fix the misspelled keyword.", "prit('Ready')", ["print('Ready')", "print(\"Ready\")"], "The built-in output function is print."),
 fix("Correct this condition so it tests whether x is greater than 5.", "if x => 5:", ["ifx>5:", "ifx>=5:"], "Python uses > for greater than and >= for greater-than-or-equal."),
 fix("Correct the loop range so it visits 0, 1, and 2.", "for i in range(1, 3):", ["foriinrange(3):"], "range(3) produces 0, 1, and 2."),
 fix("Make this variable hold the text Code.", "message = Code", ["message='Code'", "message=\"Code\""], "Text must be written as a quoted string."),
 fix("Fix the missing closing parenthesis.", "print('Done'", ["print('Done')", "print(\"Done\")"], "Close the print call with a parenthesis."),
 fix("Correct this boolean value in Python.", "active = Truee", ["active=true", "active=True"], "Python's boolean literal is True with a capital T."),
 fix("Correct the list append call.", "items.add(4)", ["items.append(4)"], "Use append() to add an item to a Python list."),
])
CH[7]["items"].extend([
 code("Write cube(n) returning n cubed.", "cube", "def cube(n):\n    pass", [((2,), 8), ((-3,), -27), ((0,), 0)], "Return n ** 3."),
 code("Write triple(n) returning three times n.", "triple", "def triple(n):\n    pass", [((2,), 6), ((0,), 0), ((-4,), -12)], "Multiply n by 3."),
 code("Write add(a, b) returning their sum.", "add", "def add(a, b):\n    pass", [((2, 5), 7), ((-1, 1), 0), ((0, 0), 0)], "Return a + b."),
 code("Write is_positive(n), True only when n is above zero.", "is_positive", "def is_positive(n):\n    pass", [((1,), True), ((0,), False), ((-2,), False)], "Compare n with zero."),
 code("Write is_zero(n), True only when n equals zero.", "is_zero", "def is_zero(n):\n    pass", [((0,), True), ((1,), False), ((-1,), False)], "Compare n == 0."),
 code("Write smaller(a, b) returning the smaller value.", "smaller", "def smaller(a, b):\n    pass", [((3, 8), 3), ((-2, -5), -5), ((4, 4), 4)], "Use min(a, b) or a condition."),
 code("Write last_item(items) returning the final list item.", "last_item", "def last_item(items):\n    pass", [(([1, 2, 3],), 3), (([9],), 9), ((['a', 'b'],), 'b')], "Negative index -1 selects the last item."),
 code("Write count_items(items) returning the list length.", "count_items", "def count_items(items):\n    pass", [(([1, 2, 3],), 3), (([],), 0), ((['x'],), 1)], "Use len(items)."),
 code("Write double_items(items) returning every number doubled.", "double_items", "def double_items(items):\n    pass", [(([1, 2],), [2, 4]), (([],), []), (([-1, 3],), [-2, 6])], "Build a list with each value multiplied by two."),
 code("Write sum_list(items) returning the sum of the numbers.", "sum_list", "def sum_list(items):\n    pass", [(([1, 2, 3],), 6), (([],), 0), (([-2, 5],), 3)], "Python's sum() can add the list."),
 code("Write absolute(n) returning the non-negative magnitude.", "absolute", "def absolute(n):\n    pass", [((-5,), 5), ((3,), 3), ((0,), 0)], "Use abs(n)."),
 code("Write average(a, b) returning their arithmetic mean.", "average", "def average(a, b):\n    pass", [((2, 4), 3), ((0, 0), 0), ((-2, 2), 0)], "Add both values and divide by two."),
])
CH[8]["items"].extend([
 code("Write first_char(s) returning the first character, or an empty string for empty input.", "first_char", "def first_char(s):\n    pass", [(("Code",), "C"), (("x",), "x"), (("",), "")], "Check for empty text, otherwise use s[0]."),
 code("Write last_char(s) returning the final character, or an empty string.", "last_char", "def last_char(s):\n    pass", [(("Code",), "e"), (("x",), "x"), (("",), "")], "Check for empty text, otherwise use s[-1]."),
 code("Write make_upper(s) returning the text in uppercase.", "make_upper", "def make_upper(s):\n    pass", [(("hi",), "HI"), (("Code",), "CODE"), (("",), "")], "Use s.upper()."),
 code("Write remove_spaces(s) removing ordinary space characters.", "remove_spaces", "def remove_spaces(s):\n    pass", [(("a b c",), "abc"), ((" no spaces ",), "nospaces"), (("",), "")], "Replace spaces with an empty string."),
 code("Write word_count(s) counting words separated by whitespace.", "word_count", "def word_count(s):\n    pass", [(("one two",), 2), (("",), 0), (("  a   b ",), 2)], "Split on whitespace and count the resulting words."),
 code("Write repeat_text(s, n) returning s repeated n times.", "repeat_text", "def repeat_text(s, n):\n    pass", [(("ha", 3), "hahaha"), (("x", 0), ""), (("ab", 1), "ab")], "Strings can be multiplied by an integer."),
 code("Write has_digit(s) returning True if any character is a digit.", "has_digit", "def has_digit(s):\n    pass", [(("room2",), True), (("abc",), False), (("",), False)], "Check each character with isdigit()."),
 code("Write first_vowel_index(s) returning the index of the first vowel, or -1.", "first_vowel_index", "def first_vowel_index(s):\n    pass", [(("sky",), -1), (("code",), 1), (("AE",), 0)], "Search for a, e, i, o, or u without case sensitivity."),
 code("Write replace_spaces(s) replacing each space with a hyphen.", "replace_spaces", "def replace_spaces(s):\n    pass", [(("a b",), "a-b"), (("one two three",), "one-two-three"), (("",), "")], "Use s.replace(' ', '-')."),
 code("Write is_empty(s) returning True only when s has no characters.", "is_empty", "def is_empty(s):\n    pass", [(("",), True), ((" ",), False), (("x",), False)], "Compare the string with the empty string."),
 code("Write initials(name) returning the first character of each word in uppercase.", "initials", "def initials(name):\n    pass", [(("Ada Lovelace",), "AL"), (("grace hopper",), "GH"), (("",), "")], "Split into words, take each first character, and uppercase the result."),
 code("Write count_letter(s, letter) counting case-insensitive matches.", "count_letter", "def count_letter(s, letter):\n    pass", [(("Banana", "a"), 3), (("hello", "L"), 2), (("abc", "z"), 0)], "Lowercase both strings before counting."),
])
CH[9]["items"].extend([
 code("Write is_odd(n) returning True for odd integers.", "is_odd", "def is_odd(n):\n    pass", [((3,), True), ((4,), False), ((-1,), True)], "An odd integer has a remainder of 1 or -1 when divided by 2."),
 code("Write clamp(n, low, high) limiting n to the inclusive range.", "clamp", "def clamp(n, low, high):\n    pass", [((5, 0, 3), 3), ((-2, 0, 3), 0), ((2, 0, 3), 2)], "Use min(high, max(low, n))."),
 code("Write second_item(items) returning the second item.", "second_item", "def second_item(items):\n    pass", [(([4, 7, 9],), 7), ((['a', 'b'],), 'b'), (([0, 1],), 1)], "The second item has index 1."),
 code("Write squares(items) returning the square of each number.", "squares", "def squares(items):\n    pass", [(([1, 2, 3],), [1, 4, 9]), (([],), []), (([-2, 4],), [4, 16])], "Square each number with n * n."),
 code("Write count_even(items) counting even integers in a list.", "count_even", "def count_even(items):\n    pass", [(([1, 2, 4],), 2), (([],), 0), (([-2, 3, 0],), 2)], "Even numbers have n % 2 == 0."),
 code("Write join_words(words) joining a list with one space between words.", "join_words", "def join_words(words):\n    pass", [((['code', 'quest'],), "code quest"), (([],), ""), ((['one'],), "one")], "Use ' '.join(words)."),
 code("Write unique(items) returning values in first-seen order without duplicates.", "unique", "def unique(items):\n    pass", [(([1, 2, 1, 3],), [1, 2, 3]), (([],), []), ((['a', 'a'],), ['a'])], "Append an item only if it is not already in the result."),
 code("Write count_down(n) returning integers from n down to 1.", "count_down", "def count_down(n):\n    pass", [((3,), [3, 2, 1]), ((1,), [1]), ((0,), [])], "Build a descending list; zero should return an empty list."),
 code("Write second_largest(items) returning the second distinct largest value.", "second_largest", "def second_largest(items):\n    pass", [(([3, 9, 2],), 3), (([-5, -2, -9],), -5), (([4, 4, 1],), 1)], "Sort the distinct values and select the second from the end."),
 code("Write merge_sorted(a, b) returning all values from both lists sorted.", "merge_sorted", "def merge_sorted(a, b):\n    pass", [(([1, 4], [2, 3]), [1, 2, 3, 4]), (([], [2]), [2]), (([5], []), [5])], "Combine the lists and sort the result."),
 code("Write digit_sum(n) returning the sum of the digits of a non-negative integer.", "digit_sum", "def digit_sum(n):\n    pass", [((123,), 6), ((0,), 0), ((908,), 17)], "Convert to text or repeatedly use remainder and division."),
 code("Write rotate_left(items) moving the first item to the end; empty lists stay empty.", "rotate_left", "def rotate_left(items):\n    pass", [(([1, 2, 3],), [2, 3, 1]), (([],), []), (([7],), [7])], "Handle empty input, then combine items[1:] with items[:1]."),
])
CH.extend([
 mc("The Firewall Frontier", (80, 225, 178), "Firewall Warden", 500, [
  ("What is the main job of a firewall?", ["Filter network traffic by rules", "Make passwords visible", "Speed up a monitor", "Rename files"], 0, "A firewall allows or blocks traffic according to rules."),
  ("Which choice is the strongest password?", ["password123", "qwerty", "a long unique passphrase", "your first name"], 2, "Length and uniqueness make a passphrase harder to guess."),
  ("What does MFA add to a sign-in?", ["A second verification factor", "A faster internet connection", "A public username", "An automatic password"], 0, "Multi-factor authentication requires another proof of identity."),
  ("What should you do with an unexpected link asking for your password?", ["Open it quickly", "Verify the sender and site first", "Share it with friends", "Reply with your password"], 1, "Unexpected credential links may be phishing; verify independently."),
  ("What does HTTPS help protect?", ["Data sent between browser and website", "Your keyboard hardware", "Files stored only on paper", "A computer from every virus"], 0, "HTTPS encrypts traffic between the browser and the site."),
  ("What is phishing?", ["A trick to steal information by pretending to be trusted", "A method for sorting files", "A kind of network cable", "A database backup"], 0, "Phishing messages impersonate trusted sources to steal information."),
  ("Why install security updates?", ["They can fix known vulnerabilities", "They always add more RAM", "They remove the need for backups", "They make every app public"], 0, "Updates often patch security weaknesses."),
  ("Which action is safest on public Wi-Fi?", ["Avoid sensitive tasks on untrusted networks", "Disable every device lock", "Share account codes", "Use any pop-up VPN link"], 0, "Treat public networks as untrusted, especially for sensitive activity."),
  ("What is the principle of least privilege?", ["Give only the access needed for a task", "Give everyone administrator access", "Reuse one password everywhere", "Turn off account checks"], 0, "Least privilege limits accounts to the permissions they need."),
  ("Why keep a backup disconnected or protected?", ["Ransomware may also target reachable backups", "It improves screen color", "It changes your username", "It makes Wi-Fi unnecessary"], 0, "Protected backups are harder for malware to encrypt or delete."),
  ("What should you do if a login code arrives that you did not request?", ["Never share it and secure the account", "Post it publicly", "Send it to the requester", "Turn off the screen lock"], 0, "An unexpected code can mean someone is trying to sign in."),
  ("What is a software vulnerability?", ["A weakness that could be exploited", "A type of monitor", "A saved game level", "A secure password"], 0, "A vulnerability is a flaw that could affect system security."),
  ("Which is safer for a sensitive site?", ["A verified official domain using HTTPS", "A shortened unknown link", "A misspelled look-alike domain", "A link sent by an unknown stranger"], 0, "Check the real domain and secure connection before entering data."),
  ("What does encryption do to data?", ["Makes it unreadable without the right key", "Deletes every copy", "Guarantees a site is honest", "Makes a weak password strong"], 0, "Encryption protects confidentiality when keys are handled securely."),
  ("What is a good first step after suspecting account compromise?", ["Change credentials from a trusted device and review sessions", "Ignore all alerts", "Share the password to get help", "Delete every backup"], 0, "Secure the account using a trusted device and check for unauthorized access."),
 ]),
 mc("The Cloud Citadel", (120, 190, 235), "Cloud Keeper", 600, [
  ("What is cloud computing?", ["Using computing resources over a network", "Saving files only on paper", "A weather forecast", "A programming loop"], 0, "Cloud services provide computing resources over a network."),
  ("What does scalability mean for a cloud service?", ["Adjusting resources as demand changes", "Changing the keyboard layout", "Removing all user accounts", "Turning code into a picture"], 0, "Scalability lets resources grow or shrink with workload."),
  ("Why use multiple availability zones?", ["Reduce the impact of one location failing", "Make passwords shorter", "Avoid all software updates", "Hide every log"], 0, "Separate zones can improve resilience when one location has an outage."),
  ("What is a cloud region?", ["A geographic area containing cloud infrastructure", "A folder name", "A password type", "A programming language"], 0, "Cloud regions are geographic locations with cloud infrastructure."),
  ("What does a backup help with?", ["Recovering data after loss or damage", "Preventing every possible outage", "Replacing access control", "Making data public"], 0, "Backups provide a recovery copy when data is lost or damaged."),
  ("What is an API commonly used for?", ["Letting software services communicate", "Cooling a server room", "Encrypting a monitor", "Naming a Wi-Fi network"], 0, "An API defines how software components can interact."),
  ("Why should cloud storage permissions be checked?", ["To prevent unintended data access", "To increase file size", "To remove encryption keys", "To make every object public"], 0, "Incorrect permissions can expose data to unauthorized users."),
  ("What is serverless computing?", ["Running cloud code without managing servers directly", "Computing without any hardware anywhere", "A website with no users", "A database without data"], 0, "The provider manages the underlying server infrastructure."),
  ("What does a load balancer do?", ["Distributes requests across available servers", "Stores passwords in plain text", "Deletes old backups", "Creates website content"], 0, "Load balancers spread traffic among service instances."),
  ("What is a container used for?", ["Packaging an application with its dependencies", "Measuring network weather", "Replacing a database key", "Opening a firewall port automatically"], 0, "Containers package an application and its runtime dependencies."),
  ("Why monitor cloud service logs?", ["To diagnose issues and investigate activity", "To make all data disappear", "To avoid setting permissions", "To store passwords in a public file"], 0, "Logs help with troubleshooting and security investigations."),
  ("What does data residency describe?", ["Where data is physically or legally stored", "How fast a screen refreshes", "The number of user accounts", "A file's extension"], 0, "Data residency refers to the location where data is stored."),
  ("What is an object storage bucket?", ["A container for stored objects and their metadata", "A physical network switch", "A password hint", "A programming condition"], 0, "Object storage keeps objects and associated metadata in containers."),
  ("What should a cloud access key be?", ["Secret, limited in permission, and rotated if exposed", "Posted in source code", "Shared with every user", "Used as a public username"], 0, "Protect keys, limit their privileges, and rotate compromised credentials."),
  ("What does disaster recovery planning define?", ["How to restore services after a serious disruption", "How to remove all monitoring", "How to make backups inaccessible", "How to disable user authentication"], 0, "Recovery plans set out how to restore operations after a disruption."),
 ]),
])

LESSONS = [
    ("HTML Foundations", "HTML gives a web page its structure. Elements use opening and closing tags, while attributes add details such as a link destination or image source.", "<p>Hello!</p>  <a href=\"page.html\">Open page</a>"),
    ("JavaScript Logic", "Variables store values, operators work with them, and conditions choose what happens next. Use let for a value that may change and const for one that should stay assigned.", "const score = 8;\nif (score >= 5) { console.log(\"Great!\"); }"),
    ("C++ Basics", "C++ statements commonly end with a semicolon. Variables have types, == compares values, and functions can return results to the code that called them.", "int score = 5;\nif (score == 5) { cout << score; }"),
    ("Networking Essentials", "Networks move data between devices. IP addresses identify network interfaces, DNS looks up names, and routers forward packets between networks.", "Browser -> DNS lookup -> IP address -> server"),
    ("Database Essentials", "A database table stores records in rows and fields in columns. Primary keys identify rows, while SQL queries select, filter, and sort data.", "SELECT name FROM users WHERE age > 18;"),
    ("Security Review", "Good security uses layers: verify unexpected requests, use unique passwords and MFA, install updates, protect backups, and grant only the access each task needs.", "Check the sender and real website before entering a password."),
    ("Debugging", "Debugging means comparing what a program should do with what it actually does. Read the error, inspect the values, and correct the operation that loses or changes data.", "total = total + value  # store the updated sum"),
    ("Algorithms", "An algorithm is a clear sequence of steps. Break a task into smaller operations, handle edge cases, and test the result with simple inputs.", "return sum(range(1, n + 1))"),
    ("Working with Strings", "Strings are sequences of characters. Python slicing can reverse a string, and methods such as lower() and count() help inspect its contents.", "backwards = text[::-1]"),
    ("Python and SQL", "Functions take inputs and return outputs. Lists can be transformed or filtered, while SQL describes which rows and columns to retrieve from a database.", "def double(n):\n    return n * 2"),
    ("Firewall Safety", "A firewall applies rules to network traffic. Safer accounts use MFA and unique passwords; be alert for phishing and keep software and protected backups up to date.", "Allow only the network traffic a service needs."),
    ("Cloud Computing", "Cloud services provide computing resources over a network. Regions and availability zones help place services, scaling matches demand, and backups support recovery.", "An API lets software services communicate."),
]

LANGUAGE_PATHS = [
    {
        "name": "Java",
        "color": (255, 154, 60),
        "lesson": "Java uses classes to organize programs. Give each value a type, and use System.out.println to show a message. Byte needs a clear signal to reconnect the Kingdom's Core.",
        "example": 'class Main {\n    public static void main(String[] args) {\n        System.out.println("Portal ready!");\n    }\n}',
        "questions": [
            ("Which line prints a message in Java?", ['System.out.println("Hi");', 'print("Hi")', 'echo "Hi"', 'console.log("Hi")'], 0, "System.out.println writes a line of text to the console."),
            ("Which type commonly stores a whole number?", ["int", "String", "boolean", "void"], 0, "int is Java's standard whole-number type."),
            ("Which symbol ends most Java statements?", [":", ";", ".", ","], 1, "Java statements usually end with a semicolon."),
        ],
    },
    {
        "name": "Python",
        "color": (94, 225, 255),
        "lesson": "Python uses indentation to group instructions. Use print() to show a message, and assign a value with =. Byte can use these simple instructions to repair the Kingdom's Core.",
        "example": 'message = "Portal ready!"\nprint(message)',
        "questions": [
            ("Which line displays text in Python?", ['print("Hi")', 'System.out.println("Hi")', 'echo("Hi")', 'show "Hi"'], 0, "print() displays a value in Python."),
            ("What is the first position in a Python list?", ["0", "1", "-1", "It depends on the list"], 0, "Python lists start counting positions at zero."),
            ("Which character begins an indented block after an if condition?", [":", ";", "{", "#"], 0, "A colon introduces the indented body of an if statement."),
        ],
    },
    {
        "name": "HTML",
        "color": (255, 122, 138),
        "lesson": "HTML describes the structure of a web page using tags. A heading uses <h1>, a paragraph uses <p>, and a link uses <a>. Byte is rebuilding the Kingdom's control panel.",
        "example": '<h1>Portal</h1>\n<p>Signal restored!</p>\n<a href="map.html">Return to map</a>',
        "questions": [
            ("Which tag creates a paragraph?", ["<h1>", "<p>", "<img>", "<body>"], 1, "<p> marks a paragraph of text."),
            ("Which tag creates a link?", ["<a>", "<link>", "<href>", "<nav>"], 0, "<a> is the anchor element used for links."),
            ("Which attribute gives a link its destination?", ["src", "href", "alt", "class"], 1, "The href attribute contains the link destination."),
        ],
    },
    {
        "name": "CSS",
        "color": (226, 110, 170),
        "lesson": "CSS controls how a web page looks. A selector chooses an element, and declarations set properties such as color. Byte is adding a bright style to make the Kingdom's Core visible again.",
        "example": '.portal {\n    color: cyan;\n    background-color: navy;\n}',
        "questions": [
            ("What does CSS mainly control?", ["A page's appearance", "A database's rows", "A computer's memory", "A network address"], 0, "CSS styles the appearance and layout of web pages."),
            ("Which selector targets an element with class=\"portal\"?", ["#portal", ".portal", "portal()", "*portal"], 1, "A dot selector targets an HTML class."),
            ("Which punctuation separates a CSS property from its value?", ["=", ":", "->", "#"], 1, "CSS declarations use a colon between property and value."),
        ],
    },
    {
        "name": "JavaScript",
        "color": (255, 210, 74),
        "lesson": "JavaScript adds behavior to web pages. Use const for a value that should not be reassigned, and console.log() to show information. Byte is wiring the Kingdom Core's activation switch.",
        "example": 'const message = "Portal ready!";\nconsole.log(message);',
        "questions": [
            ("Which line displays a message in JavaScript?", ['console.log("Hi");', 'print("Hi")', 'System.out.println("Hi");', 'echo("Hi")'], 0, "console.log() writes information to the developer console."),
            ("Which keyword declares a value that should not be reassigned?", ["let", "const", "int", "fixed"], 1, "const prevents reassignment of the variable binding."),
            ("Which operator checks strict equality?", ["=", "===", "=>", "!="], 1, "=== compares values without type conversion."),
        ],
    },
]

P = [(0, 420, 560), (640, 385, 120), (830, 345, 110), (1010, 385, 120), (1200, 420, 110), (1390, 385, 110), (1560, 420, 920),
     (2560, 385, 110), (2740, 350, 110), (2920, 385, 110), (3100, 420, 900),
     (4000, 420, 1950), (5950, 420, 2050)]
PORTAL_XS = [1700 + i * 120 for i in range(6)] + [3250 + (i - 6) * 160 for i in range(6, 10)] + [4650, 6650]
def PX(i): return PORTAL_XS[i]
WORLD_WIDTH = 8000
MAP_GATES = [(4000, 9), (6000, 10)]
MAP_NAMES = ["The Lost Code Kingdom", "The Firewall Frontier", "The Cloud Citadel"]
MAP_STORY = [
    "The Virus King's signal has reached the Firewall Frontier. Find the corrupted beacon and secure the network.",
    "The beacon points to the Cloud Citadel. Restore its core before the spreading outage reaches the kingdom.",
]
BX = 300
ORBS = [(200, 370), (420, 370), (700, 335), (885, 295), (1065, 335), (1255, 370), (1445, 335), (1720, 360), (1960, 360),
        (2400, 360), (2615, 345), (2795, 310), (2975, 345), (3350, 360), (3750, 360)]
XPL = 200
CHARACTER_XP_COST = 15
def character_xp_cost(index):
    if index <= 1:
        return 15
    if index <= 3:
        return (25, 40)[index - 2]
    return min(160, 60 + ((index - 4) // 4) * 20)
CHARACTERS = [
    {"id": "guardian", "name": "Code Guardian", "xp_cost": 0, "colors": ((74, 99, 216), (58, 79, 184), (39, 50, 90), (43, 58, 138), (28, 37, 64), (216, 58, 86), (42, 26, 18), (214, 160, 120), CYAN)},
    {"id": "bytebot", "name": "Byte Bot", "xp_cost": character_xp_cost(1), "colors": ((120, 145, 175), (85, 108, 145), (49, 62, 86), (66, 104, 145), (43, 55, 78), (94, 225, 255), (38, 56, 78), (190, 205, 225), (94, 225, 255))},
    {"id": "ranger", "name": "Forest Ranger", "xp_cost": character_xp_cost(2), "colors": ((55, 155, 95), (42, 126, 78), (53, 70, 48), (50, 110, 72), (38, 57, 42), (194, 120, 48), (48, 34, 22), (205, 158, 112), GOLD)},
    {"id": "mage", "name": "Crystal Mage", "xp_cost": character_xp_cost(3), "colors": ((155, 82, 208), (120, 61, 175), (55, 38, 84), (119, 69, 178), (49, 35, 78), (94, 225, 255), (78, 55, 103), (232, 196, 220), GOLD)},
]
SPRITE_NAMES = ["Horned Brawler", "Plume Gunner", "Skull Alchemist", "Top Hat Chef", "Red Ogre", "Pink Gladiator", "Green Skull Orc", "Blue Zombie Kid", "Bronze Mech", "Big Mouth Roarer", "Chainsaw Brute", "Mushroom Critter", "Green Bull", "Deep Sea Scout", "Cigar Cameraman", "Pot Hat Sailor", "Red Bandana Biker", "Bow Girl", "Red Cap Plumber", "Clown King", "Jetpack Bot", "Shades Blaster", "Blue Diver", "Dual Blaster Dancer", "Cannon Clown", "Skeleton Witch", "Golden Mech", "Teal Robot", "Lightning Rocker", "Green Hood Ninja"]
for _i, _name in enumerate(SPRITE_NAMES):
    CHARACTERS.append({"id": "pal%02d" % (_i + 1), "name": _name,
                       "xp_cost": character_xp_cost(len(CHARACTERS)),
                       "sprite": _i, "colors": CHARACTERS[0]["colors"]})

G = NS(state="login", name="", S={}, M={}, px=100, py=420, vx=0, vy=0, face=1, gnd=False, ph=0, cp=(100, 420),
       camx=0, camy=40, near=None, tt=0, ts="", auth_user="", auth_pass="", auth_focus="username",
       auth_mode="login", auth_error="", auth_notice="", admin_name="", admin_msg="",
       auth_show_password=False,
       auth_backspace_held=False, auth_backspace_timer=0, conf=False, t=0, touch_enabled=False,
       touch_left=False, touch_right=False, touch_jump=False, text_input_active=False,
       touch_fingers={}, story_stage_beat="")

def make_portal_obby(index, challenge):
    count = 5 + index // 2
    width = max(54, 130 - index * 6)
    gap = 32 + index * 6
    rise = 20 + index * 1.15
    platforms = [(50, 450, 145, 16)]
    x, y = 50, 450
    for step in range(1, count):
        x += platforms[-1][2] + gap
        y -= rise + (8 if step % 3 == 0 else 0)
        platforms.append((round(x), round(y), width, 16))
    last_x, last_y, last_width, _ = platforms[-1]
    crystals = []
    for platform_index in (1, count // 2, count - 2):
        source = platforms[platform_index]
        target = platforms[platform_index + 1]
        gap_midpoint = (source[0] + source[2] + target[0]) / 2
        crystals.append((gap_midpoint, min(source[1], target[1]) - 72 - index * 3))
    return {
        "name": challenge["n"].replace("The ", ""),
        "color": challenge["c"],
        "platforms": platforms,
        "crystals": crystals,
        "goal": (last_x + last_width // 2, last_y - 40),
        "width": last_x + last_width + 100,
    }

STORY_MECHANICS = {
    "Syntax": "Syntax stepping stones",
    "Introduction": "Java starter platforms",
    "Variables": "Variable cache blocks",
    "String": "String signal bridge",
    "Strings": "String signal bridge",
    "Booleans": "True / false safe route",
    "If else": "Choose a fork in the path",
    "Arrays": "Array value platforms",
    "Intro": "Signal relay platforms",
    "Loops": "Repeating moving platforms",
    "Operators": "Moving operator gates",
    "Strings": "String signal bridge",
    "Debugging": "Avoid moving bug hazards",
    "Table": "Rows and columns",
    "Links": "Linked bridge platforms",
    "Image": "Image frame platforms",
    "Inline": "Narrow inline route",
    "Div": "Stacked box platforms",
}

# ---- Difficulty tiers (Story Quest parkour portals) -------------------------------------
# Normal reproduces the original course exactly. Higher tiers tighten the course and pay more XP.
# gap/width scale the stepping stones, hazards/moving/vanish are the number of spike / sliding /
# disappearing platforms, amp+speed drive the moving parts, cycle+solid time the vanishing ones.
DIFFICULTIES = [
    dict(id="easy", name="EASY", sides=3, color=(124, 214, 120), crystal_xp=3, topic_xp=8,
         gap=.85, width=1.2, hazards=1, moving=0, vanish=0, amp=.6, speed=.8, cycle=4.4, solid=3.6,
         hz=.85, checkpoints=(0, 2, 7, 12),
         blurb="Wide stones, one spike and extra checkpoints. A gentle start."),
    dict(id="normal", name="NORMAL", sides=4, color=(228, 214, 108), crystal_xp=5, topic_xp=10,
         gap=1.0, width=1.0, hazards=2, moving=0, vanish=0, amp=1.0, speed=1.0, cycle=4.4, solid=3.1,
         hz=1.0, checkpoints=(0, 7),
         blurb="The classic Kingdom parkour course."),
    dict(id="difficult", name="DIFFICULT", sides=5, color=(238, 150, 62), crystal_xp=6, topic_xp=12,
         gap=1.12, width=.92, hazards=3, moving=1, vanish=0, amp=1.15, speed=1.1, cycle=4.2, solid=2.9,
         hz=1.0, checkpoints=(0, 7),
         blurb="Wider gaps, a third spike and one more sliding platform."),
    dict(id="hard", name="HARD", sides=6, color=(230, 90, 96), crystal_xp=8, topic_xp=15,
         gap=1.25, width=.82, hazards=4, moving=2, vanish=1, amp=1.3, speed=1.25, cycle=4.0, solid=2.6,
         hz=1.1, checkpoints=(0, 7),
         blurb="Narrow stones, four spikes and platforms that start to vanish."),
    dict(id="extreme", name="EXTREME", sides=8, color=(150, 82, 78), crystal_xp=10, topic_xp=20,
         gap=1.38, width=.72, hazards=5, moving=3, vanish=2, amp=1.5, speed=1.4, cycle=3.8, solid=2.3,
         hz=1.15, checkpoints=(0, 7),
         blurb="Tiny stones, five spikes, fast sliders and short-lived platforms."),
    dict(id="insane", name="INSANE", sides=10, color=(150, 150, 160), crystal_xp=15, topic_xp=30,
         gap=1.5, width=.62, hazards=5, moving=4, vanish=3, amp=1.7, speed=1.6, cycle=3.4, solid=1.9,
         hz=1.25, checkpoints=(0,),
         blurb="Giant spikes, the fastest platforms and a single checkpoint."),
]
DIFFICULTY_BY_ID = {d["id"]: d for d in DIFFICULTIES}
DEFAULT_DIFFICULTY = "normal"

def difficulty_by_id(difficulty_id):
    return DIFFICULTY_BY_ID.get(difficulty_id, DIFFICULTY_BY_ID[DEFAULT_DIFFICULTY])

def current_difficulty():
    return difficulty_by_id(G.S.get("difficulty", DEFAULT_DIFFICULTY))

def max_story_topic_xp():
    return 15 + max(d["crystal_xp"] for d in DIFFICULTIES) * 3 + max(d["topic_xp"] for d in DIFFICULTIES)

def make_story_portal_obby(language, topic_index, difficulty=None):
    difficulty = difficulty or current_difficulty()
    topic = story_language_data(language)["topics"][topic_index]
    array_branch = language == "Java" and topic_index == 4
    platforms = [(48, 450, 160, 16)]
    x, y = platforms[0][0], platforms[0][1]
    for step in range(1, 15):
        gap = round((64 + (topic_index % 3) * 9) * difficulty["gap"])
        width = 92 if topic["topic"] in ("Syntax", "Introduction", "Inline") else 120 - (step % 3) * 10
        if difficulty["width"] != 1.0:
            width = max(64, round(width * difficulty["width"]))
        if (topic["topic"] == "If else" or array_branch) and step == 4:
            branch_x = x + platforms[-1][2] + gap
            platforms.append((branch_x, y - 38, 112, 16))
            platforms.append((branch_x, y + 28, 112, 16))
            x, y = branch_x, y - 6
            continue
        x += platforms[-1][2] + gap
        y = 450 - ((step * 29 + topic_index * 17) % 70)
        platforms.append((x, y, width, 16))
    last_x, last_y, last_width, _ = platforms[-1]
    moving = (2, 6) if topic["topic"] in ("Loops", "Operators") else (3,)
    disappearing = (5, 11) if topic["topic"] in ("If else", "Debugging") or array_branch else (8,)
    last_index = len(platforms) - 1
    crystal_platforms = (3, 8, 13)
    reserved = {0, 7, last_index, *crystal_platforms}
    # Spikes first (4 and 10 are the original spots), then extra sliders and vanishing stones.
    hazard_indices = [index for index in (4, 10, 2, 12, 6, 9, 1, 5)
                      if index not in reserved and index not in moving and index not in disappearing
                      ][:difficulty["hazards"]]
    extra_moving = [index for index in (9, 12, 1, 5, 11, 6, 2)
                    if index not in reserved and index not in hazard_indices
                    and index not in moving and index not in disappearing
                    ][:difficulty["moving"]]
    extra_vanish = [index for index in (11, 2, 13, 6, 9, 1, 12, 5)
                    if index not in (0, 7, last_index) and index not in hazard_indices
                    and index not in moving and index not in disappearing
                    and index not in extra_moving][:difficulty["vanish"]]
    moving = tuple(moving) + tuple(extra_moving)
    disappearing = tuple(disappearing) + tuple(extra_vanish)
    checkpoints = tuple(index for index in difficulty["checkpoints"]
                        if index in (0, 7) or (index not in hazard_indices and index not in moving
                                               and index not in disappearing and index < last_index))
    hazard_w, hazard_h = round(22 * difficulty["hz"]), round(28 * difficulty["hz"])
    hazards = []
    for index in hazard_indices:
        hx, hy, width, _ = platforms[index]
        hazards.append((hx + width * .58, hy - 10, hazard_w, hazard_h))
    crystals = [
        (platforms[index][0] + platforms[index][2] * .5, platforms[index][1] - 34)
        for index in (3, 8, 13)
    ]
    return {
        "name": topic["topic"],
        "color": tuple(story_language_data(language)["color"]),
        "theme": story_language_data(language).get("theme", language),
        "mechanic": STORY_MECHANICS.get(topic["topic"], "Portal platform course"),
        "platforms": platforms,
        "moving": moving,
        "disappearing": disappearing,
        "hazards": hazards,
        "crystals": crystals,
        "checkpoints": checkpoints,
        "difficulty": difficulty,
        "amp": difficulty["amp"],
        "speed": difficulty["speed"],
        "cycle": difficulty["cycle"],
        "solid": difficulty["solid"],
        "crystal_xp": difficulty["crystal_xp"],
        "branch": topic["topic"] == "If else" or array_branch,
        "goal": (last_x + last_width // 2, last_y - 42),
        "width": last_x + last_width + 100,
    }

PORTAL_OBBIES = [make_portal_obby(i, challenge) for i, challenge in enumerate(CH)]

def portal_obby_completed(i):
    return i in G.S.setdefault("portal_obby_clear", [])

def start_portal_obby(i, mode="quest"):
    G.obby_idx = i
    G.obby_mode = mode
    if mode == "story":
        language, topic_index = G.story_language, G.story_topic_index
        G.story_stage = make_story_portal_obby(language, topic_index, current_difficulty())
        G.obby_obstacles = G.story_stage["hazards"]
        G.obby_stage_elapsed = 0
        progress = story_progress(language)
        key = str(topic_index)
        collected = progress.setdefault("stage_crystals", {}).setdefault(key, [])
        G.story_stage_collected = set(collected)
        topic = story_language_data(language)["topics"][topic_index]
        G.story_stage_beat = topic["story"]
        if len(G.story_stage_collected) == 3:
            G.story_stage_beat = (
                "All three code crystals are charged. Reach the portal to restore this "
                "beacon and carry its signal back to the Core.")
        G.obby_checkpoint = (100, 450)
        G.obby_cp_index = 1
    else:
        G.story_stage = None
        portal_crystals = G.S.setdefault("portal_crystals", {})
        crystal_key = "%s:%d" % (mode, i)
        G.obby_crystal_collected = set(portal_crystals.get(crystal_key, []))
    if mode in ("language", "story"):
        G.language_id = i
        if mode == "language":
            platforms = PORTAL_OBBIES[i]["platforms"]
            G.obby_obstacles = [
                (x + width * 0.62, y - 30, 24, 30)
                for step, (x, y, width, _) in enumerate(platforms[1:-1], 1)
                if step % 2 == 1
            ]
    else:
        G.obby_obstacles = []
    G.obby_x = 100
    G.obby_y = 450
    G.obby_checkpoint = (100, 450)
    G.obby_vx = G.obby_vy = 0
    G.obby_gnd = True
    G.obby_camx = 0
    G.touch_left = G.touch_right = G.touch_jump = False
    G.near = None
    G.state = "obby"

def present():
    window_w, window_h = display.get_size()
    scale = min(window_w / W, window_h / H)
    size = (max(1, round(W * scale)), max(1, round(H * scale)))
    offset = ((window_w - size[0]) // 2, (window_h - size[1]) // 2)
    display.fill((5, 4, 18))
    frame = pygame.transform.smoothscale(scr, size)
    display.blit(frame, offset)
    pygame.display.flip()
    return offset, size

def logical_pos(pos):
    window_w, window_h = display.get_size()
    scale = min(window_w / W, window_h / H)
    size = (max(1, round(W * scale)), max(1, round(H * scale)))
    offset = ((window_w - size[0]) // 2, (window_h - size[1]) // 2)
    x, y = pos
    if not (offset[0] <= x < offset[0] + size[0] and offset[1] <= y < offset[1] + size[1]):
        return None
    return ((x - offset[0]) / scale, (y - offset[1]) / scale)

def set_text_input(active):
    if active == G.text_input_active:
        return
    G.text_input_active = active
    if active:
        pygame.key.start_text_input()
    else:
        pygame.key.stop_text_input()

def load_all():
    if WEB:
        import platform
        saved = platform.window.localStorage.getItem("gamebuddy_saves")
        return json.loads(str(saved)) if saved is not None else {}
    try:
        with open(SAVE) as f: return json.load(f)
    except Exception: return {}

def load_accounts():
    try:
        with open(AUTH_SAVE) as f: data = json.load(f)
    except FileNotFoundError:
        return {}
    accounts = data.get("accounts") if isinstance(data, dict) else None
    if not isinstance(accounts, dict):
        raise ValueError("The account file has an invalid format.")
    for key, account in accounts.items():
        if (not isinstance(key, str) or not isinstance(account, dict)
                or not isinstance(account.get("username"), str)
                or not isinstance(account.get("salt"), str)
                or not isinstance(account.get("password_hash"), str)
                or account["username"].casefold() != key):
            raise ValueError("The account file has an invalid account entry.")
        try:
            salt = bytes.fromhex(account["salt"])
            password_hash = bytes.fromhex(account["password_hash"])
        except ValueError as exc:
            raise ValueError("The account file contains invalid password data.") from exc
        if len(salt) != 16 or len(password_hash) != 32:
            raise ValueError("The account file contains invalid password data.")
    return accounts

def save_accounts(accounts):
    with open(AUTH_SAVE, "w") as f:
        json.dump({"accounts": accounts}, f)

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)

def authenticate(create_account=False):
    username = G.auth_user.strip()
    password = G.auth_pass
    if not 3 <= len(username) <= 16 or not all(c.isalnum() or c in " -_" for c in username):
        G.auth_error = "Use a 3-16 character name (letters, numbers, spaces, - or _)."
        return
    if not password or len(password) > 128:
        G.auth_error = "Enter a password up to 128 characters long."
        return
    try:
        accounts = load_accounts()
        key = username.casefold()
        if create_account:
            if len(password) < 8:
                G.auth_error = "New passwords must be at least 8 characters."
                return
            if key in accounts:
                G.auth_error = "That username already has an account. Sign in instead."
                return
            salt = secrets.token_bytes(16)
            accounts[key] = {
                "username": username,
                "salt": salt.hex(),
                "password_hash": password_hash(password, salt).hex(),
                "status": "pending",
            }
            save_accounts(accounts)
            # New sign-ups wait for Admin verification before they can play.
            G.auth_error = ""
            G.auth_notice = "Account submitted! Wait for Admin approval, then sign in."
            G.auth_mode = "login"
            G.auth_pass = ""
            return
        else:
            account = accounts.get(key)
            if account is None:
                G.auth_error = "Invalid username or password."
                return
            salt = bytes.fromhex(account["salt"])
            expected = bytes.fromhex(account["password_hash"])
            if not hmac.compare_digest(password_hash(password, salt), expected):
                G.auth_error = "Invalid username or password."
                return
            status = account.get("status", "approved")
            if status == "pending":
                G.auth_error = "Your account is still waiting for Admin approval."
                return
            if status == "rejected":
                G.auth_error = "Your account request was rejected by the Admin."
                return
            username = account["username"]
            is_admin = account.get("admin") is True
    except (OSError, ValueError) as exc:
        G.auth_error = "Could not read or save accounts: %s" % exc
        return
    G.auth_error = ""
    G.auth_notice = ""
    if is_admin:
        open_admin(username)
    else:
        start(username)

def pending_accounts():
    rows = [a for a in load_accounts().values() if a.get("status") == "pending"]
    return sorted(rows, key=lambda a: a["username"].casefold())

def set_account_status(key, status):
    accounts = load_accounts()
    if key in accounts and accounts[key].get("status") == "pending":
        accounts[key]["status"] = status
        save_accounts(accounts)

def open_admin(username):
    G.admin_name = username
    G.admin_msg = ""
    G.auth_pass = ""
    G.auth_backspace_held = False
    G.M = {}
    G.state = "admin"
    set_text_input(False)

def admin_sign_out():
    G.state = "login"
    G.admin_name = ""
    G.auth_user = ""
    G.auth_pass = ""
    G.auth_focus = "username"
    G.auth_mode = "login"
    G.auth_show_password = False
    G.auth_error = ""
    G.auth_notice = ""
    G.auth_backspace_held = False
    set_text_input(False)

ADMIN_MAX_ROWS = 6

def admin_layout():
    rows = []
    try:
        pending = pending_accounts()
    except (OSError, ValueError):
        pending = []
    for i, account in enumerate(pending[:ADMIN_MAX_ROWS]):
        y = 168 + i * 52
        rows.append({
            "account": account,
            "row": pygame.Rect(120, y, 760, 44),
            "approve": pygame.Rect(640, y + 4, 110, 36),
            "reject": pygame.Rect(760, y + 4, 110, 36),
        })
    return {"rows": rows, "total": len(pending), "logout": pygame.Rect(760, 520, 120, 40)}

def draw_admin():
    scr.blit(SKY, (0, 0)); draw_particles()
    for sx, sy, size in STARS:
        scr.fill((244, 240, 226), (sx, sy, size, size))
    pygame.draw.rect(scr, (22, 32, 42), (100, 40, 800, 540), 0, 14)
    pygame.draw.rect(scr, GOLD, (100, 40, 800, 540), 2, 14)
    text("ADMIN - REVIEW REQUESTS", 120, 58, GOLD, fnt(22, True))
    text("Signed in as %s" % G.admin_name, 120, 92, CYAN, FS)
    layout = admin_layout()
    text("Pending sign-ups: %d" % layout["total"], 120, 128, WHITE, F)
    if not layout["rows"]:
        text("No pending account requests.", 120, 200, (206, 232, 214), F)
    for item in layout["rows"]:
        r = item["row"]
        pygame.draw.rect(scr, (34, 46, 58), r, 0, 8)
        pygame.draw.rect(scr, (104, 206, 172), r, 1, 8)
        text(item["account"]["username"], r.x + 12, r.y + 12, WHITE, F)
        for key, label, col in (("approve", "APPROVE", (62, 116, 96)),
                                ("reject", "REJECT", (120, 52, 60))):
            b = item[key]
            pygame.draw.rect(scr, col, b, 0, 7)
            pygame.draw.rect(scr, GOLD, b, 2, 7)
            rendered = FS.render(label, True, WHITE)
            scr.blit(rendered, (b.centerx - rendered.get_width() // 2,
                                b.centery - rendered.get_height() // 2))
    if layout["total"] > ADMIN_MAX_ROWS:
        text("+%d more - review these first, the list will refill." % (layout["total"] - ADMIN_MAX_ROWS),
             120, 484, (206, 232, 214), FS)
    if G.admin_msg:
        text(G.admin_msg, 120, 528, GREEN, FS)
    dashboard_button(layout["logout"], "LOG OUT")

def handle_admin_pointer(point):
    layout = admin_layout()
    if layout["logout"].collidepoint(point):
        admin_sign_out()
        return
    for item in layout["rows"]:
        key = item["account"]["username"].casefold()
        name = item["account"]["username"]
        try:
            if item["approve"].collidepoint(point):
                set_account_status(key, "approved")
                G.admin_msg = "Approved %s." % name
                return
            if item["reject"].collidepoint(point):
                set_account_status(key, "rejected")
                G.admin_msg = "Rejected %s." % name
                return
        except (OSError, ValueError) as exc:
            G.admin_msg = "Could not update accounts: %s" % exc
            return

def login_layout():
    card = pygame.Rect(530, 50, 430, 500)
    content_x = card.x + 34
    content_width = card.w - 68
    username = pygame.Rect(content_x, card.y + 123, content_width, 44)
    password = pygame.Rect(content_x, card.y + 213, content_width - 56, 44)
    reveal = pygame.Rect(password.right + 8, password.y, 48, password.h)
    return {
        "card": card,
        "username": username,
        "password": password,
        "reveal": reveal,
        "mode": pygame.Rect(content_x, card.y + 293, content_width, 30),
        "submit": pygame.Rect(content_x, card.y + 390, content_width, 46),
        "guest": pygame.Rect(content_x, card.y + 390, content_width, 46),
    }

def delete_auth_characters(count=1):
    if G.auth_focus == "username":
        G.auth_user = G.auth_user[:-count]
    else:
        G.auth_pass = G.auth_pass[:-count]

def update_auth_backspace(dt):
    if G.state != "login" or not G.auth_backspace_held:
        return
    G.auth_backspace_timer -= dt
    while G.auth_backspace_timer <= 0:
        delete_auth_characters(2)
        G.auth_backspace_timer += .045
def save():
    if not G.name: return
    d = load_all(); d[G.name] = G.S
    if WEB:
        import platform
        platform.window.localStorage.setItem("gamebuddy_saves", json.dumps(d))
        return
    try:
        with open(SAVE, "w") as f: json.dump(d, f)
    except Exception: pass
def lvl(): return 1 + G.S.get("xp", 0) // XPL
def unlocked(i): return i == 0 or (i - 1) in G.S["done"]
def toast(s): G.ts, G.tt = s, 2.4
def gain(n):
    old = lvl(); G.S["xp"] += n; save()
    if lvl() > old: toast("LEVEL UP! Level %d" % lvl())
def msg(t, b): G.M = dict(k="msg", t=t, b=b)
def start(name):
    G.name = name; G.auth_pass = ""; G.auth_show_password = False
    G.auth_backspace_held = False; d = load_all().get(name)
    G.S = dict(xp=0, done=[], orbs=[], won=False, crystal_balance=0,
               settings={"music": True, "sfx": True},
               owned_characters=["guardian"], character="guardian")
    if d: G.S.update(d)
    settings = G.S.setdefault("settings", {})
    settings.setdefault("music", True)
    settings.setdefault("sfx", True)
    if not d or "crystal_balance" not in d:
        G.S["crystal_balance"] = min(6, len([i for i in G.S["done"] if i < 5]) + (1 if G.S["won"] else 0))
    if "owned_characters" not in G.S: G.S["owned_characters"] = ["guardian"]
    if "character" not in G.S: G.S["character"] = "guardian"
    if (G.S["character"] in {c["id"] for c in CHARACTERS}
            and G.S["character"] not in G.S["owned_characters"]):
        G.S["owned_characters"].append(G.S["character"])
    if G.S.get("difficulty") not in DIFFICULTY_BY_ID:
        G.S["difficulty"] = DEFAULT_DIFFICULTY
    if "map_seen" not in G.S: G.S["map_seen"] = []
    if "portal_obby_clear" not in G.S: G.S["portal_obby_clear"] = []
    G.cp = (6150, 420) if 10 in G.S["done"] else (4150, 420) if 9 in G.S["done"] else (3150, 420) if G.S["won"] else (1620, 420) if G.S["done"] else (100, 420)
    G.px, G.py = G.cp; G.vx = G.vy = 0; G.state = "home"; G.M = {}
    G.show_intro = not bool(d)
    save()

def enter_game():
    G.vx = G.vy = 0
    G.touch_left = G.touch_right = G.touch_jump = False
    G.near = None
    G.state = "play"
    G.story_mode = False
    if G.show_intro:
        G.show_intro = False
        G.M = dict(
            k="msg",
            t="The Lost Code Kingdom",
            b="Game Buddy is a friendly digital guide who helps curious explorers discover the power of code. When the Virus King corrupts the Kingdom's Core, Game Buddy and Byte call on you to bring the Kingdom back to life.\n\nChoose a coding path, study its language, and answer the quiz to restore the kingdom!\n\nPress ENTER to begin.",
            next="language_select",
        )
    else:
        open_language_select()

def leaderboard_rows():
    rows = []
    for name, progress in load_all().items():
        if not isinstance(name, str) or not isinstance(progress, dict):
            continue
        xp = progress.get("xp", 0)
        if not isinstance(xp, int) or isinstance(xp, bool) or xp < 0:
            continue
        character = progress.get("character", "guardian")
        if name.casefold() == G.name.casefold():
            character = G.S.get("character", character)
        if not any(item["id"] == character for item in CHARACTERS):
            character = "guardian"
        rows.append({"name": name, "xp": xp,
                     "level": 1 + xp // XPL, "character": character})
    return sorted(rows, key=lambda row: (-row["xp"], row["name"].casefold()))

def norm(s, ci=False):
    s = "".join(s.split()).rstrip(";"); return s.lower() if ci else s
def run_tests(src, fn, tests):
    res = {}
    def work():
        try:
            g = {}; exec(src, g); f = g[fn]
            for a, e in tests:
                r = f(*a)
                if r != e: res["m"] = "%s%s returned %r, expected %r" % (fn, a, r, e); return
            res["ok"] = 1
        except Exception as x:
            if WEB and isinstance(x, TimeoutError):
                res["timeout"] = True
            else:
                res["m"] = "%s: %s" % (type(x).__name__, x)
    if WEB:
        deadline = time.monotonic() + 2.5
        previous_trace = sys.gettrace()
        timed_out = [False]

        def trace_line(frame, event, arg):
            if timed_out[0]:
                return None
            if event == "line" and time.monotonic() >= deadline:
                timed_out[0] = True
                raise TimeoutError
            return trace_line

        sys.settrace(trace_line)
        try:
            work()
        finally:
            sys.settrace(previous_trace)
        if res.get("timeout"):
            return False, "Timed out - check for an infinite loop."
        if res.get("ok"):
            return True, "All tests passed."
        return False, res.get("m", "A test failed.")
    t = threading.Thread(target=work, daemon=True); t.start(); t.join(2.5)
    if t.is_alive(): return False, "Timed out - check for an infinite loop."
    if res.get("ok"):
        return True, "All tests passed."
    return False, res.get("m", "A test failed.")
def enter(i):
    c = CH[i]
    if not unlocked(i): return msg("Portal sealed", "Finish %s first." % CH[i - 1]["n"])
    if i in G.S["done"]: return msg(c["n"], "Already complete. Badge: " + c["b"])
    if not portal_obby_completed(i):
        start_portal_obby(i)
        return
    start_portal_challenge(i)

def start_portal_challenge(i):
    c = CH[i]
    if not unlocked(i): return msg("Portal sealed", "Finish %s first." % CH[i - 1]["n"])
    if i in G.S["done"]: return msg(c["n"], "Already complete. Badge: " + c["b"])
    if c["t"] == "tr": G.M = dict(k="tr", i=i, q=0, att=0, wr=0, fb=None, buf=c["items"][0]["s"], hint=False)
    else:
        qs = c["qs"] if c["t"] == "mc" else [
            question for k in range(5) for question in random.sample(CH[k]["qs"], 3)
        ]
        if c["t"] == "boss": random.shuffle(qs)
        G.M = dict(k="mc", i=i, q=0, att=0, wr=0, ok=0, fb=None, qs=qs)

def lesson_card_rect(i):
    row, column = i % 6, i // 6
    return pygame.Rect(132 + column * 368, 122 + row * 58, 350, 50)

def open_lesson(i):
    G.M = dict(k="lesson", i=i)

def open_language_select(selected=0):
    G.M = dict(k="language_select", selected=selected)

def story_language_data(language):
    return STORY_QUEST_DATA["languages"][language]

def story_badges_for_progress(language, progress):
    completed = progress.get("completed_topics", [])
    if not isinstance(completed, (list, tuple, set)):
        completed = []
    completed_topics = {
        topic for topic in completed
        if isinstance(topic, int) and not isinstance(topic, bool)
        and 0 <= topic < 5
    }
    badges = [
        "%s Portal %d" % (language, topic + 1)
        for topic in sorted(completed_topics)
    ]
    if len(completed_topics) == 5:
        badges.append("%s Kingdom Restorer" % language)
    return badges

def story_progress(language):
    all_progress = G.S.setdefault("story_quest", {})
    progress = all_progress.setdefault(language, {})
    progress.setdefault("completed_topics", [])
    progress.setdefault("topic_results", {})
    progress.setdefault("quiz_attempts", [])
    progress.setdefault("challenge_attempts", [])
    progress.setdefault("coding_attempts", [])
    progress.setdefault("coding_completed", [])
    progress.setdefault("stage_crystals", {})
    progress.setdefault("claimed_crystals", [])
    progress.setdefault("rewarded_questions", [])
    progress.setdefault("rewarded_topics", [])
    progress.setdefault("topic_xp", {})
    progress.setdefault("topic_difficulty", {})
    progress.setdefault("earned_badges", [])
    progress.setdefault("xp_earned", 0)
    progress.setdefault("crystals_earned", 0)
    progress.setdefault("run_start_xp", G.S.get("xp", 0))
    progress.setdefault("run_start_level", lvl())
    valid_completed = {
        topic for topic in progress["completed_topics"]
        if isinstance(topic, int) and not isinstance(topic, bool) and 0 <= topic < 5
    }
    progress["completed_topics"] = sorted(valid_completed)
    progress["earned_badges"] = story_badges_for_progress(language, progress)
    return progress

def open_story_quest():
    set_text_input(False)
    G.state = "play"
    G.story_mode = True
    open_story_intro()

def open_story_language_select():
    G.M = dict(k="story_language_select", selected=0)

def select_story_language(language):
    progress = story_progress(language)
    if len(progress["completed_topics"]) == 5:
        G.M = dict(k="story_results", language=language)
    else:
        open_story_lesson_list(language)

def open_story_lesson_list(language, selected=0):
    G.M = dict(k="story_lesson_list", language=language, selected=selected)

def open_story_lesson(language, topic_index):
    completed = topic_index in story_progress(language)["completed_topics"]
    G.M = dict(k="story_lesson", language=language, topic=topic_index,
               read_only=completed, scroll=0)

PRACTICAL_CODING_FALLBACK = {
    "Python": {
        "Introduction": ("Type a complete Python print statement. The print function should display the text Ready. Use quotation marks around the text.",
                         "print( )",
                         ["print", "Ready"], "Ready"),
        "Operators": ("Write a Python expression inside print(). Add the numbers 10 and 5 using the + operator, then display the result.",
                      "print(  )",
                      ["print", "10", "+", "5"], "15"),
        "Casting": ("Create a variable named number. Use int() to convert the text 3 into an integer and assign it to number.",
                    "number = int( )",
                    ["int", "3"], "number is 3"),
        "String": ("Write a print() statement that displays the text Hello. Keep the text inside matching quotation marks.",
                   "print( )",
                   ["print", "Hello"], "Hello"),
        "Data Types": ("Create a variable named numbers. Assign it a list containing the integer values 1 and 2.",
                       "numbers = [ ]",
                       ["numbers", "[", "1", "2"], "[1, 2]"),
    },
    "Java": {
        "Introduction": ("Write a Java statement using System.out.println. Put Hello Java inside double quotation marks and end the statement with a semicolon.",
                         "System.out.println( );",
                         ["System.out.println", "Hello Java"], "Hello Java"),
        "Variables": ("Declare an integer variable named lives. Use the int keyword, the assignment operator, and store 3.",
                      "int lives = ;", ["int", "lives", "=", "3"], "3"),
        "Strings": ("Declare a String variable named name. Assign it the text Byte inside double quotation marks.",
                    "String name = ;", ["String", "name", "Byte"], "Byte"),
        "Booleans": ("Declare a boolean variable named active. Assign it the lowercase Java Boolean value true.",
                     "boolean active = ;",
                     ["boolean", "active", "true"], "true"),
        "Arrays": ("Declare a String array named colors. Use [] after String and place Red and Blue in a pair of braces.",
                   "String[] colors = { };",
                   ["String[]", "colors", "Red", "Blue"], "Red, Blue"),
    },
}

def story_coding_spec(language, topic):
    coding = topic.get("coding")
    if isinstance(coding, dict):
        return {
            "prompt": coding.get("prompt", "Complete the practical coding task."),
            "starter": coding.get("starter", ""),
            "checks": coding.get("checks", []),
            "expected_output": coding.get("expected_output", ""),
        }
    fallback = PRACTICAL_CODING_FALLBACK.get(language, {}).get(topic["topic"])
    if fallback:
        prompt, starter, checks, expected_output = fallback
        return {
            "prompt": prompt,
            "starter": starter,
            "checks": checks,
            "expected_output": expected_output,
        }
    return {
        "prompt": "Write code that demonstrates this lesson.",
        "starter": "",
        "checks": [],
        "expected_output": "Your code demonstrates the lesson.",
    }

def re_placeholder_start(text):
    start = text.find("{{")
    if start < 0:
        return None
    end = text.find("}}", start + 2)
    if end < 0:
        return None
    return start, end + 2

def re_placeholder_ranges(text):
    ranges = []
    search_from = 0
    while True:
        start = text.find("{{", search_from)
        if start < 0:
            break
        end = text.find("}}", start + 2)
        if end < 0:
            break
        ranges.append((start, end + 2))
        search_from = end + 2
    return ranges

def select_next_story_placeholder(modal):
    ranges = re_placeholder_ranges(modal["input"])
    if not ranges:
        return
    cursor = modal["cursor"]
    for start, end in ranges:
        if end > cursor:
            modal["anchor"] = start
            modal["cursor"] = end
            return
    start, end = ranges[0]
    modal["anchor"] = start
    modal["cursor"] = end

def open_story_coding(language, topic_index):
    topic = story_language_data(language)["topics"][topic_index]
    spec = story_coding_spec(language, topic)
    first_placeholder = re_placeholder_start(spec["starter"])
    cursor = len(spec["starter"])
    anchor = None
    if first_placeholder is not None:
        placeholder_start, placeholder_end = first_placeholder
        anchor = placeholder_start
        cursor = placeholder_end
    G.M = dict(k="story_coding", language=language, topic=topic_index,
               input=spec["starter"], cursor=cursor,
               anchor=anchor, spec=spec, feedback=None)
    set_text_input(True)

def start_story_parkour(language, topic_index):
    if topic_index in story_progress(language)["completed_topics"]:
        open_story_lesson(language, topic_index)
        return
    open_story_difficulty(language, topic_index)

def open_story_difficulty(language, topic_index):
    set_text_input(False)
    chosen = current_difficulty()
    G.M = dict(k="story_difficulty", language=language, topic=topic_index,
               selected=DIFFICULTIES.index(chosen))

def launch_story_parkour(language, topic_index, difficulty_index):
    difficulty = DIFFICULTIES[difficulty_index]
    G.S["difficulty"] = difficulty["id"]
    save()
    language_index = STORY_LANGUAGE_NAMES.index(language)
    set_text_input(False)
    G.M = {}
    G.story_language = language
    G.story_topic_index = topic_index
    start_portal_obby(language_index, "story")
    toast("%s difficulty: crystals +%d XP each." % (difficulty["name"], difficulty["crystal_xp"]))

def start_story_quiz(language, topic_index, replay=False):
    if topic_index in story_progress(language)["completed_topics"] and not replay:
        open_story_lesson(language, topic_index)
        return
    G.state = "play"
    progress = story_progress(language)
    records = progress["quiz_attempts"] + progress["challenge_attempts"]
    topic_records = {
        record["question"]: record
        for record in records if record["topic"] == topic_index
    }
    unresolved = next((index for index in range(3)
                       if index in topic_records and not topic_records[index].get("advanced")), None)
    first_unanswered = next((index for index in range(3)
                             if index not in topic_records), None)
    if unresolved is None and first_unanswered is None:
        if topic_index == 4:
            player_hp, king_hp = story_battle_health(topic_records)
            if player_hp <= king_hp:
                set_text_input(False)
                G.M = dict(
                    k="story_battle_result",
                    language=language,
                    battle_player_hp=player_hp,
                    battle_king_hp=king_hp,
                    battle_hits=3 - king_hp,
                    battle_effect=None,
                    battle_effect_start=G.t,
                )
                return
        coding_key = "%d" % topic_index
        if coding_key not in progress.get("coding_completed", []):
            open_story_coding(language, topic_index)
        else:
            complete_story_topic(language, topic_index)
        return
    question_index = unresolved if unresolved is not None else first_unanswered
    feedback = None
    player_hp, king_hp = story_battle_health(topic_records)
    if unresolved is not None:
        saved = topic_records[unresolved]
        feedback = {
            "correct": saved["correct"],
            "selected": saved["submitted_answer"],
            "correct_answer": saved["correct_answer"],
            "explanation": saved["explanation"],
            "xp_awarded": saved.get("xp_awarded", 0),
        }
    G.M = dict(k="story_quiz", language=language, topic=topic_index,
               question=question_index, input="", feedback=feedback, answers=[],
               records=topic_records, battle_hits=sum(
                   bool(record["correct"]) for record in topic_records.values()),
               battle_player_hp=player_hp, battle_king_hp=king_hp,
               battle_effect=None, battle_effect_start=G.t)
    if topic_index == 4 and feedback is not None:
        G.M["battle_effect"] = "strike" if feedback["correct"] else "counter"
    question = story_language_data(language)["topics"][topic_index]["questions"][question_index]
    set_text_input(feedback is None and
                   (topic_index == 4 or question["type"] != "multiple_choice"))

def story_attempt_records(progress, topic_index):
    records = progress["quiz_attempts"] + progress["challenge_attempts"]
    return {
        record["question"]: record
        for record in records if record["topic"] == topic_index
    }

def story_battle_health(topic_records):
    correct = sum(bool(record["correct"]) for record in topic_records.values())
    incorrect = len(topic_records) - correct
    return max(0, 3 - incorrect), max(0, 3 - correct)

def submit_story_answer(answer):
    modal = G.M
    if modal["feedback"] is not None:
        return
    progress = story_progress(modal["language"])
    topic_records = story_attempt_records(progress, modal["topic"])
    if modal["question"] in topic_records:
        return
    topic = story_language_data(modal["language"])["topics"][modal["topic"]]
    question = topic["questions"][modal["question"]]
    normalized = answer.strip()
    accepted = question["answers"]
    if not question.get("case_sensitive", True):
        normalized = normalized.casefold()
        accepted = [candidate.strip().casefold() for candidate in accepted]
    else:
        accepted = [candidate.strip() for candidate in accepted]
    correct = normalized in accepted
    record_key = "%d:%d" % (modal["topic"], modal["question"])
    xp_awarded = int(correct and record_key not in progress["rewarded_questions"]) * 5
    modal["feedback"] = {
        "correct": correct,
        "selected": answer,
        "correct_answer": question["answers"][0],
        "explanation": question["explanation"],
        "xp_awarded": xp_awarded,
    }
    if modal["topic"] == 4:
        modal["battle_effect"] = "strike" if correct else "counter"
        modal["battle_effect_start"] = G.t
        modal["battle_hits"] = modal.get("battle_hits", 0) + int(correct)
        modal["battle_player_hp"] = max(
            0, modal.get("battle_player_hp", 3) - int(not correct))
        modal["battle_king_hp"] = max(
            0, modal.get("battle_king_hp", 3) - int(correct))
    record = {
        "topic": modal["topic"],
        "question": modal["question"],
        "type": question["type"],
        "submitted_answer": answer,
        "correct": correct,
        "score": int(correct),
        "total_items": 1,
        "xp_awarded": xp_awarded,
        "correct_answer": question["answers"][0],
        "explanation": question["explanation"],
        "feedback": ("Correct. " if correct else "Incorrect. Correct answer: %s. " %
                     question["answers"][0]) + question["explanation"],
        "advanced": False,
    }
    if question["type"] == "multiple_choice":
        progress["quiz_attempts"].append(record)
    else:
        progress["challenge_attempts"].append(record)
    if correct and record_key not in progress["rewarded_questions"]:
        progress["rewarded_questions"].append(record_key)
        progress["xp_earned"] += 5
        progress["topic_xp"][str(modal["topic"])] = (
            progress["topic_xp"].get(str(modal["topic"]), 0) + 5)
        gain(5)
    else:
        save()
    set_text_input(False)

def story_coding_guidance(check):
    guidance = {
        "Replace every {{TYPE_HERE}} field":
            "replace each highlighted {{TYPE_HERE}} field with your answer",
        "print": "include the print() function",
        "Ready": 'put Ready inside quotation marks, such as "Ready"',
        "10": "include the number 10",
        "5": "include the number 5",
        "+": "use the + operator between the numbers",
        "int": "use int() to convert the text",
        "3": "include 3 as the value",
        "Hello": 'put Hello inside quotation marks',
        "numbers": "create a variable named numbers",
        "1": "include the value 1",
        "2": "include the value 2",
        "System.out.println": "use System.out.println()",
        "Hello Java": 'put Hello Java inside double quotes',
        "int": "use the int keyword",
        "lives": "name the variable lives",
        "=": "use = to assign the value",
        "String": "use the String keyword",
        "name": "name the variable name",
        "Byte": 'use "Byte" inside double quotes',
        "boolean": "use the boolean keyword",
        "active": "name the variable active",
        "true": "assign the lowercase value true",
        "String[]": "declare a String array with []",
        "colors": "name the array colors",
        "Red": 'include "Red"',
        "Blue": 'include "Blue"',
        "<i": "start the icon element with <i",
        "fa-solid": 'include class="fa-solid"',
        "fa-house": "include the fa-house icon name",
    }
    text = guidance.get(check)
    if text:
        return text
    if check.startswith("<"):
        return "include the %s HTML tag" % check
    return "include %s" % check

def submit_story_coding():
    modal = G.M
    if modal.get("feedback"):
        return
    language = modal["language"]
    topic_index = modal["topic"]
    code = modal["input"]
    checks = modal["spec"].get("checks", [])
    lowered_code = code.lower()
    missing = [
        check for check in checks
        if str(check).lower() not in lowered_code
    ]
    placeholder_ranges = re_placeholder_ranges(code)
    if placeholder_ranges:
        missing.append("Replace every {{TYPE_HERE}} field")
    progress = story_progress(language)
    coding_attempts = progress.setdefault("coding_attempts", [])
    coding_attempts.append({
        "topic": topic_index,
        "code": code,
        "correct": not missing,
    })
    if missing:
        modal["feedback"] = {
            "correct": False,
            "missing": missing,
            "guidance": [story_coding_guidance(check) for check in missing],
        }
        save()
        set_text_input(True)
        return
    coding_completed = progress.setdefault("coding_completed", [])
    already_completed = "%d" % topic_index in coding_completed
    if not already_completed:
        coding_completed.append("%d" % topic_index)
        progress["xp_earned"] = progress.get("xp_earned", 0) + 10
        progress["topic_xp"][str(topic_index)] = (
            progress["topic_xp"].get(str(topic_index), 0) + 10)
        gain(10)
    modal["feedback"] = {
        "correct": True,
        "xp_awarded": 0 if already_completed else 10,
    }
    if topic_index == 4:
        play_boss_defeat_sound(language)
    save()
    set_text_input(False)

def advance_story_question():
    modal = G.M
    feedback = modal["feedback"]
    progress = story_progress(modal["language"])
    topic_records = story_attempt_records(progress, modal["topic"])
    topic_records[modal["question"]]["advanced"] = True
    save()
    modal["input"] = ""
    modal["feedback"] = None
    next_question = next((index for index in range(3)
                          if index not in topic_records), None)
    if next_question is None:
        set_text_input(False)
        if (modal["topic"] == 4
                and modal["battle_player_hp"] <= modal["battle_king_hp"]):
            G.M = dict(
                k="story_battle_result",
                language=modal["language"],
                battle_player_hp=modal["battle_player_hp"],
                battle_king_hp=modal["battle_king_hp"],
                battle_hits=modal["battle_hits"],
                battle_effect=modal.get("battle_effect"),
                battle_effect_start=modal.get("battle_effect_start", G.t),
            )
        else:
            open_story_coding(modal["language"], modal["topic"])
    else:
        modal["question"] = next_question
        question = story_language_data(modal["language"])["topics"][modal["topic"]]["questions"][next_question]
        set_text_input(modal["topic"] == 4 or
                       question["type"] != "multiple_choice")

def retry_story_topic_quiz(language, topic_index):
    progress = story_progress(language)
    progress["quiz_attempts"] = [
        record for record in progress["quiz_attempts"]
        if record.get("topic") != topic_index
    ]
    progress["challenge_attempts"] = [
        record for record in progress["challenge_attempts"]
        if record.get("topic") != topic_index
    ]
    progress["topic_results"].pop(str(topic_index), None)
    save()
    start_story_quiz(language, topic_index, replay=True)

def retry_story_battle(language):
    progress = story_progress(language)
    for key in ("quiz_attempts", "challenge_attempts"):
        progress[key] = [
            record for record in progress[key]
            if not (record["topic"] == 4)
        ]
    progress["topic_results"].pop("4", None)
    if 4 in progress["completed_topics"]:
        progress["completed_topics"].remove(4)
    save()
    start_story_quiz(language, 4)

def complete_story_topic(language, topic_index):
    progress = story_progress(language)
    topic_records = story_attempt_records(progress, topic_index)
    if len(topic_records) != 3:
        return
    results = [topic_records[index]["correct"] for index in range(3)]
    progress["topic_results"][str(topic_index)] = results
    if topic_index not in progress["completed_topics"]:
        progress["completed_topics"].append(topic_index)
        badge = "%s Portal %d" % (language, topic_index + 1)
        if badge not in progress["earned_badges"]:
            progress["earned_badges"].append(badge)
    if topic_index not in progress["rewarded_topics"]:
        progress["rewarded_topics"].append(topic_index)
        topic_bonus = difficulty_by_id(
            progress.get("topic_difficulty", {}).get(str(topic_index))
        )["topic_xp"]
        progress["xp_earned"] += topic_bonus
        progress["topic_xp"][str(topic_index)] = (
            progress["topic_xp"].get(str(topic_index), 0) + topic_bonus)
        gain(topic_bonus)
    save()
    if len(progress["completed_topics"]) == 5:
        path_badge = "%s Kingdom Restorer" % language
        if path_badge not in progress["earned_badges"]:
            progress["earned_badges"].append(path_badge)
            save()
        G.M = dict(k="story_ending", language=language, t=0.0, typed=0.0)
    else:
        next_topic = next(i for i in range(5) if i not in progress["completed_topics"])
        open_story_lesson_list(language, next_topic)

def story_results_summary(language):
    progress = story_progress(language)
    by_topic = []
    by_type = {question_type: [0, 0] for question_type in STORY_QUESTION_TYPES}
    total = 0
    for topic_index, topic in enumerate(story_language_data(language)["topics"]):
        results = progress["topic_results"].get(str(topic_index), [False, False, False])
        score = sum(bool(result) for result in results)
        total += score
        by_topic.append((topic["topic"], score))
        for question_index, question in enumerate(topic["questions"]):
            by_type[question["type"]][0] += int(bool(results[question_index]))
            by_type[question["type"]][1] += 1
    return total, by_topic, by_type

def reset_story_language(language):
    old = story_progress(language)
    G.S["story_quest"][language] = {
        "completed_topics": [],
        "topic_results": {},
        "quiz_attempts": [],
        "challenge_attempts": [],
        "coding_attempts": [],
        "coding_completed": [],
        "stage_crystals": {},
        "claimed_crystals": old["claimed_crystals"],
        "rewarded_questions": old["rewarded_questions"],
        "rewarded_topics": old["rewarded_topics"],
        "earned_badges": [],
        "topic_xp": {},
        "xp_earned": 0,
        "crystals_earned": 0,
        "run_start_xp": G.S.get("xp", 0),
        "run_start_level": lvl(),
    }
    save()
    open_story_lesson_list(language)

def open_language_lesson(i):
    G.M = dict(k="language_lesson", i=i)

def start_language_quiz(i):
    G.M = dict(k="language_quiz", i=i, q=0, correct=0, answers=[], feedback=None)

def answer_language_question(choice):
    modal = G.M
    question = LANGUAGE_PATHS[modal["i"]]["questions"][modal["q"]]
    correct = choice == question[2]
    modal["feedback"] = {
        "choice": choice,
        "correct": correct,
        "correct_choice": question[2],
        "explanation": question[3],
    }

def advance_language_quiz():
    modal = G.M
    feedback = modal["feedback"]
    question = LANGUAGE_PATHS[modal["i"]]["questions"][modal["q"]]
    modal["answers"].append({
        "correct": feedback["correct"],
        "selected": feedback["choice"],
        "correct_choice": feedback["correct_choice"],
        "explanation": feedback["explanation"],
    })
    modal["correct"] += int(feedback["correct"])
    modal["q"] += 1
    modal["feedback"] = None
    if modal["q"] == len(LANGUAGE_PATHS[modal["i"]]["questions"]):
        G.M = dict(k="language_result", i=modal["i"], score=modal["correct"],
                   answers=modal["answers"])

def close_message():
    next_modal = G.M.get("next")
    G.M = {}
    if next_modal == "language_select":
        open_language_select()

def start_lesson_quiz(i):
    G.M = {}
    start_portal_challenge(i)
def finish(i, att, wr):
    c = CH[i]; G.S["done"].append(i)
    if i == 5: G.S["won"] = True
    if i < 6: G.S["crystal_balance"] += 1
    gain(c["xp"])
    story = {
        5: "\n\nVICTORY! The kingdom is saved. New coding trials wait beyond the fortress, to the east.",
        9: "\n\nThe compiler reveals a hidden signal beyond the old kingdom. Byte has found a path to the Firewall Frontier.",
        10: "\n\nThe firewall beacon is secure, but its logs trace the Virus King's signal to the Cloud Citadel.",
        11: "\n\nThe cloud core is restored. The kingdom's network is safe, and its neighboring regions are connected again!",
    }.get(i, "")
    msg("Quest complete!", "You earned the %s badge and %d XP.\nAttempts: %d   Mistakes: %d" % (c["b"], c["xp"], att, wr) +
        story)
def advance_question():
    M = G.M
    M.pop("answer", None); M.pop("fb_until", None)
    if M["k"] == "mc":
        if M["q"] + 1 >= len(M["qs"]):
            i, a, w = M["i"], M["att"], M["wr"]; G.M = {}; finish(i, a, w)
        else:
            M["q"] += 1; M["fb"] = None
        return
    items = CH[M["i"]]["items"]
    if M["q"] + 1 >= len(items):
        i, a, w = M["i"], M["att"], M["wr"]; G.M = {}; finish(i, a, w)
    else:
        M["q"] += 1; M["fb"] = None; M["hint"] = False; M["buf"] = items[M["q"]]["s"]

def submit(it):
    M = G.M; M["att"] += 1
    if it["k"] == "code": ok, m = run_tests(M["buf"], it["fn"], it["t"])
    else: ok = any(norm(a, it["ci"]) == norm(M["buf"], it["ci"]) for a in it["a"]); m = "Re-read the code carefully, or press F1 for a hint."
    if not ok:
        M["wr"] += 1
        M["fb"] = (False, it["h"])
        M["answer"] = it["solution"]
        M["fb_until"] = G.t + 5
        return
    M["fb"] = (True, "Correct!")
def modal_key(e):
    M = G.M; k = M["k"]
    if e.key == pygame.K_ESCAPE:
        if k == "story_quiz":
            return
        elif k == "story_coding":
            open_story_lesson(M["language"], M["topic"])
        elif k == "story_ending":
            G.M = dict(k="story_results", language=M["language"])
        elif k == "story_battle_result":
            open_story_lesson_list(M["language"], 4)
        elif k == "story_results":
            stop_boss_defeat_sound()
            G.M = {}; G.state = "home"; G.story_mode = False
        elif k == "story_lesson":
            open_story_lesson_list(M["language"], M["topic"])
        elif k == "story_difficulty":
            open_story_lesson(M["language"], M["topic"])
        elif k in ("story_intro", "story_language_select", "story_lesson_list"):
            if k == "story_intro":
                stop_story_voice()
                G.M = {}; G.state = "home"; G.story_mode = False
            elif k == "story_language_select":
                open_story_intro(len(INTRO_SCENES) - 1)
            else:
                open_story_language_select()
        elif k == "language_lesson":
            open_language_select(M["i"])
        elif k in ("language_select", "language_quiz", "language_result"):
            G.M = {}; G.state = "home"
        else:
            G.M = {}
        return
    if k == "build":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            if M["elapsed"] >= len(BUILD_STEPS) * BUILD_STEP_SECONDS:
                G.M = {}
            else:
                M["elapsed"] = min(
                    len(BUILD_STEPS) * BUILD_STEP_SECONDS,
                    (int(M["elapsed"] / BUILD_STEP_SECONDS) + 1) * BUILD_STEP_SECONDS,
                )
    elif k == "msg":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE): close_message()
    elif k == "language_select":
        if pygame.K_1 <= e.key <= pygame.K_5:
            open_language_lesson(e.key - pygame.K_1)
        elif e.key in (pygame.K_LEFT, pygame.K_a):
            M["selected"] = (M["selected"] - 1) % len(LANGUAGE_PATHS)
        elif e.key in (pygame.K_RIGHT, pygame.K_d):
            M["selected"] = (M["selected"] + 1) % len(LANGUAGE_PATHS)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
            open_language_lesson(M["selected"])
    elif k == "language_lesson":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            i = M["i"]
            start_language_quiz(i)
    elif k == "language_quiz":
        if M["feedback"] is None:
            if pygame.K_1 <= e.key <= pygame.K_4:
                answer_language_question(e.key - pygame.K_1)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
            advance_language_quiz()
    elif k == "language_result":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            open_language_select(M["i"])
    elif k == "story_intro":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            advance_story_intro()
        elif e.key == pygame.K_s and M["scene"] < len(INTRO_SCENES) - 1:
            skip_story_intro()
    elif k == "story_ending":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            advance_story_ending()
    elif k == "story_language_select":
        if pygame.K_1 <= e.key <= pygame.K_5:
            select_story_language(STORY_LANGUAGE_NAMES[e.key - pygame.K_1])
        elif e.key in (pygame.K_LEFT, pygame.K_a):
            M["selected"] = (M["selected"] - 1) % len(STORY_LANGUAGE_NAMES)
        elif e.key in (pygame.K_RIGHT, pygame.K_d):
            M["selected"] = (M["selected"] + 1) % len(STORY_LANGUAGE_NAMES)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
            select_story_language(STORY_LANGUAGE_NAMES[M["selected"]])
    elif k == "story_lesson_list":
        if e.key in (pygame.K_UP, pygame.K_w):
            M["selected"] = (M["selected"] - 1) % 5
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            M["selected"] = (M["selected"] + 1) % 5
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
            open_story_lesson(M["language"], M["selected"])
    elif k == "story_difficulty":
        if pygame.K_1 <= e.key <= pygame.K_6:
            M["selected"] = e.key - pygame.K_1
        elif e.key in (pygame.K_LEFT, pygame.K_a):
            M["selected"] = (M["selected"] - 1) % len(DIFFICULTIES)
        elif e.key in (pygame.K_RIGHT, pygame.K_d):
            M["selected"] = (M["selected"] + 1) % len(DIFFICULTIES)
        elif e.key in (pygame.K_UP, pygame.K_w):
            M["selected"] = (M["selected"] - 2) % len(DIFFICULTIES)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            M["selected"] = (M["selected"] + 2) % len(DIFFICULTIES)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
            launch_story_parkour(M["language"], M["topic"], M["selected"])
        elif e.key == pygame.K_b:
            open_story_lesson(M["language"], M["topic"])
    elif k == "story_lesson":
        if e.key == pygame.K_b:
            open_story_lesson_list(M["language"], M["topic"])
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE) and M["read_only"]:
            retry_story_topic_quiz(M["language"], M["topic"])
        elif e.key in (pygame.K_UP, pygame.K_w):
            M["scroll"] = max(0, M.get("scroll", 0) - 28)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            M["scroll"] = M.get("scroll", 0) + 28
        elif e.key == pygame.K_PAGEUP:
            M["scroll"] = max(0, M.get("scroll", 0) - 120)
        elif e.key == pygame.K_PAGEDOWN:
            M["scroll"] = M.get("scroll", 0) + 120
    elif k == "story_quiz":
        question = story_language_data(M["language"])["topics"][M["topic"]]["questions"][M["question"]]
        if M["feedback"] is not None:
            if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                advance_story_question()
        elif M["topic"] == 4:
            if e.key == pygame.K_BACKSPACE:
                M["input"] = M["input"][:-1]
            elif e.key == pygame.K_RETURN:
                submit_story_answer(M["input"])
        elif question["type"] == "multiple_choice" and pygame.K_1 <= e.key <= pygame.K_4:
            choice = e.key - pygame.K_1
            if choice < len(question["options"]):
                submit_story_answer(question["options"][choice])
        elif question["type"] != "multiple_choice":
            if e.key == pygame.K_BACKSPACE:
                M["input"] = M["input"][:-1]
            elif e.key == pygame.K_RETURN:
                submit_story_answer(M["input"])
    elif k == "story_coding":
        if M["feedback"] is not None:
            if (M["feedback"]["correct"] and
                    e.key in (pygame.K_RETURN, pygame.K_SPACE)):
                complete_story_topic(M["language"], M["topic"])
                set_text_input(False)
                return
        if not M.get("cursor") and M.get("cursor") != 0:
            M["cursor"] = len(M["input"])
        mod = e.mod
        ctrl = bool(mod & pygame.KMOD_CTRL)
        if ctrl and e.key == pygame.K_a:
            M["anchor"] = 0
            M["cursor"] = len(M["input"])
        elif ctrl and e.key == pygame.K_l:
            M["input"] = ""
            M["cursor"] = 0
            M["anchor"] = None
            M["feedback"] = None
        elif e.key == pygame.K_TAB:
            select_next_story_placeholder(M)
        elif e.key == pygame.K_BACKSPACE:
            cursor = M["cursor"]
            anchor = M.get("anchor")
            if anchor is not None:
                start, end = sorted((anchor, cursor))
                M["input"] = M["input"][:start] + M["input"][end:]
                M["cursor"] = start
                M["anchor"] = None
            elif cursor > 0:
                M["input"] = M["input"][:cursor - 1] + M["input"][cursor:]
                M["cursor"] -= 1
            M["feedback"] = None
        elif e.key == pygame.K_DELETE:
            cursor = M["cursor"]
            anchor = M.get("anchor")
            if anchor is not None:
                start, end = sorted((anchor, cursor))
                M["input"] = M["input"][:start] + M["input"][end:]
                M["cursor"] = start
                M["anchor"] = None
            elif cursor < len(M["input"]):
                M["input"] = M["input"][:cursor] + M["input"][cursor + 1:]
            M["feedback"] = None
        elif e.key == pygame.K_LEFT:
            M["cursor"] = max(0, M["cursor"] - 1)
        elif e.key == pygame.K_RIGHT:
            M["cursor"] = min(len(M["input"]), M["cursor"] + 1)
        elif e.key == pygame.K_HOME:
            M["cursor"] = M["input"].rfind("\n", 0, M["cursor"]) + 1
        elif e.key == pygame.K_END:
            next_newline = M["input"].find("\n", M["cursor"])
            M["cursor"] = len(M["input"]) if next_newline < 0 else next_newline
        elif e.key == pygame.K_UP:
            line_start = M["input"].rfind("\n", 0, M["cursor"])
            previous_start = M["input"].rfind("\n", 0, line_start)
            column = M["cursor"] - (line_start + 1)
            previous_line_end = line_start
            M["cursor"] = min(previous_start + 1 + column, previous_line_end)
            if line_start < 0:
                M["cursor"] = 0
        elif e.key == pygame.K_DOWN:
            line_start = M["input"].rfind("\n", 0, M["cursor"])
            next_newline = M["input"].find("\n", M["cursor"])
            if next_newline >= 0:
                following_newline = M["input"].find("\n", next_newline + 1)
                following_end = len(M["input"]) if following_newline < 0 else following_newline
                column = M["cursor"] - (line_start + 1) if line_start >= 0 else M["cursor"]
                M["cursor"] = min(next_newline + 1 + column, following_end)
        elif e.key == pygame.K_RETURN:
            if ctrl or bool(mod & pygame.KMOD_SHIFT):
                submit_story_coding()
            else:
                cursor = M["cursor"]
                M["input"] = M["input"][:cursor] + "\n" + M["input"][cursor:]
                M["cursor"] = cursor + 1
                M["feedback"] = None
    elif k == "story_battle_result":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            retry_story_battle(M["language"])
    elif k == "story_results":
        if e.key == pygame.K_r:
            reset_story_language(M["language"])
        elif e.key in (pygame.K_l, pygame.K_RETURN, pygame.K_SPACE):
            open_story_language_select()
    elif k == "lesson_menu":
        if e.key in (pygame.K_UP, pygame.K_w):
            M["selected"] = M["selected"] // 6 * 6 + (M["selected"] % 6 - 1) % 6
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            M["selected"] = M["selected"] // 6 * 6 + (M["selected"] % 6 + 1) % 6
        elif e.key == pygame.K_LEFT:
            M["selected"] = (M["selected"] - 6) % len(LESSONS)
        elif e.key == pygame.K_RIGHT:
            M["selected"] = (M["selected"] + 6) % len(LESSONS)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
            open_lesson(M["selected"])
    elif k == "lesson":
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            i = M["i"]
            if unlocked(i) and i not in G.S["done"]:
                start_lesson_quiz(i)
            else:
                G.M = dict(k="lesson_menu", selected=i)
    elif k == "mc":
        if M["fb"] is None:
            n = e.key - pygame.K_1; q = M["qs"][M["q"]]
            if 0 <= n < len(q[1]):
                M["att"] += 1; ok = n == q[2]; M["wr"] += 0 if ok else 1
                if ok:
                    M["fb"] = (True, q[3])
                else:
                    M["fb"] = (False, q[3])
                    M["answer"] = q[1][q[2]]
                    M["fb_until"] = G.t + 5
        elif e.key == pygame.K_RETURN:
            if not M["fb"][0]: advance_question()
            else:
                M["q"] += 1; M["ok"] += 1; M["fb"] = None
                if M["q"] >= len(M["qs"]): i, a, w = M["i"], M["att"], M["wr"]; G.M = {}; finish(i, a, w)
    else:
        items = CH[M["i"]]["items"]; it = items[M["q"]]; cd = it["k"] == "code"
        if M["fb"] and not M["fb"][0]:
            if e.key == pygame.K_RETURN: advance_question()
            return
        if M["fb"] and M["fb"][0]:
            if e.key == pygame.K_RETURN:
                M["q"] += 1; M["fb"] = None; M["hint"] = False
                if M["q"] >= len(items): i, a, w = M["i"], M["att"], M["wr"]; G.M = {}; finish(i, a, w)
                else: M["buf"] = items[M["q"]]["s"]
            return
        run = e.key == pygame.K_F5 or (e.key == pygame.K_RETURN and (e.mod & pygame.KMOD_CTRL or not cd))
        if e.key == pygame.K_F1: M["hint"] = True
        elif e.key == pygame.K_BACKSPACE: M["buf"] = M["buf"][:-1]
        elif e.key == pygame.K_TAB and cd: M["buf"] += "    "
        elif run: submit(it)
        elif e.key == pygame.K_RETURN: M["buf"] += "\n"
        elif e.unicode and e.unicode.isprintable(): M["buf"] += e.unicode

def make_sky(top, middle, bottom):
    sky = pygame.Surface((W, H))
    for y in range(H):
        f = y / H
        a, b = (top, middle) if f < .55 else (middle, bottom)
        blend = f / .55 if f < .55 else (f - .55) / .45
        color = tuple(int(a[i] + (b[i] - a[i]) * blend) for i in range(3))
        pygame.draw.line(sky, color, (0, y), (W, y))
    return sky

SKY = make_sky((12, 26, 30), (40, 88, 76), (214, 140, 60))
MAP_SKIES = [
    SKY,
    make_sky((30, 10, 24), (112, 32, 50), (222, 100, 64)),
    make_sky((22, 56, 92), (66, 148, 200), (190, 232, 244)),
]
PARKOUR_BACKGROUND_FILES = {
    "Java": "java_parkour_background.png",
    "JavaScript": "javascript_parkour_background.png",
    "HTML": "html_parkour_background.png",
    "CSS": "css_parkour_background.png",
}

def cover_background(image):
    scale = max(W / image.get_width(), H / image.get_height())
    scaled_size = (
        round(image.get_width() * scale),
        round(image.get_height() * scale),
    )
    scaled = pygame.transform.smoothscale(image, scaled_size)
    crop = pygame.Rect(0, 0, W, H)
    crop.center = scaled.get_rect().center
    return scaled.subsurface(crop).copy()

PARKOUR_BACKGROUNDS = {
    language: cover_background(
        pygame.image.load(os.path.join(ASSET_DIR, filename)).convert()
    )
    for language, filename in PARKOUR_BACKGROUND_FILES.items()
}
PARKOUR_HUD_SHADE = pygame.Surface((W, 112), pygame.SRCALPHA)
PARKOUR_HUD_SHADE.fill((12, 20, 32, 135))
STORY_BATTLE_SHADE = pygame.Surface((W - 264, 148), pygame.SRCALPHA)
STORY_BATTLE_SHADE.fill((12, 20, 32, 96))
STARS = [(random.randint(0, W), random.randint(0, 300), random.randint(1, 3)) for _ in range(70)]
JUNGLE_BG_DATA = "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"
def load_jungle_bg():
    try:
        import base64, io
        img = pygame.image.load(io.BytesIO(base64.b64decode(JUNGLE_BG_DATA)), "jungle_bg.png").convert()
        w = round(img.get_width() * H / img.get_height())
        img = pygame.transform.scale(img, (w, H))
        return img.subsurface(((w - W) // 2, 0, W, H)).copy()
    except Exception as err:
        print("Jungle background could not be loaded:", err)
        return None
JUNGLE_BG = load_jungle_bg()
STORY_SCENE_BACKGROUND_CACHE = {}
def story_scene_background(language, size):
    key = (language, size)
    if key not in STORY_SCENE_BACKGROUND_CACHE:
        background = JUNGLE_BG if language == "Python" else PARKOUR_BACKGROUNDS[language]
        if background is None:
            return None
        scale = max(size[0] / background.get_width(),
                    size[1] / background.get_height())
        scaled_size = (round(background.get_width() * scale),
                       round(background.get_height() * scale))
        scaled = pygame.transform.smoothscale(background, scaled_size)
        crop = pygame.Rect(0, 0, *size)
        crop.center = scaled.get_rect().center
        STORY_SCENE_BACKGROUND_CACHE[key] = scaled.subsurface(crop).copy()
    return STORY_SCENE_BACKGROUND_CACHE[key]
CLOUDS = [(random.randint(0, 3000), random.randint(470, 670), random.randint(120, 300), random.choice((.25, .5))) for _ in range(16)]
def wrap(t, f, w):
    out = []
    for p in t.split("\n"):
        line = ""
        for word in p.split(" "):
            test = (line + " " + word) if line else word
            if f.size(test)[0] <= w: line = test
            else: out.append(line); line = word
        out.append(line)
    return out
def text(s, x, y, col=WHITE, f=F): scr.blit(f.render(s, True, col), (x, y))
def para(t, x, y, w, col=WHITE, f=F):
    for l in wrap(t, f, w): text(l, x, y, col, f); y += f.get_linesize() + 2
    return y
_PANEL_CACHE = {}
def _panel_surfaces(size):
    if size not in _PANEL_CACHE:
        w, h = size
        body = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            f = y / h
            c = (int(70 - 34 * f), int(88 - 42 * f), int(102 - 46 * f), 255)
            pygame.draw.line(body, c, (0, y), (w, y))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (244, 240, 226, 255), (0, 0, w, h), 0, 14)
        body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        glow = pygame.Surface((w + 40, h + 40), pygame.SRCALPHA)
        for i in range(1, 6):
            pygame.draw.rect(glow, (255, 205, 64, 46 - i * 8),
                             (20 - i * 3, 20 - i * 3, w + i * 6, h + i * 6), 3, 14 + i * 3)
        _PANEL_CACHE[size] = (body, glow)
    return _PANEL_CACHE[size]

def panel(title):
    r = pygame.Rect(110, 40, W - 220, H - 80)
    body, glow = _panel_surfaces(r.size)
    scr.blit(glow, (r.x - 20, r.y - 20))
    scr.blit(body, r.topleft)
    pygame.draw.rect(scr, GOLD, r, 3, 14)
    pygame.draw.rect(scr, (104, 206, 172), r.inflate(-12, -12), 1, 10)
    text(title, r.x + 24, r.y + 14, (10, 20, 22), FB)
    text(title, r.x + 22, r.y + 12, GOLD, FB)
    return r

_SPARK_CACHE = {}
SPARK_COLORS = ((255, 205, 70), (160, 230, 60), (240, 150, 40), (96, 214, 226), (230, 72, 84))
def draw_particles():
    t = G.t
    for i in range(30):
        size = 2 + i % 3
        color = SPARK_COLORS[i % len(SPARK_COLORS)]
        key = (color, size)
        if key not in _SPARK_CACHE:
            surf = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            pygame.draw.circle(surf, color + (45,), (size * 3, size * 3), size * 3)
            pygame.draw.circle(surf, color + (210,), (size * 3, size * 3), size)
            _SPARK_CACHE[key] = surf
        x = (i * 137 + t * (6 + i % 5 * 3) + math.sin(t * .8 + i) * 18) % W
        y = H - ((i * 71 + t * (12 + i % 4 * 5)) % H)
        scr.blit(_SPARK_CACHE[key], (x - size * 3, y - size * 3))
DEFAULT_PLATFORM_PALETTE = {
    "base": (122, 106, 90),
    "edge": (90, 64, 48),
    "top": (150, 220, 80),
    "highlight": (150, 220, 80),
}
PARKOUR_PLATFORM_PALETTES = {
    "Java": {
        "base": (76, 91, 113),
        "edge": (49, 62, 81),
        "top": (144, 173, 201),
        "highlight": (105, 212, 232),
    },
    "Python": {
        "base": (83, 91, 59),
        "edge": (52, 69, 43),
        "top": (128, 180, 68),
        "highlight": (184, 224, 105),
    },
    "JavaScript": {
        "base": (51, 62, 87),
        "edge": (29, 38, 61),
        "top": (77, 111, 149),
        "highlight": (127, 192, 235),
    },
    "HTML": {
        "base": (105, 137, 66),
        "edge": (68, 103, 44),
        "top": (157, 218, 66),
        "highlight": (216, 243, 125),
    },
    "CSS": {
        "base": (157, 81, 51),
        "edge": (105, 51, 35),
        "top": (222, 145, 68),
        "highlight": (255, 204, 107),
    },
}

def plat(x, y, w, palette=None):
    if x + w < 0 or x > W: return
    palette = palette or DEFAULT_PLATFORM_PALETTE
    d = min(150, w * .4)
    pygame.draw.polygon(scr, palette["base"], [(x, y + 12), (x + w, y + 12), (x + w * .62, y + d), (x + w * .48, y + d * .7), (x + w * .32, y + d * .92)])
    pygame.draw.rect(scr, palette["edge"], (x, y + 12, w, 10)); pygame.draw.rect(scr, palette["top"], (x, y, w, 14))
def tree(x, y):
    pygame.draw.rect(scr, (107, 74, 43), (x - 4, y - 30, 8, 30))
    pygame.draw.polygon(scr, (46, 158, 87), [(x - 28, y - 24), (x, y - 76), (x + 28, y - 24)])
    pygame.draw.polygon(scr, (55, 178, 102), [(x - 22, y - 48), (x, y - 96), (x + 22, y - 48)])
def forest_tree(x, y):
    pygame.draw.rect(scr, (38, 51, 61), (x - 7, y - 70, 14, 70))
    pygame.draw.polygon(scr, (27, 107, 104), [(x - 42, y - 42), (x, y - 132), (x + 42, y - 42)])
    pygame.draw.polygon(scr, (44, 156, 133), [(x - 31, y - 76), (x, y - 155), (x + 31, y - 76)])
    pygame.draw.circle(scr, (112, 245, 199), (x, y - 100), 4)

def story_platform_positions(stage):
    positions = []
    active = set()
    for index, (x, y, width, height) in enumerate(stage["platforms"]):
        if index in stage["moving"]:
            phase = G.obby_stage_elapsed * 1.8 * stage.get("speed", 1.0) + index
            x += math.sin(phase) * 18 * stage.get("amp", 1.0)
            y += math.sin(phase * .7) * 10 * stage.get("amp", 1.0)
        if index in stage["disappearing"]:
            cycle = (G.obby_stage_elapsed + index * .7) % stage.get("cycle", 4.4)
            if cycle > stage.get("solid", 3.1):
                positions.append((x, y, width, height))
                continue
        active.add(index)
        positions.append((x, y, width, height))
    return positions, active

def story_hazard_positions(stage):
    hazards = []
    for index, (x, y, width, height) in enumerate(stage["hazards"]):
        if stage["name"] == "Debugging":
            x += math.sin(G.obby_stage_elapsed * 2 * stage.get("speed", 1.0) + index) * 22 * stage.get("amp", 1.0)
        hazards.append((x, y, width, height))
    return hazards

def draw_story_theme(language):
    color = tuple(story_language_data(language)["color"])
    theme = story_language_data(language).get("theme", language)
    if language == "Python" and JUNGLE_BG:
        scr.blit(JUNGLE_BG, (0, 0))
    elif language == "Python":
        for x in range(-80, W + 100, 145):
            forest_tree(x + int(G.obby_camx * .12) % 145, H - 15)
        for x in range(80, W + 100, 220):
            pygame.draw.rect(scr, (50, 86, 74), (x, 280, 20, 200))
            pygame.draw.rect(scr, color, (x + 6, 300, 6, 165), 2)
    elif language in PARKOUR_BACKGROUNDS:
        scr.blit(PARKOUR_BACKGROUNDS[language], (0, 0))
    else:
        for index in range(12):
            x = 56 + index * 82
            pygame.draw.rect(scr, (46 + index * 3, 35, 83 + index * 5),
                             (x, 192 + (index % 3) * 30, 54, 35), 0, 7)
            pygame.draw.rect(scr, color, (x, 192 + (index % 3) * 30, 54, 35), 2, 7)
        for index, swatch in enumerate(((255, 104, 119), (255, 204, 76),
                                         (85, 219, 174), (98, 182, 255))):
            pygame.draw.circle(scr, swatch, (140 + index * 70, 135), 19)
    text(theme.upper(), 26, 48, color, FS)

def draw_story_field_note(rect, message, color):
    old_clip = scr.get_clip()
    scr.set_clip(rect)
    text("BYTE'S FIELD NOTE", rect.x + 12, rect.y + 7, color, FS)
    lines = wrap(message, FS, rect.w - 24)
    line_step = FS.get_linesize() + 2
    max_lines = max(1, (rect.h - 34) // line_step)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last_line = lines[-1].rstrip()
        while last_line and FS.size(last_line + "...")[0] > rect.w - 24:
            last_line = (last_line.rsplit(" ", 1)[0]
                         if " " in last_line else last_line[:-1])
        lines[-1] = last_line.rstrip() + "..." if last_line else "..."
    for index, line in enumerate(lines):
        text(line, rect.x + 12, rect.y + 28 + index * line_step,
             WHITE, FS)
    scr.set_clip(old_clip)

def draw_portal_obby():
    i = G.obby_idx
    layout = G.story_stage if G.obby_mode == "story" else PORTAL_OBBIES[i]
    language = LANGUAGE_PATHS[i] if G.obby_mode == "language" else None
    story_language = story_language_data(G.story_language) if G.obby_mode == "story" else None
    image_background = (
        (story_language is not None and G.story_language in PARKOUR_BACKGROUNDS)
        or (language is not None and language["name"] in PARKOUR_BACKGROUNDS)
    )
    color = (tuple(story_language["color"]) if story_language else
             language["color"] if language else layout["color"])
    platform_theme = (G.story_language if story_language else
                      language["name"] if language else None)
    platform_palette = PARKOUR_PLATFORM_PALETTES.get(
        platform_theme, DEFAULT_PLATFORM_PALETTE)
    scr.blit(MAP_SKIES[min(i // 4, len(MAP_SKIES) - 1)], (0, 0))
    if story_language:
        draw_story_theme(G.story_language)
    elif language and language["name"] in PARKOUR_BACKGROUNDS:
        scr.blit(PARKOUR_BACKGROUNDS[language["name"]], (0, 0))
    if not (image_background or
            (story_language and G.story_language == "Python" and JUNGLE_BG)):
        for sx, sy, size in STARS:
            scr.fill(WHITE, (sx, sy, size, size))
    if image_background:
        scr.blit(PARKOUR_HUD_SHADE, (0, 0))
    story_active = set()
    platforms = layout["platforms"]
    if story_language:
        platforms, story_active = story_platform_positions(layout)
    for platform_index, (px, py, pw, ph) in enumerate(platforms):
        if story_language and platform_index not in story_active:
            continue
        screen_x = round(px - G.obby_camx)
        py = round(py)
        if -pw < screen_x < W:
            plat(screen_x, py, pw, platform_palette)
            pygame.draw.rect(scr, platform_palette["highlight"],
                             (screen_x, py, pw, 4), 0, 2)
            if story_language and layout["name"] == "Div":
                pygame.draw.rect(scr, (26, 38, 47),
                                 (screen_x + 10, py - 22, pw - 20, 21), 0, 4)
                pygame.draw.rect(scr, color,
                                 (screen_x + 10, py - 22, pw - 20, 21), 2, 4)
            elif story_language and layout["name"] == "Table":
                for grid_x in range(int(screen_x + 20), int(screen_x + pw), 24):
                    pygame.draw.line(scr, color, (grid_x, py + 2), (grid_x, py + 12), 1)
            elif story_language and layout["name"] in ("String", "Strings"):
                text("\"...\"", screen_x + pw // 2 - 20, py - 21, WHITE, FS)
            elif story_language and layout["name"] == "If else" and platform_index in (4, 5):
                text("IF" if platform_index == 4 else "ELSE",
                     screen_x + pw // 2 - 16, py - 22, GOLD, FS)
            elif story_language and layout["name"] == "Arrays" and platform_index in (4, 5):
                text("[0]" if platform_index == 4 else "[1]",
                     screen_x + pw // 2 - 12, py - 22, GOLD, FS)
            elif story_language and layout["name"] == "Booleans":
                state_color = GREEN if platform_index % 2 == 0 else RED
                pygame.draw.line(scr, state_color, (screen_x + 12, py + 7),
                                 (screen_x + pw - 12, py + 7), 3)
            elif story_language and layout["name"] == "Image":
                pygame.draw.rect(scr, GOLD, (screen_x + 15, py - 24, pw - 30, 21), 2, 3)
            elif story_language and layout["name"] == "Links":
                pygame.draw.circle(scr, WHITE, (int(screen_x + 10), py + 7), 3)
                pygame.draw.circle(scr, WHITE, (int(screen_x + pw - 10), py + 7), 3)
    if language or story_language:
        hazards = story_hazard_positions(layout) if story_language else G.obby_obstacles
        for obstacle_x, obstacle_y, obstacle_w, obstacle_h in hazards:
            screen_x = round(obstacle_x - G.obby_camx)
            if -obstacle_w < screen_x < W:
                if story_language and layout["name"] == "Debugging":
                    pygame.draw.circle(scr, RED, (screen_x + obstacle_w // 2, obstacle_y - 10), 12)
                    pygame.draw.circle(scr, WHITE, (screen_x + obstacle_w // 2 - 4, obstacle_y - 12), 2)
                    pygame.draw.circle(scr, WHITE, (screen_x + obstacle_w // 2 + 4, obstacle_y - 12), 2)
                else:
                    pygame.draw.polygon(scr, RED, [
                        (screen_x, obstacle_y),
                        (screen_x + obstacle_w // 2, obstacle_y - obstacle_h),
                        (screen_x + obstacle_w, obstacle_y),
                    ])
                    pygame.draw.line(scr, GOLD, (screen_x, obstacle_y),
                                     (screen_x + obstacle_w, obstacle_y), 3)
    if layout.get("crystals"):
        collected_crystals = (G.story_stage_collected if story_language
                              else G.obby_crystal_collected)
        for crystal_index, (crystal_x, crystal_y) in enumerate(layout["crystals"]):
            if crystal_index in collected_crystals:
                continue
            cx, cy = round(crystal_x - G.obby_camx), round(crystal_y)
            pygame.draw.circle(scr, (18, 43, 53), (cx, cy), 31)
            pygame.draw.circle(scr, CYAN, (cx, cy), 32, 3)
            _crystal(cx, cy, G.t + crystal_index)
            label_y = cy + 36 if cy < 55 else cy - 44
            text("+%d XP" % layout.get("crystal_xp", 5), cx - 20, label_y, GOLD, FS)
    goal_x, goal_y = layout["goal"]
    screen_goal = (round(goal_x - G.obby_camx), goal_y)
    portal_open = not story_language or len(G.story_stage_collected) == 3
    portal_color = (255, 223, 110) if portal_open else (122, 74, 116)
    pygame.draw.ellipse(scr, portal_color, (screen_goal[0] - 22, screen_goal[1] - 30, 44, 60), 4)
    pygame.draw.ellipse(scr, color, (screen_goal[0] - 15, screen_goal[1] - 24, 30, 48), 3)
    pygame.draw.circle(scr, WHITE, screen_goal, 4)
    if story_language:
        stage_difficulty = layout["difficulty"]
        text("CRYSTALS %d / 3" % len(G.story_stage_collected),
             W - 330, 24, WHITE, FS)
        text("CHECKPOINT %d / %d" %
             (G.obby_cp_index, len(layout["checkpoints"])),
             W - 330, 48, WHITE, FS)
        tag = FS.render(stage_difficulty["name"], True, (20, 28, 34))
        tag_rect = pygame.Rect(W - 170, 46, tag.get_width() + 18, 22)
        pygame.draw.rect(scr, stage_difficulty["color"], tag_rect, 0, 11)
        scr.blit(tag, (tag_rect.x + 9, tag_rect.y + 3))
        course_title = "%s  /  PORTAL %d" % (G.story_language.upper(), G.story_topic_index + 1)
    else:
        text("CRYSTALS %d / 3" % len(G.obby_crystal_collected),
             W - 220, 48, WHITE, FS)
        course_title = "%s PARKOUR" % language["name"].upper() if language else layout["name"]
    text(course_title, 24, 18, GOLD, FB)
    island = max((index + 1 for index, (x, _, width, _) in enumerate(layout["platforms"])
                  if G.obby_x >= x + width / 2), default=1)
    text("ISLAND %d / %d" % (island, len(layout["platforms"])), W - 170, 24, WHITE, FS)
    dashboard_button(obby_settings_rect(), "SETTINGS")
    hero(round(G.obby_x - G.obby_camx), round(G.obby_y), G.t,
         abs(G.obby_vx) > 20, not G.obby_gnd, abs(G.obby_vx) > 300)
    instruction = ("Collect all 3 crystals for XP; reach portal  |  A/D move  SPACE/W jump" if story_language else
                   "Collect crystals for XP; avoid red spikes  |  A/D move  SPACE/W jump" if language else
                   "Collect crystals for XP  |  A/D move  SPACE/W jump  SHIFT: sprint  ESC: leave")
    text(instruction + ("   |   ESC: leave" if language or story_language else ""), 24, H - 34, WHITE, FS)
    if G.touch_enabled:
        controls = touch_button_rects()
        back_label = "BACK" if G.obby_mode == "story" else "EXIT"
        for name, label in (("left", "<"), ("right", ">"),
                            ("interact", back_label), ("jump", "JUMP")):
            rect = controls[name]
            pygame.draw.rect(scr, (26, 38, 47), rect, 0, 12)
            pygame.draw.rect(scr, CYAN if name == "jump" else (189, 202, 201), rect, 2, 12)
            rendered = FS.render(label, True, WHITE)
            scr.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                                rect.centery - rendered.get_height() // 2))
    if G.tt > 0:
        rendered = F.render(G.ts, True, (42, 26, 0))
        pygame.draw.rect(scr, GOLD, (W // 2 - rendered.get_width() // 2 - 12, 90,
                                     rendered.get_width() + 24, 34), 0, 16)
        scr.blit(rendered, (W // 2 - rendered.get_width() // 2, 96))
    if G.M.get("k") == "settings":
        draw_settings()

def portal(i, x, oy, t):
    ok, done = unlocked(i), i in G.S["done"]; col = (255, 207, 90) if done else CH[i]["c"] if ok else (80, 99, 111)
    pygame.draw.rect(scr, (54, 69, 80), (x - 36, 414 + oy, 72, 8))
    inner = tuple(int(c * (.35 + .15 * math.sin(t * 3 + i))) if ok else 60 for c in col)
    pygame.draw.ellipse(scr, inner, (x - 30, 306 + oy, 60, 104)); pygame.draw.ellipse(scr, col, (x - 34, 302 + oy, 68, 112), 6)
    if ok:
        for k in range(3): pygame.draw.ellipse(scr, (244, 240, 226), (x - 8 - k * 7, 344 + oy - k * 12 + int(2 * math.sin(t * 2 + k)), 16 + k * 14, 28 + k * 24), 1)
    lab = str(i + 1) if i < 5 or i >= 10 else "BOSS" if i == 5 else "*%d" % (i - 5); s = FS.render(lab, True, WHITE); scr.blit(s, (x - s.get_width() // 2, 276 + oy))
def byte(x, y, t):
    bob = math.sin(t * 2.4) * 6
    x, y = round(x + math.sin(t * 1.3) * 2), round(y + bob)
    pulse = math.sin(t * 3)
    width, height = 20 + round(pulse), 20 - round(pulse)
    pygame.draw.ellipse(scr, (200, 215, 245),
                        (x - width, y - height, width * 2, height * 2))
    pygame.draw.ellipse(scr, (28, 39, 48), (x - 10, y - 10, 26, 18))
    blink = .2 if t % 4.2 > 4.08 else 1.0
    eye_y = y - 1
    pygame.draw.ellipse(scr, CYAN, (x + 4, eye_y - 5, 7, max(2, round(10 * blink))))
    gaze = round(math.sin(t * 1.1) * 2)
    pygame.draw.circle(scr, WHITE, (x + 8 + gaze, eye_y - 1), 2)
    antenna_sway = math.sin(t * 4) * 3
    pygame.draw.line(scr, (159, 180, 232), (x, y - height),
                     (round(x - 3 + antenna_sway), y - height - 10), 2)
    pygame.draw.circle(scr, GOLD, (round(x - 3 + antenna_sway), y - height - 11), 3)
def limb(x, y, f, sx, sy, a, b, l1, l2, w, col, hand):
    mx, my = sx + math.sin(a) * l1, sy + math.cos(a) * l1; ex, ey = mx + math.sin(a + b) * l2, my + math.cos(a + b) * l2
    pts = [(x + f * sx, y + sy), (x + f * mx, y + my), (x + f * ex, y + ey)]
    pygame.draw.lines(scr, col, False, pts, w)
    for p in pts: pygame.draw.circle(scr, col, p, w // 2)
    if hand: pygame.draw.circle(scr, (224, 172, 132), pts[2], 3)
    else: pygame.draw.ellipse(scr, (26, 20, 16), (pts[2][0] + (f * 4 - 8), pts[2][1] - 5, 16, 8))
_SPRITES = {}
_SPRITE_SCALED = {}
_CHAR_IMG = {}
def sprite_atlas():
    if "atlas" not in _SPRITES:
        try:
            import base64, io
            color = pygame.image.load(io.BytesIO(base64.b64decode(SPRITE_RGB_DATA)), "sprites.png").convert()
            mask = pygame.image.load(io.BytesIO(base64.b64decode(SPRITE_ALPHA_DATA)), "alpha.png").convert()
            size = color.get_size()
            rgb = pygame.image.tostring(color, "RGB"); gray = pygame.image.tostring(mask, "RGB")
            buf = bytearray(size[0] * size[1] * 4)
            buf[0::4], buf[1::4], buf[2::4], buf[3::4] = rgb[0::3], rgb[1::3], rgb[2::3], gray[0::3]
            _SPRITES["atlas"] = pygame.image.frombuffer(bytes(buf), size, "RGBA").convert_alpha()
        except Exception as err:
            print("Character sprites could not be loaded:", err)
            _SPRITES["atlas"] = None
    return _SPRITES["atlas"]
def sprite_image(character):
    atlas = sprite_atlas()
    if atlas is None: return None
    rx, ry, rw, rh = SPRITE_RECTS[character["sprite"]]
    return atlas.subsurface((rx, ry, rw, rh))
def fit_image(img, max_w, max_h, flip=False, key=None):
    k = (key, max_w, max_h, flip)
    if key is not None and k in _SPRITE_SCALED: return _SPRITE_SCALED[k]
    f = min(max_w / img.get_width(), max_h / img.get_height())
    out = pygame.transform.smoothscale(img, (max(1, round(img.get_width() * f)), max(1, round(img.get_height() * f))))
    if flip: out = pygame.transform.flip(out, True, False)
    if key is not None: _SPRITE_SCALED[k] = out
    return out
def character_image(character):
    cid = character["id"]
    if cid in _CHAR_IMG: return _CHAR_IMG[cid]
    img = sprite_image(character) if "sprite" in character else None
    if img is None:
        global scr
        old_scr, old_face = scr, G.face
        tmp = pygame.Surface((180, 190), pygame.SRCALPHA)
        scr = tmp; G.face = 1
        try: hero(90, 160, 0, False, False, False, cid, True)
        finally: scr = old_scr; G.face = old_face
        img = tmp.subsurface(tmp.get_bounding_rect()).copy()
    _CHAR_IMG[cid] = img
    return img
def hero(x, y, t, mv, air, spr, character_id=None, procedural=False):
    character_id = character_id or G.S.get("character", "guardian")
    character = next((c for c in CHARACTERS if c["id"] == character_id), CHARACTERS[0])
    phase = G.ph
    vertical_velocity = (getattr(G, "obby_vy", 0) if G.state == "obby"
                         else G.vy)
    if "sprite" in character and not procedural:
        img = sprite_image(character)
        if img is not None:
            img = fit_image(img, 84, 100, G.face < 0, character_id)
            if air:
                bob = 0
                tilt = -G.face * (7 if vertical_velocity < 0 else -4)
                stretch = .045 if vertical_velocity < 0 else -.025
            elif mv:
                stride = math.sin(phase)
                bob = abs(stride) * (5 if spr else 3.5)
                tilt = -G.face * (6 if spr else 3) + stride * 1.5
                stretch = math.cos(phase * 2) * .025
            else:
                bob = math.sin(t * 2.4) * 1.8
                tilt = math.sin(t * 1.6) * 1.2
                stretch = math.sin(t * 2.4) * .012
            if abs(stretch) > .001:
                size = (max(1, round(img.get_width() * (1 - stretch * .55))),
                        max(1, round(img.get_height() * (1 + stretch))))
                img = pygame.transform.smoothscale(img, size)
            if abs(tilt) > .1:
                img = pygame.transform.rotozoom(img, tilt, 1)
            scr.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() - bob)))
            return
    torso, front_arm, front_leg, back_arm, back_leg, cape, hair, skin, accent = character["colors"]
    f = G.face
    br = (abs(math.sin(phase)) * 2 if mv and not air
          else math.sin(t * 2.4) * 1.8)
    sp = 1 if spr else .5 if mv else .1
    def L(front, col):
        p = phase + (0 if front else math.pi); a, b = 0, -.05
        if air: a, b = (.7, -.9) if front else (-.5, -.5)
        elif mv: a, b = math.sin(p) * .8, -(.12 + .9 * max(0, math.cos(p)))
        limb(x, y, f, 0, -47, a, b, 23, 24, 9, col, False)
    def A(front, col):
        p = phase + (math.pi if front else 0); a, b = (math.sin(p) * .7 if mv else 0), .35 + (.5 if mv else 0)
        if air: a, b = (-.9, .5) if front else (.7, .5)
        limb(x, y, f, 0, -75 + br, a, b, 17, 16, 6, col, True)
    L(False, back_leg); A(False, back_arm)
    pygame.draw.polygon(scr, torso, [(x - 9, y - 78 + br), (x + 10, y - 78 + br), (x + 8, y - 47), (x - 8, y - 47)])
    pygame.draw.rect(scr, (42, 29, 18), (x - 8, y - 51, 16, 4)); pygame.draw.rect(scr, GOLD, (x + f * 1 - 2, y - 51, 4, 4))
    pygame.draw.polygon(scr, accent, [(x + f * 3, y - 70), (x + f * 6, y - 65), (x + f * 3, y - 60), (x, y - 65)])
    pygame.draw.rect(scr, skin, (x - 3, y - 85 + br, 6, 8))
    pygame.draw.lines(scr, cape, False, [(x - f * 3, y - 80 + br), (x - f * (16 + sp * 8), y - 78 + math.sin(t * 8) * 3 * sp), (x - f * (26 + sp * 14), y - 72 + math.sin(t * 8 + 1) * 5 * sp)], 5)
    if character_id == "bytebot":
        pygame.draw.rect(scr, skin, (x + f * 1 - 8, y - 101 + br, 16, 16), 0, 3)
        pygame.draw.rect(scr, hair, (x + f * 4 - 1, y - 94 + br, 5, 5), 0, 2)
        pygame.draw.line(scr, accent, (x + f * 4, y - 94 + br), (x + f * 4, y - 90 + br), 2)
        pygame.draw.line(scr, accent, (x, y - 100 + br), (x, y - 106 + br), 2)
        pygame.draw.circle(scr, GOLD, (x, y - 107 + br), 2)
    else:
        pygame.draw.ellipse(scr, skin, (x + f * 1 - 7, y - 101 + br, 15, 18))
        pygame.draw.polygon(scr, hair, [(x - f * 8, y - 90 + br), (x - f * 8, y - 102 + br), (x + f * 2, y - 104 + br), (x + f * 9, y - 98 + br), (x + f * 8, y - 94 + br), (x - f * 1, y - 97 + br)])
        pygame.draw.circle(scr, (244, 240, 226), (x + f * 4, y - 92 + br), 2); pygame.draw.circle(scr, (26, 16, 8), (x + f * 5, y - 92 + br), 1)
        pygame.draw.line(scr, hair, (x + f * 2, y - 95 + br), (x + f * 7, y - 96 + br))
        if character_id == "mage":
            pygame.draw.polygon(scr, cape, [(x - 12, y - 98 + br), (x, y - 119 + br), (x + 12, y - 98 + br)])
            pygame.draw.circle(scr, accent, (x, y - 118 + br), 3)
    A(True, front_arm); L(True, front_leg)
def draw_world():
    t = G.t
    region = 0 if G.px < 4000 else 1 if G.px < 6000 else 2
    scr.blit(MAP_SKIES[region], (0, 0))
    for sx, sy, s in STARS: scr.fill(WHITE, (sx, sy, s, s))
    for cx, cy, w, l in CLOUDS: pygame.draw.ellipse(scr, (177, 194, 196), ((cx - G.camx * l) % (W + 400) - 200, cy - G.camy * .2, w, w * .18))
    ox, oy = -G.camx, -G.camy
    for x, y, w in P: plat(x + ox, y + oy, w)
    for x in (90, 480, 1600, 2440, 3120, 3960): tree(x + ox, 420 + oy)
    for x in (4110, 4440, 4780, 5120, 5480, 5790):
        forest_tree(x + ox, 420 + oy)
    for i, x in enumerate((6100, 6450, 6800, 7150, 7500, 7840)):
        h = 110 + (i % 3) * 35
        pygame.draw.rect(scr, (47, 61, 72), (x + ox - 42, 420 + oy - h, 84, h))
        pygame.draw.rect(scr, (138, 163, 171), (x + ox - 42, 420 + oy - h, 84, 7))
        for wy in range(420 - h + 20, 408, 28):
            for wx in (x - 24, x, x + 24):
                pygame.draw.rect(scr, (119, 232, 255), (wx + ox, wy + oy, 8, 12))
    text(MAP_NAMES[region], 360, 16, GOLD, FS)
    for r in ((2370, 310, 100, 110), (2355, 255, 34, 165), (2450, 245, 30, 175)): pygame.draw.rect(scr, (24, 35, 43), (r[0] + ox, r[1] + oy, r[2], r[3]))
    for i in range(len(CH)):
        x = PX(i) + ox
        if -80 < x < W + 80: portal(i, x, oy, t)
    for fx, checkpoint, required in ((1590, 1600, None), (3110, 3200, None), (4000, 0, 9), (6000, 0, 10)):
        unlocked_gate = required in G.S["done"] if required is not None else G.cp[0] > checkpoint
        c = GREEN if unlocked_gate else (64, 81, 93)
        pygame.draw.rect(scr, c, (fx + ox, 350 + oy, 4, 70)); pygame.draw.polygon(scr, c, [(fx + 4 + ox, 350 + oy), (fx + 30 + ox, 360 + oy), (fx + 4 + ox, 370 + oy)])
    for i, (x, y) in enumerate(ORBS):
        if i not in G.S["orbs"]:
            yy = y + math.sin(t * 3 + i) * 4 + oy; pygame.draw.circle(scr, (140, 100, 20), (x + ox, yy), 14); pygame.draw.circle(scr, (255, 210, 74), (x + ox, yy), 9)
    byte(BX + ox, 330 + oy, t)
    if G.gnd: pygame.draw.ellipse(scr, (33, 46, 56), (G.px + ox - 20, G.py + oy - 3, 40, 10))
    hero(G.px + ox, G.py + oy, t, abs(G.vx) > 20, not G.gnd, abs(G.vx) > 300)
def hud():
    xp_panel = pygame.Rect(14, 9, 244, 56)
    pygame.draw.rect(scr, (22, 32, 40), xp_panel, 0, 8)
    pygame.draw.rect(scr, GOLD, xp_panel, 2, 8)
    text("LV.%d" % lvl(), 22, 14, (206, 232, 214), FS)
    text("XP %d" % G.S["xp"], 78, 11, GOLD, fnt(17, True))
    pygame.draw.rect(scr, (21, 31, 39), (20, 38, 230, 10)); pygame.draw.rect(scr, CYAN, (20, 38, int(230 * (G.S["xp"] % XPL) / XPL), 10))
    text("UNLOCK CHARACTERS WITH XP", 22, 51, CYAN, FTAG)
    n = len(G.S["done"])
    if G.S["won"]:
        m = 6
        while m in G.S["done"]: m += 1
        q = "Beyond the fortress: portal %d, %s." % (m + 1, CH[m]["n"]) if m < len(CH) else "All quests complete. Master Coder!"
    elif n == 0: q = "Cross the stones east, enter portal 1: The Portal of HTML."
    elif n < 5: q = "Enter portal %d: %s." % (n + 1, CH[n]["n"])
    else: q = "Enter the Fortress portal and defeat the Virus King!"
    para("Quest: " + q, 14, 70, 300, WHITE, FS)
    pygame.draw.rect(scr, (21, 31, 39), (W - 190, H - 30, 180, 20)); pygame.draw.rect(scr, (74, 138, 96), (W - 185, H - 21, 170, 3))
    for i in range(len(CH)): pygame.draw.rect(scr, GOLD if unlocked(i) else (54, 69, 80), (W - 185 + PX(i) / WORLD_WIDTH * 170 - 2, H - 26, 4, 10))
    pygame.draw.circle(scr, WHITE, (W - 185 + G.px / WORLD_WIDTH * 170, H - 20), 4)
    if G.near and not G.M:
        action = "Tap USE / press E: " if G.touch_enabled else "Press E: "
        target = "learn with Byte" if G.near[0] == "b" else "enter " + CH[G.near[1]]["n"] + ("" if unlocked(G.near[1]) else " (sealed)")
        s = action + target
        r = F.render(s, True, GOLD); pygame.draw.rect(scr, (22, 32, 40), (W // 2 - r.get_width() // 2 - 10, H - 60, r.get_width() + 20, 32), 0, 8); scr.blit(r, (W // 2 - r.get_width() // 2, H - 56))
    if G.tt > 0: r = F.render(G.ts, True, (42, 26, 0)); pygame.draw.rect(scr, GOLD, (W // 2 - r.get_width() // 2 - 12, 90, r.get_width() + 24, 34), 0, 16); scr.blit(r, (W // 2 - r.get_width() // 2, 96))
    if G.touch_enabled and G.state == "play" and not G.M:
        draw_touch_controls()

def touch_button_rects():
    return {
        "left": pygame.Rect(20, H - 102, 78, 72),
        "right": pygame.Rect(108, H - 102, 78, 72),
        "jump": pygame.Rect(W - 98, H - 102, 78, 72),
        "interact": pygame.Rect(W - 190, H - 102, 82, 72),
        "shop": pygame.Rect(W - 184, 14, 78, 54),
        "pause": pygame.Rect(W - 92, 14, 78, 54),
    }

def draw_touch_controls():
    labels = {"left": "<", "right": ">", "jump": "JUMP", "interact": "USE", "shop": "STORE", "pause": "||"}
    for name, rect in touch_button_rects().items():
        pygame.draw.rect(scr, (26, 38, 47, 210), rect, 0, 12)
        pygame.draw.rect(scr, CYAN if name in ("jump", "interact", "pause") else (189, 202, 201), rect, 2, 12)
        label = FS.render(labels[name], True, WHITE)
        scr.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

def draw_wrong_answer(r, modal):
    text("Correct answer", r.x + 24, r.y + 68, GOLD, fnt(21, True))
    answer_y = r.y + 101
    answer_y = para(modal["answer"], r.x + 28, answer_y, r.w - 56, CYAN, FS) + 10
    text("Explanation", r.x + 24, answer_y, GOLD, fnt(19, True))
    para(modal["fb"][1], r.x + 28, answer_y + 28, r.w - 56, WHITE, FS)
    remaining = max(0, modal.get("fb_until", G.t) - G.t)
    text("ENTER / tap NEXT to continue  |  auto-advancing in %d seconds  |  ESC leave" %
         math.ceil(remaining), r.x + 22, r.bottom - 32, (206, 232, 214), FS)
    if G.touch_enabled:
        draw_modal_touch_buttons(modal["k"], modal)

def language_card_rect(i):
    return pygame.Rect(132 + i * 145, 190, 132, 128)

def language_option_rect(i):
    return pygame.Rect(136, 196 + i * 54, 728, 46)

def language_result_action_rect():
    return pygame.Rect(365, H - 132, 270, 50)

def language_quiz_continue_rect():
    return pygame.Rect(390, H - 120, 220, 42)

def story_language_card_rect(i):
    return pygame.Rect(132 + i * 145, 190, 132, 128)

def story_lesson_card_rect(i):
    return pygame.Rect(132, 120 + i * 72, W - 264, 60)

def story_lesson_action_rects(read_only=False):
    if read_only:
        return {
            "back": pygame.Rect(130, H - 116, 190, 48),
            "replay": pygame.Rect(650, H - 116, 220, 48),
        }
    return {
        "back": pygame.Rect(130, H - 116, 190, 48),
        "lessons": pygame.Rect(350, H - 116, 270, 48),
        "parkour": pygame.Rect(650, H - 116, 220, 48),
    }

def story_difficulty_card_rect(i):
    return pygame.Rect(130 + (i % 2) * 370, 144 + (i // 2) * 94, 350, 86)

def story_difficulty_action_rects():
    return {
        "back": pygame.Rect(130, H - 116, 190, 48),
        "start": pygame.Rect(650, H - 116, 220, 48),
    }

def story_question_rect(i):
    return pygame.Rect(136, 190 + i * 54, W - 272, 46)

def story_quiz_input_rect():
    return pygame.Rect(136, 300, W - 272, 48)

def story_quiz_submit_rect():
    return pygame.Rect(650, 432, 220, 46)

def story_quiz_next_rect():
    return pygame.Rect(650, H - 104, 220, 46)

def story_coding_input_rect():
    return pygame.Rect(130, 190, W - 260, 160)

def story_coding_run_rect():
    return pygame.Rect(650, H - 104, 220, 46)

def story_coding_clear_rect():
    return pygame.Rect(520, H - 104, 110, 46)

def story_battle_input_rect():
    layout = story_battle_quiz_layout(G.M)
    return layout["input"]

def story_battle_submit_rect():
    layout = story_battle_quiz_layout(G.M)
    input_box = layout["input"]
    return pygame.Rect(input_box.right - 220, input_box.y,
                       220, input_box.h)

def story_battle_retry_rect():
    return pygame.Rect(390, H - 104, 220, 46)

def story_battle_scene_rect():
    return pygame.Rect(132, 94, W - 264, 148)

def story_results_button_rects():
    return {
        "replay": pygame.Rect(132, H - 104, 230, 48),
        "languages": pygame.Rect(385, H - 104, 230, 48),
        "menu": pygame.Rect(638, H - 104, 230, 48),
    }

def draw_learning_background():
    scr.blit(SKY, (0, 0)); draw_particles()
    for sx, sy, size in STARS:
        scr.fill((244, 240, 226), (sx, sy, size, size))
    text("GAME BUDDY  |  CODE QUEST", 24, 18, GOLD, FS)

def draw_language_select(modal):
    r = panel("Choose Your Coding Path")
    text("Choose one language. Byte will teach you, then you can test what you learned.",
         r.x + 22, r.y + 56, WHITE, FS)
    for i, language in enumerate(LANGUAGE_PATHS):
        card = language_card_rect(i)
        selected = i == modal["selected"]
        pygame.draw.rect(scr, (45, 60, 71) if selected else (36, 48, 62), card, 0, 10)
        pygame.draw.rect(scr, GOLD if selected else language["color"], card, 3 if selected else 2, 10)
        text("%d" % (i + 1), card.centerx - 5, card.y + 20, language["color"], FB)
        label = FS.render(language["name"], True, WHITE)
        scr.blit(label, (card.centerx - label.get_width() // 2, card.y + 75))
        text("SELECT", card.centerx - 26, card.y + 99, (206, 232, 214), FS)
    selected_language = LANGUAGE_PATHS[modal["selected"]]
    para("Byte's briefing: " + selected_language["lesson"], r.x + 24, r.y + 350,
         r.w - 48, CYAN, FS)
    text("LEFT / RIGHT or 1-5 to choose  |  ENTER open lesson  |  ESC close",
         r.x + 22, r.bottom - 34, (206, 232, 214), FS)

def draw_language_lesson(modal):
    language = LANGUAGE_PATHS[modal["i"]]
    r = panel("Byte's %s Lesson" % language["name"])
    text("RESTORE THE KINGDOM", r.x + 24, r.y + 62, GOLD, fnt(19, True))
    para(language["lesson"], r.x + 24, r.y + 94, r.w - 48, WHITE, F)
    text("EXAMPLE", r.x + 24, r.y + 178, GOLD, fnt(19, True))
    code_lines = language["example"].splitlines()
    box = pygame.Rect(r.x + 22, r.y + 208, r.w - 44, max(90, len(code_lines) * 22 + 20))
    pygame.draw.rect(scr, (21, 31, 39), box, 0, 7)
    y = box.y + 10
    for line in code_lines:
        text(line, box.x + 14, y, CYAN, FS)
        y += 22
    text("Review the example, then answer a few questions to help restore the kingdom.",
         r.x + 24, r.y + 382, (238, 242, 226), FS)
    button = language_result_action_rect()
    pygame.draw.rect(scr, (58, 76, 90), button, 0, 10)
    pygame.draw.rect(scr, language["color"], button, 2, 10)
    rendered = FS.render("START QUIZ", True, WHITE)
    scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                        button.centery - rendered.get_height() // 2))
    text("ENTER / SPACE / tap button  |  ESC return to language choice",
         r.x + 22, r.bottom - 30, (206, 232, 214), FS)

def draw_language_quiz(modal):
    language = LANGUAGE_PATHS[modal["i"]]
    r = panel("%s Quiz" % language["name"])
    question = language["questions"][modal["q"]]
    text("Question %d/%d  |  Score: %d" %
         (modal["q"] + 1, len(language["questions"]), modal["correct"]),
         r.x + 24, r.y + 62, GOLD, FS)
    para(question[0], r.x + 24, r.y + 90, r.w - 48, WHITE, F)
    feedback = modal["feedback"]
    for i, option in enumerate(question[1]):
        rect = language_option_rect(i)
        fill = (36, 48, 62)
        edge = language["color"]
        if feedback:
            if i == feedback["correct_choice"]:
                fill, edge = (25, 75, 58), GREEN
            elif i == feedback["choice"]:
                fill, edge = (88, 34, 52), RED
        pygame.draw.rect(scr, fill, rect, 0, 8)
        pygame.draw.rect(scr, edge, rect, 2, 8)
        para("%d) %s" % (i + 1, option), rect.x + 14, rect.y + 14,
             rect.w - 28, WHITE, FS)
    if feedback:
        status = "Correct!" if feedback["correct"] else "Not quite. The correct answer is: %s" % question[1][question[2]]
        feedback_y = para(status, r.x + 24, r.y + 366, r.w - 48,
                           GREEN if feedback["correct"] else RED, FS) + 4
        para(feedback["explanation"], r.x + 24, feedback_y, r.w - 48, WHITE, FS)
        button = language_quiz_continue_rect()
        pygame.draw.rect(scr, (58, 76, 90), button, 0, 9)
        pygame.draw.rect(scr, language["color"], button, 2, 9)
        rendered = FS.render("NEXT QUESTION", True, WHITE)
        scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                            button.centery - rendered.get_height() // 2))
        text("ENTER / SPACE / tap button", r.x + 22, r.bottom - 22,
             (206, 232, 214), FS)
    else:
        text("Press 1-4 or tap an answer  |  ESC leave quiz",
             r.x + 22, r.bottom - 28, (206, 232, 214), FS)

def draw_language_result(modal):
    language = LANGUAGE_PATHS[modal["i"]]
    r = panel("%s Quiz Results" % language["name"])
    text("Score: %d / %d" % (modal["score"], len(modal["answers"])),
         r.x + 24, r.y + 62, GOLD, FB)
    y = r.y + 112
    for i, answer in enumerate(modal["answers"]):
        label = "Correct" if answer["correct"] else "Review"
        color = GREEN if answer["correct"] else RED
        text("Question %d: %s" % (i + 1, label), r.x + 24, y, color, FS)
        y = para(answer["explanation"], r.x + 40, y + 22, r.w - 80, WHITE, FS) + 10
    button = language_result_action_rect()
    pygame.draw.rect(scr, (58, 76, 90), button, 0, 10)
    pygame.draw.rect(scr, language["color"], button, 2, 10)
    rendered = FS.render("CHOOSE ANOTHER PATH", True, WHITE)
    scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                        button.centery - rendered.get_height() // 2))
    text("ENTER / SPACE / tap button  |  ESC return to world",
         r.x + 22, r.bottom - 30, (206, 232, 214), FS)

def draw_lesson_menu(modal):
    r = panel("Byte's Lessons")
    text("Choose a topic to study. Lessons are always open; quizzes unlock as you progress.",
         r.x + 22, r.y + 52, WHITE, FS)
    for i in range(len(LESSONS)):
        card = lesson_card_rect(i)
        done = i in G.S["done"]
        ready = unlocked(i) and not done
        fill = (62, 116, 96) if i == modal["selected"] else (36, 48, 62)
        edge = GOLD if i == modal["selected"] else GREEN if done else CYAN if ready else (104, 206, 172)
        pygame.draw.rect(scr, fill, card, 0, 8)
        pygame.draw.rect(scr, edge, card, 2, 8)
        text("%02d. %s" % (i + 1, CH[i]["n"]), card.x + 10, card.y + 6, WHITE, FS)
        status = "COMPLETE" if done else "QUIZ READY" if ready else "QUIZ LOCKED"
        status_color = GREEN if done else CYAN if ready else (206, 232, 214)
        text(status, card.x + 10, card.y + 28, status_color, FS)
    text("UP / DOWN / LEFT / RIGHT to choose  |  ENTER open lesson  |  ESC close",
         r.x + 22, r.bottom - 34, (206, 232, 214), FS)

def lesson_action_rect():
    return pygame.Rect(365, H - 132, 270, 50)

def draw_lesson(modal):
    i = modal["i"]
    title, lesson, example = LESSONS[i]
    r = panel("Byte's Lesson: " + title)
    text("PORTAL %d  |  %s" % (i + 1, CH[i]["n"]), r.x + 24, r.y + 58, CYAN, FS)
    text("KEY IDEA", r.x + 24, r.y + 96, GOLD, fnt(19, True))
    y = para(lesson, r.x + 24, r.y + 126, r.w - 48, WHITE, F)
    text("EXAMPLE", r.x + 24, y + 22, GOLD, fnt(19, True))
    example_y = y + 52
    pygame.draw.rect(scr, (21, 31, 39), (r.x + 22, example_y - 8, r.w - 44, 58), 0, 7)
    para(example, r.x + 34, example_y, r.w - 68, CYAN, FS)
    done = i in G.S["done"]
    ready = unlocked(i) and not done
    if ready:
        button_label = "START PORTAL QUIZ"
        status = "You are ready to try this portal's quiz or coding challenge."
    elif done:
        button_label = "BACK TO LESSONS"
        status = "This quest is complete. You can review this lesson any time."
    else:
        button_label = "BACK TO LESSONS"
        status = "Study now; finish %s to unlock this portal's quiz." % CH[i - 1]["n"]
    text(status, r.x + 24, r.bottom - 124, (238, 242, 226), FS)
    button = lesson_action_rect()
    pygame.draw.rect(scr, (58, 76, 90), button, 0, 10)
    pygame.draw.rect(scr, CYAN if ready else (104, 206, 172), button, 2, 10)
    rendered = FS.render(button_label, True, WHITE)
    scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                        button.centery - rendered.get_height() // 2))
    text("ENTER / SPACE / tap button  |  ESC close", r.x + 22, r.bottom - 32,
         (206, 232, 214), FS)

def draw_modal():
    ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((18, 27, 34, 170)); scr.blit(ov, (0, 0)); M = G.M; k = M["k"]
    if k == "build":
        draw_build_animation(M)
        return
    if k == "language_select":
        draw_language_select(M)
        return
    if k == "language_lesson":
        draw_language_lesson(M)
        return
    if k == "language_quiz":
        draw_language_quiz(M)
        return
    if k == "language_result":
        draw_language_result(M)
        return
    if k == "lesson_menu":
        draw_lesson_menu(M)
        return
    if k == "lesson":
        draw_lesson(M)
        return
    if k == "story_intro":
        draw_story_intro()
        return
    if k == "story_ending":
        draw_story_ending()
        return
    if k == "story_language_select":
        draw_story_language_select(M)
        return
    if k == "story_lesson_list":
        draw_story_lesson_list(M)
        return
    if k == "story_lesson":
        draw_story_lesson(M)
        return
    if k == "story_difficulty":
        draw_story_difficulty(M)
        return
    if k == "story_quiz":
        draw_story_quiz(M)
        return
    if k == "story_coding":
        draw_story_coding(M)
        return
    if k == "story_battle_result":
        draw_story_battle_result(M)
        return
    if k == "story_results":
        draw_story_results(M)
        return
    if k == "msg":
        r = panel(M["t"]); para(M["b"], r.x + 22, r.y + 70, r.w - 44); text("ENTER / tap to continue", r.x + 22, r.bottom - 32, (206, 232, 214), FS); return
    c = CH[M["i"]]; r = panel(c["n"]); y = r.y + 66
    if k == "mc":
        if M["fb"] and not M["fb"][0]:
            draw_wrong_answer(r, M)
            return
        q = M["qs"][M["q"]]
        if c["t"] == "boss":
            remaining = 1 - M["ok"] / len(M["qs"])
            text("Virus King HP: %d%%" % round(remaining * 100), r.x + 22, y, RED, FS); y += 22
            pygame.draw.rect(scr, (60, 20, 40), (r.x + 22, y, r.w - 44, 12)); pygame.draw.rect(scr, (255, 51, 85), (r.x + 22, y, int((r.w - 44) * remaining), 12)); y += 24
        y = para("Question %d/%d: %s" % (M["q"] + 1, len(M["qs"]), q[0]), r.x + 22, y, r.w - 44) + 8
        for n, o in enumerate(q[1]): y = para("%d) %s" % (n + 1, o), r.x + 40, y, r.w - 80, CYAN) + 4
        if M["fb"]: y = para(("Correct! " if M["fb"][0] else "Not quite. ") + M["fb"][1], r.x + 22, y + 10, r.w - 44, GREEN if M["fb"][0] else RED)
        if not G.touch_enabled:
            text("Press 1-4 to answer" + ("  |  ENTER to continue" if M["fb"] else "") + "  |  ESC leave", r.x + 22, r.bottom - 32, (206, 232, 214), FS)
        if G.touch_enabled:
            draw_modal_touch_buttons(k, M)
        return
    if M["fb"] and not M["fb"][0]:
        draw_wrong_answer(r, M)
        return
    it = c["items"][M["q"]]; cd = it["k"] == "code"
    y = para("Challenge %d/%d: %s" % (M["q"] + 1, len(c["items"]), it["p"]), r.x + 22, r.y + 62, r.w - 44) + 6
    if it.get("c"):
        ls = it["c"].split("\n"); pygame.draw.rect(scr, (21, 31, 39), (r.x + 22, y, r.w - 44, len(ls) * 19 + 10), 0, 6)
        for l in ls: text(l, r.x + 30, y + 5, CYAN, FS); y += 19
        y += 14
    ls = (M["buf"] + ("|" if int(G.t * 2) % 2 == 0 and not (M["fb"] and M["fb"][0]) else "")).split("\n")[-9:]
    hh = max(34, len(ls) * 19 + 12) if not cd else 9 * 19 + 12
    pygame.draw.rect(scr, (21, 31, 39), (r.x + 22, y, r.w - 44, hh), 0, 6); pygame.draw.rect(scr, (104, 206, 172), (r.x + 22, y, r.w - 44, hh), 2, 6)
    for l in ls: text(l, r.x + 30, y + 6, WHITE, FS); y += 19
    y += hh - len(ls) * 19 + 8
    if M["fb"]: y = para(M["fb"][1], r.x + 22, y, r.w - 44, GREEN if M["fb"][0] else RED)
    if M["hint"]: para("Hint: " + it["h"], r.x + 22, y + 4, r.w - 44, GOLD, FS)
    foot = ("ENTER continue" if M["fb"] and M["fb"][0] else ("F5 / Ctrl+Enter run tests  |  TAB indent  |  " if cd else "ENTER submit  |  ") + "F1 hint") + "  |  ESC leave"
    if not G.touch_enabled:
        text(foot, r.x + 22, r.bottom - 32, (206, 232, 214), FS)
    if G.touch_enabled:
        draw_modal_touch_buttons(k, M)

def modal_touch_button_rects(modal):
    if modal["k"] == "mc":
        if modal["fb"] is not None:
            return [pygame.Rect(365, H - 92, 270, 54)]
        return [pygame.Rect(150 + i * 180, H - 92, 160, 54) for i in range(4)]
    if modal["k"] == "tr":
        if modal["fb"] and not modal["fb"][0]:
            return [pygame.Rect(365, H - 92, 270, 54)]
        return [pygame.Rect(150, H - 92, 190, 54), pygame.Rect(405, H - 92, 190, 54),
                pygame.Rect(660, H - 92, 190, 54)]
    return [pygame.Rect(365, H - 92, 270, 54)]

def draw_modal_touch_buttons(kind, modal):
    if kind == "mc":
        labels = ["NEXT"] if modal["fb"] and not modal["fb"][0] else ["CONTINUE"] if modal["fb"] is not None else ["1", "2", "3", "4"]
    elif kind == "tr":
        labels = ["NEXT"] if modal["fb"] and not modal["fb"][0] else ["HINT", "RUN / SUBMIT", "CONTINUE" if modal["fb"] and modal["fb"][0] else "ENTER"]
    else:
        labels = ["CONTINUE"]
    for rect, label in zip(modal_touch_button_rects(modal), labels):
        pygame.draw.rect(scr, (58, 76, 90), rect, 0, 10)
        pygame.draw.rect(scr, CYAN, rect, 2, 10)
        rendered = FS.render(label, True, WHITE)
        scr.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                            rect.centery - rendered.get_height() // 2))

def draw_build_animation(modal):
    r = panel("How GameBuddy is built")
    text("A 2D tour of the pieces behind your adventure", r.x + 24, r.y + 54, WHITE, FS)
    elapsed = modal["elapsed"]
    total = len(BUILD_STEPS) * BUILD_STEP_SECONDS
    complete = elapsed >= total
    step = min(int(elapsed / BUILD_STEP_SECONDS), len(BUILD_STEPS) - 1)
    phase = 1 if complete else (elapsed % BUILD_STEP_SECONDS) / BUILD_STEP_SECONDS
    centers = [192, 346, 500, 654, 808]
    card_y, card_w, card_h = 188, 138, 132

    for i in range(len(BUILD_STEPS) - 1):
        pygame.draw.line(scr, (62, 79, 91), (centers[i] + 70, 252), (centers[i + 1] - 70, 252), 4)
    for i, (title, caption, _) in enumerate(BUILD_STEPS):
        active = i == step and not complete
        done = complete or i < step
        col = GREEN if done else CYAN if active else (99, 120, 130)
        x = centers[i] - card_w // 2
        card = pygame.Rect(x, card_y, card_w, card_h)
        pygame.draw.rect(scr, (26, 38, 47) if not active else (39, 53, 63), card, 0, 10)
        pygame.draw.rect(scr, col, card, 3 if active else 2, 10)
        cx = centers[i]
        iy = card_y + 38
        if i == 0:
            pygame.draw.rect(scr, col, (cx - 18, iy - 13, 30, 34), 2, 3)
            pygame.draw.line(scr, col, (cx - 11, iy - 5), (cx + 5, iy - 5), 2)
            pygame.draw.line(scr, col, (cx - 11, iy + 2), (cx + 5, iy + 2), 2)
            pygame.draw.line(scr, col, (cx - 11, iy + 9), (cx + 1, iy + 9), 2)
        elif i == 1:
            pygame.draw.circle(scr, col, (cx, iy + 2), 17, 2)
            for angle in range(0, 360, 60):
                a = math.radians(angle)
                pygame.draw.line(scr, col, (cx + int(17 * math.cos(a)), iy + 2 + int(17 * math.sin(a))),
                                 (cx + int(23 * math.cos(a)), iy + 2 + int(23 * math.sin(a))), 3)
            pygame.draw.circle(scr, col, (cx, iy + 2), 5)
        elif i == 2:
            pygame.draw.ellipse(scr, col, (cx - 16, iy - 19, 32, 42), 3)
            pygame.draw.ellipse(scr, (73, 91, 103), (cx - 9, iy - 12, 18, 29))
            pygame.draw.circle(scr, GOLD if active else col, (cx, iy + 3), 3)
        elif i == 3:
            pygame.draw.rect(scr, col, (cx - 17, iy - 16, 34, 35), 2, 4)
            pygame.draw.rect(scr, col, (cx - 10, iy - 11, 20, 8), 2, 2)
            pygame.draw.rect(scr, col, (cx - 9, iy + 3, 18, 11), 2, 2)
        else:
            pygame.draw.circle(scr, col, (cx, iy + 1), 18, 2)
            pygame.draw.lines(scr, col, False, [(cx - 9, iy + 1), (cx - 2, iy + 8), (cx + 11, iy - 8)], 4)
        text(title, x + 8, card_y + 72, col, FS)
        cap = FS.render(caption, True, WHITE)
        scr.blit(cap, (cx - cap.get_width() // 2, card_y + 99))

    if not complete:
        travel = (step + phase) / (len(BUILD_STEPS) - 1)
        packet_x = int(centers[0] + (centers[-1] - centers[0]) * travel)
        pulse = 5 + int(2 * (1 + math.sin(G.t * 8)))
        pygame.draw.circle(scr, (55, 38, 18), (packet_x, 252), pulse + 4)
        pygame.draw.circle(scr, GOLD, (packet_x, 252), pulse)

    stage_title, _, description = BUILD_STEPS[step]
    pygame.draw.rect(scr, (23, 33, 42), (r.x + 24, 345, r.w - 48, 38), 0, 8)
    progress = min(1, elapsed / total)
    pygame.draw.rect(scr, (50, 65, 76), (r.x + 34, 360, r.w - 68, 7), 0, 4)
    pygame.draw.rect(scr, CYAN if not complete else GREEN,
                     (r.x + 34, 360, int((r.w - 68) * progress), 7), 0, 4)

    byte(164, 456, G.t)
    pygame.draw.rect(scr, (23, 33, 42), (204, 399, 356, 112), 0, 10)
    pygame.draw.rect(scr, (104, 206, 172), (204, 399, 356, 112), 2, 10)
    text("BYTE  /  " + ("BUILD COMPLETE" if complete else stage_title), 220, 411, GOLD, FS)
    para("The app grows one piece at a time. " + description, 220, 438, 322, WHITE, FS)

    app = pygame.Rect(596, 399, 278, 112)
    pygame.draw.rect(scr, (20, 29, 37), app, 0, 9)
    pygame.draw.rect(scr, (94, 225, 255) if complete else (98, 119, 129), app, 2, 9)
    pygame.draw.rect(scr, (47, 61, 72), (app.x + 2, app.y + 2, app.w - 4, 19), 0, 7)
    text("GAMEBUDDY.EXE", app.x + 13, app.y + 4, WHITE, FS)
    pygame.draw.rect(scr, (48, 63, 74), (app.x + 12, app.y + 31, 92, 67), 0, 5)
    pygame.draw.rect(scr, (19, 53, 68), (app.x + 112, app.y + 31, 152, 67), 0, 5)
    layers = min(len(BUILD_STEPS), step + (1 if complete or phase > .35 else 0) + 1)
    for i in range(layers):
        bx = app.x + 20 + i * 14
        pygame.draw.rect(scr, (67 + i * 12, 105 + i * 8, 171 + i * 5),
                         (bx, app.y + 79 - i * 7, 12, 12), 0, 2)
    for i in range(min(3, max(1, layers - 1))):
        pygame.draw.ellipse(scr, (80, 212, 255), (app.x + 123 + i * 43, app.y + 47, 27, 34), 2)
    pygame.draw.circle(scr, GOLD, (app.x + 234, app.y + 43), 5)
    text("PORTAL  >  QUEST  >  XP", app.x + 115, app.y + 78, CYAN, FS)

    if complete:
        footer = "BUILD COMPLETE!  TAP / ENTER / SPACE close"
    else:
        footer = "TAP / SPACE / ENTER fast-forward  |  ESC close"
    text(footer, r.x + 24, r.bottom - 33, (206, 232, 214), FS)

def draw_story_button(rect, label, color=CYAN):
    hovered = False
    try:
        hovered = rect.collidepoint(logical_pos(pygame.mouse.get_pos()))
    except Exception:
        hovered = False
    fill = (82, 108, 122) if hovered else (58, 76, 90)
    pygame.draw.rect(scr, fill, rect, 0, 9)
    pygame.draw.rect(scr, (86, 112, 126), (rect.x + 3, rect.y + 3, rect.w - 6, rect.h // 2 - 3), 0, 7)
    pygame.draw.rect(scr, GOLD if hovered else color, rect, 3 if hovered else 2, 9)
    pygame.draw.line(scr, color, (rect.x + 10, rect.bottom - 5), (rect.right - 10, rect.bottom - 5), 2)
    rendered = FS.render(label, True, WHITE)
    scr.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                        rect.centery - rendered.get_height() // 2))

INTRO_SCENES = [
    ("CHAPTER 1  |  THE LOST CODE KINGDOM",
     "Game Buddy and Byte guard the Kingdom's Core, the glowing heart of the Lost Code Kingdom. "
     "Every portal in the land runs on its light."),
    ("CHAPTER 2  |  A SHADOW FALLS",
     "But one night the torches begin to flicker. A cold signal crawls through the walls, "
     "and watching eyes open in the dark."),
    ("CHAPTER 3  |  THE VIRUS KING",
     "Game Buddy and Byte discover that the Virus King has scrambled the Kingdom's Core. "
     "The Kingdom's signal goes dark."),
    ("CHAPTER 4  |  THE BROKEN KINGDOM",
     "Banners tear, portals fall silent, and the old code can no longer be read. "
     "Without the Core, the Kingdom is lost."),
    ("CHAPTER 5  |  BYTE CALLS FOR HELP",
     "Game Buddy and Byte need your help. Only a Guardian who can learn code can repair the Core!"),
    ("CHAPTER 6  |  CHOOSE A PATH",
     "Choose a learning path and study its lesson. Python, Java, JavaScript, HTML and CSS "
     "portals are waiting."),
    ("CHAPTER 7  |  THE PORTAL COURSES",
     "Cross the Kingdom's portal courses, collect three code crystals, restore the portal, "
     "and answer each portal quiz."),
    ("CHAPTER 8  |  RESTORE THE SIGNAL",
     "Restore its signal by learning code. Every lesson brings the team closer to "
     "stopping the Virus King."),
]
INTRO_CPS = 42
INTRO_LANG_COLORS = ((94, 225, 255), (255, 154, 60), (255, 210, 74), (255, 122, 138), (226, 110, 170))
INTRO_LANG_LABELS = ("PY", "JAVA", "JS", "HTML", "CSS")
STORY_VOICE_CHANNEL = None
STORY_VOICE_SOUNDS = []

if pygame.mixer is not None:
    try:
        STORY_VOICE_CHANNEL = pygame.mixer.Channel(
            min(pygame.mixer.get_num_channels(), 7))
    except (pygame.error, AttributeError):
        STORY_VOICE_CHANNEL = pygame.mixer.Channel(0)
    for scene_index in range(1, len(INTRO_SCENES) + 1):
        voice_extension = "ogg" if WEB else "mp3"
        voice_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "scene %d.%s" % (scene_index, voice_extension))
        try:
            STORY_VOICE_SOUNDS.append(
                pygame.mixer.Sound(voice_path) if os.path.isfile(voice_path)
                else None)
        except pygame.error:
            STORY_VOICE_SOUNDS.append(None)

def open_story_intro(scene=0):
    set_text_input(False)
    G.M = dict(k="story_intro", scene=scene, t=0.0, typed=0.0)
    start_story_voice(scene)

def stop_story_voice():
    if STORY_VOICE_CHANNEL is not None:
        STORY_VOICE_CHANNEL.stop()

def start_story_voice(scene):
    stop_story_voice()
    if pygame.mixer is None or scene < 0 or scene >= len(STORY_VOICE_SOUNDS):
        return
    if not G.S.get("settings", {"sfx": True}).get("sfx", True):
        return
    voice = STORY_VOICE_SOUNDS[scene]
    if voice is not None:
        voice.set_volume(0.85)
        STORY_VOICE_CHANNEL.play(voice)

def story_intro_skip_rect():
    return pygame.Rect(132 + 736 - 86, 40 + 64 + 8, 78, 26)

def story_intro_finished():
    M = G.M
    return M["typed"] >= len(INTRO_SCENES[M["scene"]][1])

def advance_story_intro(from_click=False):
    M = G.M
    last = len(INTRO_SCENES) - 1
    if not story_intro_finished():
        M["typed"] = float(len(INTRO_SCENES[M["scene"]][1]))
    elif M["scene"] < last:
        M["scene"] += 1; M["t"] = 0.0; M["typed"] = 0.0
        start_story_voice(M["scene"])
    elif not from_click:
        stop_story_voice()
        open_story_language_select()

def skip_story_intro():
    M = G.M
    M["scene"] = len(INTRO_SCENES) - 1; M["t"] = 0.0; M["typed"] = 0.0
    start_story_voice(M["scene"])

def story_ending_finished():
    language = G.M["language"]
    return G.M["typed"] >= len(STORY_LANGUAGE_ENDINGS[language][1])

def advance_story_ending():
    modal = G.M
    if not story_ending_finished():
        modal["typed"] = float(len(STORY_LANGUAGE_ENDINGS[modal["language"]][1]))
    else:
        G.M = dict(k="story_results", language=modal["language"])

def story_ending_continue_rect():
    return pygame.Rect(365, H - 116, 270, 48)

def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def _mix(a, b, f):
    f = max(0.0, min(1.0, f))
    return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))

def _R(*vals):
    return tuple(int(v) for v in vals)

_GLOW_CACHE = {}
def _glow(x, y, rad, col, alpha=80):
    col = tuple((v // 16) * 16 for v in col)
    key = (rad, col, alpha)
    surf = _GLOW_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
        for i in range(4):
            pygame.draw.circle(surf, col + (min(255, alpha // 4 + i * alpha // 4),),
                               (rad, rad), rad - i * rad // 5)
        _GLOW_CACHE[key] = surf
    scr.blit(surf, (int(x - rad), int(y - rad)))

_FOG_CACHE = {}
def _fog(view, gy, t, col, alpha=46):
    key = (col, alpha)
    surf = _FOG_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((260, 54), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, col + (alpha,), (0, 0, 260, 54))
        _FOG_CACHE[key] = surf
    for i in range(4):
        fx = view.x + ((t * (14 + i * 6) + i * 210) % (view.w + 260)) - 260
        scr.blit(surf, (int(fx), int(gy - 30 + (i % 2) * 14 + math.sin(t + i) * 5)))

def _flame(x, y, t, seed, c, size=1.0):
    outer = _mix((150, 235, 60), (255, 96, 60), c)
    inner = _mix((226, 255, 150), (255, 214, 96), c)
    sway = math.sin(t * 7 + seed) * 3 * size
    h = (16 + 5 * math.sin(t * 11 + seed * 2)) * size
    w = 7 * size
    pygame.draw.polygon(scr, outer, [(x - w, y), (x - w * .6 + sway * .3, y - h * .55),
                                     (x + sway, y - h), (x + w * .7 + sway * .3, y - h * .5),
                                     (x + w, y)])
    pygame.draw.polygon(scr, inner, [(x - w * .5, y), (x + sway * .5, y - h * .62), (x + w * .5, y)])

def _torch(x, y, t, seed, c):
    pygame.draw.rect(scr, (60, 52, 46), _R(x - 3, y, 6, 16))
    pygame.draw.rect(scr, (90, 76, 60), _R(x - 8, y - 2, 16, 5), 0, 2)
    _glow(x, y - 12, 40, _mix((150, 235, 60), (255, 96, 60), c), 70)
    _flame(x, y - 2, t, seed, c)

def _core(cx, cy, t, col, size=1.0, shake=0):
    cx = cx + math.sin(t * 40) * shake
    _glow(cx, cy, int(84 * size), col, 90)
    pts = [(cx, cy - 30 * size), (cx + 20 * size, cy), (cx, cy + 30 * size), (cx - 20 * size, cy)]
    pygame.draw.polygon(scr, col, pts)
    pygame.draw.polygon(scr, WHITE, [(cx, cy - 30 * size), (cx + 5 * size, cy - 4 * size),
                                     (cx, cy + 8 * size), (cx - 6 * size, cy - 4 * size)])
    for k in range(3):
        a = t * 1.6 + k * 2.09
        pygame.draw.circle(scr, col, (int(cx + math.cos(a) * 38 * size),
                                      int(cy + math.sin(a) * 12 * size)), 3)

def _pedestal(cx, gy):
    pygame.draw.polygon(scr, (92, 104, 114), [(cx - 36, gy), (cx + 36, gy), (cx + 24, gy - 30), (cx - 24, gy - 30)])
    pygame.draw.rect(scr, (130, 146, 154), _R(cx - 28, gy - 36, 56, 8), 0, 3)

def _hero(x, y, t, moving=False, air=False):
    G.face = 1
    G.ph = t * 9
    hero(int(x), int(y), G.t, moving, air, False)

def _bubble(x, y, label, fill=WHITE, ink=(40, 52, 60)):
    s = FS.render(label, True, ink)
    rect = pygame.Rect(int(x), int(y), s.get_width() + 22, 30)
    pygame.draw.rect(scr, fill, rect, 0, 10)
    pygame.draw.polygon(scr, fill, [(rect.x + 14, rect.bottom - 2), (rect.x + 30, rect.bottom - 2),
                                    (rect.x + 16, rect.bottom + 12)])
    scr.blit(s, (rect.x + 11, rect.y + 6))

def _bats(view, t, n, col=(21, 30, 38)):
    for i in range(n):
        bx = view.x + ((t * (60 + i * 17) + i * 120) % (view.w + 80)) - 40
        by = view.y + 40 + (i * 37) % 110 + math.sin(t * 3 + i) * 14
        flap = math.sin(t * 14 + i) * 7
        pygame.draw.polygon(scr, col, [(bx, by), (bx - 14, by - 6 - flap), (bx - 24, by + 3), (bx - 8, by + 4)])
        pygame.draw.polygon(scr, col, [(bx, by), (bx + 14, by - 6 - flap), (bx + 24, by + 3), (bx + 8, by + 4)])
        pygame.draw.circle(scr, col, (int(bx), int(by + 1)), 4)

def _glyphs(view, t, n, col):
    syms = "01{};<>/=#"
    for i in range(n):
        gx = view.x + (i * 53 + 17) % view.w
        gyy = view.y + (t * (60 + (i % 5) * 18) + i * 37) % view.h
        scr.blit(FS.render(syms[(i + int(t * 4)) % len(syms)], True, col), (int(gx), int(gyy)))

def _debris(view, gy, t):
    for i in range(10):
        dx = view.x + (i * 83 + 40) % view.w
        dy = view.y + (t * (80 + i * 9) + i * 41) % (gy - view.y)
        size = 3 + i % 3
        pygame.draw.rect(scr, (69, 86, 98), _R(dx, dy, size, size))

def _wall_eyes(x, y, t, seed, openness):
    if openness <= 0:
        return
    blink = .15 if (t * .9 + seed) % 3 > 2.8 else 1.0
    h = max(2, int(10 * openness * blink))
    for dx in (-11, 11):
        pygame.draw.ellipse(scr, (214, 240, 160), _R(x + dx - 8, y - h // 2, 16, h))
        if h > 5:
            pygame.draw.circle(scr, (40, 96, 36), (int(x + dx + math.sin(t + seed) * 3), int(y)), 3)

def _crystal(x, y, t):
    y = round(y + math.sin(t * 3) * 2)
    _glow(x, y, 36, (96, 214, 226), 100)
    pygame.draw.polygon(scr, (96, 214, 226), [(x, y - 20), (x + 14, y - 2),
                                              (x + 9, y + 16), (x, y + 21),
                                              (x - 9, y + 16), (x - 14, y - 2)])
    pygame.draw.polygon(scr, (184, 248, 255), [(x, y - 18), (x + 4, y - 2),
                                               (x, y + 10), (x - 4, y - 2)])
    pygame.draw.line(scr, WHITE, (x, y - 18), (x, y + 15), 2)

def _portal(px, base, col, lit, t, i, label=None):
    pygame.draw.rect(scr, (55, 71, 82), _R(px - 28, base - 4, 56, 7))
    if lit:
        _glow(px, base - 48, 56, col, 80)
    pulse = .5 + .5 * math.sin(t * 4 + i)
    inner = _mix((21, 31, 39), col, .35 + .25 * pulse) if lit else (21, 30, 38)
    pygame.draw.ellipse(scr, inner, _R(px - 22, base - 92, 44, 90))
    pygame.draw.ellipse(scr, col if lit else (88, 100, 112), _R(px - 25, base - 96, 50, 98), 5)
    if lit:
        for k in range(3):
            pygame.draw.ellipse(scr, WHITE, _R(px - 6 - k * 5, base - 62 - k * 10 + 2 * math.sin(t * 2 + k),
                                               12 + k * 10, 22 + k * 16), 1)
    if label:
        text_img = FS.render(label, True, WHITE if lit else (140, 150, 160))
        scr.blit(text_img, (px - text_img.get_width() // 2, base - 120))

def _firework(x, y, age, cols):
    if age < 0 or age > 1.6:
        return
    rr = age * 90
    for k in range(12):
        a = k * math.tau / 12
        col = _mix(cols[k % len(cols)], (150, 200, 230), age / 1.6)
        pygame.draw.circle(scr, col, (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr + age * age * 30)),
                           3 if age < 1.0 else 2)

def _king(kx, ky, t, s=1.0, look=(-1, .4), mouth=0.0):
    flesh, dark, tooth = (150, 44, 56), (96, 26, 46), (246, 224, 176)
    for i in range(7):
        bx = kx + (i - 3) * 22 * s
        pts = [(bx + math.sin(t * 3 + i + j * .7) * (3 + j * 3) * s, ky + 40 * s + j * 14 * s)
               for j in range(7)]
        pygame.draw.lines(scr, dark, False, pts, max(2, int(9 * s)))
    pygame.draw.ellipse(scr, dark, _R(kx - 86 * s, ky - 64 * s, 172 * s, 138 * s))
    pygame.draw.ellipse(scr, flesh, _R(kx - 80 * s, ky - 60 * s, 160 * s, 126 * s))
    for k in range(5):
        pygame.draw.circle(scr, dark, (int(kx + (k - 2) * 34 * s), int(ky - 40 * s + (k % 2) * 62 * s)),
                           max(2, int(5 * s)))
    pygame.draw.rect(scr, GOLD, _R(kx - 44 * s, ky - 62 * s, 88 * s, 10 * s), 0, 3)
    for dx in (-30, 0, 30):
        pygame.draw.polygon(scr, GOLD, [(kx + dx * s - 12 * s, ky - 60 * s), (kx + dx * s, ky - 88 * s),
                                        (kx + dx * s + 12 * s, ky - 60 * s)])
    blink = (t % 3.4) > 3.25
    er = max(3, int(15 * s))
    for dx in (-34, 34):
        ex, ey = int(kx + dx * s), int(ky - 20 * s)
        pygame.draw.circle(scr, (214, 240, 160), (ex, ey), er)
        px_, py_ = int(ex + look[0] * 4 * s), int(ey + look[1] * 4 * s)
        pygame.draw.circle(scr, (40, 96, 36), (px_, py_), max(2, int(7 * s)))
        pygame.draw.circle(scr, (10, 22, 10), (px_, py_), max(1, int(3 * s)))
        if blink:
            pygame.draw.rect(scr, flesh, _R(ex - er, ey - er, er * 2, er + 1))
    mh = (10 + 26 * mouth) * s
    pygame.draw.ellipse(scr, (50, 10, 28), _R(kx - 40 * s, ky + 12 * s, 80 * s, mh))
    for k in range(6):
        tx = kx - 30 * s + k * 12 * s
        pygame.draw.polygon(scr, tooth, [(tx, ky + 15 * s), (tx + 10 * s, ky + 15 * s),
                                         (tx + 5 * s, ky + 15 * s + (6 + 8 * mouth) * s)])

def _bg_gradient(view, top, bottom):
    for y in range(0, view.h, 6):
        scr.fill(_mix(top, bottom, y / view.h), _R(view.x, view.y + y, view.w, 6))

def _bg_arches(view, gy, t, c):
    _bg_gradient(view, (12, 26, 30), (46, 92, 76))
    for yy in range(view.y + 70, gy, 34):
        pygame.draw.line(scr, (26, 56, 50), (view.x, yy), (view.right, yy))
    for i in range(5):
        ax = view.x + 70 + i * 148
        pygame.draw.rect(scr, (14, 34, 34), _R(ax - 44, view.y + 56, 88, gy - view.y - 56), 0,
                         border_top_left_radius=44, border_top_right_radius=44)
        px = ax + 74
        pygame.draw.rect(scr, (62, 112, 92), _R(px - 11, view.y + 36, 22, gy - view.y - 36))
        pygame.draw.rect(scr, (90, 148, 118), _R(px - 15, view.y + 30, 30, 10), 0, 3)
        pygame.draw.rect(scr, (90, 148, 118), _R(px - 15, gy - 12, 30, 12), 0, 3)
        _torch(px, view.y + 96, t, i * 1.7, c)

def _bg_banner(view, gy, t, c):
    cx = view.centerx
    _bg_gradient(view, (60, 76, 88), (41, 55, 65))
    for row, yy in enumerate(range(view.y + 40, gy, 28)):
        pygame.draw.line(scr, (47, 62, 73), (view.x, yy), (view.right, yy))
        for xx in range(view.x + (0 if row % 2 else 36), view.right, 72):
            pygame.draw.line(scr, (47, 62, 73), (xx, yy), (xx, yy + 28))
    for i in range(5):
        x0 = view.x + i * 160
        dip = math.sin(t * 2 + i) * 3
        pygame.draw.polygon(scr, (176, 36, 52), [(x0, view.y), (x0 + 160, view.y), (x0 + 130, view.y + 40 + dip),
                                                 (x0 + 80, view.y + 20), (x0 + 30, view.y + 40 + dip)])
        pygame.draw.line(scr, GOLD, (x0 + 30, view.y + 40 + dip), (x0 + 80, view.y + 20), 2)
        pygame.draw.line(scr, GOLD, (x0 + 80, view.y + 20), (x0 + 130, view.y + 40 + dip), 2)
    for px in (view.x + 70, view.right - 70):
        pygame.draw.rect(scr, (78, 96, 108), _R(px - 18, view.y + 40, 36, gy - view.y - 40))
        for k in range(3):
            pygame.draw.ellipse(scr, GOLD, _R(px - 5, view.y + 70 + k * 40, 10, 24), 2)
    sway = math.sin(t * 1.6) * 7
    top = view.y + 34
    pts = [(cx - 36, top), (cx + 36, top), (cx + 36 + sway, top + 150), (cx + sway, top + 126),
           (cx - 36 + sway, top + 150)]
    pygame.draw.polygon(scr, (176, 36, 52), pts)
    pygame.draw.polygon(scr, GOLD, pts, 3)
    ex = int(cx + sway * .4)
    pygame.draw.circle(scr, GOLD, (ex, int(top + 58)), 17, 3)
    pygame.draw.circle(scr, GOLD, (ex + 4, int(top + 56)), 9)
    pygame.draw.circle(scr, (176, 36, 52), (ex + 9, int(top + 52)), 8)
    if c > .5:
        pygame.draw.polygon(scr, (41, 55, 65), [(cx - 36 + sway, top + 150), (cx - 6 + sway, top + 112),
                                                (cx + 14 + sway, top + 150)])
    sx = view.x + 190
    pygame.draw.rect(scr, (52, 68, 79), _R(sx - 26, gy - 64, 52, 64), 0, 8)
    pygame.draw.line(scr, (200, 210, 220), (sx, gy - 60), (sx, gy - 10), 4)
    pygame.draw.line(scr, GOLD, (sx - 12, gy - 50), (sx + 12, gy - 50), 4)

_BEAM_CACHE = {}
def _bg_haunted(view, gy, t):
    _bg_gradient(view, (23, 34, 42), (48, 56, 70))
    wx, wy = view.x + 130, view.y + 40
    pygame.draw.rect(scr, (20, 29, 37), _R(wx, wy, 110, 100))
    pygame.draw.rect(scr, (96, 114, 128), _R(wx, wy, 110, 100), 4)
    pygame.draw.line(scr, (96, 114, 128), (wx + 55, wy), (wx + 55, wy + 100), 3)
    pygame.draw.line(scr, (96, 114, 128), (wx, wy + 50), (wx + 110, wy + 50), 3)
    key = (view.w, view.h)
    beam = _BEAM_CACHE.get(key)
    if beam is None:
        beam = pygame.Surface((view.w, view.h), pygame.SRCALPHA)
        pygame.draw.polygon(beam, (170, 200, 215, 54),
                            [(130, 140), (240, 140), (400, view.h - 46), (200, view.h - 46)])
        _BEAM_CACHE[key] = beam
    scr.blit(beam, (view.x, view.y))
    for i in range(14):
        mx = wx + 40 + (i * 29 + t * 8) % 150
        my = wy + 120 + (i * 41 + t * 12) % 100
        pygame.draw.circle(scr, (200, 220, 230), (int(mx), int(my)), 1)
    kx = view.right - 150
    pygame.draw.rect(scr, (74, 62, 52), _R(kx - 24, gy - 150, 48, 150), 0, 4)
    pygame.draw.rect(scr, (96, 82, 66), _R(kx - 24, gy - 150, 48, 150), 3, 4)
    pygame.draw.circle(scr, (226, 216, 176), (kx, gy - 122), 16)
    pygame.draw.line(scr, (18, 27, 34), (kx, gy - 122), (kx + math.cos(t) * 10, gy - 122 + math.sin(t) * 10), 2)
    sw = math.sin(t * 3) * 12
    pygame.draw.line(scr, GOLD, (kx, gy - 96), (kx + sw, gy - 40), 2)
    pygame.draw.circle(scr, GOLD, (int(kx + sw), gy - 40), 7)
    for k in range(5):
        pygame.draw.line(scr, (120, 132, 146), (view.x, view.y), (view.x + 14 + k * 20, view.y + 90 - k * 14), 1)
    for rr in (30, 56, 80):
        pygame.draw.lines(scr, (120, 132, 146), False,
                          [(view.x + rr * math.cos(i * math.pi / 12), view.y + rr * math.sin(i * math.pi / 12))
                           for i in range(7)], 1)
    for lx in (view.x + 330, view.x + 470):
        pygame.draw.rect(scr, (60, 52, 46), _R(lx - 4, view.y + 80, 8, 22))
        _glow(lx, view.y + 78, 38, (255, 200, 96), max(10, 40 + int(26 * math.sin(t * 13 + lx))))
        pygame.draw.circle(scr, (255, 226, 150), (lx, view.y + 78), 5)

def _bg_scifi(view, gy, t):
    _bg_gradient(view, (244, 202, 112), (226, 158, 72))
    for k in range(3):
        pts = [(view.x + i * 20, view.y + 12 + k * 9 + math.sin(i * .5 + k) * 5) for i in range(38)]
        pygame.draw.lines(scr, (198, 124, 46), False, pts, 7)
    mx, my, mw, mh = view.x + 230, view.y + 26, 200, 66
    pygame.draw.rect(scr, (206, 112, 70), _R(mx - 8, my - 8, mw + 16, mh + 16), 0, 8)
    pygame.draw.rect(scr, (248, 226, 180), _R(mx, my, mw, mh), 0, 4)
    for gx in range(mx, mx + mw, 20):
        pygame.draw.line(scr, (226, 184, 128), (gx, my), (gx, my + mh))
    for gyy in range(my, my + mh, 16):
        pygame.draw.line(scr, (226, 184, 128), (mx, gyy), (mx + mw, gyy))
    sweep = (t * 70) % mw
    pygame.draw.line(scr, (60, 170, 170), (mx + sweep, my), (mx + sweep, my + mh), 3)
    for bx, by in ((40, 20), (110, 44), (160, 16)):
        if sweep > bx:
            pygame.draw.circle(scr, (226, 72, 84), (int(mx + bx), int(my + by)), 4)
    for sx in (view.x + 40, view.x + 520):
        pygame.draw.rect(scr, (200, 90, 140), _R(sx - 4, view.y + 36, 68, 52), 0, 6)
        pygame.draw.rect(scr, (96, 200, 200), _R(sx, view.y + 40, 60, 44), 0, 4)
        for k in range(3):
            pygame.draw.line(scr, (230, 250, 240), (sx + 8, view.y + 52 + k * 10),
                             (sx + 38 + k * 5, view.y + 52 + k * 10), 2)
    dx = view.right - 96
    pygame.draw.rect(scr, (200, 90, 140), _R(dx - 6, gy - 130, 66, 130), 0, 8)
    pygame.draw.rect(scr, (60, 70, 90), _R(dx, gy - 124, 54, 124))
    gap = max(0.0, math.sin(t * .9)) * 14
    pygame.draw.rect(scr, (250, 228, 176), _R(dx, gy - 124, 27 - gap, 124))
    pygame.draw.rect(scr, (250, 228, 176), _R(dx + 27 + gap, gy - 124, 27 - gap, 124))

def _bg_wood(view, gy, t):
    for k, yy in enumerate(range(view.y, view.bottom, 26)):
        scr.fill((184, 118, 54) if k % 2 else (170, 106, 46), _R(view.x, yy, view.w, 26))
        pygame.draw.line(scr, (118, 68, 32), (view.x, yy), (view.right, yy))
        jx = view.x + (k * 131) % view.w
        pygame.draw.line(scr, (118, 68, 32), (jx, yy), (jx, yy + 26))
    pygame.draw.polygon(scr, (112, 62, 34), [(view.x, view.y), (view.x + 80, view.y), (view.x + 52, view.y + 120),
                                             (view.x + 70, gy), (view.x, gy)])
    pygame.draw.polygon(scr, (112, 62, 34), [(view.right, view.y), (view.right - 90, view.y),
                                             (view.right - 60, view.y + 110), (view.right - 80, gy),
                                             (view.right, gy)])
    for k in range(3):
        pygame.draw.line(scr, (112, 62, 34), (view.x + 60, view.y + 40 + k * 22),
                         (view.x + 150 + k * 30, view.y + 14 + k * 26), 9)
        pygame.draw.line(scr, (112, 62, 34), (view.right - 70, view.y + 40 + k * 22),
                         (view.right - 160 - k * 30, view.y + 14 + k * 26), 9)
    for i, lx in enumerate((view.x + 120, view.x + 400, view.right - 130)):
        sw = math.sin(t * 1.5 + i) * 6
        pygame.draw.line(scr, (60, 50, 40), (lx, view.y), (lx + sw, view.y + 56), 2)
        _glow(lx + sw, view.y + 70, 34, (255, 214, 96), 80)
        pygame.draw.rect(scr, (60, 70, 50), _R(lx + sw - 9, view.y + 56, 18, 26), 0, 4)
        pygame.draw.rect(scr, (255, 226, 130), _R(lx + sw - 6, view.y + 60, 12, 18), 0, 3)

def _bg_lab(view, gy, t):
    _bg_gradient(view, (160, 216, 240), (124, 188, 224))
    for gx in range(view.x, view.right, 38):
        pygame.draw.line(scr, (112, 172, 208), (gx, view.y), (gx, gy))
    for gyy in range(view.y, gy, 38):
        pygame.draw.line(scr, (112, 172, 208), (view.x, gyy), (view.right, gyy))
    for px in (view.x + 70, view.right - 80):
        pygame.draw.circle(scr, (66, 128, 172), (px, view.y + 54), 30)
        pygame.draw.circle(scr, (196, 236, 250), (px, view.y + 54), 23)
        for k in (-12, 0, 12):
            pygame.draw.line(scr, (66, 128, 172), (px - 22, view.y + 54 + k), (px + 22, view.y + 54 + k), 2)
    for i in range(3):
        tx = view.x + 520 + i * 44
        lvl = 70 + math.sin(t * 2 + i) * 10
        pygame.draw.rect(scr, (210, 240, 250), _R(tx - 14, gy - 112, 28, 112), 0, 10)
        pygame.draw.rect(scr, (160, 230, 60), _R(tx - 11, gy - lvl, 22, lvl), 0, 8)
        pygame.draw.rect(scr, (66, 128, 172), _R(tx - 14, gy - 112, 28, 112), 3, 10)
        for b in range(3):
            by = gy - ((t * 30 + b * 24 + i * 11) % lvl)
            pygame.draw.circle(scr, (226, 255, 160), (int(tx + math.sin(t * 3 + b) * 4), int(by)), 3)
    lx = view.right - 40
    pygame.draw.rect(scr, (70, 130, 170), _R(lx - 14, gy - 86, 28, 86), 0, 8)
    pygame.draw.circle(scr, (240, 150, 40), (lx, int(gy - 44 + math.sin(t * 1.3) * 22)), 10)
    pygame.draw.circle(scr, (240, 150, 40), (lx, int(gy - 26 + math.sin(t * 1.9) * 12)), 7)

def draw_intro_scene(scene, t, view, background=None):
    """Animated cutscene for one chapter, drawn inside the view rectangle."""
    old_clip = scr.get_clip()
    scr.set_clip(view)
    if background is not None:
        scr.blit(background, view.topleft)
    gy = view.bottom - 46
    cx = view.centerx
    G.face = 1
    cyan = (96, 214, 226)
    hx = view.x + 190
    if scene in (0, 5, 6, 7):
        c = 0.0
    elif scene == 1:
        c = min(1.0, t / 4.0) * .75
    else:
        c = 1.0
    if scene in (0, 1, 2):
        if background is None:
            _bg_arches(view, gy, t, c)
        floor = (_mix((36, 58, 54), (66, 28, 42), c), _mix((110, 170, 120), (180, 60, 70), c))
    elif scene == 3:
        if background is None:
            _bg_banner(view, gy, t, c)
        floor = ((35, 47, 58), (130, 70, 84))
    elif scene == 4:
        if background is None:
            _bg_haunted(view, gy, t)
        floor = ((23, 34, 42), (78, 92, 106))
    elif scene == 5:
        if background is None:
            _bg_scifi(view, gy, t)
        floor = ((190, 120, 56), (246, 196, 100))
    elif scene == 6:
        if background is None:
            _bg_wood(view, gy, t)
        floor = ((150, 92, 40), (214, 150, 70))
    else:
        if background is None:
            if background is None:
                _bg_lab(view, gy, t)
        else:
            scr.blit(background, view.topleft)
        floor = ((88, 128, 160), (170, 220, 244))
    pygame.draw.rect(scr, floor[0], _R(view.x, gy, view.w, 46))
    pygame.draw.rect(scr, floor[1], _R(view.x, gy, view.w, 5))
    for k in range(0, view.w, 64):
        pygame.draw.line(scr, _mix(floor[0], (0, 0, 0), .25), (view.x + k, gy + 5), (view.x + k - 16, gy + 46))

    if scene == 0:
        core_col = _mix(cyan, (200, 250, 255), (math.sin(t * 3) + 1) / 2)
        _pedestal(cx, gy)
        _core(cx, gy - 128 + math.sin(t * 2) * 5, t, core_col)
        byte(int(cx + math.cos(t * 1.2) * 150), int(view.y + 110 + math.sin(t * 1.7) * 18), t)
        _hero(view.x + 30 + _ease(t / 3.5) * 160, gy + 8, t, t < 3.5)
    elif scene == 1:
        core_col = _mix(cyan, (150, 80, 110), _ease(t / 4.0) * .8)
        if int(t * 9) % 11 == 0:
            core_col = _mix(core_col, (25, 35, 44), .6)
        _pedestal(cx, gy)
        _core(cx, gy - 128 + math.sin(t * 2) * 5, t, core_col)
        for i in range(5):
            _wall_eyes(view.x + 70 + i * 148, view.y + 130, t, i * 1.3, _ease((t - 1.0 - i * .45) / .8))
        _fog(view, gy, t, (150, 200, 180))
        _bats(view, t, min(5, 1 + int(t * 1.2)))
        _hero(hx, gy + 8, t)
        byte(int(hx + 62 + math.sin(t * 31) * 2), int(view.y + 130), t)
        flash = max(0.0, 1.0 - abs((t % 4.5) - 3.2) * 9)
        if flash > 0:
            v = int(90 * flash)
            scr.fill((v, v, v), view, special_flags=pygame.BLEND_RGB_ADD)
    elif scene == 2:
        drop = _ease(t / 2.2)
        _king(cx + 200, view.y - 90 + drop * 190, t, 1.0, (-1, .5), _ease((t - 2.2) / .8))
        core_col = _mix((150, 80, 110), (255, 70, 90), _ease(t / 1.6))
        _pedestal(cx, gy)
        _core(cx, gy - 128 + math.sin(t * 2) * 5, t, core_col, 1.0, 3 if t > 2.2 else 0)
        if t > 1.5:
            _glyphs(view, t, 28, (255, 120, 140))
        step = _ease((t - 2.2) / 1.2)
        _hero(hx - 50 * step, gy + 8, t, 0 < step < 1)
        byte(int(hx + 20 - 40 * step), int(view.y + 130), t)
        if 2.15 < t < 2.4:
            scr.fill((90, 0, 0), view, special_flags=pygame.BLEND_RGB_ADD)
        if 2.4 < t < 3.6:
            for i in range(4):
                scr.fill((255, 60, 90), _R(view.x, view.y + ((int(t * 20) * 53 + i * 71) % view.h), view.w, 3))
    elif scene == 3:
        _debris(view, gy, t)
        for i in range(3):
            px = view.x + 170 + i * 190
            _portal(px, gy, (88, 100, 112), False, t, i)
            crack = [(px - 10, gy - 90), (px + 4, gy - 70), (px - 6, gy - 52), (px + 8, gy - 34)]
            pygame.draw.lines(scr, RED if int(t * 4 + i) % 3 else GOLD, False, crack, 2)
        _bats(view, t, 3)
        walk_x = view.x + 60 + min(t, 7.0) * 60
        _hero(walk_x, gy + 8, t, t < 7.0)
        byte(int(walk_x + 70), int(view.y + 130 + math.sin(t * 3) * 8), t)
        if int(t * 9) % 6 == 0:
            scr.fill((23, 34, 42), view, special_flags=pygame.BLEND_RGB_SUB)
    elif scene == 4:
        f = _ease(t / 1.6)
        hx4 = view.x + 330
        bx = view.x - 40 + f * (hx4 + 80 - (view.x - 40))
        by = view.y + 120 + math.sin(t * 6) * 4
        for k in range(6):
            pygame.draw.circle(scr, cyan, (int(bx - 16 - k * 14), int(by + math.sin(t * 20 + k) * 4)),
                               max(1, 4 - k // 2))
        jump = abs(math.sin((t - 3.6) * 5)) * 26 if t > 3.6 else 0
        _hero(hx4, gy + 8 - jump, t, False, jump > 3)
        byte(int(bx), int(by), t)
        if 1.6 < t < 3.6:
            _bubble(bx - 30, by - 70, "HELP!", WHITE)
        elif t >= 3.6:
            _bubble(hx4 - 10, gy - 170, "I'm ready!", (156, 232, 72))
    elif scene == 5:
        for i in range(5):
            _portal(view.x + 80 + i * 125, gy, INTRO_LANG_COLORS[i], t > .8 + i * 1.0, t, i,
                    INTRO_LANG_LABELS[i])
        hx5 = view.x + 20 + min(t * 50, 560)
        _hero(hx5, gy + 8, t, t * 50 < 560)
        byte(int(hx5 + 66), int(view.y + 118 + math.sin(t * 2) * 10), t)
    elif scene == 6:
        xs = [70, 190, 310, 430, 550, 660]
        rise = [0, 40, 76, 46, 88, 42]
        sy = [gy + 8 - r for r in rise]
        for i in range(1, 6):
            px = view.x + xs[i]
            pygame.draw.rect(scr, (120, 70, 34), _R(px - 46, sy[i], 92, 18), 0, 4)
            pygame.draw.rect(scr, (222, 160, 72), _R(px - 46, sy[i] - 2, 92, 8), 0, 3)
            pygame.draw.rect(scr, (255, 226, 130), _R(px - 18, sy[i] + 4, 36, 10), 0, 3)
        _portal(view.x + xs[5], sy[5] - 2, GOLD, True, t, 0)
        u = (t * .85) % 7.0
        seg = min(int(u), 5)
        if u < 5:
            f = u - seg
            e = _ease(f)
            px6 = view.x + xs[seg] + (xs[seg + 1] - xs[seg]) * e
            py6 = sy[seg] + (sy[seg + 1] - sy[seg]) * e - math.sin(math.pi * f) * 46
            air = 0.04 < f < .96
        else:
            px6, py6, air = view.x + xs[5], sy[5], False
        for idx in (1, 2, 4):
            kx6 = view.x + xs[idx]
            ky6 = sy[idx] - 70 + math.sin(t * 3 + idx) * 4
            if u < idx:
                _crystal(kx6, ky6, t)
            else:
                age = (u - idx) / .85
                if age < .6:
                    pygame.draw.circle(scr, cyan, (int(kx6), int(ky6)), int(age / .6 * 40) + 4, 2)
        _hero(px6, py6, t, False, air)
        byte(int(px6 - 56), int(py6 - 120 + math.sin(t * 3) * 6), t)
    else:
        f = _ease((t - .4) / 3.0)
        _king(cx + 200 + f * 260, view.y + 100 - f * 150, t, 1.0 - .55 * f, (1, -1), max(0.0, 1.0 - f))
        core_col = _mix((255, 70, 90), cyan, _ease(t / 2.0))
        cy7 = view.y + 82 + math.sin(t * 2) * 5
        if t < 4.0:
            for k in range(3):
                pygame.draw.circle(scr, core_col, (cx, int(cy7)), int((t * 110 + k * 80) % 240) + 10, 2)
        _core(cx, cy7, t, core_col, 1.1)
        jump = abs(math.sin(t * 4)) * 34 if t > 1.0 else 0
        _hero(hx, gy + 8 - jump, t, False, jump > 3)
        byte(int(cx + 90 + math.cos(t * 2) * 80), int(view.y + 130 + math.sin(t * 3) * 14), t)
        cols = (GOLD, cyan, (160, 230, 60), (240, 120, 150))
        for k, (fx, fy) in enumerate(((cx - 150, view.y + 70), (cx + 120, view.y + 60), (cx + 250, view.y + 110))):
            age = t - 2.2 - k * .6
            if age >= 0:
                _firework(fx, fy, age % 2.6, cols)

    if t < .5:
        v = int(255 * t / .5)
        scr.fill((v, v, v), view, special_flags=pygame.BLEND_RGB_MULT)
    scr.set_clip(old_clip)

def draw_story_intro():
    M = G.M
    scene = M["scene"]
    last = len(INTRO_SCENES) - 1
    title, body = INTRO_SCENES[scene]
    r = panel("Game Buddy")
    view = pygame.Rect(r.x + 22, r.y + 64, r.w - 44, 262)
    language = STORY_LANGUAGE_NAMES[scene % len(STORY_LANGUAGE_NAMES)]
    background = story_scene_background(language, view.size)
    draw_intro_scene(scene, M["t"], view, background)
    pygame.draw.rect(scr, GOLD, view, 2, 6)
    text(title, view.x + 12, view.y + 10, GOLD, FS)
    if scene < last:
        skip = story_intro_skip_rect()
        draw_story_button(skip, "SKIP", (206, 232, 214))
    # progress dots
    for i in range(len(INTRO_SCENES)):
        pygame.draw.circle(scr, GOLD if i == scene else (104, 206, 172),
                           (r.centerx - (len(INTRO_SCENES) - 1) * 10 + i * 20, view.bottom + 14),
                           5 if i == scene else 4)
    # typewriter text
    shown = int(M["typed"])
    y = view.bottom + 30
    for line in wrap(body, F, r.w - 48):
        if shown <= 0:
            break
        text(line[:shown], r.x + 24, y, CYAN if scene % 2 else WHITE, F)
        shown -= len(line) + 1
        y += F.get_linesize() + 2
    done = story_intro_finished()
    if scene == last and done:
        draw_story_button(pygame.Rect(365, H - 116, 270, 48), "CHOOSE A LANGUAGE", GOLD)
    elif done and int(G.t * 2) % 2 == 0:
        text("NEXT  >>", r.right - 130, r.bottom - 50, GOLD, FS)
    footer = ("ENTER / SPACE to continue  |  ESC return to menu" if scene == last else
              "ENTER / SPACE / tap: next  |  SKIP  |  ESC return to menu")
    text(footer, r.x + 22, r.bottom - 24, (206, 232, 214), FS)

def draw_story_ending():
    modal = G.M
    title, body = STORY_LANGUAGE_ENDINGS[modal["language"]]
    color = tuple(story_language_data(modal["language"])["color"])
    r = panel("Game Buddy")
    view = pygame.Rect(r.x + 22, r.y + 64, r.w - 44, 210)
    draw_intro_scene(7, modal["t"], view)
    pygame.draw.rect(scr, color, view, 2, 6)
    text(title, view.x + 12, view.y + 10, color, FS)
    shown = int(modal["typed"])
    y = view.bottom + 22
    body_font = fnt(16)
    body_bottom = story_ending_continue_rect().y - 12
    body_clip = pygame.Rect(r.x + 24, y, r.w - 48,
                            max(20, body_bottom - y))
    scr.set_clip(body_clip)
    for line in wrap(body, body_font, r.w - 48):
        if shown <= 0:
            break
        text(line[:shown], r.x + 24, y, WHITE, body_font)
        shown -= len(line) + 1
        y += body_font.get_linesize() + 2
        if y >= body_bottom:
            break
    scr.set_clip(None)
    if story_ending_finished():
        draw_story_button(story_ending_continue_rect(), "VIEW FINAL RESULTS", GOLD)
    text("ENTER / SPACE to continue  |  ESC to results",
         r.x + 22, r.bottom - 24, (206, 232, 214), FS)

def draw_story_language_select(modal):
    r = panel("Choose a Language Path")
    text("Select one of five paths. Each path has five lessons and its own score.",
         r.x + 22, r.y + 60, WHITE, FS)
    for i, language in enumerate(STORY_LANGUAGE_NAMES):
        language_data = story_language_data(language)
        card = story_language_card_rect(i)
        selected = i == modal["selected"]
        pygame.draw.rect(scr, (45, 60, 71) if selected else (36, 48, 62),
                         card, 0, 10)
        pygame.draw.rect(scr, GOLD if selected else tuple(language_data["color"]),
                         card, 3 if selected else 2, 10)
        text("%d" % (i + 1), card.centerx - 5, card.y + 16,
             tuple(language_data["color"]), FB)
        label = FS.render(language, True, WHITE)
        scr.blit(label, (card.centerx - label.get_width() // 2, card.y + 58))
        completed = len(story_progress(language)["completed_topics"])
        text("%d / 5 portals" % completed, card.centerx - 44, card.y + 86,
             (206, 232, 214), FS)
    text("LEFT / RIGHT or 1-5 to choose  |  ENTER or click a path",
         r.x + 22, r.bottom - 26, (206, 232, 214), FS)

def draw_story_lesson_list(modal):
    language = modal["language"]
    topics = story_language_data(language)["topics"]
    completed = story_progress(language)["completed_topics"]
    r = panel("%s: Choose a Portal" % language)
    text("Choose any portal. Study its lesson, collect crystals in parkour, and answer its quiz.",
         r.x + 22, r.y + 50, WHITE, FS)
    for i, topic in enumerate(topics):
        card = story_lesson_card_rect(i)
        done = i in completed
        selected = i == modal["selected"]
        color = tuple(story_language_data(language)["color"])
        pygame.draw.rect(scr, (62, 116, 96) if selected else (36, 48, 62),
                         card, 0, 8)
        pygame.draw.rect(scr, GOLD if selected else GREEN if done else color,
                         card, 2, 8)
        text("PORTAL %d: %s" % (i + 1, topic["topic"]), card.x + 16,
             card.y + 17, WHITE, FS)
        text("✓ VIEW LESSON" if done else "UP TO %d XP" % max_story_topic_xp(),
             card.right - 152, card.y + 17, GREEN if done else CYAN, FS)
        cleared_on = story_progress(language).get("topic_difficulty", {}).get(str(i))
        if done and cleared_on:
            cleared = difficulty_by_id(cleared_on)
            text(cleared["name"], card.x + 330, card.y + 17, cleared["color"], FS)
    text("UP / DOWN to choose  |  Click a lesson to study or view it  |  ESC languages",
         r.x + 22, r.bottom - 26, (206, 232, 214), FS)

def difficulty_polygon(center, sides, radius):
    start = {4: -135, 6: 0, 8: -67.5}.get(sides, -90)
    return [(center[0] + math.cos(math.radians(start + 360 * n / sides)) * radius,
             center[1] + math.sin(math.radians(start + 360 * n / sides)) * radius)
            for n in range(sides)]

def draw_difficulty_emblem(center, difficulty, selected=False):
    color = difficulty["color"]
    inner = tuple(int(c * .35 + 30 * .65) for c in color)
    pygame.draw.circle(scr, inner, center, 31)
    for dy in (-16, -5, 6, 17):
        half = int(math.sqrt(max(0, 29 * 29 - dy * dy)))
        pygame.draw.line(scr, tuple(int(c * .55 + 40 * .45) for c in color),
                         (center[0] - half, center[1] + dy), (center[0] + half, center[1] + dy), 2)
    pygame.draw.polygon(scr, color, difficulty_polygon(center, difficulty["sides"], 17))
    pygame.draw.circle(scr, GOLD if selected else color, center, 32, 4)

def draw_story_difficulty(modal):
    language = modal["language"]
    topic = story_language_data(language)["topics"][modal["topic"]]
    lang_color = tuple(story_language_data(language)["color"])
    r = panel("Choose Your Difficulty")
    text("%s  |  PORTAL %d: %s" % (language.upper(), modal["topic"] + 1, topic["topic"].upper()),
         r.x + 22, r.y + 56, lang_color, FS)
    text("Higher difficulty earns more XP; the quiz stays the same.",
         r.x + 22, r.y + 78, WHITE, FS)
    for i, difficulty in enumerate(DIFFICULTIES):
        card = story_difficulty_card_rect(i)
        selected = i == modal["selected"]
        color = difficulty["color"]
        fill = tuple(int(c * (.28 if selected else .16) + 36 * (.72 if selected else .84)) for c in color)
        pygame.draw.rect(scr, fill, card, 0, 12)
        pygame.draw.rect(scr, GOLD if selected else color, card, 3 if selected else 2, 12)
        draw_difficulty_emblem((card.x + 52, card.centery), difficulty, selected)
        text(difficulty["name"], card.x + 104, card.y + 18, WHITE, fnt(24, True))
        text("CRYSTAL +%d XP" % difficulty["crystal_xp"], card.x + 104, card.y + 50, GOLD, FS)
        text("PORTAL +%d XP" % difficulty["topic_xp"], card.x + 104, card.y + 68, CYAN, FS)
        text(str(i + 1), card.right - 24, card.y + 10, (206, 232, 214), FS)
    chosen = DIFFICULTIES[modal["selected"]]
    text(chosen["blurb"], r.x + 22, r.y + 386, chosen["color"], FS)
    actions = story_difficulty_action_rects()
    draw_story_button(actions["back"], "BACK", lang_color)
    draw_story_button(actions["start"], "START PARKOUR", GOLD)
    text("1-6 / arrows to choose  |  ENTER start  |  ESC back",
         r.x + 22, r.bottom - 24, (206, 232, 214), FS)

def draw_story_lesson(modal):
    language = modal["language"]
    topic = story_language_data(language)["topics"][modal["topic"]]
    r = panel("%s: %s" % (language, topic["topic"]))
    color = tuple(story_language_data(language)["color"])
    content_rect = pygame.Rect(r.x + 24, r.y + 56, r.w - 48, r.bottom - 122 - (r.y + 56))
    content_width = content_rect.w - 18
    story_font = FS
    lesson_font = FS
    code_font = fnt(13)
    y = content_rect.y
    scr.set_clip(content_rect)

    y -= modal.get("scroll", 0)
    text("STORY MOMENT", r.x + 24, y, GOLD, FS)
    y += 26
    y = para(topic["story"], r.x + 24, y, content_width, WHITE, story_font) + 14

    text("LESSON", r.x + 24, y, GOLD, FS)
    y += 26
    y = para(topic["lesson"], r.x + 24, y, content_width, WHITE, lesson_font) + 14

    for example_index, example in enumerate(topic["examples"]):
        text("EXAMPLE %d" % (example_index + 1), r.x + 24, y, color, FS)
        y += 26
        code_lines = []
        for line in example.splitlines():
            code_lines.extend(wrap(line if line else " ", code_font, content_width - 28))
        code_height = max(44, 24 + len(code_lines) * (code_font.get_linesize() + 1))
        code_box = pygame.Rect(r.x + 22, y, content_rect.w - 12, code_height)
        pygame.draw.rect(scr, (21, 31, 39), code_box, 0, 7)
        code_y = code_box.y + 12
        for line in code_lines:
            text(line, code_box.x + 14, code_y, CYAN, code_font)
            code_y += code_font.get_linesize() + 1
        y = code_box.bottom + 12

    scr.set_clip(None)
    content_bottom = y + modal.get("scroll", 0)
    maximum_scroll = max(0, content_bottom - content_rect.bottom)
    modal["scroll"] = max(0, min(modal.get("scroll", 0), maximum_scroll))

    if maximum_scroll > 0:
        track = pygame.Rect(r.right - 18, content_rect.y, 6, content_rect.h)
        pygame.draw.rect(scr, (31, 44, 54), track, 0, 3)
        thumb_h = max(24, int(track.h * content_rect.h / (content_rect.h + maximum_scroll)))
        thumb_y = track.y + int((track.h - thumb_h) * modal["scroll"] / maximum_scroll)
        pygame.draw.rect(scr, color, pygame.Rect(track.x, thumb_y, track.w, thumb_h), 0, 3)
    actions = story_lesson_action_rects(modal["read_only"])
    if modal["read_only"]:
        draw_story_button(actions["back"], "BACK TO LESSONS", color)
        draw_story_button(actions["replay"], "RETRY QUIZ", GOLD)
        text("Completed lesson — review the lesson or retry the quiz without losing your badge.",
             r.x + 24, r.bottom - 102, GREEN, FS)
        text("Scroll with the mouse wheel, touch, or arrow keys.",
             r.x + 24, r.bottom - 24, (206, 232, 214), FS)
    else:
        draw_story_button(actions["back"], "BACK", color)
        draw_story_button(actions["lessons"], "CHOOSE ANOTHER LESSON", color)
        draw_story_button(actions["parkour"], "START PARKOUR", GOLD)
        text("Scroll with the mouse wheel, touch, or arrow keys. Start Parkour when ready.",
             r.x + 24, r.bottom - 24, (206, 232, 214), FS)

def draw_story_battle_scene(modal, rect):
    language = modal["language"]
    background = story_scene_background(language, rect.size)
    if background is None:
        scr.fill((28, 38, 48), rect)
    else:
        scr.blit(background, rect.topleft)
    scr.blit(STORY_BATTLE_SHADE, rect.topleft)
    ground_y = rect.bottom - 18
    pygame.draw.line(scr, (226, 218, 180), (rect.x + 12, ground_y),
                     (rect.right - 12, ground_y), 3)

    effect = modal.get("battle_effect")
    elapsed = max(0.0, G.t - modal.get("battle_effect_start", G.t))
    hero_x = rect.x + 132
    king_x = rect.right - 132
    if effect == "strike" and elapsed < .7:
        king_x += math.sin(min(1.0, elapsed / .7) * math.pi) * 18
    _hero(hero_x, ground_y + 7, G.t, effect == "strike" and elapsed < .3)
    byte(rect.centerx, rect.y + 82, G.t)
    _king(king_x, rect.y + 94, G.t, .48, (-1, .2),
          .65 if effect == "counter" and elapsed < .7 else 0.0)
    text("GUARDIAN", rect.x + 22, rect.y + 27, WHITE, FS)
    text("VIRUS KING", rect.right - 124, rect.y + 27, WHITE, FS)
    player_hp = modal.get("battle_player_hp", 3)
    king_hp = modal.get("battle_king_hp", 3)
    text("HP %d / 3" % player_hp, rect.x + 20, rect.y + 45, GREEN, FS)
    text("HP %d / 3" % king_hp, rect.right - 82, rect.y + 45, RED, FS)
    player_bar = pygame.Rect(rect.x + 12, rect.y + 65, 90, 8)
    king_bar = pygame.Rect(rect.right - 102, rect.y + 65, 90, 8)
    for bar, health, color in (
            (player_bar, player_hp, GREEN), (king_bar, king_hp, RED)):
        pygame.draw.rect(scr, (21, 31, 39), bar, 0, 4)
        fill = pygame.Rect(bar.x + 1, bar.y + 1,
                           (bar.w - 2) * health // 3, bar.h - 2)
        pygame.draw.rect(scr, color, fill, 0, 3)
        pygame.draw.rect(scr, WHITE, bar, 1, 4)
    text("CODE HITS %d / 3" % modal.get("battle_hits", 0),
         rect.right - 142, rect.y + 5, GOLD, FS)

    feedback = modal.get("feedback")
    if feedback is None or elapsed >= .8:
        return
    progress = min(1.0, elapsed / .8)
    if effect == "strike":
        projectile_x = hero_x + 38 + (king_x - hero_x - 86) * progress
        projectile_y = rect.y + 80 - math.sin(progress * math.pi) * 24
        _glow(projectile_x, projectile_y, 20, CYAN, 120)
        code = feedback["selected"].replace("\n", " ")[:12]
        text(code, projectile_x - 24, projectile_y - 11, WHITE, FS)
    else:
        projectile_x = king_x - 86 - (king_x - hero_x - 86) * progress
        projectile_y = rect.y + 90 - math.sin(progress * math.pi) * 18
        _glow(projectile_x, projectile_y, 20, RED, 120)
        pygame.draw.circle(scr, RED, (int(projectile_x), int(projectile_y)), 9)
        if progress > .55:
            pygame.draw.circle(scr, CYAN, (rect.centerx, rect.y + 82), 38, 3)

def story_battle_quiz_layout(modal):
    r = pygame.Rect(110, 40, W - 220, H - 80)
    battle_rect = story_battle_scene_rect()
    language = modal["language"]
    topic = story_language_data(language)["topics"][modal["topic"]]
    question = topic["questions"][modal["question"]]
    prompt_font = F
    prompt_top = battle_rect.bottom + 32
    prompt_lines = wrap(question["prompt"].replace("____", "________"),
                        prompt_font, r.w - 44)
    prompt_bottom = prompt_top + 24 + len(prompt_lines) * (
        prompt_font.get_linesize() + 2)

    choices = (question.get("options") if question["type"] == "multiple_choice"
               else question.get("bank") if question["type"] == "fill_blank"
               else question.get("choices", []))
    reference_font = fnt(12)
    choice_rows = max(1, (len(choices) + 1) // 2)
    reference_height = max(44, 16 + choice_rows * 20)
    reference_label_y = prompt_bottom + 8
    reference_box = pygame.Rect(r.x + 22, reference_label_y + 22,
                                r.w - 44, reference_height)
    input_box = pygame.Rect(r.x + 22, reference_box.bottom + 12,
                            r.w - 44, 46)
    submit_box = pygame.Rect(input_box.right - 220, input_box.y,
                             220, input_box.h)
    return {
        "prompt_top": prompt_top,
        "prompt_bottom": prompt_bottom,
        "reference_label_y": reference_label_y,
        "reference_box": reference_box,
        "reference_font": reference_font,
        "choices": choices,
        "input": input_box,
        "submit": submit_box,
    }

def draw_story_battle_quiz(modal):
    language = modal["language"]
    topic = story_language_data(language)["topics"][modal["topic"]]
    question = topic["questions"][modal["question"]]
    color = tuple(story_language_data(language)["color"])
    r = panel("%s — Final Portal Battle" % language)
    progress = story_progress(language)
    completed_score = sum(sum(bool(answer) for answer in result)
                          for result in progress["topic_results"].values())
    current_records = story_attempt_records(progress, modal["topic"])
    current_score = sum(bool(record["correct"]) for record in current_records.values())
    battle_rect = story_battle_scene_rect()
    draw_story_battle_scene(modal, battle_rect)
    text("ROUND %d / 3  |  LANGUAGE SCORE %d / 15" %
         (modal["question"] + 1, completed_score + current_score),
         battle_rect.x + 12, battle_rect.y + 5, WHITE, FS)

    layout = story_battle_quiz_layout(modal)
    text("TYPE YOUR ANSWER TO THROW A CODE STRIKE",
         r.x + 22, layout["prompt_top"] - 24, color, FS)
    para(question["prompt"].replace("____", "________"),
         r.x + 22, layout["prompt_top"], r.w - 44, WHITE, FS)
    choices = layout["choices"]
    reference_label = ("ANSWER CHOICES" if question["type"] == "multiple_choice"
                       else "WORD BANK" if question["type"] == "fill_blank"
                       else "CODE EXAMPLES — HELP ONLY")
    text(reference_label, r.x + 22, layout["reference_label_y"], GOLD, FS)
    reference_box = layout["reference_box"]
    pygame.draw.rect(scr, (21, 31, 39), reference_box, 0, 7)
    pygame.draw.rect(scr, color, reference_box, 1, 7)
    pygame.draw.rect(scr, color, (reference_box.x, reference_box.y,
                                  4, reference_box.h), 0, 7)
    reference_font = fnt(12)
    column_width = (reference_box.w - 20) // 2
    for index, choice in enumerate(choices):
        column = index % 2
        row = index // 2
        choice_x = reference_box.x + 12 + column * (column_width + 8)
        choice_y = reference_box.y + 7 + row * 20
        choice_text = ("%d) " % (index + 1) if question["type"] != "fill_blank"
                       else "") + str(choice)
        choice_lines = wrap(choice_text, reference_font, column_width - 16)
        text(choice_lines[0] if choice_lines else choice_text,
             choice_x, choice_y, CYAN, reference_font)

    feedback = modal["feedback"]
    if feedback is not None:
        status = ("CODE STRIKE LANDED! +%d XP" % feedback["xp_awarded"]
                  if feedback["correct"]
                  else "VIRUS KING COUNTERATTACKS! BYTE BLOCKS THE HIT.")
        status_y = layout["input"].y
        text(status, r.x + 22, status_y,
             GREEN if feedback["correct"] else RED, FS)
        details = (feedback["explanation"] if feedback["correct"] else
                   "Correct answer: %s. %s" %
                   (feedback["correct_answer"], feedback["explanation"]))
        details_font = fnt(13)
        details_clip = pygame.Rect(
            r.x + 22, status_y + 24, r.w - 44,
            max(20, story_quiz_next_rect().y - status_y - 32))
        scr.set_clip(details_clip)
        para(details, details_clip.x, details_clip.y,
             details_clip.w, WHITE, details_font)
        scr.set_clip(None)
        draw_story_button(story_quiz_next_rect(), "NEXT EXCHANGE", color)
        text("ENTER or click Next to continue the fight.",
             r.x + 22, r.bottom - 20, (206, 232, 214), FS)
    else:
        input_box = layout["input"]
        pygame.draw.rect(scr, (21, 31, 39), input_box, 0, 7)
        pygame.draw.rect(scr, color, input_box, 2, 7)
        shown = modal["input"] + ("|" if int(G.t * 2) % 2 == 0 else "")
        text(shown or "Type your code answer here",
             input_box.x + 12, input_box.y + 13,
             WHITE if shown else (125, 149, 158), FS)
        draw_story_button(story_battle_submit_rect(), "THROW CODE", color)
        text("Type the answer and press ENTER to attack.",
             r.x + 22, r.bottom - 20, (206, 232, 214), FS)

def draw_story_battle_result(modal):
    language = modal["language"]
    color = tuple(story_language_data(language)["color"])
    r = panel("The Virus King Wins This Exchange")
    draw_story_battle_scene(modal, story_battle_scene_rect())
    text("THE GUARDIAN NEEDS ONE MORE CODE BREAKTHROUGH",
         r.x + 22, r.y + 216, color, FS)
    para("Byte holds the final portal open. Retry the three-question battle; "
         "earned XP is kept, but answers can change the outcome.",
         r.x + 22, r.y + 242, r.w - 44, WHITE, FS)
    draw_story_button(story_battle_retry_rect(), "RETRY BATTLE", color)
    text("ENTER / SPACE / click to retry  |  ESC to lessons",
         r.x + 22, r.bottom - 20, (206, 232, 214), FS)

def draw_story_coding(modal):
    language = modal["language"]
    topic = story_language_data(language)["topics"][modal["topic"]]
    color = tuple(story_language_data(language)["color"])
    r = panel("Practical Coding")
    text("%s Portal %d — %s" %
         (language, modal["topic"] + 1, topic["topic"]),
         r.x + 22, r.y + 52, color, FS)
    text("INSTRUCTIONS", r.x + 22, r.y + 82, GOLD, FS)
    para(modal["spec"]["prompt"], r.x + 22, r.y + 108,
         r.w - 44, WHITE, fnt(14))
    input_box = story_coding_input_rect()
    pygame.draw.rect(scr, (21, 31, 39), input_box, 0, 7)
    feedback = modal["feedback"]
    edge = color if feedback is None else GREEN if feedback["correct"] else RED
    pygame.draw.rect(scr, edge, input_box, 2, 7)
    code_y = input_box.y + 12
    cursor = modal.get("cursor", len(modal["input"]))
    cursor_y = code_y
    cursor_x = input_box.x + 12
    absolute_index = 0
    cursor_y = None
    scr.set_clip(input_box)
    anchor = modal.get("anchor")
    if anchor is not None:
        selection_start, selection_end = sorted((anchor, modal["cursor"]))
        absolute_offset = 0
        selection_y = input_box.y + 12
        for source_line in modal["input"].split("\n"):
            source_line_end = absolute_offset + len(source_line)
            overlap_start = max(selection_start, absolute_offset)
            overlap_end = min(selection_end, source_line_end)
            if overlap_end > overlap_start:
                local_start = overlap_start - absolute_offset
                local_end = overlap_end - absolute_offset
                left = input_box.x + 12 + fnt(14).size(
                    source_line[:local_start])[0]
                right = input_box.x + 12 + fnt(14).size(
                    source_line[:local_end])[0]
                pygame.draw.rect(scr, (58, 112, 144),
                                 pygame.Rect(left - 2, selection_y - 2,
                                             max(8, right - left + 4),
                                             fnt(14).get_linesize() + 4), 0, 3)
            absolute_offset = source_line_end + 1
            selection_y += fnt(14).get_linesize() + 2
            if selection_y >= input_box.bottom - 8:
                break
    for line in modal["input"].split("\n"):
        for wrapped in wrap(line if line else " ", fnt(14), input_box.w - 24):
            text(wrapped, input_box.x + 12, code_y, CYAN, fnt(14))
            segment_width = fnt(14).size(wrapped[:max(
                0, cursor - absolute_index)])[0] if cursor >= absolute_index else 0
            if cursor_y is None and absolute_index <= cursor <= absolute_index + len(wrapped):
                cursor_x = input_box.x + 12 + segment_width
                cursor_y = code_y
            code_y += fnt(14).get_linesize() + 2
            absolute_index += len(wrapped) + 1
            if code_y >= input_box.bottom - 8:
                break
        if code_y >= input_box.bottom - 8:
            break
    if cursor_y is not None and int(G.t * 2) % 2 == 0:
        pygame.draw.line(scr, WHITE, (cursor_x, cursor_y),
                         (cursor_x, cursor_y + fnt(14).get_linesize()), 2)
    scr.set_clip(None)
    if feedback:
        if feedback["correct"]:
            text("Code check passed! +%d XP" % feedback["xp_awarded"],
                 r.x + 22, r.bottom - 154,
                 GREEN, FS)
            text("Output: " + modal["spec"]["expected_output"],
                 r.x + 22, r.bottom - 128,
                 WHITE, FS)
        else:
            guidance = feedback.get("guidance", [])
            para("Try again. " + "  |  ".join(guidance[:4]),
                 r.x + 22, r.bottom - 154, r.w - 300,
                 RED, FS)
    else:
        text("Edit the code, then run it.", r.x + 22, r.bottom - 154,
             (206, 232, 214), FS)
    label = "CONTINUE" if feedback and feedback["correct"] else "RUN CODE"
    if not (feedback and feedback["correct"]):
        draw_story_button(story_coding_clear_rect(), "CLEAR", (104, 206, 172))
    draw_story_button(story_coding_run_rect(), label, color)
    text("TAB next field  |  ENTER new line  |  CTRL+ENTER run  |  ESC quit",
         r.x + 22, r.bottom - 20, (206, 232, 214), FS)

def draw_story_quiz(modal):
    if modal["topic"] == 4:
        draw_story_battle_quiz(modal)
        return
    language = modal["language"]
    topic = story_language_data(language)["topics"][modal["topic"]]
    question = topic["questions"][modal["question"]]
    color = tuple(story_language_data(language)["color"])
    r = panel("%s Portal %d — %s" %
              (language, modal["topic"] + 1, topic["topic"]))
    progress = story_progress(language)
    current_records = story_attempt_records(progress, modal["topic"])
    current_score = sum(bool(record["correct"]) for record in current_records.values())
    completed_score = sum(sum(bool(answer) for answer in result)
                          for result in progress["topic_results"].values())
    text("PRACTICE QUIZ" if question["type"] == "multiple_choice"
         else "CODING CHALLENGE",
         r.x + 22, r.y + 52, color, FS)
    text("Question %d / 3  |  Language score: %d / 15" %
         (modal["question"] + 1, completed_score + current_score),
         r.x + 22, r.y + 75, GOLD, FS)
    prompt = question["prompt"].replace("____", "________")
    prompt_bottom = para(prompt, r.x + 22, r.y + 100, r.w - 44, WHITE, F)
    feedback = modal["feedback"]
    if question["type"] == "multiple_choice":
        for i, option in enumerate(question["options"]):
            rect = story_question_rect(i)
            fill, edge = (36, 48, 62), color
            if feedback:
                if option in question["answers"]:
                    fill, edge = (25, 75, 58), GREEN
                elif option == feedback.get("selected"):
                    fill, edge = (88, 34, 52), RED
            pygame.draw.rect(scr, fill, rect, 0, 8)
            pygame.draw.rect(scr, edge, rect, 2, 8)
            para("%d) %s" % (i + 1, option), rect.x + 14,
                 rect.y + 12, rect.w - 28, WHITE, FS)
    else:
        if question["type"] == "fill_blank":
            para("Word bank (type your answer; do not tap a choice): " +
                 "   |   ".join(question["bank"]),
                 r.x + 22, r.y + 192, r.w - 44, color, FS)
        input_box = story_quiz_input_rect()
        if question["type"] == "typing":
            input_box.y = prompt_bottom + 16
        else:
            input_box.y = r.y + 258
        pygame.draw.rect(scr, (21, 31, 39), input_box, 0, 7)
        pygame.draw.rect(scr, color if feedback is None else
                         GREEN if feedback["correct"] else RED, input_box, 2, 7)
        shown = modal["input"] + ("|" if feedback is None and int(G.t * 2) % 2 == 0 else "")
        text(shown or "Type your answer here", input_box.x + 12,
             input_box.y + 13, WHITE if shown else (125, 149, 158), FS)
        if question["type"] == "typing":
            text("Choices (for reference only — type your answer):",
                 r.x + 22, input_box.bottom + 12, GOLD, FS)
            choice_font = fnt(12)
            choice_top = input_box.bottom + 38
            column_width = (r.w - 48) // 2
            for index, choice in enumerate(question["choices"]):
                column = index % 2
                row = index // 2
                choice_x = r.x + 22 + column * (column_width + 8)
                choice_y = choice_top + row * 54
                choice_box = pygame.Rect(choice_x, choice_y,
                                         column_width, 46)
                pygame.draw.rect(scr, (31, 43, 52), choice_box, 0, 6)
                pygame.draw.rect(scr, (104, 206, 172), choice_box, 1, 6)
                choice_lines = wrap("%d) %s" % (index + 1, choice),
                                    choice_font, column_width - 16)
                choice_text_y = choice_box.y + 7
                for choice_line in choice_lines[:2]:
                    text(choice_line, choice_box.x + 8, choice_text_y,
                         (206, 232, 214), choice_font)
                    choice_text_y += choice_font.get_linesize()

    if feedback:
        feedback_y = 414
        status = ("Correct! +%d XP" % feedback["xp_awarded"] if feedback["correct"]
                  else "Not quite. Correct answer: %s" % feedback["correct_answer"])
        text(status, r.x + 22, feedback_y,
             GREEN if feedback["correct"] else RED, FS)
        para(feedback["explanation"], r.x + 22, feedback_y + 24,
             r.w - 44, WHITE, FS)
        draw_story_button(story_quiz_next_rect(), "NEXT", color)
        text("One attempt per question. Click Next to continue.",
             r.x + 22, r.bottom - 20, (206, 232, 214), FS)
    elif question["type"] == "multiple_choice":
        text("Tap an answer or press 1-4. One attempt only.",
             r.x + 22, r.bottom - 26, (206, 232, 214), FS)
    else:
        draw_story_button(story_quiz_submit_rect(), "SUBMIT ANSWER", color)
        text("Type your answer and tap Submit. Tapping choices will not fill the answer.",
             r.x + 22, r.bottom - 26, (206, 232, 214), FS)

def draw_story_results(modal):
    language = modal["language"]
    total, by_topic, by_type = story_results_summary(language)
    r = panel("%s — Final Results" % language)
    text("Language score: %d / 15" % total, r.x + 22, r.y + 56, GOLD, FB)
    progress = story_progress(language)
    level_gain = max(0, lvl() - progress["run_start_level"])
    text("XP gained: %d  |  Levels gained: %d  |  Code crystals: %d" %
         (progress["xp_earned"], level_gain, progress["crystals_earned"]),
         r.x + 22, r.y + 92, WHITE, FS)
    text("TOPIC SUMMARY", r.x + 22, r.y + 132, CYAN, FS)
    for i, (topic, score) in enumerate(by_topic):
        text("%s" % topic, r.x + 28, r.y + 158 + i * 26, WHITE, FS)
        text("%d / 3" % score, r.right - 90, r.y + 158 + i * 26,
             GREEN if score == 3 else RED if score == 0 else GOLD, FS)
    type_y = r.y + 300
    text("QUESTION TYPE SUMMARY", r.x + 22, type_y, CYAN, FS)
    labels = {
        "multiple_choice": "Multiple choice",
        "fill_blank": "Fill in the blanks",
        "typing": "Typing",
    }
    for i, question_type in enumerate(STORY_QUESTION_TYPES):
        correct, count = by_type[question_type]
        text("%s: %d / %d" % (labels[question_type], correct, count),
             r.x + 28, type_y + 25 + i * 24, WHITE, FS)
    text("BADGE EARNED: %s Kingdom Restorer" % language,
         r.x + 22, r.y + 438, GOLD, FS)
    actions = story_results_button_rects()
    draw_story_button(actions["replay"], "REPLAY THIS LANGUAGE", GOLD)
    draw_story_button(actions["languages"], "CHOOSE LANGUAGE", CYAN)
    draw_story_button(actions["menu"], "MAIN MENU", CYAN)

def leave_portal_obby():
    if G.obby_mode == "story":
        language, topic_index = G.story_language, G.story_topic_index
        G.touch_left = G.touch_right = G.touch_jump = False
        open_story_lesson(language, topic_index)
        return
    G.state = "play"
    G.px = PX(G.obby_idx)
    G.py = 420
    G.vx = G.vy = 0
    G.gnd = True
    G.near = ("p", G.obby_idx)
    G.camx = max(-60, min(WORLD_WIDTH - W, G.px - W * .4))
    G.camy = 40
    G.touch_left = G.touch_right = G.touch_jump = False

def update_portal_obby(dt):
    layout = G.story_stage if G.obby_mode == "story" else PORTAL_OBBIES[G.obby_idx]
    if G.obby_mode == "story":
        G.obby_stage_elapsed += dt
    keys = pygame.key.get_pressed()
    direction = ((keys[pygame.K_d] or keys[pygame.K_RIGHT] or G.touch_right) -
                 (keys[pygame.K_a] or keys[pygame.K_LEFT] or G.touch_left))
    speed = 400 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 260
    G.obby_vx += (direction * speed - G.obby_vx) * min(1, dt * (14 if G.obby_gnd else 6))
    if direction:
        G.face = 1 if direction > 0 else -1
    if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP] or G.touch_jump) and G.obby_gnd:
        G.obby_vy = -720
        G.obby_gnd = False
        play_sound("jump")
    G.touch_jump = False

    previous_y = G.obby_y
    G.obby_x += G.obby_vx * dt
    G.obby_vy += 1800 * dt
    G.obby_y += G.obby_vy * dt
    G.obby_gnd = False
    if G.obby_vy >= 0:
        platforms = layout["platforms"]
        active_platforms = None
        if G.obby_mode == "story":
            platforms, active_platforms = story_platform_positions(layout)
        for platform_index, (x, y, width, _) in enumerate(platforms):
            if active_platforms is not None and platform_index not in active_platforms:
                continue
            if x - 12 < G.obby_x < x + width + 12 and previous_y <= y + 2 and G.obby_y >= y:
                G.obby_y, G.obby_vy, G.obby_gnd = y, 0, True
                if G.obby_mode == "story" and platform_index in layout["checkpoints"]:
                    checkpoint = (x + 24, y)
                    if checkpoint != G.obby_checkpoint:
                        G.obby_checkpoint = checkpoint
                        G.obby_cp_index = layout["checkpoints"].index(platform_index) + 1
                        G.story_stage_beat = (
                            "Checkpoint secured! Byte says the beacon is close—keep "
                            "following its signal.")
                        toast("Checkpoint saved.")
                break

    if G.obby_y > H + 100 or G.obby_x < 0:
        G.obby_x, G.obby_y = G.obby_checkpoint
        G.obby_vx = G.obby_vy = 0
        G.obby_gnd = True
        G.obby_camx = max(0, G.obby_x - W * .35)
        play_sound("fall")
        toast("You fell! Back to the last checkpoint.")

    if abs(G.obby_vx) > 20 and G.obby_gnd:
        G.ph += dt * abs(G.obby_vx) * .045

    if G.obby_mode in ("language", "story"):
        obstacles = story_hazard_positions(layout) if G.obby_mode == "story" else G.obby_obstacles
        for obstacle_x, obstacle_y, obstacle_w, _ in obstacles:
            if (obstacle_x - 16 < G.obby_x < obstacle_x + obstacle_w + 16
                    and obstacle_y - 52 < G.obby_y < obstacle_y + 12):
                G.obby_x, G.obby_y = G.obby_checkpoint
                G.obby_vx = G.obby_vy = 0
                G.obby_gnd = True
                G.obby_camx = max(0, G.obby_x - W * .35)
                toast("Hazard avoided. Back to the last checkpoint.")
                return

    if G.obby_mode == "story":
        for crystal_index, (crystal_x, crystal_y) in enumerate(layout["crystals"]):
            if (crystal_index not in G.story_stage_collected
                    and abs(G.obby_x - crystal_x) < 28
                    and abs(G.obby_y - crystal_y) < 58):
                G.story_stage_collected.add(crystal_index)
                language, topic_index = G.story_language, G.story_topic_index
                crystal_count = len(G.story_stage_collected)
                if crystal_count == 3:
                    G.story_stage_beat = (
                        "All three code crystals are charged. Reach the portal to restore "
                        "this beacon and carry its signal back to the Core.")
                else:
                    G.story_stage_beat = (
                        "Signal crystal %d / 3 recovered. Byte can hear the beacon growing "
                        "stronger—keep moving toward it." % crystal_count)
                progress = story_progress(language)
                stage_key = str(topic_index)
                collected = progress["stage_crystals"].setdefault(stage_key, [])
                if crystal_index not in collected:
                    collected.append(crystal_index)
                claim_key = "%d:%d" % (topic_index, crystal_index)
                crystal_xp = layout["crystal_xp"]
                if claim_key not in progress["claimed_crystals"]:
                    progress["claimed_crystals"].append(claim_key)
                    progress["crystals_earned"] = progress.get("crystals_earned", 0) + 1
                    progress["xp_earned"] += crystal_xp
                    progress["topic_xp"][stage_key] = (
                        progress["topic_xp"].get(stage_key, 0) + crystal_xp)
                    old_level = lvl()
                    gain(crystal_xp)
                else:
                    old_level = lvl()
                save()
                play_sound("crystal")
                level_message = (" | LEVEL UP! Level %d" % lvl()
                                 if lvl() > old_level else "")
                toast("Crystal collected! +%d XP (%d / 3)%s" %
                      (crystal_xp, len(G.story_stage_collected), level_message))
    else:
        progress = G.S.setdefault("portal_crystals", {})
        crystal_key = "%s:%d" % (G.obby_mode, G.obby_idx)
        collected = progress.setdefault(crystal_key, [])
        for crystal_index, (crystal_x, crystal_y) in enumerate(layout["crystals"]):
            if (crystal_index not in G.obby_crystal_collected
                    and abs(G.obby_x - crystal_x) < 28
                    and abs(G.obby_y - crystal_y) < 58):
                G.obby_crystal_collected.add(crystal_index)
                collected.append(crystal_index)
                old_level = lvl()
                gain(5)
                save()
                play_sound("crystal")
                level_message = (" | LEVEL UP! Level %d" % lvl()
                                 if lvl() > old_level else "")
                toast("Crystal collected! +5 XP (%d / 3)%s" %
                      (len(G.obby_crystal_collected), level_message))

    goal_x, goal_y = layout["goal"]
    if abs(G.obby_x - goal_x) < 28 and abs(G.obby_y - goal_y) < 52:
        if G.obby_mode == "story":
            if len(G.story_stage_collected) < 3:
                toast("Collect all 3 code crystals to open this portal.")
                return
            language, topic_index = G.story_language, G.story_topic_index
            G.obby_vx = G.obby_vy = 0
            story_progress(language).setdefault("topic_difficulty", {})[
                str(topic_index)] = layout["difficulty"]["id"]
            save()
            start_story_quiz(language, topic_index)
            toast("Beacon restored! The %s quiz will confirm its signal." %
                  story_language_data(language)["topics"][topic_index]["topic"])
            return
        if G.obby_mode == "language":
            language_id = G.language_id
            G.obby_vx = G.obby_vy = 0
            G.state = "play"
            start_language_quiz(language_id)
            toast("Portal entered! Answer the %s quiz." % LANGUAGE_PATHS[language_id]["name"])
            return
        cleared = G.S.setdefault("portal_obby_clear", [])
        if G.obby_idx not in cleared:
            cleared.append(G.obby_idx)
            save()
        leave_portal_obby()
        toast("%s cleared! Press E to enter the portal." % layout["name"])
        return

    camera_target = max(0, min(layout["width"] - W, G.obby_x - W * .35))
    G.obby_camx += (camera_target - G.obby_camx) * min(1, dt * 5)

def update(dt):
    k = pygame.key.get_pressed()
    f = ((k[pygame.K_d] or k[pygame.K_RIGHT] or G.touch_right) -
         (k[pygame.K_a] or k[pygame.K_LEFT] or G.touch_left))
    sp = 400 if k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT] else 260
    G.vx += (f * sp - G.vx) * min(1, dt * (14 if G.gnd else 6))
    if f: G.face = 1 if f > 0 else -1
    if (k[pygame.K_SPACE] or k[pygame.K_w] or k[pygame.K_UP] or G.touch_jump) and G.gnd:
        G.vy = -720; G.gnd = False
        play_sound("jump")
    G.touch_jump = False
    pv = G.py; G.px += G.vx * dt; G.vy += 1800 * dt; G.py += G.vy * dt; G.gnd = False
    if G.vy >= 0:
        for x, y, w in P:
            if x - 6 < G.px < x + w + 6 and pv <= y + 2 and G.py >= y:
                G.py, G.vy, G.gnd = y, 0, True
                if x >= 5950 and G.cp[0] < 6200: G.cp = (6150, 420); toast("Cloud Citadel checkpoint saved")
                elif x >= 4000 and G.cp[0] < 4200: G.cp = (4150, 420); toast("Firewall Frontier checkpoint saved")
                elif x >= 3100 and G.cp[0] < 3200: G.cp = (3150, 420); toast("Checkpoint saved")
                elif 1560 <= x < 2500 and G.cp[0] < 1600: G.cp = (1620, 420); toast("Checkpoint saved")
                break
    for gate, required_quest in MAP_GATES:
        if G.px > gate and required_quest not in G.S["done"]:
            G.px = gate - 10
            G.vx = 0
            warnings = G.S.setdefault("gate_warnings", [])
            if required_quest not in warnings:
                warnings.append(required_quest)
                toast("The gateway is sealed. Complete %s first." % CH[required_quest]["n"])
                save()
            break
    G.px = max(-20, min(WORLD_WIDTH - 10, G.px))
    if G.py > 800:
        G.px, G.py = G.cp
        G.vx = G.vy = 0
        play_sound("fall")
        toast("You fell! Back to the checkpoint.")
    region = 0 if G.px < MAP_GATES[0][0] else 1 if G.px < MAP_GATES[1][0] else 2
    seen_maps = G.S.setdefault("map_seen", [])
    if region > 0 and region - 1 not in seen_maps:
        seen_maps.append(region - 1)
        save()
        msg(MAP_NAMES[region], MAP_STORY[region - 1])
    if abs(G.vx) > 20 and G.gnd: G.ph += dt * abs(G.vx) * .045
    for i, (x, y) in enumerate(ORBS):
        if i not in G.S["orbs"] and math.hypot(G.px - x, G.py - 50 - y) < 40: G.S["orbs"].append(i); gain(10); toast("+10 XP")
    G.near = ("b",) if abs(G.px - BX) < 90 else None
    for i in range(len(CH)):
        if abs(G.px - PX(i)) < 55 and 380 < G.py < 430: G.near = ("p", i)
    G.camx += (max(-60, min(WORLD_WIDTH - W, G.px - W * .4)) - G.camx) * min(1, dt * 5); G.camy += ((G.py - 380) - G.camy) * min(1, dt * 3)
def dev_key(e):
    if e.key == pygame.K_F2: G.px, G.py = 1620, 420
    elif e.key == pygame.K_F3: gain(100)
    elif e.key == pygame.K_F5: G.px, G.py = 3150, 420
    elif e.key == pygame.K_F6: G.px, G.py = 900, 700
    elif e.key == pygame.K_F4:
        i = 0
        while i in G.S["done"]: i += 1
        if i < len(CH): G.S["done"].append(i); G.S["won"] = G.S["won"] or i == 5; gain(CH[i]["xp"])
    G.vx = G.vy = 0
def login_screen():
    scr.blit(SKY, (0, 0)); draw_particles(); t = G.t
    for sx, sy, s in STARS: scr.fill(WHITE, (sx, sy, s, s))
    hero_x, hero_y = 244, 482
    title_image = fit_image(LOGIN_TITLE_IMAGE, 400, 56, key="login_title")
    scr.blit(title_image, (hero_x - title_image.get_width() // 2, 112))
    text("Learn coding", 60, 190, WHITE, fnt(32, True))
    text("through play.", 60, 230, CYAN, fnt(32, True))
    para("Complete quests, earn XP, and unlock new characters.",
         62, 294, 300, (224, 238, 232), F)

    pygame.draw.circle(scr, (24, 40, 52), (hero_x, 426), 88)
    pygame.draw.circle(scr, (104, 206, 172), (hero_x, 426), 88, 2)
    pygame.draw.circle(scr, GOLD, (hero_x, 426), 73, 1)
    for x, y, color in ((168, 389, GOLD), (315, 380, CYAN), (324, 463, GREEN)):
        pygame.draw.circle(scr, color, (x, y), 5)
        pygame.draw.circle(scr, color, (x, y), 10, 1)
    platform = pygame.Rect(hero_x - 76, hero_y + 4, 152, 14)
    pygame.draw.rect(scr, (44, 58, 72), platform, 0, 8)
    pygame.draw.rect(scr, (104, 206, 172), platform, 1, 8)
    hero(hero_x, hero_y, t, False, False, False, "guardian")

    layout = login_layout()
    r = layout["card"]
    pygame.draw.rect(scr, (13, 23, 31), (r.x + 5, r.y + 6, r.w, r.h), 0, 16)
    pygame.draw.rect(scr, (44, 58, 72), r, 0, 16)
    pygame.draw.rect(scr, GOLD, r, 2, 16)
    content_x = layout["username"].x
    content_width = layout["username"].w
    title = "Welcome, Player!" if WEB else (
        "Create your account" if G.auth_mode == "register" else "Welcome back")
    subtitle = ("Play now. Your progress is saved in this browser." if WEB else
                "Save your progress and keep playing." if G.auth_mode == "register"
                else "Sign in to continue your coding adventure.")
    text(title, content_x, r.y + 25, WHITE, fnt(25, True))
    text(subtitle, content_x, r.y + 61, (206, 232, 214), FS)

    if WEB:
        button = layout["guest"]
        pygame.draw.rect(scr, (62, 116, 96), button, 0, 8)
        pygame.draw.rect(scr, CYAN, button, 2, 8)
        rendered = FS.render("PLAY NOW", True, WHITE)
        scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                            button.centery - rendered.get_height() // 2))
        return

    user_rect = layout["username"]
    text("Username", user_rect.x, user_rect.y - 24, WHITE, FS)
    pygame.draw.rect(scr, (21, 31, 39), user_rect, 0, 7)
    pygame.draw.rect(scr, GOLD if G.auth_focus == "username" else (104, 206, 172), user_rect, 2, 7)
    user_value = G.auth_user or ("Enter username" if G.auth_focus != "username" else "")
    user_color = WHITE if G.auth_user else (143, 162, 171)
    if G.auth_focus == "username" and int(t * 2) % 2 == 0:
        user_value += "|"
    text(user_value, user_rect.x + 12, user_rect.y + (user_rect.h - FS.get_height()) // 2,
         user_color, FS)

    pass_rect, reveal_rect = layout["password"], layout["reveal"]
    text("Password", pass_rect.x, pass_rect.y - 24, WHITE, FS)
    pygame.draw.rect(scr, (21, 31, 39), pass_rect, 0, 6)
    pygame.draw.rect(scr, GOLD if G.auth_focus == "password" else (104, 206, 172), pass_rect, 2, 6)
    visible_password = G.auth_pass if G.auth_show_password else "*" * len(G.auth_pass)
    password_text = visible_password or ("Enter password" if G.auth_focus != "password" else "")
    if G.auth_focus == "password" and int(t * 2) % 2 == 0:
        password_text += "|"
    scr.set_clip(pygame.Rect(pass_rect.x + 8, pass_rect.y + 2, pass_rect.w - 16, pass_rect.h - 4))
    text(password_text, pass_rect.x + 10, pass_rect.y + (pass_rect.h - FS.get_height()) // 2,
         WHITE if visible_password else (143, 162, 171), FS)
    scr.set_clip(None)
    pygame.draw.rect(scr, (21, 31, 39), reveal_rect, 0, 6)
    pygame.draw.rect(scr, GOLD if G.auth_show_password else (104, 206, 172),
                     reveal_rect, 2, 6)
    eye = pygame.Rect(17, 26, 32, 17)
    eye.center = reveal_rect.center
    pygame.draw.ellipse(scr, CYAN, eye, 2)
    pygame.draw.circle(scr, CYAN, eye.center, 4)
    pygame.draw.circle(scr, WHITE, eye.center, 1)
    if not G.auth_show_password:
        pygame.draw.line(scr, GOLD, (eye.left + 2, eye.bottom - 1),
                         (eye.right - 2, eye.top + 1), 2)
    text("TAB switches fields     ENTER submits", content_x, r.y + 270, CYAN, FTAG)
    mode_rect = layout["mode"]
    mode_label = ("New here? Create an account" if G.auth_mode == "login"
                  else "Already have an account? Sign in")
    rendered = FS.render(mode_label, True, CYAN)
    scr.blit(rendered, (mode_rect.centerx - rendered.get_width() // 2,
                        mode_rect.centery - rendered.get_height() // 2))
    if G.auth_error:
        para(G.auth_error, content_x, r.y + 336, content_width, RED, FS)
    elif G.auth_notice and G.auth_mode == "login":
        para(G.auth_notice, content_x, r.y + 336, content_width, GREEN, FS)
    elif G.auth_mode == "register":
        text("Password must be at least 8 characters.",
             content_x, r.y + 336, (206, 232, 214), FS)
    button = layout["submit"]
    pygame.draw.rect(scr, (62, 116, 96), button, 0, 8)
    pygame.draw.rect(scr, CYAN, button, 2, 8)
    label = "CREATE ACCOUNT" if G.auth_mode == "register" else "SIGN IN"
    rendered = FS.render(label, True, WHITE)
    scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                        button.centery - rendered.get_height() // 2))

def dashboard_button(rect, label, active=False):
    pygame.draw.rect(scr, (66, 122, 100) if active else (34, 46, 58), rect, 0, 8)
    pygame.draw.rect(scr, GOLD if active else (104, 206, 172), rect, 2, 8)
    rendered = FS.render(label, True, GOLD if active else WHITE)
    scr.blit(rendered, (rect.centerx - rendered.get_width() // 2,
                        rect.centery - rendered.get_height() // 2))

def ui_point(x, y):
    offset_y = (H - 1125 * .5) / 2
    return round(x * .5), round(y * .5 + offset_y)

def ui(x, y, width, height):
    left, top = ui_point(x, y)
    return pygame.Rect(left, top, max(1, round(width * .5)),
                       max(1, round(height * .5)))

def dashboard_layout():
    return {
        "profile": ui(70, 35, 127, 130),
        "settings": ui(1800, 28, 108, 109),
        "sidebar": ui(68, 210, 300, 740),
        "home": ui(92, 240, 256, 88),
        "progress": ui(92, 347, 256, 89),
        "character_label": ui(95, 565, 245, 30),
        "frame": ui(95, 598, 245, 245),
        "customize": ui(107, 864, 216, 52),
        "enter": ui(585, 985, 602, 92),
    }

def home_layout():
    layout = dashboard_layout()
    layout.update({
        "main": ui(393, 210, 1039, 740),
        "players": ui(1475, 210, 440, 740),
        "story_button": ui(780, 808, 300, 82),
        "player_rows": [
            ui(1493, 298 + index * 107, 395, 92)
            for index in range(5)
        ],
    })
    return layout

def progress_layout():
    layout = dashboard_layout()
    rows = []
    for index in range(5):
        y = 365 + index * 88
        rows.append({
            "language": ui(421, y, 250, 28),
            "theme": ui(421, y + 34, 245, 24),
            "portals": ui(680, y, 105, 28),
            "bar": ui(680, y + 47, 150, 16),
            "accuracy": ui(895, y + 16, 200, 30),
            "xp": ui(1165, y + 16, 80, 30),
            "divider": (ui_point(421, y + 82), ui_point(1280, y + 82)),
        })
    layout.update({
        "main": ui(393, 210, 917, 740),
        "summary": ui(1335, 210, 580, 740),
        "rows": rows,
        "level_label": ui(421, 842, 835, 34),
        "level_bar": ui(421, 883, 835, 26),
        "badge_tiles": [
            {"tile": ui(1400, 535, 115, 115),
             "label": ui(1385, 654, 145, 24)},
            {"tile": ui(1560, 535, 115, 115),
             "label": ui(1545, 654, 145, 24)},
            {"tile": ui(1720, 535, 115, 115),
             "label": ui(1705, 654, 145, 24)},
            {"tile": ui(1480, 720, 115, 115),
             "label": ui(1465, 839, 145, 24)},
            {"tile": ui(1640, 720, 115, 115),
             "label": ui(1625, 839, 145, 24)},
        ],
    })
    return layout

def fit_ui_label(value, font, max_width):
    label = str(value)
    if font.size(label)[0] <= max_width:
        return label
    suffix = "..."
    while label and font.size(label + suffix)[0] > max_width:
        label = label[:-1]
    return label.rstrip() + suffix

def dashboard_text(value, rect, color=WHITE, font=FS, align="left"):
    label = fit_ui_label(value, font, max(1, rect.w - 4))
    rendered = font.render(label, True, color)
    if align == "center":
        position = (rect.centerx - rendered.get_width() // 2,
                    rect.centery - rendered.get_height() // 2)
    elif align == "right":
        position = (rect.right - rendered.get_width(),
                    rect.centery - rendered.get_height() // 2)
    else:
        position = (rect.x, rect.centery - rendered.get_height() // 2)
    old_clip = scr.get_clip()
    scr.set_clip(rect)
    scr.blit(rendered, position)
    scr.set_clip(old_clip)

_UI_IMAGE_CACHE = {}
_UI_SCALED_IMAGE_CACHE = {}

def load_ui_image(filename):
    if filename not in _UI_IMAGE_CACHE:
        path = os.path.join(ASSET_DIR, "ui", filename)
        if not os.path.isfile(path):
            _UI_IMAGE_CACHE[filename] = None
        else:
            try:
                _UI_IMAGE_CACHE[filename] = pygame.image.load(path).convert_alpha()
            except (pygame.error, OSError) as error:
                print("Could not load optional UI image %s: %s" %
                      (path, error), file=sys.stderr)
                _UI_IMAGE_CACHE[filename] = None
    return _UI_IMAGE_CACHE[filename]

def draw_ui_image(filename, rect):
    image = load_ui_image(filename)
    if image is None:
        return False
    key = (filename, rect.size)
    scaled = _UI_SCALED_IMAGE_CACHE.get(key)
    if scaled is None:
        scaled = pygame.transform.smoothscale(image, rect.size)
        _UI_SCALED_IMAGE_CACHE[key] = scaled
    scr.blit(scaled, rect.topleft)
    return True

def draw_dashboard_panel(rect, color=(35, 48, 61)):
    pygame.draw.rect(scr, color, rect, 0, 8)
    pygame.draw.rect(scr, (104, 206, 172), rect, 2, 8)

def draw_dashboard_button(rect, label, active=False, font=FS):
    hovered = False
    try:
        hovered = rect.collidepoint(logical_pos(pygame.mouse.get_pos()))
    except Exception:
        hovered = False
    fill = ((78, 152, 124) if hovered else (61, 122, 96)) if active else (
        (43, 82, 68) if hovered else (19, 51, 43))
    border = GOLD if (active or hovered) else (104, 206, 172)
    pygame.draw.rect(scr, fill, rect, 0, 8)
    pygame.draw.rect(scr, border, rect, 2, 8)
    dashboard_text(label, rect.inflate(-10, -2),
                   GOLD, font, "center")

def draw_gear(rect):
    pygame.draw.rect(scr, (18, 40, 37), rect, 0, 9)
    pygame.draw.rect(scr, (126, 177, 151), rect, 2, 9)
    cx, cy = rect.center
    outer = max(8, rect.w // 4)
    for angle in range(0, 360, 45):
        radians = math.radians(angle)
        start = (round(cx + math.cos(radians) * (outer - 2)),
                 round(cy + math.sin(radians) * (outer - 2)))
        end = (round(cx + math.cos(radians) * (outer + 4)),
               round(cy + math.sin(radians) * (outer + 4)))
        pygame.draw.line(scr, (163, 197, 165), start, end, 4)
    pygame.draw.circle(scr, (163, 197, 165), (cx, cy), outer, 4)
    pygame.draw.circle(scr, (18, 40, 37), (cx, cy), max(3, outer // 3))

def draw_character_avatar(rect, character_id=None, background=(91, 135, 156)):
    pygame.draw.rect(scr, background, rect)
    character_id = character_id or G.S.get("character", "guardian")
    character = next((item for item in CHARACTERS
                      if item["id"] == character_id), CHARACTERS[0])
    image = character_image(character)
    if image is not None:
        image = fit_image(image, max(1, rect.w - 8), max(1, rect.h - 8),
                          False, "dashboard-avatar-" + character["id"])
        scr.blit(image, (rect.centerx - image.get_width() // 2,
                         rect.bottom - image.get_height() - 4))
    pygame.draw.rect(scr, (104, 206, 172), rect, 1)

def draw_character_frame(rect):
    inner = rect.inflate(-18, -18)
    pygame.draw.rect(scr, (91, 60, 33), inner, 0, 2)
    if draw_ui_image("frame.png", rect):
        return
    gold = (242, 190, 65)
    light_gold = (255, 222, 113)
    dark_gold = (88, 52, 22)
    pygame.draw.rect(scr, dark_gold, rect, 0, 2)
    pygame.draw.rect(scr, gold, rect.inflate(-5, -5), 2, 1)
    pygame.draw.rect(scr, dark_gold, rect.inflate(-12, -12), 2, 1)
    pygame.draw.rect(scr, gold, rect.inflate(-16, -16), 1, 1)
    corner = max(10, rect.w // 7)
    for x in (rect.left + 2, rect.right - corner - 2):
        for y in (rect.top + 2, rect.bottom - corner - 2):
            ornament = pygame.Rect(x, y, corner, corner)
            pygame.draw.rect(scr, light_gold, ornament, 0, 1)
            pygame.draw.rect(scr, dark_gold, ornament.inflate(-4, -4), 2, 1)
            pygame.draw.line(scr, dark_gold, ornament.topleft,
                             ornament.bottomright, 2)
            pygame.draw.line(scr, dark_gold, ornament.topright,
                             ornament.bottomleft, 2)
    for cy in (rect.top + corner + 1, rect.bottom - corner - 2):
        pygame.draw.rect(scr, gold,
                         pygame.Rect(rect.centerx - 7, cy, 14, 6), 0, 1)
        pygame.draw.rect(scr, dark_gold,
                         pygame.Rect(rect.centerx - 3, cy + 1, 6, 4), 1, 1)
    for cx in (rect.left + corner, rect.right - corner - 3):
        pygame.draw.rect(scr, gold,
                         pygame.Rect(cx, rect.centery - 6, 6, 12), 0, 1)
        pygame.draw.rect(scr, dark_gold,
                         pygame.Rect(cx + 1, rect.centery - 3, 4, 6), 1, 1)

def draw_character_in_frame(rect, character_id=None):
    character_id = character_id or G.S.get("character", "guardian")
    character = next((item for item in CHARACTERS
                      if item["id"] == character_id), CHARACTERS[0])
    image = character_image(character)
    if image is None:
        return
    image = fit_image(image, max(1, rect.w - 10), max(1, rect.h - 8),
                      False, "dashboard-frame-" + character["id"])
    scr.blit(image, (rect.centerx - image.get_width() // 2,
                     rect.bottom - image.get_height() - 4))

def draw_medal_fallback(rect, rank):
    medal_colors = {
        1: ((255, 214, 87), (178, 115, 25)),
        2: ((235, 239, 242), (113, 127, 142)),
        3: ((210, 133, 57), (119, 68, 30)),
    }
    bright, shade = medal_colors[rank]
    cx, cy = rect.center
    ribbon = pygame.Rect(cx - rect.w // 6, cy + rect.h // 5,
                         rect.w // 3, rect.h // 2)
    pygame.draw.polygon(scr, (159, 44, 49), [
        (ribbon.left, ribbon.top), (ribbon.right, ribbon.top),
        (ribbon.right + 3, ribbon.bottom), (cx, ribbon.bottom - 3),
        (ribbon.left - 3, ribbon.bottom)])
    pygame.draw.circle(scr, shade, (cx, cy - rect.h // 8),
                       max(4, rect.w // 3))
    pygame.draw.circle(scr, bright, (cx, cy - rect.h // 8),
                       max(3, rect.w // 3 - 2))
    label_font = fnt(max(8, rect.w // 3), True)
    rendered = label_font.render(str(rank), True, shade)
    scr.blit(rendered, (cx - rendered.get_width() // 2,
                        cy - rect.h // 8 - rendered.get_height() // 2))

def draw_badge_fallback(rect, language):
    styles = {
        "Java": ((240, 183, 41), "star"),
        "Python": ((222, 75, 75), "heart"),
        "HTML": ((86, 190, 96), "leaf"),
        "JavaScript": ((183, 193, 205), "crown"),
        "CSS": ((244, 192, 52), "bolt"),
    }
    color, symbol = styles[language]
    cx, cy = rect.center
    radius = max(8, min(rect.w, rect.h) // 3)
    pygame.draw.polygon(scr, color, [
        (cx - radius // 2, cy + radius // 2),
        (cx - radius // 3, rect.bottom - 2),
        (cx, cy + radius // 2),
        (cx + radius // 3, rect.bottom - 2),
        (cx + radius // 2, cy + radius // 2),
    ])
    pygame.draw.circle(scr, (92, 68, 27), (cx, cy), radius + 1)
    pygame.draw.circle(scr, color, (cx, cy), radius)
    pygame.draw.circle(scr, (255, 232, 153), (cx, cy), radius - 3, 1)
    if symbol == "star":
        points = []
        for index in range(10):
            angle = math.radians(-90 + index * 36)
            point_radius = radius * (.68 if index % 2 == 0 else .31)
            points.append((round(cx + math.cos(angle) * point_radius),
                           round(cy + math.sin(angle) * point_radius)))
        pygame.draw.polygon(scr, (255, 241, 180), points)
    elif symbol == "heart":
        pygame.draw.circle(scr, (255, 218, 210),
                           (cx - 3, cy - 2), max(2, radius // 4))
        pygame.draw.circle(scr, (255, 218, 210),
                           (cx + 3, cy - 2), max(2, radius // 4))
        pygame.draw.polygon(scr, (255, 218, 210), [
            (cx - 6, cy), (cx + 6, cy), (cx, cy + 8)])
    elif symbol == "leaf":
        pygame.draw.ellipse(scr, (215, 255, 204),
                            (cx - radius // 2, cy - radius // 3,
                             radius, radius // 2))
        pygame.draw.line(scr, (68, 122, 52), (cx - 3, cy + 3),
                         (cx + 5, cy - 4), 1)
    elif symbol == "crown":
        pygame.draw.polygon(scr, (244, 247, 252), [
            (cx - 8, cy + 5), (cx - 7, cy - 5), (cx - 2, cy),
            (cx, cy - 7), (cx + 3, cy), (cx + 8, cy - 5),
            (cx + 7, cy + 5)])
    else:
        pygame.draw.polygon(scr, (255, 249, 207), [
            (cx + 2, cy - 9), (cx - 4, cy + 1), (cx, cy + 1),
            (cx - 2, cy + 9), (cx + 5, cy - 2), (cx + 1, cy - 2)])

def home_settings_rect():
    return dashboard_layout()["settings"]

def obby_settings_rect():
    return pygame.Rect(W - 108, 72, 90, 32)

def settings_option_rects():
    return {
        "music": ui(627, 404, 774, 94),
        "sfx": ui(627, 562, 774, 94),
        "back": ui(479, 758, 366, 94),
        "logout": ui(1170, 758, 365, 94),
    }

def toggle_setting(name):
    settings = G.S.setdefault("settings", {})
    settings[name] = not settings.get(name, True)
    save()
    if name == "sfx":
        if not settings[name] and G.M.get("k") == "story_intro":
            stop_story_voice()
        elif settings[name] and G.M.get("k") == "story_intro":
            start_story_voice(G.M["scene"])

def open_settings():
    G.M = {"k": "settings"}
    if G.state == "obby":
        G.touch_left = G.touch_right = G.touch_jump = False

def sign_out():
    save()
    stop_boss_defeat_sound()
    G.M = {}
    G.state = "login"
    G.story_mode = False
    G.auth_user = ""
    G.auth_pass = ""
    G.auth_focus = "username"
    G.auth_mode = "login"
    G.auth_show_password = False
    G.auth_error = ""
    G.auth_backspace_held = False
    set_text_input(False)

def dashboard_frame(active):
    layout = dashboard_layout()
    scr.blit(SKY, (0, 0))
    for sx, sy, size in STARS:
        scr.fill((244, 240, 226), (sx, sy, size, size))
    for sx, sy, size in ((226, 52, 4), (470, 43, 3), (815, 58, 4),
                         (932, 99, 5), (596, 105, 3), (357, 91, 2)):
        pygame.draw.line(scr, (220, 229, 220),
                         (sx - size, sy), (sx + size, sy), 1)
        pygame.draw.line(scr, (220, 229, 220),
                         (sx, sy - size), (sx, sy + size), 1)
        pygame.draw.circle(scr, WHITE, (sx, sy), 1)

    pygame.draw.rect(scr, (20, 45, 43), layout["sidebar"], 0, 9)
    pygame.draw.rect(scr, (104, 206, 172), layout["sidebar"], 2, 9)
    profile = layout["profile"]
    draw_character_avatar(profile)
    dashboard_text(G.name, ui(212, 76, 420, 50), WHITE, fnt(22, True))
    dashboard_text("Lv.%d" % lvl(), ui(212, 143, 115, 32),
                   (238, 242, 226), FTAG)
    dashboard_text("%dxp" % G.S.get("xp", 0), ui(275, 143, 150, 32),
                   GOLD, FTAG)
    if active in ("home", "progress"):
        draw_gear(layout["settings"])

    draw_dashboard_button(layout["home"], "HOME", active == "home", fnt(18, True))
    draw_dashboard_button(layout["progress"], "PROGRESS",
                          active == "progress", fnt(17, True))
    dashboard_text("YOUR CHARACTER", layout["character_label"],
                   GOLD, FTAG, "center")
    frame = layout["frame"]
    draw_character_frame(frame)
    inside = frame.inflate(-34, -34)
    draw_character_in_frame(inside)
    draw_dashboard_button(layout["customize"], "CUSTOMIZE",
                          False, FTAG)
    draw_dashboard_button(layout["enter"], "ENTER KINGDOM",
                          True, fnt(22, True))
    return layout

def draw_gradient_row(rect, top_color, bottom_color):
    pygame.draw.rect(scr, bottom_color, rect, 0, 7)
    inner = rect.inflate(-2, -2)
    if inner.h <= 0:
        return
    old_clip = scr.get_clip()
    scr.set_clip(inner)
    for offset in range(inner.h):
        amount = offset / max(1, inner.h - 1)
        color = tuple(round(top_color[i] * (1 - amount) +
                            bottom_color[i] * amount) for i in range(3))
        pygame.draw.line(scr, color, (inner.left, inner.y + offset),
                         (inner.right - 1, inner.y + offset))
    scr.set_clip(old_clip)
    pygame.draw.rect(scr, (114, 147, 125), rect, 1, 7)

def draw_top_player_row(rect, rank, player):
    gradients = {
        1: ((255, 197, 74), (219, 126, 35)),
        2: ((238, 241, 243), (139, 151, 162)),
        3: ((193, 124, 54), (119, 68, 34)),
    }
    if rank in gradients:
        draw_gradient_row(rect, *gradients[rank])
    else:
        pygame.draw.rect(scr, (10, 34, 25), rect, 0, 7)
        pygame.draw.rect(scr, (41, 79, 56), rect, 1, 7)

    rank_rect = pygame.Rect(rect.x + 3, rect.y + 2, 28, rect.h - 4)
    rank_color = (64, 50, 25) if rank <= 3 else (129, 165, 112)
    dashboard_text("%02d" % rank, rank_rect, rank_color, fnt(13, True), "center")
    avatar = pygame.Rect(rect.x + 31, rect.y + 6, 34, 34)
    draw_character_avatar(avatar, player.get("character"))

    name_rect = pygame.Rect(rect.x + 71, rect.y + 5,
                            max(30, rect.w - 118), 18)
    details_rect = pygame.Rect(rect.x + 71, rect.y + 23,
                               max(30, rect.w - 118), 17)
    dashboard_text(player["name"], name_rect, WHITE, FTAG)
    dashboard_text("Lv.%d   %dxp" % (player["level"], player["xp"]),
                   details_rect, (255, 244, 213), FTAG)
    if rank <= 3:
        medal = pygame.Rect(rect.right - 30, rect.y + 5, 27, 34)
        if not draw_ui_image("medal_%d.png" % rank, medal):
            draw_medal_fallback(medal, rank)
    if player["name"].casefold() == G.name.casefold():
        pygame.draw.rect(scr, CYAN, rect, 2, 7)

def draw_player_scrollbar(panel, item_count, offset):
    visible_count = 5
    if item_count <= visible_count:
        return
    track = ui(1894, 298, 10, 535)
    pygame.draw.rect(scr, (15, 42, 34), track, 0, 4)
    maximum = item_count - visible_count
    thumb_height = max(24, round(track.h * visible_count / item_count))
    thumb_y = track.y + round((track.h - thumb_height) * offset / maximum)
    thumb = pygame.Rect(track.x, thumb_y, track.w, thumb_height)
    pygame.draw.rect(scr, (104, 206, 172), thumb, 0, 4)

def draw_home():
    layout = home_layout()
    dashboard_frame("home")
    draw_dashboard_panel(layout["main"])
    draw_dashboard_panel(layout["players"])

    dashboard_text("WELCOME BACK, %s" % G.name.upper(),
                   ui(421, 229, 920, 44), GOLD, fnt(20, True))
    dashboard_text("Your next adventure is ready.",
                   ui(421, 280, 900, 32), WHITE, FS)
    dashboard_text("YOUR CODING ADVENTURE",
                   ui(421, 347, 920, 30), CYAN, FTAG)
    dashboard_text("Game Buddy and Byte need your help!",
                   ui(421, 392, 940, 46), WHITE, fnt(18, True))
    dashboard_text(
        "Choose a language path, study its lessons, and restore the Kingdom's portals.",
        ui(421, 449, 920, 54), (238, 242, 226), FS)

    next_quest_index = next(
        (index for index in range(len(CH))
         if index not in G.S.get("done", [])), None)
    next_quest = ("All quests complete!" if next_quest_index is None
                  else CH[next_quest_index]["n"])
    dashboard_text("Next kingdom milestone: %s" % next_quest,
                   ui(421, 545, 940, 32), GOLD, FTAG)
    story_data = G.S.get("story_quest", {})
    if not isinstance(story_data, dict):
        story_data = {}
    portal_text = []
    for language in STORY_LANGUAGE_NAMES:
        language_progress = story_data.get(language, {})
        completed = (language_progress.get("completed_topics", [])
                     if isinstance(language_progress, dict) else [])
        count = len(completed) if isinstance(completed, (list, tuple)) else 0
        portal_text.append("%s %d/5" % (language, min(count, 5)))
    dashboard_text("PORTALS  " + "   ".join(portal_text[:3]),
                   ui(421, 588, 950, 30), CYAN, FTAG)
    dashboard_text("   ".join(portal_text[3:]),
                   ui(421, 621, 950, 30), CYAN, FTAG)
    draw_dashboard_button(layout["story_button"], "STORY QUEST",
                          True, fnt(17, True))

    dashboard_text("TOP PLAYERS", ui(1490, 222, 390, 40),
                   GOLD, fnt(17, True))
    dashboard_text("LOCAL KINGDOM RANKING", ui(1490, 260, 390, 26),
                   (183, 199, 186), FTAG)
    rows = leaderboard_rows()
    offset = max(0, min(getattr(G, "home_players_offset", 0),
                        max(0, len(rows) - 5)))
    if not rows:
        dashboard_text("No saved players yet.",
                       ui(1493, 298, 390, 44), WHITE, FS)
    else:
        old_clip = scr.get_clip()
        scr.set_clip(layout["players"].inflate(-8, -85))
        for index, player in enumerate(rows[offset:offset + 5]):
            draw_top_player_row(layout["player_rows"][index],
                                offset + index + 1, player)
        scr.set_clip(old_clip)
        draw_player_scrollbar(layout["players"], len(rows), offset)
    if G.M.get("k") == "settings":
        draw_settings()

def draw_settings():
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((5, 23, 19, 205))
    scr.blit(overlay, (0, 0))
    panel_rect = ui(420, 215, 1175, 675)
    pygame.draw.rect(scr, (12, 39, 32), panel_rect, 0, 12)
    pygame.draw.rect(scr, (126, 177, 151), panel_rect, 2, 12)
    dashboard_text("Settings", ui(700, 267, 620, 75),
                   GOLD, fnt(27, True), "center")
    dashboard_text("AUDIO", ui(627, 350, 774, 35),
                   (155, 190, 166), FTAG)
    settings = G.S.get("settings", {})
    options = settings_option_rects()

    def toggle_button(rect, label, enabled):
        fill = (64, 130, 102) if enabled else (19, 49, 42)
        border = (126, 177, 151)
        pygame.draw.rect(scr, fill, rect, 0, 9)
        pygame.draw.rect(scr, border, rect, 2, 9)
        color = (25, 55, 45) if enabled else (153, 182, 164)
        dashboard_text("%s : %s" % (label, "ON" if enabled else "OFF"),
                       rect.inflate(-18, -4), color, fnt(16, True), "center")

    toggle_button(options["music"], "BACKGROUND MUSIC",
                  settings.get("music", True))
    toggle_button(options["sfx"], "SOUND EFFECTS",
                  settings.get("sfx", True))

    back = options["back"]
    pygame.draw.rect(scr, (12, 39, 32), back, 0, 8)
    pygame.draw.rect(scr, (126, 177, 151), back, 2, 8)
    icon_x, icon_y = back.x + 16, back.centery
    pygame.draw.polygon(scr, (154, 195, 168), [
        (icon_x, icon_y - 4), (icon_x + 9, icon_y - 12),
        (icon_x + 18, icon_y - 4)])
    pygame.draw.rect(scr, (154, 195, 168),
                     (icon_x + 3, icon_y - 5, 12, 13), 2)
    pygame.draw.rect(scr, (12, 39, 32),
                     (icon_x + 8, icon_y + 1, 4, 7))
    dashboard_text("BACK TO HOME",
                   pygame.Rect(back.x + 39, back.y, back.w - 45, back.h),
                   (164, 196, 174), FTAG, "center")

    logout = options["logout"]
    pygame.draw.rect(scr, (34, 47, 62), logout, 0, 8)
    pygame.draw.rect(scr, (126, 177, 151), logout, 2, 8)
    lx, ly = logout.x + 18, logout.centery
    pygame.draw.rect(scr, (154, 195, 168),
                     (lx + 3, ly - 9, 12, 18), 2, 2)
    pygame.draw.line(scr, (154, 195, 168),
                     (lx - 3, ly), (lx + 9, ly), 2)
    pygame.draw.polygon(scr, (154, 195, 168), [
        (lx + 7, ly - 5), (lx + 12, ly), (lx + 7, ly + 5)])
    dashboard_text("SIGN OUT",
                   pygame.Rect(logout.x + 42, logout.y,
                               logout.w - 48, logout.h),
                   (164, 196, 174), FTAG, "center")

def draw_leaderboard():
    dashboard_frame("leaderboard")
    layout = home_layout()
    table = layout["main"]
    profile = layout["players"]
    draw_dashboard_panel(table)
    draw_dashboard_panel(profile)
    dashboard_text("KINGDOM LEADERBOARD", ui(421, 222, 920, 38),
                   GOLD, fnt(18, True))
    dashboard_text("Players on this device, ranked by total XP",
                   ui(421, 268, 920, 26), (206, 232, 214), FTAG)
    dashboard_text("RANK", ui(421, 319, 80, 24), CYAN, FTAG)
    dashboard_text("PLAYER", ui(535, 319, 410, 24), CYAN, FTAG)
    dashboard_text("LEVEL", ui(1035, 319, 120, 24), CYAN, FTAG)
    dashboard_text("XP", ui(1175, 319, 100, 24), CYAN, FTAG)
    pygame.draw.line(scr, (104, 206, 172), ui_point(421, 351),
                     ui_point(1280, 351), 1)
    rows = leaderboard_rows()
    current_rank = next((i for i, row in enumerate(rows, 1)
                         if row["name"].casefold() == G.name.casefold()), None)
    if not rows:
        dashboard_text("No saved players yet.",
                       ui(421, 371, 800, 30), WHITE, FS)
    for rank, player in enumerate(rows[:8], 1):
        y = 365 + (rank - 1) * 68
        row = ui(421, y, 835, 62)
        is_current = player["name"].casefold() == G.name.casefold()
        if is_current:
            pygame.draw.rect(scr, (38, 77, 62), row, 0, 6)
            pygame.draw.rect(scr, CYAN, row, 1, 6)
        dashboard_text("%02d" % rank, ui(435, y + 12, 72, 36),
                       GOLD if rank <= 3 else WHITE, FS)
        avatar = ui(505, y + 5, 52, 52)
        draw_character_avatar(avatar, player.get("character"))
        dashboard_text(player["name"], ui(572, y + 10, 430, 36),
                       WHITE, FS)
        dashboard_text("Lv.%d" % player["level"],
                       ui(1035, y + 10, 120, 36), WHITE, FS)
        dashboard_text(str(player["xp"]), ui(1175, y + 10, 90, 36),
                       GOLD, FS)
        if rank < min(8, len(rows)):
            pygame.draw.line(scr, (54, 68, 80),
                             ui_point(421, y + 64),
                             ui_point(1256, y + 64), 1)

    dashboard_text("TOP PLAYERS", ui(1490, 222, 390, 40),
                   GOLD, fnt(17, True))
    dashboard_text(G.name, ui(1490, 282, 390, 36), WHITE, fnt(17, True))
    dashboard_text("RANK  #%s" % (current_rank if current_rank is not None else "-"),
                   ui(1490, 340, 390, 30), CYAN, FS)
    dashboard_text("LEVEL  %d" % lvl(),
                   ui(1490, 395, 390, 30), WHITE, FS)
    dashboard_text("TOTAL XP  %d" % G.S.get("xp", 0),
                   ui(1490, 445, 390, 30), GOLD, FS)
    done = G.S.get("done", [])
    dashboard_text("QUESTS  %d / %d" %
                   (len(done) if isinstance(done, list) else 0, len(CH)),
                   ui(1490, 495, 390, 30), WHITE, FS)
    pygame.draw.line(scr, (104, 206, 172), ui_point(1490, 545),
                     ui_point(1888, 545), 1)
    dashboard_text("Press L again or H to return.",
                   ui(1490, 570, 390, 40), (206, 232, 214), FTAG)

def progress_summary():
    save_data = G.S if isinstance(G.S, dict) else {}
    story_data = save_data.get("story_quest", {})
    if not isinstance(story_data, dict):
        story_data = {}

    raw_xp = save_data.get("xp", 0)
    total_xp = (raw_xp if isinstance(raw_xp, int) and
                not isinstance(raw_xp, bool) and raw_xp >= 0 else 0)
    raw_crystals = save_data.get("crystal_balance", 0)
    crystals = (raw_crystals if isinstance(raw_crystals, int) and
                not isinstance(raw_crystals, bool) and raw_crystals >= 0 else 0)

    languages = []
    portals = attempts_total = correct_total = 0
    for language in STORY_LANGUAGE_NAMES:
        progress = story_data.get(language, {})
        if not isinstance(progress, dict):
            progress = {}
        completed = progress.get("completed_topics", [])
        valid_completed = {
            topic for topic in completed
            if isinstance(topic, int) and not isinstance(topic, bool)
            and 0 <= topic < 5
        } if isinstance(completed, (list, tuple)) else set()
        completed_count = len(valid_completed)
        attempts = []
        for key in ("quiz_attempts", "challenge_attempts"):
            records = progress.get(key, [])
            if isinstance(records, list):
                attempts.extend(record for record in records
                                if isinstance(record, dict))
        correct = sum(record.get("correct") is True for record in attempts)
        earned_xp = progress.get("xp_earned", 0)
        if not isinstance(earned_xp, int) or isinstance(earned_xp, bool):
            earned_xp = 0
        language_info = STORY_QUEST_DATA.get("languages", {}).get(language, {})
        theme = (language_info.get("theme", language)
                 if isinstance(language_info, dict) else language)
        color = (language_info.get("color", CYAN)
                 if isinstance(language_info, dict) else CYAN)
        languages.append({
            "name": language,
            "theme": str(theme),
            "color": tuple(color),
            "completed": completed_count,
            "attempts": len(attempts),
            "correct": correct,
            "accuracy": (round(correct * 100 / len(attempts))
                         if attempts else None),
            "xp": earned_xp,
            "earned_badges": story_badges_for_progress(language, progress),
        })
        portals += completed_count
        attempts_total += len(attempts)
        correct_total += correct

    return {
        "languages": languages,
        "portals": portals,
        "attempts": attempts_total,
        "accuracy": (round(correct_total * 100 / attempts_total)
                     if attempts_total else None),
        "xp": total_xp,
        "crystals": crystals,
        "level": 1 + total_xp // XPL,
        "level_xp": total_xp % XPL,
    }

def draw_badge_tile(rect, label_rect, language, earned):
    fill = (88, 75, 35) if earned else (16, 36, 31)
    border = GOLD if earned else (57, 91, 71)
    pygame.draw.rect(scr, fill, rect, 0, 8)
    pygame.draw.rect(scr, border, rect, 2, 8)
    icon_rect = rect.inflate(-10, -10)
    asset_name = "badge_%s.png" % language.lower()
    if not draw_ui_image(asset_name, icon_rect):
        draw_badge_fallback(icon_rect, language)
    if not earned:
        dim = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
        dim.fill((5, 14, 12, 150))
        scr.blit(dim, icon_rect.topleft)
    dashboard_text(language.upper(), label_rect,
                   GOLD if earned else (109, 133, 119), fnt(8, True), "center")

def draw_progress():
    layout = progress_layout()
    dashboard_frame("progress")
    draw_dashboard_panel(layout["main"])
    draw_dashboard_panel(layout["summary"])
    summary = progress_summary()

    dashboard_text("LEARNING PROGRESS", ui(421, 222, 835, 40),
                   GOLD, fnt(18, True))
    profile = "%s  |  LEVEL %d  |  XP %d  |  CRYSTALS %d" % (
        G.name, summary["level"], summary["xp"], summary["crystals"])
    dashboard_text(profile, ui(421, 267, 835, 30),
                   (238, 242, 226), FTAG)

    dashboard_text("LANGUAGE / THEME", ui(421, 322, 245, 24),
                   CYAN, FTAG)
    dashboard_text("PORTALS", ui(680, 322, 170, 24), CYAN, FTAG)
    dashboard_text("ACCURACY", ui(895, 322, 210, 24), CYAN, FTAG)
    dashboard_text("XP", ui(1165, 322, 90, 24), CYAN, FTAG)
    divider_y = ui_point(421, 352)[1]
    pygame.draw.line(scr, (104, 206, 172), (layout["main"].x + 14, divider_y),
                     (layout["main"].right - 14, divider_y), 1)

    for index, (language, row_layout) in enumerate(
            zip(summary["languages"], layout["rows"])):
        dashboard_text(language["name"], row_layout["language"],
                       WHITE, FS)
        dashboard_text(language["theme"], row_layout["theme"],
                       (199, 215, 203), FTAG)
        dashboard_text("%d / 5" % min(language["completed"], 5),
                       row_layout["portals"], WHITE, FS)
        bar = row_layout["bar"]
        pygame.draw.rect(scr, (15, 30, 30), bar, 0, 4)
        fill_width = round(bar.w * min(max(language["completed"], 0), 5) / 5)
        if fill_width:
            pygame.draw.rect(scr, language["color"],
                             pygame.Rect(bar.x, bar.y, fill_width, bar.h),
                             0, 4)
        accuracy = ("no attempts" if language["accuracy"] is None
                    else "%d%%" % language["accuracy"])
        dashboard_text(accuracy, row_layout["accuracy"], WHITE,
                       FTAG if language["accuracy"] is None else FS)
        dashboard_text(str(language["xp"]), row_layout["xp"], GOLD, FS)
        if index < len(layout["rows"]) - 1:
            pygame.draw.line(scr, (54, 68, 80),
                             row_layout["divider"][0],
                             row_layout["divider"][1], 1)

    level_xp = summary["level_xp"]
    dashboard_text("LEVEL PROGRESS  %d / %d XP" % (level_xp, XPL),
                   layout["level_label"], CYAN, FTAG)
    level_bar = layout["level_bar"]
    pygame.draw.rect(scr, (15, 30, 30), level_bar, 0, 6)
    fill_width = round(level_bar.w * level_xp / XPL)
    if fill_width:
        pygame.draw.rect(scr, GOLD,
                         pygame.Rect(level_bar.x, level_bar.y,
                                     fill_width, level_bar.h), 0, 6)

    panel = layout["summary"]
    dashboard_text("YOUR SUMMARY", ui(1360, 222, 520, 40),
                   GOLD, fnt(17, True))
    dashboard_text("PORTALS  %d / 25" % summary["portals"],
                   ui(1360, 300, 520, 34), WHITE, FS)
    accuracy = ("no attempts" if summary["accuracy"] is None
                else "%d%%" % summary["accuracy"])
    dashboard_text("ACCURACY  %s" % accuracy,
                   ui(1360, 350, 520, 34), CYAN, FS)
    dashboard_text("ATTEMPTS  %d" % summary["attempts"],
                   ui(1360, 400, 520, 34), WHITE, FS)
    divider_y = ui_point(1360, 475)[1]
    pygame.draw.line(scr, WHITE, (panel.x + 12, divider_y),
                     (panel.right - 12, divider_y), 2)
    dashboard_text("BADGES", ui(1360, 490, 520, 38),
                   GOLD, fnt(17, True), "center")
    badges_by_language = {
        item["name"]: item["earned_badges"] for item in summary["languages"]
    }
    badge_order = ("Java", "Python", "HTML", "JavaScript", "CSS")
    for language, badge_layout in zip(badge_order, layout["badge_tiles"]):
        badge_name = "%s Kingdom Restorer" % language
        earned = badge_name in badges_by_language.get(language, [])
        draw_badge_tile(badge_layout["tile"], badge_layout["label"],
                        language, earned)

    if G.M.get("k") == "settings":
        draw_settings()

def pause_screen():
    ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((18, 27, 34, 200)); scr.blit(ov, (0, 0)); r = panel("Paused")
    b = [CH[i]["b"] for i in G.S["done"]]
    y = para("Guardian %s - Level %d - %d XP - Orbs %d/%d" % (G.name, lvl(), G.S["xp"], len(G.S["orbs"]), len(ORBS)), r.x + 22, r.y + 70, r.w - 44)
    y = para("Badges: " + (", ".join(b) if b else "none yet"), r.x + 22, y + 8, r.w - 44, GOLD)
    para("B store   |   ESC resume   |   S save   |   M home   |   R reset progress" + ("  - press Y to CONFIRM reset" if G.conf else ""), r.x + 22, y + 24, r.w - 44, CYAN if not G.conf else RED)
    if G.touch_enabled:
        labels = ["RESUME", "STORE", "SAVE", "HOME", "CONFIRM" if G.conf else "RESET"]
        for i, label in enumerate(labels):
            button = pygame.Rect(r.x + 22 + i * 145, r.bottom - 104, 130, 58)
            pygame.draw.rect(scr, (58, 76, 90), button, 0, 9)
            pygame.draw.rect(scr, RED if label == "RESET" else CYAN, button, 2, 9)
            rendered = FS.render(label, True, WHITE)
            scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                                button.centery - rendered.get_height() // 2))
SHOP_COLS, SHOP_ROWS = 6, 4
FTAG = fnt(11, True)
FPAGE = fnt(12, True)
SHOP_PER_PAGE = SHOP_COLS * SHOP_ROWS
def shop_origin():
    r = pygame.Rect(110, 40, W - 220, H - 80)
    return r, (r.x + 22, r.y + 116)
def shop_cell(i):
    r, (gx, gy) = shop_origin(); n = i % SHOP_PER_PAGE
    return pygame.Rect(gx + (n % SHOP_COLS) * 74, gy + (n // SHOP_COLS) * 80, 70, 76)
def shop_page_buttons():
    r, (gx, gy) = shop_origin()
    return pygame.Rect(gx, r.y + 446, 90, 26), pygame.Rect(gx + 354, r.y + 446, 90, 26)
def character_owned(character):
    return character["xp_cost"] == 0 or character["id"] in G.S.get("owned_characters", ["guardian"])
def shop_screen():
    ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((18, 27, 34, 205)); scr.blit(ov, (0, 0)); r = panel("Choose Your Character")
    info = pygame.Rect(r.x + 500, r.y + 50, 250, 100)
    xp_badge = pygame.Rect(info.centerx - 100, info.y, 200, 28)
    pygame.draw.rect(scr, (35, 46, 54), xp_badge, 0, 6)
    pygame.draw.rect(scr, GOLD, xp_badge, 2, 6)
    text("XP TO SPEND: %d" % G.S.get("xp", 0), xp_badge.x + 8, xp_badge.y + 6, GOLD, FS)
    for label, color, y in (
            ("SPEND XP TO UNLOCK CHARACTERS", CYAN, info.y + 32),
            ("Code Guardian free; characters unlock in XP tiers.",
             (206, 232, 214), info.y + 49)):
        rendered = FTAG.render(label, True, color)
        scr.blit(rendered, (info.centerx - rendered.get_width() // 2, y))
    selected = CHARACTERS[G.shop_index]
    equipped = G.S.get("character", "guardian")
    page = G.shop_index // SHOP_PER_PAGE
    pages = (len(CHARACTERS) + SHOP_PER_PAGE - 1) // SHOP_PER_PAGE
    for i in range(page * SHOP_PER_PAGE, min(len(CHARACTERS), (page + 1) * SHOP_PER_PAGE)):
        character = CHARACTERS[i]; cell = shop_cell(i)
        pygame.draw.rect(scr, (62, 116, 96) if i == G.shop_index else (21, 31, 39), cell, 0, 8)
        border = GOLD if i == G.shop_index else GREEN if character["id"] == equipped else (104, 206, 172)
        pygame.draw.rect(scr, border, cell, 3 if character["id"] == equipped or i == G.shop_index else 1, 8)
        img = fit_image(character_image(character), 54, 50, False, character["id"])
        if not character_owned(character):
            img = img.copy(); img.set_alpha(110)
        scr.blit(img, (cell.centerx - img.get_width() // 2, cell.y + 4 + (52 - img.get_height()) // 2))
        if character["id"] == equipped: tag, col = "IN USE", GREEN
        elif character_owned(character): tag, col = "FREE" if character["xp_cost"] == 0 else "OWNED", CYAN
        else: tag, col = "%d XP" % character["xp_cost"], GOLD
        rendered = FTAG.render(tag, True, col)
        scr.blit(rendered, (cell.centerx - rendered.get_width() // 2, cell.bottom - 16))
    prev_btn, next_btn = shop_page_buttons()
    for btn, label in ((prev_btn, "< PREV"), (next_btn, "NEXT >")):
        pygame.draw.rect(scr, (34, 46, 58), btn, 0, 6); pygame.draw.rect(scr, (104, 206, 172), btn, 1, 6)
        rendered = FPAGE.render(label, True, WHITE)
        scr.blit(rendered, (btn.centerx - rendered.get_width() // 2, btn.centery - rendered.get_height() // 2))
    rendered = FPAGE.render("PAGE %d / %d" % (page + 1, pages), True, CYAN)
    scr.blit(rendered, ((prev_btn.right + next_btn.x) // 2 - rendered.get_width() // 2, prev_btn.y + 6))
    box = pygame.Rect(r.x + 500, r.y + 116, 250, 220)
    pygame.draw.rect(scr, (21, 31, 39), box, 0, 10); pygame.draw.rect(scr, (104, 206, 172), box, 2, 10)
    big = fit_image(character_image(selected), 190, 180, False, selected["id"])
    bob = math.sin(G.t * 2.2) * 2
    scr.blit(big, (box.centerx - big.get_width() // 2, round(box.bottom - 18 - big.get_height() - bob)))
    pygame.draw.ellipse(scr, (14, 22, 28), (box.centerx - 40, box.bottom - 20, 80, 10))
    rendered = FB.render(selected["name"], True, WHITE) if FB.size(selected["name"])[0] <= 250 else F.render(selected["name"], True, WHITE)
    scr.blit(rendered, (box.centerx - rendered.get_width() // 2, box.bottom + 10))
    if selected["id"] == equipped: status, scol = "Your character", GREEN
    elif character_owned(selected): status, scol = "Press ENTER to use", CYAN
    else: status, scol = "%d XP to unlock" % selected["xp_cost"], GOLD
    rendered = FS.render(status, True, scol)
    scr.blit(rendered, (box.centerx - rendered.get_width() // 2, box.bottom + 44))
    if G.shop_notice:
        para(G.shop_notice, box.x, r.y + 456, box.w, GOLD, FS)
    text("ARROWS select   |   ENTER choose   |   B or ESC close", r.x + 22, r.bottom - 32, (206, 232, 214), FS)
    for button, label, col in ((pygame.Rect(r.x + 500, r.y + 408, 120, 40), "CHOOSE", GREEN),
                               (pygame.Rect(r.x + 630, r.y + 408, 120, 40), "CLOSE", CYAN)):
        pygame.draw.rect(scr, (58, 76, 90), button, 0, 9)
        pygame.draw.rect(scr, col, button, 2, 9)
        rendered = FS.render(label, True, WHITE)
        scr.blit(rendered, (button.centerx - rendered.get_width() // 2,
                            button.centery - rendered.get_height() // 2))

def open_shop(return_state):
    G.shop_return = return_state
    G.shop_index = next((i for i, c in enumerate(CHARACTERS)
                         if c["id"] == G.S.get("character", "guardian")), 0)
    G.shop_notice = ""
    G.state = "shop"

def shop_action():
    character = CHARACTERS[G.shop_index]
    owned = G.S.setdefault("owned_characters", ["guardian"])
    if character["id"] in owned or character["xp_cost"] == 0:
        G.S["character"] = character["id"]
        G.shop_notice = "%s equipped." % character["name"]
    elif G.S.get("xp", 0) < character["xp_cost"]:
        G.shop_notice = "You need %d more XP to unlock this character." % (
            character["xp_cost"] - G.S.get("xp", 0))
    else:
        G.S["xp"] -= character["xp_cost"]
        owned.append(character["id"])
        G.S["character"] = character["id"]
        G.shop_notice = "%s unlocked and equipped!" % character["name"]
    save()

def handle_touch_button(name, finger_id):
    if name in ("left", "right"):
        G.touch_fingers[finger_id] = name
        setattr(G, "touch_" + name, True)
    elif name == "jump":
        G.touch_jump = True
    elif name == "interact" and G.state == "obby":
        leave_portal_obby()
    elif name == "pause":
        G.state = "pause"
    elif name == "shop":
        open_shop("play")
    elif name == "interact" and G.near:
        handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, mod=0, unicode=""))

def handle_pointer(pos, touch=False):
    if pos is None:
        return
    if touch:
        G.touch_enabled = True
    x, y = pos
    point = (int(x), int(y))
    if G.state == "admin":
        handle_admin_pointer(point)
        return
    if G.state == "login":
        layout = login_layout()
        if layout["username"].collidepoint(point):
            G.auth_focus = "username"; set_text_input(True)
        elif layout["reveal"].collidepoint(point):
            G.auth_show_password = not G.auth_show_password
        elif layout["password"].collidepoint(point):
            G.auth_focus = "password"; set_text_input(True)
        elif layout["mode"].collidepoint(point):
            G.auth_mode = "register" if G.auth_mode == "login" else "login"
            G.auth_error = ""
        elif WEB and layout["guest"].collidepoint(point):
            start("Guest")
        elif layout["submit"].collidepoint(point):
            set_text_input(False)
            authenticate(G.auth_mode == "register")
        return
    if G.state == "obby" and G.M.get("k") == "settings":
        options = settings_option_rects()
        if options["music"].collidepoint(point):
            toggle_setting("music")
        elif options["sfx"].collidepoint(point):
            toggle_setting("sfx")
        elif options["back"].collidepoint(point):
            G.M = {}
        elif options["logout"].collidepoint(point):
            sign_out()
        return
    if G.state == "obby" and obby_settings_rect().collidepoint(point):
        open_settings()
        return
    if G.state in ("home", "leaderboard", "progress"):
        if (G.state in ("home", "progress")
                and G.M.get("k") == "settings"):
            options = settings_option_rects()
            if options["music"].collidepoint(point):
                toggle_setting("music")
            elif options["sfx"].collidepoint(point):
                toggle_setting("sfx")
            elif options["back"].collidepoint(point):
                G.M = {}
                G.state = "home"
            elif options["logout"].collidepoint(point):
                sign_out()
            return

        shared = dashboard_layout()
        if (G.state in ("home", "progress")
                and shared["settings"].collidepoint(point)):
            open_settings()
        elif shared["home"].collidepoint(point):
            G.M = {}
            G.state = "home"
        elif shared["progress"].collidepoint(point):
            G.M = {}
            G.state = "progress"
        elif shared["customize"].collidepoint(point):
            open_shop(G.state)
        elif shared["enter"].collidepoint(point):
            open_story_quest()
        elif (G.state == "home"
              and home_layout()["story_button"].collidepoint(point)):
            open_story_quest()
        elif (G.state == "home"
              and home_layout()["players"].collidepoint(point)):
            G.state = "leaderboard"
        return
    if G.M:
        modal = G.M
        if modal["k"] == "build":
            if modal["elapsed"] >= len(BUILD_STEPS) * BUILD_STEP_SECONDS:
                G.M = {}
            else:
                modal["elapsed"] = min(
                    len(BUILD_STEPS) * BUILD_STEP_SECONDS,
                    (int(modal["elapsed"] / BUILD_STEP_SECONDS) + 1) * BUILD_STEP_SECONDS,
                )
            return
        if modal["k"] == "language_select":
            for i in range(len(LANGUAGE_PATHS)):
                if language_card_rect(i).collidepoint(point):
                    open_language_lesson(i)
                    return
            return
        if modal["k"] == "language_lesson":
            if language_result_action_rect().collidepoint(point):
                start_language_quiz(modal["i"])
            return
        if modal["k"] == "language_quiz":
            if modal["feedback"] is None:
                for i in range(4):
                    if language_option_rect(i).collidepoint(point):
                        answer_language_question(i)
                        return
            elif language_quiz_continue_rect().collidepoint(point):
                advance_language_quiz()
            return
        if modal["k"] == "language_result":
            if language_result_action_rect().collidepoint(point):
                open_language_select(modal["i"])
            return
        if modal["k"] == "story_intro":
            last = len(INTRO_SCENES) - 1
            if modal["scene"] == last and story_intro_finished():
                if pygame.Rect(365, H - 116, 270, 48).collidepoint(point):
                    stop_story_voice()
                    open_story_language_select()
            elif modal["scene"] < last and story_intro_skip_rect().collidepoint(point):
                skip_story_intro()
            else:
                advance_story_intro(from_click=True)
            return
        if modal["k"] == "story_ending":
            if story_ending_finished():
                if story_ending_continue_rect().collidepoint(point):
                    advance_story_ending()
            else:
                advance_story_ending()
            return
        if modal["k"] == "story_language_select":
            for i, language in enumerate(STORY_LANGUAGE_NAMES):
                if story_language_card_rect(i).collidepoint(point):
                    select_story_language(language)
                    return
            return
        if modal["k"] == "story_lesson_list":
            for i in range(5):
                if story_lesson_card_rect(i).collidepoint(point):
                    open_story_lesson(modal["language"], i)
                    return
            return
        if modal["k"] == "story_lesson":
            actions = story_lesson_action_rects(modal["read_only"])
            if actions["back"].collidepoint(point):
                open_story_lesson_list(modal["language"], modal["topic"])
            elif modal["read_only"] and actions["replay"].collidepoint(point):
                retry_story_topic_quiz(modal["language"], modal["topic"])
            elif not modal["read_only"] and actions["lessons"].collidepoint(point):
                open_story_lesson_list(modal["language"], modal["topic"])
            elif not modal["read_only"] and actions["parkour"].collidepoint(point):
                start_story_parkour(modal["language"], modal["topic"])
            return
        if modal["k"] == "story_difficulty":
            actions = story_difficulty_action_rects()
            for i in range(len(DIFFICULTIES)):
                if story_difficulty_card_rect(i).collidepoint(point):
                    modal["selected"] = i
                    return
            if actions["back"].collidepoint(point):
                open_story_lesson(modal["language"], modal["topic"])
            elif actions["start"].collidepoint(point):
                launch_story_parkour(modal["language"], modal["topic"], modal["selected"])
            return
        if modal["k"] == "story_quiz":
            question = story_language_data(modal["language"])["topics"][modal["topic"]]["questions"][modal["question"]]
            if modal["feedback"] is not None:
                if story_quiz_next_rect().collidepoint(point):
                    advance_story_question()
                return
            if modal["topic"] == 4:
                if story_battle_submit_rect().collidepoint(point):
                    submit_story_answer(modal["input"])
                elif story_battle_input_rect().collidepoint(point):
                    set_text_input(True)
                return
            if question["type"] == "multiple_choice":
                for i, option in enumerate(question["options"]):
                    if story_question_rect(i).collidepoint(point):
                        submit_story_answer(option)
                        return
            elif story_quiz_submit_rect().collidepoint(point):
                submit_story_answer(modal["input"])
            elif question["type"] != "multiple_choice":
                set_text_input(True)
            return
        if modal["k"] == "story_coding":
            if story_coding_input_rect().collidepoint(point):
                set_text_input(True)
                box = story_coding_input_rect()
                font = fnt(14)
                relative_y = max(0, point[1] - box.y - 12)
                line_index = relative_y // (font.get_linesize() + 2)
                source_lines = modal["input"].split("\n")
                if line_index < len(source_lines):
                    line = source_lines[line_index]
                    line_start = sum(len(part) + 1
                                     for part in source_lines[:line_index])
                    cursor_column = 0
                    best_distance = float("inf")
                    for column in range(len(line) + 1):
                        distance = abs(font.size(line[:column])[0] -
                                       (point[0] - box.x - 12))
                        if distance < best_distance:
                            best_distance = distance
                            cursor_column = column
                    clicked_position = line_start + cursor_column
                    clicked_placeholder = next(
                        ((start, end) for start, end in re_placeholder_ranges(modal["input"])
                         if start <= clicked_position <= end),
                        None)
                    if clicked_placeholder is not None:
                        modal["anchor"], modal["cursor"] = clicked_placeholder
                    else:
                        modal["cursor"] = clicked_position
                        modal["anchor"] = None
            elif (not (modal["feedback"] and modal["feedback"]["correct"])
                  and story_coding_clear_rect().collidepoint(point)):
                modal["input"] = ""
                modal["cursor"] = 0
                modal["anchor"] = None
                modal["feedback"] = None
                set_text_input(True)
            elif story_coding_run_rect().collidepoint(point):
                if modal["feedback"] is not None and modal["feedback"]["correct"]:
                    complete_story_topic(modal["language"], modal["topic"])
                else:
                    submit_story_coding()
            return
        if modal["k"] == "story_battle_result":
            if story_battle_retry_rect().collidepoint(point):
                retry_story_battle(modal["language"])
            return
        if modal["k"] == "story_results":
            actions = story_results_button_rects()
            if actions["replay"].collidepoint(point):
                reset_story_language(modal["language"])
            elif actions["languages"].collidepoint(point):
                open_story_language_select()
            elif actions["menu"].collidepoint(point):
                stop_boss_defeat_sound()
                G.M = {}; G.state = "home"; G.story_mode = False
            return
        if modal["k"] == "lesson_menu":
            for i in range(len(LESSONS)):
                if lesson_card_rect(i).collidepoint(point):
                    open_lesson(i)
                    return
            return
        if modal["k"] == "lesson":
            if lesson_action_rect().collidepoint(point):
                i = modal["i"]
                if unlocked(i) and i not in G.S["done"]:
                    start_lesson_quiz(i)
                else:
                    G.M = dict(k="lesson_menu", selected=i)
            return
        if modal["k"] == "msg":
            close_message()
            return
        buttons = modal_touch_button_rects(modal)
        for i, button in enumerate(buttons):
            if button.collidepoint(point):
                if modal["k"] == "mc":
                    key = pygame.K_RETURN if modal["fb"] is not None else pygame.K_1 + i
                    handle_key(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
                elif modal["k"] == "tr":
                    if modal["fb"] and not modal["fb"][0]:
                        handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
                    elif i == 0:
                        handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0, unicode=""))
                    elif i == 1:
                        key = pygame.K_F5 if CH[modal["i"]]["items"][modal["q"]]["k"] == "code" else pygame.K_RETURN
                        handle_key(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
                    elif modal["fb"] and modal["fb"][0]:
                        handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
                    else:
                        handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
                return
        if modal["k"] == "tr":
            set_text_input(True)
        return
    if G.state == "shop":
        r = pygame.Rect(110, 40, W - 220, H - 80)
        page = G.shop_index // SHOP_PER_PAGE
        for i in range(page * SHOP_PER_PAGE, min(len(CHARACTERS), (page + 1) * SHOP_PER_PAGE)):
            if shop_cell(i).collidepoint(point):
                if G.shop_index == i: shop_action()
                else: G.shop_index = i; G.shop_notice = ""
                return
        prev_btn, next_btn = shop_page_buttons()
        pages = (len(CHARACTERS) + SHOP_PER_PAGE - 1) // SHOP_PER_PAGE
        if prev_btn.collidepoint(point):
            G.shop_index = ((G.shop_index // SHOP_PER_PAGE - 1) % pages) * SHOP_PER_PAGE; G.shop_notice = ""
        elif next_btn.collidepoint(point):
            G.shop_index = ((G.shop_index // SHOP_PER_PAGE + 1) % pages) * SHOP_PER_PAGE; G.shop_notice = ""
        elif pygame.Rect(r.x + 500, r.y + 408, 120, 40).collidepoint(point):
            shop_action()
        elif pygame.Rect(r.x + 630, r.y + 408, 120, 40).collidepoint(point):
            G.state = G.shop_return
        return
    if G.state == "pause":
        r = pygame.Rect(110, 40, W - 220, H - 80)
        for i, action in enumerate(("resume", "store", "save", "menu", "reset")):
            button = pygame.Rect(r.x + 22 + i * 145, r.bottom - 104, 130, 58)
            if button.collidepoint(point):
                if action == "resume":
                    G.state = "play"; G.conf = False
                elif action == "store":
                    open_shop("pause")
                elif action == "save":
                    save(); toast("Saved")
                elif action == "menu":
                    save(); G.state = "home"
                elif action == "reset":
                    if G.conf:
                        settings = G.S.get("settings", {"music": True, "sfx": True})
                        G.S = dict(xp=0, done=[], orbs=[], won=False, crystal_balance=0,
                                   settings=settings,
                                   owned_characters=["guardian"], character="guardian", map_seen=[], portal_obby_clear=[])
                        save(); G.cp = (100, 420); G.px, G.py = G.cp
                        G.conf = False; G.state = "play"; toast("Progress reset")
                    else:
                        G.conf = True
                return
        return
    if G.state == "obby" and touch:
        G.touch_jump = True

def handle_key(e):
    if G.state == "admin":
        if e.key == pygame.K_ESCAPE:
            admin_sign_out()
        return
    if G.state == "login":
        if e.key == pygame.K_TAB: G.auth_focus = "password" if G.auth_focus == "username" else "username"
        elif e.key == pygame.K_F2: G.auth_mode = "register"; G.auth_error = ""
        elif e.key == pygame.K_F1: G.auth_mode = "login"; G.auth_error = ""
        elif e.key == pygame.K_RETURN:
            G.auth_backspace_held = False
            set_text_input(False)
            if WEB:
                start("Guest")
            else:
                authenticate(G.auth_mode == "register")
        elif e.key == pygame.K_BACKSPACE:
            if not G.auth_backspace_held:
                delete_auth_characters()
                G.auth_backspace_held = True
                G.auth_backspace_timer = .32
        elif e.key == pygame.K_ESCAPE:
            G.auth_backspace_held = False
            G.auth_error = ""
    elif G.state in ("home", "progress", "obby") and G.M.get("k") == "settings":
        if e.key == pygame.K_ESCAPE:
            G.M = {}
        elif e.key == pygame.K_1:
            toggle_setting("music")
        elif e.key == pygame.K_2:
            toggle_setting("sfx")
        elif e.key == pygame.K_3:
            sign_out()
    elif G.state in ("home", "leaderboard", "progress"):
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            open_story_quest()
        elif G.state == "home" and e.key == pygame.K_t:
            open_story_quest()
        elif G.state in ("home", "progress") and e.key == pygame.K_s:
            open_settings()
        elif e.key == pygame.K_c:
            open_shop(G.state)
        elif e.key == pygame.K_l:
            G.state = "leaderboard"
        elif e.key == pygame.K_p:
            G.state = "progress"
        elif e.key == pygame.K_h or (
                e.key == pygame.K_ESCAPE and G.state in ("leaderboard", "progress")):
            G.state = "home"
    elif G.M:
        modal_key(e)
        if G.M and G.M.get("k") == "story_quiz":
            question = story_language_data(G.M["language"])["topics"][G.M["topic"]]["questions"][G.M["question"]]
            if (G.M["feedback"] is not None
                    or (G.M["topic"] != 4 and question["type"] == "multiple_choice")):
                set_text_input(False)
        elif G.M and G.M.get("k") == "story_coding":
            if (G.M["feedback"] is not None
                    and G.M["feedback"]["correct"]):
                set_text_input(False)
        elif not G.M or G.M.get("k") != "tr":
            set_text_input(False)
    elif G.state == "shop":
        if e.key in (pygame.K_ESCAPE, pygame.K_b): G.state = G.shop_return
        elif e.key in (pygame.K_LEFT, pygame.K_a): G.shop_index = (G.shop_index - 1) % len(CHARACTERS); G.shop_notice = ""
        elif e.key in (pygame.K_RIGHT, pygame.K_d): G.shop_index = (G.shop_index + 1) % len(CHARACTERS); G.shop_notice = ""
        elif e.key in (pygame.K_UP, pygame.K_w): G.shop_index = max(0, G.shop_index - SHOP_COLS); G.shop_notice = ""
        elif e.key in (pygame.K_DOWN, pygame.K_s): G.shop_index = min(len(CHARACTERS) - 1, G.shop_index + SHOP_COLS); G.shop_notice = ""
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE): shop_action()
    elif G.state == "pause":
        if e.key == pygame.K_ESCAPE: G.state = "play"; G.conf = False
        elif e.key == pygame.K_s: save(); toast("Saved")
        elif e.key == pygame.K_m: save(); G.state = "home"
        elif e.key == pygame.K_b: open_shop("pause")
        elif e.key == pygame.K_r: G.conf = True
        elif e.key == pygame.K_y and G.conf:
            settings = G.S.get("settings", {"music": True, "sfx": True})
            G.S = dict(xp=0, done=[], orbs=[], won=False, crystal_balance=0,
                       settings=settings,
                       owned_characters=["guardian"], character="guardian", map_seen=[], portal_obby_clear=[])
            save(); G.cp = (100, 420); G.px, G.py = G.cp; G.conf = False; G.state = "play"; toast("Progress reset")
    elif G.state == "obby":
        if e.key == pygame.K_ESCAPE:
            leave_portal_obby()
        elif e.key == pygame.K_s:
            open_settings()
    else:
        if e.key == pygame.K_ESCAPE: G.state = "home"
        elif DEV: dev_key(e)

async def main():
    global display
    while True:
        dt = min(.05, clk.tick(60) / 1000); G.t += dt; G.tt = max(0, G.tt - dt)
        await asyncio.sleep(0)
        if G.M.get("k") == "build":
            G.M["elapsed"] += dt
        elif G.M.get("k") == "story_intro":
            G.M["t"] += dt
            G.M["typed"] += dt * INTRO_CPS
        elif G.M.get("k") == "story_ending":
            ending_body = STORY_LANGUAGE_ENDINGS[G.M["language"]][1]
            G.M["t"] += dt
            G.M["typed"] = min(len(ending_body), G.M["typed"] + dt * INTRO_CPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: save(); pygame.quit(); sys.exit()
            if e.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                width = getattr(e, "w", getattr(e, "x", W))
                height = getattr(e, "h", getattr(e, "y", H))
                display = pygame.display.set_mode((max(320, width), max(240, height)), pygame.RESIZABLE)
                continue
            if e.type == pygame.FINGERDOWN:
                G.touch_enabled = True
                window_w, window_h = display.get_size()
                pos = logical_pos((int(e.x * window_w), int(e.y * window_h)))
                if G.M.get("k") == "story_lesson":
                    G.story_lesson_drag_y = e.y
                if pos is not None and G.state == "obby":
                    controls = touch_button_rects()
                    for name in ("left", "right", "interact", "jump"):
                        if controls[name].collidepoint(pos):
                            handle_touch_button(name, e.finger_id)
                            break
                    else:
                        handle_pointer(pos, True)
                elif pos is not None and G.state == "play":
                    handle_pointer(pos, True)
                else:
                    handle_pointer(pos, True)
                continue
            if e.type == pygame.FINGERMOTION:
                if G.M.get("k") == "story_lesson":
                    previous_y = getattr(G, "story_lesson_drag_y", e.y)
                    movement = (previous_y - e.y) * H
                    G.M["scroll"] = max(
                        0, G.M.get("scroll", 0) + int(movement))
                    G.story_lesson_drag_y = e.y
                continue
            if e.type == pygame.FINGERUP:
                name = G.touch_fingers.pop(e.finger_id, None)
                if name:
                    setattr(G, "touch_" + name,
                            any(button == name for button in G.touch_fingers.values()))
                continue
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                handle_pointer(logical_pos(e.pos))
                continue
            if e.type == pygame.MOUSEWHEEL:
                if G.M.get("k") == "story_lesson":
                    G.M["scroll"] = max(
                        0, G.M.get("scroll", 0) - e.y * 36)
                elif G.state == "home" and G.M.get("k") != "settings":
                    pointer = logical_pos(pygame.mouse.get_pos())
                    if (pointer is not None
                            and home_layout()["players"].collidepoint(pointer)):
                        maximum = max(0, len(leaderboard_rows()) - 5)
                        current = getattr(G, "home_players_offset", 0)
                        G.home_players_offset = max(
                            0, min(maximum, current - e.y))
                continue
            if e.type == pygame.TEXTINPUT:
                if G.state == "login" and G.text_input_active:
                    if G.auth_focus == "username":
                        accepted = "".join(c for c in e.text if c.isalnum() or c in " -_")
                        G.auth_user = (G.auth_user + accepted)[:16]
                    else:
                        G.auth_pass = (G.auth_pass + e.text)[:128]
                    G.auth_error = ""
                elif G.M.get("k") == "tr" and G.text_input_active and not (G.M["fb"] and G.M["fb"][0]):
                    G.M["buf"] += e.text
                elif G.M.get("k") == "story_quiz" and G.text_input_active and G.M["feedback"] is None:
                    question = story_language_data(G.M["language"])["topics"][G.M["topic"]]["questions"][G.M["question"]]
                    if (G.M["topic"] == 4 or
                            question["type"] != "multiple_choice"):
                        G.M["input"] = (G.M["input"] + e.text)[:256]
                elif G.M.get("k") == "story_coding" and G.text_input_active:
                    modal = G.M
                    cursor = modal["cursor"]
                    anchor = modal.get("anchor")
                    if anchor is not None:
                        start, end = sorted((anchor, cursor))
                        modal["input"] = modal["input"][:start] + e.text + modal["input"][end:]
                        modal["cursor"] = start + len(e.text)
                        modal["anchor"] = None
                    else:
                        modal["input"] = (modal["input"][:cursor] + e.text +
                                          modal["input"][cursor:])[:2000]
                        modal["cursor"] = cursor + len(e.text)
                    modal["feedback"] = None
                continue
            if e.type == pygame.KEYUP and e.key == pygame.K_BACKSPACE:
                G.auth_backspace_held = False
                continue
            if e.type == pygame.WINDOWFOCUSLOST:
                G.auth_backspace_held = False
                continue
            if e.type == pygame.KEYDOWN:
                handle_key(e)
        update_auth_backspace(dt)
        if (G.M.get("fb") and not G.M["fb"][0]
                and G.t >= G.M.get("fb_until", float("inf"))):
            advance_question()
        update_background_music()
        if G.state == "login": login_screen()
        elif G.state == "admin": draw_admin()
        elif G.state == "home": draw_home()
        elif G.state == "leaderboard": draw_leaderboard()
        elif G.state == "progress": draw_progress()
        elif G.state == "obby":
            if G.M.get("k") != "settings":
                update_portal_obby(dt)
            draw_portal_obby()
        elif G.state == "shop" and G.shop_return in ("home", "leaderboard", "progress"):
            if G.shop_return == "home": draw_home()
            elif G.shop_return == "leaderboard": draw_leaderboard()
            else: draw_progress()
            shop_screen()
        elif G.state == "play":
            G.near = None
            draw_learning_background()
            if G.M: draw_modal()
        else:
            draw_world(); hud()
            if G.M: draw_modal()
            elif G.state == "pause": pause_screen()
            elif G.state == "shop": shop_screen()
        present()

SPRITE_RECTS = [[0, 0, 150, 113], [150, 0, 100, 130], [250, 0, 108, 130], [358, 0, 104, 130], [462, 0, 135, 130], [597, 0, 103, 130], [700, 0, 101, 130], [801, 0, 108, 130], [0, 130, 150, 126], [150, 130, 95, 130], [245, 130, 111, 130], [356, 130, 150, 126], [506, 130, 118, 130], [624, 130, 117, 130], [741, 130, 135, 130], [876, 130, 136, 130], [0, 260, 123, 130], [123, 260, 150, 130], [273, 260, 115, 130], [388, 260, 103, 130], [491, 260, 134, 130], [625, 260, 150, 123], [775, 260, 124, 130], [899, 260, 111, 130], [0, 390, 112, 130], [112, 390, 122, 130], [234, 390, 143, 130], [377, 390, 114, 130], [491, 390, 130, 130], [621, 390, 139, 130]]
SPRITE_RGB_DATA = "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"
SPRITE_ALPHA_DATA = "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"

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        import traceback
        crash_log = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "gamebuddy_crash.log")
        try:
            with open(crash_log, "w", encoding="utf-8") as crash_file:
                traceback.print_exception(
                    type(error), error, error.__traceback__, file=crash_file)
        except OSError as log_error:
            print("Could not write gamebuddy_crash.log: %s" % log_error,
                  file=sys.stderr)
        raise