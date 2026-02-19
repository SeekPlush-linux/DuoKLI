# DuoKLI &middot; [![Discord](https://img.shields.io/discord/1434791849289056350?style=flat&logo=discord&logoColor=white&label=Discord&labelColor=%235662f6&color=gray)](https://discord.gg/eBTkzsm7TE) [![GitHub Release](https://img.shields.io/github/v/release/SeekPlush-linux/DuoKLI?logo=github&label=Release&labelColor=%2307a007&color=gray)](https://github.com/SeekPlush-linux/DuoKLI/releases)

A Duolingo XP/gem/streak/etc. farmer CLI Python script, based on [DuoXPy](https://github.com/DuoXPy/DuoXPy-Bot)'s open sourced code. Supports Windows and Linux.

![Image of DuoKLI](/assets/duokli-image.png)

## Prerequisites
Ensure you have the following programs installed:
- Python (`py` for Windows, `python3` for Linux/MacOS)

## Installation
### Method 1: ZIP Download
1. Go to the [Releases](https://github.com/SeekPlush-linux/DuoKLI/releases) page and download the zip file from the latest release.

2. Extract the zip file and open a terminal in the extracted folder.

3. In the terminal, install the required Python packages:
   ```
   py -m pip install -r requirements.txt
   ```

4. Launch the main Python script:
   ```
   py DuoKLI.py
   ```
  
### Method 2: Automatic download (currently on BETA)
This installation script allows running DuoKLI by executing this in your terminal:
```
$ duokli
```
When using it, it will install DuoKLI in your current directory.

```
curl -fsSL https://raw.githubusercontent.com/SeekPlush-linux/DuoKLI/refs/heads/main/Installation/install.sh | bash -s -- --github-repo SeekPlush-linux/DuoKLI
```
#### Tested on:
- [x] Linux (debian 13)
- [x] macOS (Tahoe 26.2)
- [ ] ~~Windows~~

## Usage
- To navigate around the CLI, press the corresponding key on your keyboard that's next to the option you want to select.
- When launching the script for the first time, you'll need to add an account through the account manager menu to start using DuoKLI.
  - Press `9` to go into the account manager menu, then `L` to log in to your Duolingo account.
  - Enter your account credentials (email/username and password).
  - Once completed, press `0` to go back to the account selection menu, and select your account (in this case, press `1`).

## FAQ
- Q: Pip is giving me an error: `ERROR: Could not open the requirements file`. \
  A: Ensure you opened the terminal in the extracted folder where DuoKLI's files are.
- Q: I'm getting the error "There are no accounts with a saver feature enabled!" in the saver. \
  A: Go back into the main menu, open `Settings`, then `Saver Settings`, and enable at least one saver feature.

## Contact me
**Have any questions or suggestions?** Contact me on [Discord](https://discord.com/users/1107715665730740224)! DMs are open :3
