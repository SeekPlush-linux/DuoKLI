import json, sys, traceback, time, pytz, requests
_print = print
from rich import print
from tzlocal import get_localzone
from datetime import datetime
from utils import get_duo_info, get_headers, clear, current_time

VERSION = "v0.1.1 Beta"
TIMEZONE = str(get_localzone())

with open("config.json", "r") as f:
    config: dict = json.load(f)

DEBUG = config['debug']
title_string = f'\n   [bold][bright_green]Duo[/][bright_blue]KLI[/] [bright_green]Saver[/] [white]{VERSION}[/]{" [magenta][Debug Mode Enabled][/]" if DEBUG else ""}[/]'

def farm_xp(account, amount):
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Starting to farm {amount} XP for {config['accounts'][account]['username']}")
        original_amount = amount
    headers = get_headers(account)

    while True:
        now = datetime.now(pytz.timezone(TIMEZONE))
        base_xp = 30
        max_happy_hour = 469
        happy_hour_bonus = min(max_happy_hour, amount - base_xp) if amount > base_xp else 0
        dataget = {
            "awardXp": True,
            "completedBonusChallenge": True,
            "fromLanguage": "en",
            "hasXpBoost": False,
            "illustrationFormat": "svg",
            "isFeaturedStoryInPracticeHub": True,
            "isLegendaryMode": True,
            "isV2Redo": False,
            "isV2Story": False,
            "learningLanguage": "fr",
            "masterVersion": True,
            "maxScore": 0,
            "score": 0,
            "happyHourBonusXp": happy_hour_bonus,
            "startTime": now.timestamp(),
            "endTime": datetime.now(pytz.timezone(TIMEZONE)).timestamp(),
        }
        response = requests.post('https://stories.duolingo.com/api2/stories/fr-en-le-passeport/complete', headers=headers, json=dataget)
        if response.status_code == 200:
            response_data = response.json()
            amount -= response_data.get('awardedXp', 0)
            if DEBUG:
                print(f"{current_time()} [bold magenta][DEBUG][/] Farmed {response_data.get('awardedXp', 0)} XP")
        else:
            if DEBUG:
                _print("\a", end="")
                print(
                    f"{current_time()} [bold magenta][DEBUG][/] Failed to farm {base_xp + happy_hour_bonus} XP\n"
                    f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                    f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
                )

        if amount <= 0:
            break

    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Finished farming {original_amount - amount} XP for {config['accounts'][account]['username']}")

def leaderboard_registration(account):
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Attempting to enter a leaderboard for {config['accounts'][account]['username']}")
    duo_id = int(config['accounts'][account]['id'])
    headers = get_headers(account)

    url = f"https://www.duolingo.com/2017-06-30/users/{duo_id}/privacy-settings"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"{current_time()} [red]Failed to get privacy settings.[/]")
        if DEBUG:
            _print("\a", end="")
            print(
                f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
            )
        return
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Fetched privacy settings")
    data = response.json()
    privacy_settings = data.get('privacySettings', [])
    social_setting = next((setting for setting in privacy_settings if setting['id'] == 'disable_social'), None)
    was_private = social_setting['enabled'] if social_setting else False
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] {was_private = }")

    if was_private:
        url = f"https://www.duolingo.com/2017-06-30/users/{duo_id}/privacy-settings?fields=privacySettings"
        payload = {"DISABLE_SOCIAL": False}
        response = requests.patch(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"{current_time()} [red]Failed to set profile to public.[/]")
            if DEBUG:
                _print("\a", end="")
                print(
                    f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                    f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
                )
            return
        if DEBUG:
            print(f"{current_time()} [bold magenta][DEBUG][/] Set profile to public")

        time.sleep(2)

    farm_xp(account, 30)

    if was_private:
        url = f"https://www.duolingo.com/2017-06-30/users/{duo_id}/privacy-settings?fields=privacySettings"
        payload = {"DISABLE_SOCIAL": True}
        response = requests.patch(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"{current_time()} [red]Failed to restore privacy settings.[/]")
            if DEBUG:
                _print("\a", end="")
                print(
                    f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                    f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
                )
            return

