import requests, random, sys, os, json, re, base64
from rich import print
from rich.progress import Progress, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from datetime import datetime
if os.name == "nt":
    import msvcrt
else:
    import tty, termios

if not os.path.exists("config.json"):
    with open("config.json", "w") as f:
        json.dump({
            "accounts": [],
            "delay": 900,
            "debug": False
        }, f, indent=4)

with open("config.json", "r") as f:
    config: dict = json.load(f)

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def current_time():
    return f"[bold bright_black]{datetime.now():%Y-%m-%d %H:%M:%S}[/]"

def time_taken(t: int | float) -> str:
    d, r = divmod(round(t), 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    return f"{d:02}:{h:02}:{m:02}:{s:02}" if d else f"{h:02}:{m:02}:{s:02}"

def getch():
    if os.name == "nt":
        ch = msvcrt.getch().decode("utf-8")
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def farm_progress(): 
    return Progress(
        *Progress.get_default_columns()[:3],
        TextColumn("[cyan]ETA:"),
        TimeRemainingColumn(),
        TextColumn("[yellow]Elapsed:"),
        TimeElapsedColumn(),
        "\033[D"
    )

def get_headers(account: int = None, token: str = None, user_id: int = None):
    if account != None:
        token = config['accounts'][account]['token']
        user_id = config['accounts'][account]['id']
    return {
        "accept": "application/json", 
        "authorization": f"Bearer {token}",
        "connection": "Keep-Alive",
        "content-type": "application/json",
        "cookie": f"jwt_token={token}",
        "origin": "https://www.duolingo.com",
        "user-agent": randomize_mobile_user_agent(),
        "x-amzn-trace-id": f"User={user_id}",
    }

def randomize_mobile_user_agent() -> str:
    duolingo_version = "6.26.2"
    android_version = random.randint(12, 15)
    build_codes = ['AE3A', 'TQ3A', 'TP1A', 'SP2A', 'UP1A', 'RQ3A', 'RD2A', 'SD2A']
    build_date = f"{random.randint(220101, 240806)}"
    build_suffix = f"{random.randint(1, 999):03d}"

    devices = [
        'sdk_gphone64_x86_64',
        'Pixel 6',
        'Pixel 6 Pro',
        'Pixel 7',
        'Pixel 7 Pro', 
        'Pixel 8',
        'SM-A536B',
        'SM-S918B',
        'SM-G998B',
        'SM-N986B',
        'OnePlus 9 Pro',
        'OnePlus 10 Pro',
        'M2102J20SG',
        'M2012K11AG'
    ]

    device = random.choice(devices)
    build_code = random.choice(build_codes)

    user_agent = f"Duodroid/{duolingo_version} Dalvik/2.1.0 (Linux; U; Android {android_version}; {device} Build/{build_code}.{build_date}.{build_suffix})"
    return user_agent

def get_duo_info(account: int, debug: bool = False):
    url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}"
    headers = get_headers(account)

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        if debug:
            print(f"{current_time()} [bold magenta][DEBUG][/] Retrieved Duolingo info for user {config['accounts'][account]['username']}")
        return response.json()
    else:
        if debug:
            print(
                f"{current_time()} [bold magenta][DEBUG][/] Failed to retrieve Duolingo info for user {config['accounts'][account]['username']}\n"
                f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
            )
        return None

def fetch_username_and_id(token: str, debug: bool = False):
    token = token.strip().replace(" ", "").replace("'", "").replace("\"", "")

    if not re.match(r'^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$', token):
        return " [bold red]Invalid token. Please ensure it's correctly formatted and try again.[/]"

    parts = token.split('.')
    payload_encoded = parts[1]
    payload_decoded = base64.urlsafe_b64decode(payload_encoded + "==").decode('utf-8')
    payload = json.loads(payload_decoded)
    user_id = payload.get('sub')

    headers = get_headers(token=token, user_id=user_id)
    url = f"https://www.duolingo.com/2017-06-30/users/{user_id}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        s = " [bold red]Failed to retrieve Duolingo profile. Please check your privacy settings or try again later.[/]"
        if debug:
            s += (
                f"\n[bold magenta][DEBUG][/] Status code {response.status_code}\n"
                f"[bold magenta][DEBUG][/] Content: {response.text}"
            )
        return s

    username = response.json().get("username", "Unknown")

    return {"username": username, "id": user_id}
