import requests, random, pytz, sys, os, json, traceback
_print = print
from rich import print
from datetime import datetime, timedelta
from tzlocal import get_localzone
from utils import getch, get_headers, get_duo_info, clear, fetch_username_and_id

# TODO: Use rich's progress bars for farms
# TODO: Add endless farming
# TODO: Add "Time Taken" to farm functions
# TODO: Port some functions from [my private project] to here
# TODO: Add questsaver function to the saver script

VERSION = "v1.0.0"
TIMEZONE = str(get_localzone())

with open("config.json", "r") as f:
    config: dict = json.load(f)

DEBUG = config['debug']
def title_string():
    return f'\n   [bold][bright_green]Duo[/][bright_blue]KLI[/] [white]{VERSION}[/]{" [magenta][Debug Mode Enabled][/]" if DEBUG else ""}[/]'

def xp_farm(amount, account):
    if amount <= 0:
        print("[red]Cannot farm 0 or negative XP![/]")
        return

    url = f'https://stories.duolingo.com/api2/stories/fr-en-le-passeport/complete'
    headers = get_headers(account)

    error_messages = ""
    error_count = 0
    total_xp = 0
    xp_left = amount

    try:
        while True:
            current_time = datetime.now(pytz.timezone(TIMEZONE))
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
                "startTime": current_time.timestamp(),
                "endTime": datetime.now(pytz.timezone(TIMEZONE)).timestamp(),
            }

            response = requests.post(url, headers=headers, json=dataget)
            if response.status_code == 200:
                result = response.json()
                total_xp += result.get('awardedXp', 0)
                _print("\r\033[2K", end="") if not DEBUG else None
                print(f"[green]Farmed {total_xp}/{amount} XP (+{result.get('awardedXp', 0)} XP)[/]", end="" if not DEBUG else "\n")
                xp_left -= result.get('awardedXp', 0)
            else:
                if not DEBUG:
                    error_messages += f"\n[red]Failed to farm {499 if xp_left >= 499 else xp_left} XP ({total_xp}/{amount} XP)[/]"
                    error_count += 1
                    print(error_messages, end="")
                    _print(f"\r\033[{error_count}A", end="")
                else:
                    print(f"[red]Failed to farm {499 if xp_left >= 499 else xp_left} XP ({total_xp}/{amount} XP)[/]")
            if DEBUG:
                print(
                    f"[bold magenta][DEBUG][/] Status code {response.status_code}\n"
                    f"[bold magenta][DEBUG][/] Content: {response.text}"
                )
            if xp_left <= 0:
                break
    except KeyboardInterrupt:
        pass

    _print("\r\033[2K", end="") if not DEBUG else None
    print(f"[green]Successfully farmed {total_xp} XP![/]")

def gem_farm(amount, account):
    if amount <= 0:
        print("[red]Cannot farm 0 or negative gems![/]")
        return

    headers = get_headers(account)
    duo_info = get_duo_info(account)
    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')
    reward_types = [
        "SKILL_COMPLETION_BALANCED-3cc66443_c14d_3965_a68b_e4eb1cfae15e-2-GEMS",
        "SKILL_COMPLETION_BALANCED-110f61a1_f8bc_350f_ac25_1ded90c1d2ed-2-GEMS"
    ]

    error_messages = ""
    error_count = 0
    total_gems = 0
    gems_left = amount

    try:
        while True:
            random.shuffle(reward_types)
            for reward_type in reward_types:
                url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}/rewards/{reward_type}"
                payload = {"consumed": True, "fromLanguage": fromLanguage, "learningLanguage": learningLanguage}

                response = requests.patch(url, headers=headers, json=payload)
                if response.status_code == 200:
                    total_gems += 30
                    _print("\r\033[2K", end="") if not DEBUG else None
                    print(f"[green]Farmed {total_gems}/{amount} gems (+30 gems)[/]", end="" if not DEBUG else "\n")
                    gems_left -= 30
                else:
                    if not DEBUG:
                        error_messages += f"\n[red]Failed to farm 30 gems ({total_gems}/{amount} gems)[/]"
                        error_count += 1
                        print(error_messages, end="")
                        _print(f"\r\033[{error_count}A", end="")
                    else:
                        print(f"[red]Failed to farm 30 gems ({total_gems}/{amount} gems)[/]")
                if DEBUG:
                    print(
                        f"[bold magenta][DEBUG][/] Status code {response.status_code}\n"
                        f"[bold magenta][DEBUG][/] Content: {response.text}"
                    )
                if gems_left <= 0:
                    break
            if gems_left <= 0:
                break
    except KeyboardInterrupt:
        pass

    _print("\r\033[2K", end="") if not DEBUG else None
    print(f"[green]Successfully farmed {total_gems} gems![/]")

