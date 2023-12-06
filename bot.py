import asyncio
from playwright.async_api import async_playwright
from discord_webhook import DiscordWebhook, DiscordEmbed
import json
import os
import urllib.parse

# script will loop through each course and then wait 150 seconds before checking if it's available again.
# you should run this script 24/7 for best results, if any errors arise then the script will start itself over.

courses = [
    {'subject': 'ACCT', 'course_number': '2301'},
    {'subject': 'FINA', 'course_number': '2201'},
    {'subject': '...', 'course_number': '...'},
    # etc...
]

discord_webhook_url = 'YOUR_DISCORD_WEBHOOK_HERE'
check_interval = 150 # seconds
username = 'YOUR_USERNAME_HERE'
password = 'YOUR_PASSWORD_HERE'

async def fetch_course_data(course):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        if os.path.exists('cookies.json'):
            with open('cookies.json', 'r') as cookies_file:
                cookies = json.load(cookies_file)
                await page.context.add_cookies(cookies)

        await page.goto('https://nubanner.neu.edu/StudentRegistrationSsb/ssb/registration', wait_until='networkidle')

        await page.wait_for_selector('#registerLink')
        await page.click('#registerLink')

        await page.wait_for_load_state('networkidle')

        try:
            await page.wait_for_selector('#user', timeout=2000)
        except:
            await page.wait_for_selector('#username')
            await page.fill('#username', username)
            await page.fill('#password', password)
            await page.click('[name="_eventId_proceed"]')

            duo_check = await page.content()
            if 'Authentication with Duo is required for the requested service.' in duo_check:
                try:
                    duo_frame = await page.wait_for_selector("iframe#duo_iframe")
                    frame = await duo_frame.content_frame()

                    await frame.click('.remember_me_label_field')
                    await asyncio.sleep(0.5)
                    await frame.click('.auth-button.positive')

                    await frame.wait_for_selector('.message-content')
                    message_text = await frame.inner_text('.message-content')
                    expected_text = "Pushed a login request to your device..."
                    if expected_text not in message_text:
                        print("Unexpected message received:", message_text)
                        return

                    while True:
                        try:
                            current_message_text = await frame.inner_text('.message-content')
                            if 'Success!' in current_message_text:
                                print("Authentication successful!")

                                cookies = await page.context.cookies()
                                with open('cookies.json', 'w') as file:
                                    json.dump(cookies, file)

                                break
                            await asyncio.sleep(1)
                        except Exception as e:
                            if 'Frame was detached' in e:
                                break

                except Exception as e:
                    print('Duo authentication step encountered an issue:', str(e))
            else:
                print('duo not required')

            await asyncio.sleep(0.5)

        await page.wait_for_selector('.select2-arrow')
        await page.click('.select2-arrow')
        await page.wait_for_selector('.select2-results-dept-0:nth-child(3)')
        await page.click('.select2-results-dept-0:nth-child(3)')
        await page.click('#term-go')

        await page.wait_for_selector('#search-fields')
        
        subject = course['subject']
        course_number = course['course_number']
        await page.goto(f"https://nubanner.neu.edu/StudentRegistrationSsb/ssb/searchResults/searchResults?txt_subject={subject}&txt_courseNumber={course_number}&txt_term=202430&startDatepicker=&endDatepicker=&uniqueSessionId=vqitp1701463283302&pageOffset=0&pageMaxSize=500&sortColumn=subjectDescription&sortDirection=asc", wait_until='networkidle')
        json_data = await page.inner_text('pre')
        data = json.loads(json_data)

        await browser.close()
        return data

def convert_to_standard_time(military_time):
    if not military_time:
        return "N/A"
    hours, minutes = divmod(int(military_time), 100)
    period = "AM" if hours < 12 else "PM"
    if hours == 0:
        hours = 12
    elif hours > 12:
        hours -= 12
    return f"{int(hours)}:{minutes:02d} {period}"

async def send_discord_notification(course):
    if course['faculty'] and course['faculty'][0]['displayName']:
        faculty_name = course['faculty'][0]['displayName']
        encoded_faculty_name = urllib.parse.quote(faculty_name)
        faculty_hyperlink = f"[**{faculty_name}**](https://www.ratemyprofessors.com/search/professors/696?q={encoded_faculty_name})"
    else:
        faculty_hyperlink = 'No instructor'

    begin_time = convert_to_standard_time(course['meetingsFaculty'][0]['meetingTime']['beginTime'])
    end_time = convert_to_standard_time(course['meetingsFaculty'][0]['meetingTime']['endTime'])
    
    # Extract meeting days and separate them with ", "
    meeting_days = []
    if course['meetingsFaculty'][0]['meetingTime']['monday']:
        meeting_days.append('M')
    if course['meetingsFaculty'][0]['meetingTime']['tuesday']:
        meeting_days.append('T')
    if course['meetingsFaculty'][0]['meetingTime']['wednesday']:
        meeting_days.append('W')
    if course['meetingsFaculty'][0]['meetingTime']['thursday']:
        meeting_days.append('TH')
    if course['meetingsFaculty'][0]['meetingTime']['friday']:
        meeting_days.append('F')
    
    meeting_days_str = ', '.join(meeting_days)

    webhook = DiscordWebhook(url=discord_webhook_url)
    embed = DiscordEmbed(title='Course Available!', color=int('FF0000', 16), url='https://nubanner.neu.edu/StudentRegistrationSsb/ssb/term/termSelection?mode=registration')
    embed.set_thumbnail(url='https://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/111.png')
    embed.add_embed_field(name='Course Title', value=course['courseTitle'])
    embed.add_embed_field(name='Course', value=f"`{course['subject']}{course['courseNumber']}`")
    embed.add_embed_field(name='CRN', value=f"`{course['courseReferenceNumber']}`")
    embed.add_embed_field(name='Instructor', value=faculty_hyperlink)
    embed.add_embed_field(name='Class Time', value=f"{begin_time} - {end_time}")
    embed.add_embed_field(name='Meeting Days', value=meeting_days_str)
    
    webhook.add_embed(embed)
    try:
        webhook.execute()
    except:
        print('submitted webhook to AYCD')

sent_crns = set()
async def main():
    while True:
        for course in courses:
            try:
                course_data = await fetch_course_data(course)
                if not course_data.get('success', False):
                    print("Data fetch unsuccessful for", course)
                    continue

                for course_detail in course_data.get('data', []):
                    if course_detail['campusDescription'] == 'Boston' and course_detail['status']['sectionOpen'] and course_detail['meetingsFaculty'][0]['meetingTime']['beginTime'] != '0800':
                        crn = course_detail['courseReferenceNumber']
                        
                        if crn not in sent_crns:
                            if 'sectionAttributes' not in course_detail['status'] or course_detail['status']['sectionAttributes']['description'] != 'Honors':
                                await send_discord_notification(course_detail)
                                
                            sent_crns.add(crn)

            except Exception as e:
                print(f"Error occurred while processing {course}: {e}")
        await asyncio.sleep(check_interval)

async def run_forever():
    while True:
        try:
            await main()
        except Exception as e:
            print(f"Error occurred: {e}. Restarting main...")
            await asyncio.sleep(5)

asyncio.run(run_forever())