import requests, pytz, sys, os, json, traceback, time, concurrent.futures, threading
_print = print
from rich import print
from datetime import datetime, timedelta
from tzlocal import get_localzone
from utils import (getch, fint, inp, current_time, time_taken, get_headers, get_duo_info, clear,
                   fetch_username_and_id, farm_progress, warn_request_count, ratelimited_warning)

# TODO: Port some functions from [my private project] to here
# TODO: Add questsaver function to the saver script
# TODO: Implement multi-threading and proxies
# TODO: Implement setup screen when no accounts exist in config file
# TODO: Add more items to the items menu
# TODO: Auto login to the preferred account
# TODO: Add Verbose Mode in addition to Debug Mode
# TODO: Fix DuoKLI crashing when trying to farm on the newly added account right after adding it
# TODO: Implement "Check for updates" setting that will check the GitHub repo for updates, automatically update DuoKLI if an update is found
# TODO: Write debug info into a log file

VERSION = "v1.2.0"
TIMEZONE = str(get_localzone())

with open("config.json", "r") as f:
    config: dict = json.load(f)

DEBUG = config['debug']
def title_string() -> str:
    return f'\n   [bold][bright_green]Duo[/][bright_blue]KLI[/] [white]{VERSION}[/]{" [magenta][Debug Mode Enabled][/]" if DEBUG else ""}[/]'

def start_task(type: str, account: int, request_amount: bool = True) -> bool:
    if request_amount:
        try:
            amount = int(inp(f" Enter amount of {type}"))
        except ValueError:
            return False

    if type.lower() in ['gems', 'fast gems']:
        if amount == 0:
            if not warn_request_count(0):
                return False
        else:
            per_request = 30
            requests_needed = (amount + per_request - 1) // per_request
            if not warn_request_count(requests_needed):
                return False

    if type == "Super Duolingo":
        print(" [bright_yellow]Activating 3 days of Super Duolingo...[/]", end="")
    else:
        print("\n  [bright_yellow]Press Ctrl+C to stop farming.[/]\n")
        print(f" [blue]Starting to farm {fint(amount)} {type}...[/]", end="")
    _print("\r", end="")

    if type.lower() == "xp":
        farm = xp_farm(amount, account)
    elif type.lower() == "gems":
        farm = gem_farm(amount, account)
    elif type.lower() == "fast gems":
        farm = fast_gem_farm(amount, account)
    elif type.lower() == "streak days":
        farm = streak_farm(amount, account)
    elif type.lower() == "super duolingo":
        farm = activate_super(account)

    if farm and type.lower() in ["xp", "gems", "fast gems", "streak days"]:
        print(
            f"\n [green]✅ Successfully farmed {farm['total']:,} {type}![/]\n"
            f" [blue]🕒 Time Taken: {time_taken(farm['end'] - farm['start'])}[/]"
        )

    _print("\033[?25l", end="")
    print("\n [bright_yellow]Press any key to continue.[/]")
    getch()
    return True

def xp_farm(amount, account):
    if amount < 0:
        print(" [red]Cannot farm negative XP![/]")
        return

    url = f'https://stories.duolingo.com/api2/stories/fr-en-le-passeport/complete'
    headers = get_headers(account)

    total_xp = 0
    xp_left = amount if amount else sys.maxsize

    with farm_progress("XP", "yellow", amount == 0) as prog:
        task = prog.add_task("", total=amount if amount else None)
        start = time.monotonic()
        while True:
            try:
                cur_time = datetime.now(pytz.timezone(TIMEZONE))
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
                    "happyHourBonusXp": 469 if xp_left >= 499 else xp_left - 30,
                    "startTime": cur_time.timestamp(),
                    "endTime": datetime.now(pytz.timezone(TIMEZONE)).timestamp(),
                }

                response = requests.post(url, headers=headers, json=dataget, timeout=10)

                if response.status_code == 200:
                    result = response.json()
                    total_xp += result.get('awardedXp', 0)
                    prog.update(task, completed=total_xp)
                    xp_left -= result.get('awardedXp', 0)
                else:
                    print(f" [red]Failed to farm {499 if xp_left >= 499 else xp_left} XP ({total_xp:,}/{fint(amount)} XP)[/]")
                if DEBUG:
                    print(
                        f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                        f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}\n"
                    )
                if xp_left <= 0:
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f" [bold red]An error occurred ({total_xp:,}/{fint(amount)} XP): {e}[/]")

    end = time.monotonic()
    return {'total': total_xp, 'start': start, 'end': end}