def streak_farm(amount, account):
    duo_info = get_duo_info(account)
    headers = get_headers(account)
    fromLanguage = duo_info.get('fromLanguage', 'Unknown')
    learningLanguage = duo_info.get('learningLanguage', 'Unknown')

    streak_data = duo_info.get('streakData', {})
    current_streak = streak_data.get('currentStreak', {})

    user_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(user_tz)
    day_count = 0

    if not current_streak:
        streak_start_date = now
    else:
        try:
            streak_start_date = datetime.strptime(current_streak.get('startDate'), "%Y-%m-%d")
        except:
            print("[yellow]You have already reached the maximum amount of streak days possible![/]")
            return

    try:
        while True:
            try:
                simulated_day = streak_start_date - timedelta(days=day_count)
                if simulated_day.year <= 0:
                    print(f"[green]Reached the maximum amount of streak days possible! ({day_count}/{amount} days)[/]")
                    return
            except:
                print(f"[green]Reached the maximum amount of streak days possible! ({day_count}/{amount} days)[/]")
                return

            if day_count == amount:
                _print("\r\033[2K", end="") if not DEBUG else None
                print("[blue]Finishing up...[/]", end="" if not DEBUG else "\n")

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
            response = requests.post("https://www.duolingo.com/2017-06-30/sessions", headers=headers, json=session_payload)

            if response.status_code == 200:
                session_data = response.json()
            else:
                print("[red]An error has occurred while trying to create a session.[/]")
                return
            if 'id' not in session_data:
                print("[red]Session ID not found in response data.[/]")
                return
            if DEBUG:
                print(
                    "[bold magenta][DEBUG][/] Session creation result:\n"
                   f"[bold magenta][DEBUG][/] Status code {response.status_code}"
                )

            try:
                start_timestamp = int((simulated_day - timedelta(seconds=1)).timestamp())
                end_timestamp = int(simulated_day.timestamp())
            except ValueError:
                print(f"[green]Reached the maximum amount of streak days possible! ({day_count}/{amount} days)[/]")
                return

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
            response = requests.put(f"https://www.duolingo.com/2017-06-30/sessions/{session_data['id']}", headers=headers, json=update_payload)

            if response.status_code == 200:
                day_count += 1
                _print("\r\033[2K", end="") if not DEBUG else None
                print(f"[green]Farmed {day_count}/{amount} streak days.[/]", end="" if not DEBUG else "\n")
            else:
                print(f"[red]Failed to extend streak ({day_count}/{amount} days)[/]")
            if DEBUG:
                print(f"[bold magenta][DEBUG][/] Status code {response.status_code}")

            if day_count > amount:
                break
    except KeyboardInterrupt:
        pass

    _print("\r\033[2K", end="") if not DEBUG else None
    print(f"[green]Successfully farmed {day_count - 1} streak days![/]")

def activate_super(account):
    url = f"https://www.duolingo.com/2017-06-30/users/{config['accounts'][account]['id']}/shop-items"
    headers = get_headers(account)
    json_data = {"itemName":"immersive_subscription","productId":"com.duolingo.immersive_free_trial_subscription"}

    response = requests.post(url, headers=headers, json=json_data)
    try:
        res_json = response.json()
    except requests.exceptions.JSONDecodeError:
        print(
            "[red]Failed to extract JSON data in response.[/]",
            f"[yellow]However, Duolingo returned status OK (status code {response.status_code})\nBut you most likely didn't get Duolingo Super.[/]" if response.status_code == 200 else "[red]Failed to activate 3 days of Duolingo Super.[/]",
            sep="\n"
        )
        if DEBUG:
            print(
                f"[bold magenta][DEBUG][/] Status code {response.status_code}\n"
                f"[bold magenta][DEBUG][/] Content: {response.text}"
            )
        return
    if response.status_code == 200 and "purchaseId" in res_json:
        print("[green]Successfully activated 3 days of Duolingo Super![/]")
        print("[blue]Note that you most likely didn't actually get Duolingo Super\ndue to Duolingo's new detection system.[/]")
    else:
        print("[red]Failed to activate 3 days of Duolingo Super.[/]")
    if DEBUG:
        print(
            f"[bold magenta][DEBUG][/] Status code {response.status_code}\n"
            f"[bold magenta][DEBUG][/] Content: {response.text}"
        )