def save_streak(account):
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Checking streak for {config['accounts'][account]['username']}")
    duo_info = get_duo_info(account, True)
    headers = get_headers(account)
    user_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(user_tz)
    streak_data = duo_info.get('streakData', {})
    current_streak = streak_data.get('currentStreak', {})
    should_do_lesson = True
    if current_streak:
        last_extended = current_streak.get('lastExtendedDate')
        if last_extended:
            last_extended = datetime.strptime(last_extended, "%Y-%m-%d")
            last_extended = user_tz.localize(last_extended)
            should_do_lesson = last_extended.date() < now.date()
    if not should_do_lesson:
        return
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Attempting to save streak")

    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')
    session_payload = {
        "challengeTypes": [
            "assist", "characterIntro", "characterMatch", "characterPuzzle",
            "characterSelect", "characterTrace", "characterWrite",
            "completeReverseTranslation", "definition", "dialogue",
            "extendedMatch", "extendedListenMatch", "form", "freeResponse",
            "gapFill", "judge", "listen", "listenComplete", "listenMatch",
            "match", "name", "listenComprehension", "listenIsolation",
            "listenSpeak", "listenTap", "orderTapComplete", "partialListen",
            "partialReverseTranslate", "patternTapComplete", "radioBinary",
            "radioImageSelect", "radioListenMatch", "radioListenRecognize",
            "radioSelect", "readComprehension", "reverseAssist",
            "sameDifferent", "select", "selectPronunciation",
            "selectTranscription", "svgPuzzle", "syllableTap",
            "syllableListenTap", "speak", "tapCloze", "tapClozeTable",
            "tapComplete", "tapCompleteTable", "tapDescribe", "translate",
            "transliterate", "transliterationAssist", "typeCloze",
            "typeClozeTable", "typeComplete", "typeCompleteTable",
            "writeComprehension"
        ],
        "fromLanguage": fromLanguage,
        "isFinalLevel": False,
        "isV2": True,
        "juicy": True,
        "learningLanguage": learningLanguage,
        "smartTipsVersion": 2,
        "type": "GLOBAL_PRACTICE"
    }
    session_url = "https://www.duolingo.com/2017-06-30/sessions"
    response = requests.post(session_url, headers=headers, json=session_payload)

    if response.status_code == 200:
        if DEBUG:
            print(f"{current_time()} [bold magenta][DEBUG][/] Created session")
        session_data = response.json()
    else:
        print(f"{current_time()} [red]An error has occurred while trying to create a session.[/]")
        if DEBUG:
            _print("\a", end="")
            print(
                f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
            )
        return
    if 'id' not in session_data:
        print(f"{current_time()} [red]Session ID not found in response data.[/]")
        if DEBUG:
            _print("\a", end="")
        return

    start_time = now.timestamp()
    end_time = datetime.now(user_tz).timestamp()
    update_payload = {
        **session_data,
        "heartsLeft": 5,
        "startTime": start_time,
        "endTime": end_time,
        "enableBonusPoints": False,
        "failed": False,
        "maxInLessonStreak": 9,
        "shouldLearnThings": True
    }
    update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session_data['id']}"

    response = requests.put(update_url, headers=headers, json=update_payload)
    if response.status_code == 200:
        if DEBUG:
            print(f"{current_time()} [bold magenta][DEBUG][/] Updated session")
        update_data = response.json()
        if update_data.get('xpGain') is not None:
            print(f"{current_time()} [green]Saved streak![/]")
            if DEBUG:
                print(f"{current_time()} [bold magenta][DEBUG][/] {update_data.get('xpGain') = }")
        else:
            print(f"{current_time()} [red]Failed to save streak.[/]")
            if DEBUG:
                _print("\a", end="")
    else:
        print(f"{current_time()} [red]Failed to update session to save streak.[/]")
        if DEBUG:
            _print("\a", end="")
            print(
                f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
            )

