import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

def google_calendar_service():
    """Create a Google Calendar API service."""
    creds = Credentials(None, refresh_token=os.getenv("REFRESH_TOKEN"), token_uri='https://oauth2.googleapis.com/token', client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET"), scopes=SCOPES)
    creds.refresh(Request())
    return build('calendar', 'v3', credentials=creds)

def fetch_upcoming_matches():
    """Fetch upcoming matches for Al-Ahli from the football API."""
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"X-RapidAPI-Key": API_FOOTBALL_KEY}
    query = {"team": "5580", "season": "2023"}  # Al-Ahli team ID and season
    
    response = requests.get(url, headers=headers, params=query)
    if response.status_code == 200:
        matches = response.json()["response"]
        return matches
    else:
        print(f"Failed to fetch matches: {response.text}")
        return []

def add_match_to_calendar(service, match):
    """Add a given match to the specified Google Calendar."""
    match_date = datetime.strptime(match['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
    event = {
        'summary': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
        'location': match.get('venue', {}).get('name', 'Unknown Location'),
        'description': f"Match in {match['league']['name']}",
        'start': {'dateTime': match_date.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (match_date + timedelta(hours=2)).isoformat(), 'timeZone': 'UTC'},
    }
    
    created_event = service.events().insert(calendarId='63495d25ec0bee2fdf0383cee26f571985a9cc96d8748f634a77b649046ca01d@group.calendar.google.com', body=event).execute()
    print(f"Added to Calendar: {created_event.get('htmlLink')}")

def lambda_handler(event, context):
    service = google_calendar_service()
    matches = fetch_upcoming_matches()
    for match in matches:
        if 'fixture' in match and 'date' in match['fixture']:
            add_match_to_calendar(service, match)
    
    return {
        'statusCode': 200,
        'body': 'Successfully processed matches.'
    }
