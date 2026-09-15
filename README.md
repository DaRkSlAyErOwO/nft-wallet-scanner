# NFT Wallet Scanner

A CLI tool for analyzing NFT wallets, ranking them by portfolio value and trading activity.

---

## 🚀 Setup Guide

This guide will walk you through setting up and running the NFT Wallet Scanner on your computer, whether you are on Windows or Mac. No prior coding experience required!

### Step 1: Prerequisites (What you need installed)
Before doing anything, you need **Python** installed on your computer.

- **Windows**: Download Python from [python.org](https://www.python.org/downloads/). When installing, **make sure you check the box that says "Add Python to PATH"** before clicking "Install Now".
- **Mac**: Open your Terminal (search for "Terminal" in Spotlight) and type `python3 --version`. If it prompts you to install developer tools, say yes. Otherwise, download it from [python.org](https://www.python.org/downloads/).

### Step 2: Open your Terminal / Command Prompt
You need to navigate to the folder where this project is located.

- **Windows**: Open the folder where this code is saved. Click on the address bar at the top of the folder window, delete everything, type `cmd` and press **Enter**. This opens a black box (Command Prompt) exactly in this folder.
- **Mac**: Open the **Terminal** app. Type `cd ` (with a space after it), then drag and drop the folder containing this code into the Terminal window and press **Return**.

### Step 3: Create a Virtual Environment (Safe Space)
A virtual environment keeps the code and its dependencies from messing with the rest of your computer.

- **Windows**:
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate
  ```
  *(If you get a red text error on PowerShell saying scripts are disabled, type `cmd` and press Enter to switch to standard command prompt, then try again).*

- **Mac**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
*(You will know it worked if you see `(venv)` appear at the beginning of the line you type in).*

### Step 4: Install the Required Packages
Now, we tell Python to download the small programs this script needs to run.

- **Windows & Mac**:
  ```bash
  pip install -r requirements.txt
  ```

### Step 5: Add your API Key
The scanner needs an OpenSea API key to fetch data.

1. Find the file named `.env.example` in this folder.
2. Rename it to just `.env` (On Mac, you might need to show hidden files, or just run `cp .env.example .env` in the terminal).
3. Open the `.env` file in Notepad (Windows) or TextEdit (Mac).
4. You will see `OPENSEA_API_KEY=your_key_here`.
5. Replace `your_key_here` with your actual OpenSea API key. It should look like this: `OPENSEA_API_KEY=a1b2c3d4e5f6g7h8i9j0`.
6. Save and close the file. **Do not ever upload this `.env` file to the public internet, it holds your secret key!**

### Step 6: Run the Program!
You are all set! To start the interactive menu, type:

- **Windows**:
  ```cmd
  python -m src.cli
  ```
- **Mac**:
  ```bash
  python3 -m src.cli
  ```

A beautiful menu will appear, letting you analyze a single wallet, run a big batch of wallets from a `.csv` file, or export your results!

---

## 📖 Key Concepts to Know

- **Total USD Ranking**: To correctly score a wallet by total USD, you must explicitly request portfolio fetching (either answer `y` in the menu or use the `--portfolio` flag).
- **Resume**: When running a batch, the script caches all successful fetches in a SQLite database (`data/cache.db`). If you abort and restart with the same CSV and answer `Y` to "Resume previous run?", it will completely skip any wallet that was already fully fetched.
- **Truncated**: You might see a `Warning: Data was truncated` or a `truncated` column set to `1`. This means the wallet had more NFTs or sales than could fit into a single API request, so the scanner processed a subset.