def gem_farm(amount, account):
    if amount < 0:
        print(" [red]Cannot farm negative gems![/]")
        return

    headers = get_headers(account)
    duo_info = get_duo_info(account, DEBUG)
    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')

    per_request = 30
    requests_needed = (amount + per_request - 1) // per_request
    expected_total = requests_needed * per_request
    total_gems = 0
    gems_left = expected_total if amount else sys.maxsize

    with farm_progress("gems", "cyan", amount == 0) as prog:
        task = prog.add_task("", total=expected_total if amount else None)
        start = time.monotonic()
        while True:
            try:
                url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}/rewards/SKILL_COMPLETION_BALANCED-…-2-GEMS"
                payload = {"consumed": True, "fromLanguage": fromLanguage, "learningLanguage": learningLanguage}

                response = requests.patch(url, headers=headers, json=payload, timeout=10)

                if response.status_code == 200:
                    total_gems += per_request
                    prog.update(task, completed=total_gems)
                    gems_left -= per_request
                elif response.status_code == 403:
                    ratelimited_warning()
                    return
                else:
                    print(f" [red]Failed to farm {per_request} gems ({total_gems:,}/{fint(expected_total)} gems)[/]")
                if DEBUG:
                    print(
                        f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                        f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}\n"
                    )
                if gems_left <= 0:
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f" [bold red]An error occurred ({total_gems:,}/{fint(expected_total)} gems): {e}[/]")

    end = time.monotonic()
    return {'total': total_gems, 'start': start, 'end': end}

def fast_gem_farm(amount, account):
    if amount < 0:
        print(" [red]Cannot farm negative gems![/]")
        return

    headers = get_headers(account)
    duo_info = get_duo_info(account, DEBUG)
    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')

    per_request = 30
    requests_needed = (amount + per_request - 1) // per_request
    expected_total = requests_needed * per_request
    total_gems = 0

    stop_event = threading.Event()

    with farm_progress("gems", "cyan", amount == 0) as prog:
        task = prog.add_task("", total=expected_total if amount else None)
        start = time.monotonic()
        url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}/rewards/SKILL_COMPLETION_BALANCED-…-2-GEMS"
        payload = {"consumed": True, "fromLanguage": fromLanguage, "learningLanguage": learningLanguage}

        def do_patch():
            if stop_event.is_set():
                return None, "stopped"
            try:
                resp = requests.patch(url, headers=headers, json=payload, timeout=10)
                return resp.status_code, getattr(resp, 'text', '')
            except Exception as ex:
                return None, str(ex)

        max_workers = min(20, requests_needed) if requests_needed > 0 else 1 if amount else 20
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        futures = []
        try:
            while not stop_event.is_set():
                futures = [executor.submit(do_patch) for _ in range(requests_needed if amount else 1000)]
                for fut in concurrent.futures.as_completed(futures):
                    if stop_event.is_set():
                        break
                    try:
                        status, content = fut.result()
                    except Exception as e:
                        status, content = None, str(e)
                    if status == 200:
                        total_gems += per_request
                        prog.update(task, completed=total_gems)
                    elif status == 403:
                        ratelimited_warning()
                        stop_event.set()
                        return
                    else:
                        print(f" [red]Failed to farm {per_request} gems ({total_gems:,}/{fint(expected_total)} gems)[/]")
                    if DEBUG:
                        print(
                            f"{current_time()} [bold magenta][DEBUG][/] Status code {status}\n"
                            f"{current_time()} [bold magenta][DEBUG][/] Content: {content}\n"
                        )
                if amount:
                    break
        except KeyboardInterrupt:
            stop_event.set()
            for fut in futures:
                fut.cancel()
        except Exception as e:
            print(f" [bold red]An error occurred ({total_gems:,}/{fint(expected_total)} gems): {e}[/]")
        finally:
            try:
                executor.shutdown(wait=False)
            except Exception:
                pass

    end = time.monotonic()
    return {'total': total_gems, 'start': start, 'end': end}