def save_league(account, position):
    if DEBUG:
        print(f"{current_time()} [bold magenta][DEBUG][/] Checking league position for {config['accounts'][account]['username']}")
    headers = get_headers(account)
    duo_id = int(config['accounts'][account]['id'])

    url = (f"https://duolingo-leaderboards-prod.duolingo.com/leaderboards/7d9f5dd1-8423-491a-91f2-2532052038ce/users/{duo_id}"
           f"?client_unlocked=true&get_reactions=true&_={int(time.time() * 1000)}")
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            if DEBUG:
                _print("\a", end="")
                print(
                    f"{current_time()} [bold magenta][DEBUG][/] Failed to fetch user data on leaderboard\n"
                    f"{current_time()} [bold magenta][DEBUG][/] Status code: {response.status_code}\n"
                    f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
                )
            leaderboard_registration(account)
            return
        leaderboard_data = response.json()
        if not leaderboard_data or 'active' not in leaderboard_data:
            leaderboard_registration(account)
            return
        active_data = leaderboard_data.get('active', None)
        if active_data is None or 'cohort' not in active_data:
            leaderboard_registration(account)
            return
        cohort_data = active_data.get('cohort', {})
        rankings = cohort_data.get('rankings', [])
        current_user = next((user_data for user_data in rankings if user_data['user_id'] == duo_id), None)
        if current_user is None:
            leaderboard_registration(account)
            return

        current_score = current_user['score']
        current_rank = next((index + 1 for index, user_data in enumerate(rankings) if user_data['user_id'] == duo_id), None)
        if DEBUG:
            print(
                f"{current_time()} [bold magenta][DEBUG][/] {current_score = }\n"
                f"{current_time()} [bold magenta][DEBUG][/] {current_rank = }"
            )
        if current_rank is not None and current_rank <= position:
            break
        target_user = rankings[position - 1] if position and position - 1 < len(rankings) else None
        if DEBUG:
            print(f"{current_time()} [bold magenta][DEBUG][/] {target_user = }")
        if target_user is None:
            break
        target_score = target_user['score']
        xp_needed = (target_score - current_score) + 60
        if DEBUG:
            print(
                f"{current_time()} [bold magenta][DEBUG][/] {target_score = }\n"
                f"{current_time()} [bold magenta][DEBUG][/] {xp_needed = }"
            )
        if xp_needed > 0:
            if DEBUG:
                print(f"{current_time()} [bold magenta][DEBUG][/] Attempting to save league position")
            farm_xp(account, xp_needed)
            print(f"{current_time()} [green]Saved league position![/]")

try:
    clear()
    print(title_string)
    print("\n[yellow]  Press Ctrl+C to stop the saver.[/]\n")
    print("[blue]  Starting saver...[/]", end="")
    _print("\r", end="")

    if not any([acc['autostreak'] for acc in config['accounts']]) and not any([acc['autoleague']['active'] for acc in config['accounts']]):
        print("[red]  There are no accounts with a saver feature enabled![/]\n")
        sys.exit()

    while True:
        for account in range(len(config['accounts'])):
            autostreak = config['accounts'][account]['autostreak']
            autoleague = config['accounts'][account]['autoleague']['active']
            league_pos = config['accounts'][account]['autoleague']['position']
            delay      = config['delay']

            if autostreak or autoleague:
                if DEBUG:
                    print(f"{current_time()} [bold magenta][DEBUG][/] ----------------------------------------")
                print(f"{current_time()} [blue]Checking [bold]{config['accounts'][account]['username']}[/] ...[/]")
                try:
                    save_streak(account) if autostreak else None
                    save_league(account, league_pos) if autoleague and league_pos else None
                except Exception as e:
                    _print("\a", end="")
                    print(f"[red][bold]An unexpected error occurred while trying to save {config['accounts'][account]['username']}: {e}[/]\nDetailed error:[/]")
                    traceback.print_exc()

        print(f"{current_time()} [blue]Waiting {delay} seconds...[/]")
        time.sleep(delay)

except KeyboardInterrupt:
    _print("\r\033[2K", end="")
    print("\n  [bright_red]Stopping saver...[/]\n")
    sys.exit()

except Exception as e:
    _print("\a", end="")
    print(f"[red][bold]An unexpected error occurred: {e}[/]\nDetailed error:[/]")
    traceback.print_exc()
    print("\n  [bright_red]Stopping saver...[/]\n")
    sys.exit()
