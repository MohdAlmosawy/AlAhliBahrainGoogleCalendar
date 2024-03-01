import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

def google_calendar_service():
    """Authenticate and return a service object to interact with Google Calendar API."""
    # Load and parse the credentials from environment variable
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    creds_dict = json.loads(creds_json_str)
    installed_creds_dict = creds_dict["installed"]  # Access the inner dictionary

    creds = Credentials.from_authorized_user_info(installed_creds_dict, SCOPES)

    service = build('calendar', 'v3', credentials=creds)
    return service

def fetch_upcoming_matches():
    """Fetch upcoming matches for Al-Ahli from API-Football."""
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "X-RapidAPI-Key": API_FOOTBALL_KEY,
        "X-RapidAPI-Host": "v3.football.api-sports.io"
    }
    query = {"team": "5580", "season": "2023"}  # Example team ID and season
    response = requests.get(url, headers=headers, params=query)
    if response.status_code == 200:
        return response.json()["response"]
    else:
        print(f"Failed to fetch matches: {response.text}")
        return []

def add_match_to_calendar(service, match):
    """Add a given match to Google Calendar."""
    start_time = match['fixture']['date']
    start_datetime = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
    end_datetime = start_datetime + timedelta(hours=2)  # Assuming 2 hours for the match duration
    end_time = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    event = {
        'summary': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
        'location': match['venue']['name'],
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
    }

    try:
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Added to Calendar: {event_result.get('htmlLink')}")
    except Exception as e:
        print(f"Failed to add event to calendar: {e}")

def lambda_handler(event, context):
    service = google_calendar_service()
    matches = fetch_upcoming_matches()
    for match in matches:
        if all(k in match for k in ('fixture', 'teams', 'venue')):
            add_match_to_calendar(service, match)
    
    return {
        'statusCode': 200,
        'body': 'Successfully processed matches.'
    }