def streak_farm(amount, account):
    duo_info = get_duo_info(account, DEBUG)
    headers = get_headers(account)
    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')

    streak_data = duo_info.get('streakData', {})
    current_streak = streak_data.get('currentStreak', {})

    user_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(user_tz)
    day_count = 0
    is_finishing = False

    if not current_streak:
        streak_start_date = now
    else:
        streak_start_date = datetime.strptime(current_streak.get('startDate'), "%Y-%m-%d")
        if streak_start_date <= datetime(1, 1, 2, 0, 0):
            print(" [yellow]You have already reached the maximum amount of streak days possible![/]")
            return

    with farm_progress("streak days", "sandy_brown", amount == 0) as prog:
        task = prog.add_task("", total=amount if amount else None)
        amount = amount if amount else sys.maxsize
        start = time.monotonic()
        while True:
            try:
                try:
                    simulated_day = streak_start_date - timedelta(days=day_count)
                    if simulated_day <= datetime(1, 1, 2, 0, 0):
                        print(" [green]Reached the maximum amount of streak days possible![/]")
                        end = time.monotonic()
                        return {'total': day_count, 'start': start, 'end': end}
                except:
                    print(" [green]Reached the maximum amount of streak days possible![/]")
                    end = time.monotonic()
                    return {'total': day_count, 'start': start, 'end': end}

                if day_count == amount:
                    is_finishing = True
                    print(" [blue]Finishing up...[/]\n")

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

                response = requests.post("https://www.duolingo.com/2017-06-30/sessions", headers=headers, json=session_payload, timeout=10)

                if response.status_code == 200:
                    session_data = response.json()
                    if DEBUG:
                        print(f"{current_time()} [bold magenta][DEBUG][/] Session created")
                else:
                    print(f" [red]Failed to create a session ({day_count:,}/{fint(amount)} days)[/]")
                    if DEBUG:
                        print(
                            f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                            f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
                        )
                    continue
                if 'id' not in session_data:
                    print(f" [red]Session ID not found in response data ({day_count:,}/{fint(amount)} days)[/]")
                    if DEBUG:
                        print(
                            f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                            f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
                        )
                    continue

                try:
                    start_timestamp = int((simulated_day - timedelta(seconds=1)).timestamp())
                    end_timestamp = int(simulated_day.timestamp())
                except ValueError:
                    print(" [green]Reached the maximum amount of streak days possible![/]")
                    end = time.monotonic()
                    return {'total': day_count, 'start': start, 'end': end}

                update_payload = {
                    **session_data,
                    "heartsLeft": 5,
                    "startTime": start_timestamp,
                    "endTime": end_timestamp,
                    "enableBonusPoints": False,
                    "failed": False,
                    "maxInLessonStreak": 9,
                    "shouldLearnThings": True
                }

                response = requests.put(f"https://www.duolingo.com/2017-06-30/sessions/{session_data['id']}", headers=headers, json=update_payload, timeout=10)

                if response.status_code == 200:
                    day_count += 1
                    prog.update(task, completed=day_count) if not is_finishing else None
                    if DEBUG:
                        print(f"{current_time()} [bold magenta][DEBUG][/] Session updated")
                else:
                    print(f" [red]Failed to extend streak ({day_count:,}/{fint(amount)} days)[/]")
                if DEBUG:
                    print(
                        f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                        f"{f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}" if response.status_code != 200 else ""}"
                    )

                if day_count > amount:
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f" [bold red]An error occurred ({day_count:,}/{fint(amount)} days): {e}[/]")

    end = time.monotonic()
    return {'total': day_count-1, 'start': start, 'end': end}

