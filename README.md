# neu-registrar-monitor
Monitors NEU class registrar system with playwright to see if given classes are available.

📝 Uses *Playwright's Firefox* library to monitor the NEU registrar.

🏃 To run the script, you must have Python installed as well as Playwright.

:star: You must have the script running 24/7 for it to alert you with available classes.

__How to run the script:__

1. Install Python at https://www.python.org/downloads/

2. Install Playwright in your IDE with `pip install playwright` then `playwright install firefox`

3. Replace the course list with courses that you would like to monitor for.

4. Input your Discord webhook and NEU credentials.

5. Run `py bot.py`

6. When Duo authentication appears, accept it and your browser will automatically store the cookies.

7. You're done! Leave it running and the monitor will send a Discord embed when a given class has availability.

<img width="506" alt="image" src="https://github.com/frankiered/neu-registrar-monitor/assets/75506077/8905e9b7-1375-4b3e-ac5d-53d8d61b9c94">

P.S. The Monitor will automatically filter out campuses that aren't Boston and classes that start at 8:00 AM. You can adjust this on line 169.