def give_item(account, item):
    item_id = item[0]
    item_name = item[1]
    headers = get_headers(account)
    duo_info = get_duo_info(account)
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

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"[green]Successfully received item \"{item_name}\"![/]")
    else:
        print(f"[red]Failed to receive item \"{item_name}\".[/]")
    if DEBUG:
        print(
            f"[bold magenta][DEBUG][/] Status code {response.status_code}\n"
            f"[bold magenta][DEBUG][/] Content: {response.text}"
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
                            print("[yellow]U. Update Token[/] | [magenta]J. Move Down[/] | [magenta]K. Move Up[/] | [red]R. Remove[/]  [bright_black][Enter to cancel][/]")
                            while acc_manager_option not in ['\r', 'U', 'J', 'K', 'R']:
                                acc_manager_option = getch().upper()
                            if acc_manager_option == "\r":
                                continue
                            elif acc_manager_option == "U":
                                new_token = input("Enter your new token [Enter to cancel]: ")
                                if not new_token:
                                    continue
                                print("[bright_yellow]Updating your account credentials, please wait...[/]", end='\r')
                                new_account = fetch_username_and_id(new_token)
                                _print("\033[2K", end="")
                                if isinstance(new_account, str):
                                    print(new_account)
                                    print("[bright_yellow]Press any key to continue.[/]")
                                    getch()
                                    continue
                                config['accounts'][acc_to_update]['username'] = new_account['username']
                                config['accounts'][acc_to_update]['id'] = new_account['id']
                                config['accounts'][acc_to_update]['token'] = new_token
                                print(f"[bright_green]Successfully updated account {new_account['username']}![/]")
                                print("[bright_yellow]Press any key to continue.[/]")
                                getch()
                            elif acc_manager_option == "J":
                                if acc_to_update != len(config['accounts'])-1:
                                    config['accounts'][acc_to_update], config['accounts'][acc_to_update+1] = config['accounts'][acc_to_update+1], config['accounts'][acc_to_update]
                            elif acc_manager_option == "K":
                                if acc_to_update != 0:
                                    config['accounts'][acc_to_update], config['accounts'][acc_to_update-1] = config['accounts'][acc_to_update-1], config['accounts'][acc_to_update]
                            elif acc_manager_option == "R":
                                config['accounts'].pop(acc_to_update)
                        elif acc_manager_option == "A":
                            new_token = input("Enter your account's token [Enter to cancel]: ")
                            if not new_token:
                                continue
                            print("[bright_yellow]Adding your account, please wait...[/]", end='\r')
                            new_account = fetch_username_and_id(new_token)
                            _print("\033[2K", end="")
                            if isinstance(new_account, str):
                                print(new_account)
                                print("[bright_yellow]Press any key to continue.[/]")
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
                            print(f"[bright_green]Successfully added account {new_account['username']}![/]")
                            print("[bright_yellow]Press any key to continue.[/]")
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
            "  [bright_green]6. Saver[/]",
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
            try:
                amount = int(input("Enter amount of XP [Enter to cancel]: "))
            except ValueError:
                continue
            print(f"[blue]Starting to farm {amount} XP...[/]", end="")
            _print("\r", end="")
            xp_farm(amount, account)
            print("[bright_yellow]Press any key to continue.[/]")
            getch()
        elif option == "2":
            try:
                amount = int(input("Enter amount of gems [Enter to cancel]: "))
            except ValueError:
                continue
            print(f"[blue]Starting to farm {amount} gems...[/]", end="")
            _print("\r", end="")
            gem_farm(amount, account)
            print("[bright_yellow]Press any key to continue.[/]")
            getch()
        elif option == "3":
            try:
                amount = int(input("Enter amount of streak days [Enter to cancel]: "))
            except ValueError:
                continue
            print(f"[blue]Starting to farm {amount} streak days...[/]", end="")
            _print("\r", end="")
            streak_farm(amount, account)
            print("[bright_yellow]Press any key to continue.[/]")
            getch()
        elif option == "4":
            print("[bright_yellow]Activating 3 days of Super Duolingo...[/]", end="")
            _print("\r", end="")
            activate_super(account)
            print("[bright_yellow]Press any key to continue.[/]")
            getch()
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
                    "  [bright_magenta]E. Row Blaster 250[/]",
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
                    print(f"[bright_yellow]Giving \"{items[items_option][1]}\"...[/]", end="")
                    _print("\r", end="")
                    give_item(account, items[items_option])
                    print("[bright_yellow]Press any key to continue.[/]")
                    getch()
                elif items_option == "0":
                    break
        elif option == "6":
            clear()
            os.system("python saver.py")
            print("[bright_yellow]Press any key to continue.[/]")
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
                        print("\n  [bright_blue]Press Q for Streaksaver, W for Leaguesaver, E for Position, any other key to cancel[/]")
                        saver_col_option = getch().upper()
                        if saver_col_option == "Q":
                            config['accounts'][int(saver_row_option)-1]['autostreak'] = not config['accounts'][int(saver_row_option)-1]['autostreak']
                        elif saver_col_option == "W":
                            config['accounts'][int(saver_row_option)-1]['autoleague']['active'] = not config['accounts'][int(saver_row_option)-1]['autoleague']['active']
                        elif saver_col_option == "E":
                            try:
                                amount = int(input("\n  Enter league position [Enter to cancel]: "))
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