def activate_super(account):
    url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}/shop-items"
    headers = get_headers(account)
    json_data = {"itemName":"immersive_subscription","productId":"com.duolingo.immersive_free_trial_subscription"}

    response = requests.post(url, headers=headers, json=json_data, timeout=10)

    try:
        res_json = response.json()
    except requests.exceptions.JSONDecodeError:
        print(" [red]Failed to activate 3 days of Duolingo Super.[/]")
        if response.status_code == 200:
            print(
                " [yellow]However, Duolingo returned status OK (status code 200).\n"
                " Still, you most likely didn't get Duolingo Super.[/]"
            )
        elif response.status_code == 400:
            print(" [red]You're most likely banned from getting Duolingo Super trials.[/]")
        if DEBUG:
            print(
                f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
                f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
            )
        return

    if response.status_code == 200 and "purchaseId" in res_json:
        print(" [green]Successfully activated 3 days of Duolingo Super![/]")
        print(" [blue]Note that you most likely didn't actually get Duolingo Super,\n due to Duolingo's new detection system.[/]")
    else:
        print(" [red]Failed to activate 3 days of Duolingo Super.[/]")
    if DEBUG:
        print(
            f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
            f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
        )

def give_item(account, item):
    item_id = item[0]
    item_name = item[1]
    headers = get_headers(account)
    duo_info = get_duo_info(account, DEBUG)
    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')

    if item_id == "xp_boost_refill":
        inner_body = {
            "isFree": False,
            "learningLanguage": learningLanguage,
            "subscriptionFeatureGroupId": 0,
            "xpBoostSource": "REFILL",
            "xpBoostMinutes": 15,
            "xpBoostMultiplier": 3,
            "id": item_id
        }
        payload = {
            "includeHeaders": True,
            "requests": [
                {
                    "url": f"/2023-05-23/users/{config['accounts'][account]['id']}/shop-items",
                    "extraHeaders": {},
                    "method": "POST",
                    "body": json.dumps(inner_body)
                }
            ]
        }
        url = "https://ios-api-2.duolingo.com/2023-05-23/batch"
        headers["host"] = "ios-api-2.duolingo.com"
        headers["x-amzn-trace-id"] = f"User={config['accounts'][account]['id']}"
        data = payload
    else:
        data = {
            "itemName": item_id,
            "isFree": True,
            "consumed": True,
            "fromLanguage": fromLanguage,
            "learningLanguage": learningLanguage
        }
        url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}/shop-items"

    response = requests.post(url, headers=headers, json=data, timeout=10)
    if response.status_code == 200:
        print(f" [green]Successfully received item \"{item_name}\"![/]")
    else:
        print(f" [red]Failed to receive item \"{item_name}\".[/]")
    if DEBUG:
        print(
            f"{current_time()} [bold magenta][DEBUG][/] Status code {response.status_code}\n"
            f"{current_time()} [bold magenta][DEBUG][/] Content: {response.text}"
        )

# Program starts here ------------------------------------------------------------------------------------------------

try:
    _print("\033[?25l")
    while True:
        clear()
        print(title_string())
        print("\n  [bright_magenta]Accounts: [/]")
        for i in range(len(config['accounts'])):
            print(f"  {i+1}: {config['accounts'][i]['username']}")
        print("\n  [bright_blue]9. Manage Accounts[/]")
        print("  [bright_red]0. Quit[/]")
        while True:
            try:
                account = int(getch())
                if account == 9:
                    while True:
                        clear()
                        acc_manager_option = ""
                        acc_manager_menu = [
                            title_string(),
                            f"\n  [bright_magenta]Accounts:[/]",
                            *[f"  {i+1}: {acc['username']}" for i, acc in enumerate(config['accounts'])],
                            f"\n  [bright_green]A. Add Account[/]",
                            f"  [bright_yellow]Select an account to edit it.[/]",
                            f"\n  [bright_red]0. Go Back[/]\n"
                        ]
                        for string in acc_manager_menu:
                            print(string)
                        while acc_manager_option not in [*[str(i) for i in range(len(config['accounts']) + 1)], "A"]:
                            acc_manager_option = getch().upper()
                        clear()
                        for i, s in enumerate(acc_manager_menu):
                            print(s if i < 2 or i == len(acc_manager_menu)-1 else f"[bold bright_yellow]{s}[/]" if f" {acc_manager_option.upper()}: " in s else s)
                        if acc_manager_option == "0":
                            with open("config.json", "w") as f:
                                json.dump(config, f, indent=4)
                            break
                        elif acc_manager_option.isdigit():
                            acc_to_update = int(acc_manager_option)-1
                            print(" [yellow]U. Update Token[/] | [magenta]J. Move Down[/] | [magenta]K. Move Up[/] | [red]R. Remove[/]  [bright_black][Esc to cancel][/]")
                            while acc_manager_option not in ['\033', 'U', 'J', 'K', 'R']:
                                acc_manager_option = getch().upper()
                            if acc_manager_option == "\033":
                                continue
                            elif acc_manager_option == "U":
                                try:
                                    new_token = inp("\n Enter your new token")
                                except ValueError:
                                    continue
                                if not new_token:
                                    continue
                                print(" [bright_yellow]Updating your account credentials, please wait...[/]", end='\r')
                                new_account = fetch_username_and_id(new_token, DEBUG)
                                _print("\033[2K", end="")
                                if isinstance(new_account, str):
                                    print(new_account)
                                    print(" [bright_yellow]Press any key to continue.[/]")
                                    getch()
                                    continue
                                config['accounts'][acc_to_update]['username'] = new_account['username']
                                config['accounts'][acc_to_update]['id'] = new_account['id']
                                config['accounts'][acc_to_update]['token'] = new_token
                                print(f" [bright_green]Successfully updated account {new_account['username']}![/]")
                                print(" [bright_yellow]Press any key to continue.[/]")
                                getch()
                            elif acc_manager_option == "J":
                                if acc_to_update != len(config['accounts'])-1:
                                    config['accounts'][acc_to_update], config['accounts'][acc_to_update+1] = config['accounts'][acc_to_update+1], config['accounts'][acc_to_update]
                            elif acc_manager_option == "K":
                                if acc_to_update != 0:
                                    config['accounts'][acc_to_update], config['accounts'][acc_to_update-1] = config['accounts'][acc_to_update-1], config['accounts'][acc_to_update]
                            elif acc_manager_option == "R":
                                print(f"\n [bright_red]Are you sure you want to remove {config['accounts'][acc_to_update]['username']}? \\[y/N][/]")
                                if getch().upper() in ["Y", "\r"]:
                                    config['accounts'].pop(acc_to_update)
                        elif acc_manager_option == "A":
                            try:
                                new_token = inp(" Enter your account's token")
                            except ValueError:
                                continue
                            if not new_token:
                                continue
                            print(" [bright_yellow]Adding your account, please wait...[/]", end='\r')
                            new_account = fetch_username_and_id(new_token, DEBUG)
                            _print("\033[2K", end="")
                            if isinstance(new_account, str):
                                print(new_account)
                                print(" [bright_yellow]Press any key to continue.[/]")
                                getch()
                                continue
                            config['accounts'].append({
                                "username": new_account['username'],
                                "id": new_account['id'],
                                "token": new_token,
                                "autostreak": False,
                                "autoleague": {
                                    "active": False,
                                    "position": None
                                }
                            })
                            print(f" [bright_green]Successfully added account {new_account['username']}![/]")
                            print(" [bright_yellow]Press any key to continue.[/]")
                            getch()
                    break
                elif account == 0:
                    print("\n  [bright_red]Exiting program...[/]")
                    _print("\033[?25h", end="")
                    sys.exit()
                account -= 1
                config['accounts'][account]
                break
            except (IndexError, ValueError) as e:
                pass
        if account != 9:
            break

    while True:
        option = ""
        main_menu = [
            title_string(),
           f"\n  [bold bright_green]Logged in as {config['accounts'][account]['username']}[/]",
            "  [bright_yellow]1. XP[/]",
            "  [bright_cyan]2. Gem[/]",
            "  [sandy_brown]3. Streak[/]",
            "  [medium_purple1]4. Super Duolingo[/]",
            "  [pink1]5. Items Menu[/]",
            "  [bright_green]6. Saver[/]\n",
            "  [bright_blue]9. Settings[/]",
            "  [bright_red]0. Quit[/]\n",
        ]
        clear()
        for string in main_menu:
            print(string)
        while option not in ['1', '2', '3', '4', '5', '6', '9', '0']:
            option = getch().upper()
        clear()
        for string in main_menu:
            print(string if main_menu.index(string) < 2 else f"[bold]{string}[/]" if f"{option.upper()}. " in string else f"  [bright_black]{string.split("]", maxsplit=1)[1]}")
        if option == "1":
            start_task("XP", account)
        elif option == "2":
            while True:
                methods = {
                    "1": "gems",
                    "2": "fast gems",
                }
                methods_option = ""
                clear()
                methods_menu = [
                    title_string(),
                    "\n  [bold bright_blue]Choose a gem farm method:[/]",
                    "  [bright_cyan]1. Gems[/]",
                    "  [bright_yellow]2. Fast Gems[/]\n",
                    "  [bright_red]0. Go Back[/]\n",
                ]
                for string in methods_menu:
                    print(string)
                while methods_option not in ['1', '2', '0']:
                    methods_option = getch().upper()
                clear()
                for string in methods_menu:
                    print(string if methods_menu.index(string) < 2 else f"[bold]{string}[/]" if f"{methods_option.upper()}. " in string else f"  [bright_black]{string.split("]", maxsplit=1)[1]}")
                if methods_option in ['1', '2']:
                    success = start_task(methods[methods_option], account)
                    if success:
                        break
                elif methods_option == "0":
                    break
        elif option == "3":
            start_task("streak days", account)
        elif option == "4":
            start_task("Super Duolingo", account, request_amount=False)
        elif option == "5":
            while True:
                items = {
                    "1": ("society_streak_freeze", "Streak Freeze"),
                    "2": ("streak_repair", "Streak Repair"),
                    "3": ("heart_segment", "Heart Segment"),
                    "4": ("health_refill", "Health Refill"),
                    "5": ("xp_boost_stackable", "XP Boost Stackable"),
                    "6": ("general_xp_boost", "General XP Boost"),
                    "7": ("xp_boost_15", "XP Boost x2 15 Mins"),
                    "8": ("xp_boost_60", "XP Boost x2 60 Mins"),
                    "9": ("xp_boost_refill", "XP Boost x3 15 Mins"),
                    "Q": ("early_bird_xp_boost", "Early Bird XP Boost"),
                    "W": ("row_blaster_150", "Row Blaster 150"),
                    "E": ("row_blaster_250", "Row Blaster 250"),
                }
                items_option = ""
                clear()
                items_menu = [
                    title_string(),
                    "\n  [bold bright_blue]Choose an item to claim:[/]",
                    "  [bright_cyan]1. Streak Freeze[/]",
                    "  [sandy_brown]2. Streak Repair[/]",
                    "  [bright_red]3. Heart Segment[/]",
                    "  [bright_red]4. Health Refill[/]",
                    "  [bright_yellow]5. XP Boost Stackable[/]",
                    "  [bright_yellow]6. General XP Boost[/]",
                    "  [bright_yellow]7. XP Boost x2 15 Mins[/]",
                    "  [bright_yellow]8. XP Boost x2 60 Mins[/]",
                    "  [bright_yellow]9. XP Boost x3 15 Mins[/]",
                    "  [bright_yellow]Q. Early Bird XP Boost[/]",
                    "  [bright_magenta]W. Row Blaster 150[/]",
                    "  [bright_magenta]E. Row Blaster 250[/]\n",
                    "  [bright_red]0. Go Back[/]\n",
                ]
                for string in items_menu:
                    print(string)
                while items_option not in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'Q', 'W', 'E', '0']:
                    items_option = getch().upper()
                clear()
                for string in items_menu:
                    print(string if items_menu.index(string) < 2 else f"[bold]{string}[/]" if f"{items_option.upper()}. " in string else f"  [bright_black]{string.split("]", maxsplit=1)[1]}")
                if items_option in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'Q', 'W', 'E']:
                    print(f" [bright_yellow]Giving \"{items[items_option][1]}\"...[/]", end="")
                    _print("\r", end="")
                    give_item(account, items[items_option])
                    print(" [bright_yellow]Press any key to continue.[/]")
                    getch()
                elif items_option == "0":
                    break
        elif option == "6":
            clear()
            os.system(f"{sys.executable} saver.py")
            print(" [bright_yellow]Press any key to continue.[/]")
            getch()
        elif option == "9":
            while True:
                setting_option = ""
                clear()
                settings_menu = [
                    title_string(),
                    "\n  [bold bright_blue]Settings:[/]",
                    "  1. Saver Settings: [bold bright_yellow]Configure[/]",
                   f"  2. Debug Mode: {"[bright_green]Enabled[/]" if config['debug'] else "[bright_red]Disabled[/]"}",
                    "",
                    "  [bright_red]0. Go Back[/]\n",
                ]
                for string in settings_menu:
                    print(string)
                while setting_option not in ['1', '2', '0']:
                    setting_option = getch()
                clear()
                for string in settings_menu:
                    print(string if settings_menu.index(string) < 2 else f"[bold bright_yellow]{string}[/]" if f"{setting_option.upper()}. " in string else string)
                if setting_option == "1":
                    space = max(len(acc['username']) for acc in config['accounts']) + 1
                    enabled = "[bright_green]✅[/]"
                    disabled = "[bright_red]❌[/]"
                    while True:
                        saver_row_option = ""
                        saver_col_option = ""
                        clear()
                        saver_settings_menu = [
                            title_string(),
                           f"\n  [bold]{"Accounts":{space}}  Streaksaver   Leaguesaver   Position[/]",
                           *[f"  {i+1}. {config['accounts'][i]['username']:{space}}    {enabled if config['accounts'][i]['autostreak'] else disabled}{" "*12}{enabled if config['accounts'][i]['autoleague']['active'] else disabled}{" "*10}{config['accounts'][i]['autoleague']['position'] if config['accounts'][i]['autoleague']['position'] else disabled}" for i in range(len(config['accounts']))],
                            "\n  [bright_red]0. Go Back[/]"
                        ]
                        for string in saver_settings_menu:
                            print(string)
                        while saver_row_option not in [str(i) for i in range(len(config['accounts']) + 1)]:
                            saver_row_option = getch()
                        clear()
                        for string in saver_settings_menu:
                            print(string if saver_settings_menu.index(string) < 2 or saver_settings_menu.index(string) == len(saver_settings_menu)-1 else f"[bold bright_yellow]{string}[/]" if f" {saver_row_option.upper()}. " in string else string)
                        if saver_row_option == "0":
                            break
                        print("\n [sandy_brown]Q. Streaksaver[/] | [bright_green]W. Leaguesaver[/] | [cyan]E. Position[/]  [bright_black][Any other key to cancel][/]")
                        saver_col_option = getch().upper()
                        if saver_col_option == "Q":
                            config['accounts'][int(saver_row_option)-1]['autostreak'] = not config['accounts'][int(saver_row_option)-1]['autostreak']
                        elif saver_col_option == "W":
                            config['accounts'][int(saver_row_option)-1]['autoleague']['active'] = not config['accounts'][int(saver_row_option)-1]['autoleague']['active']
                        elif saver_col_option == "E":
                            try:
                                amount = int(input("\n Enter league position [Enter to cancel, 0 to remove]: "))
                            except ValueError:
                                continue
                            config['accounts'][int(saver_row_option)-1]['autoleague']['position'] = amount if amount >= 1 and amount <= 30 else None
                elif setting_option == "2":
                    DEBUG = config['debug'] = not config['debug']
                elif setting_option == "0":
                    with open("config.json", "w") as f:
                        json.dump(config, f, indent=4)
                    break
        elif option == "0":
            print("  [bright_red]Exiting program...[/]")
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            _print("\033[?25h", end="")
            sys.exit()

except KeyboardInterrupt:
    print("\n\n  [bright_red]Exiting program...[/]")
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    _print("\033[?25h", end="")
    sys.exit()

except Exception as e:
    print(f"[red][bold]An unexpected error occurred: {e}[/]\nDetailed error:[/]")
    traceback.print_exc()
    print("\n  [bright_red]Exiting program...[/]")
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    _print("\033[?25h", end="")
    sys.exit()
