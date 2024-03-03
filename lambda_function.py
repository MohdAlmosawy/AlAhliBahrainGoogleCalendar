import os
import json
import requests
from datetime import datetime, timedelta  # Corrected import here
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

def find_existing_event(service, calendar_id, match_id):
    """Search for an existing event by match ID."""
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=f"matchID={match_id}"
        ).execute()
        events = events_result.get('items', [])
        return events[0] if events else None
    except Exception as e:
        print(f"Error searching for existing event: {e}")
        return None

def add_match_to_calendar(service, match, calendar_id):
    """Add a given match to the specified Google Calendar if it doesn't exist."""
    match_id = str(match['fixture']['id'])
    existing_event = find_existing_event(service, calendar_id, match_id)

    if existing_event:
        print(f"Event for match ID {match_id} already exists: {existing_event.get('htmlLink')}")
        return

    match_date = datetime.strptime(match['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
    event = {
        'summary': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
        'location': 'Unknown Venue',  # Simplified for now
        'description': f"Match in {match['league']['name']}. Match ID: {match_id}",
        'start': {'dateTime': match_date.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (match_date + timedelta(hours=2)).isoformat(), 'timeZone': 'UTC'},
        'extendedProperties': {
            'private': {
                'matchID': match_id
            }
        }
    }
    
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Added to Calendar: {created_event.get('htmlLink')}")

def update_match_event(service, match, calendar_id):
    """Update an existing match event with the match result if not already updated."""
    match_id = str(match['fixture']['id'])
    existing_event = find_existing_event(service, calendar_id, match_id)
    
    if existing_event:
        # Define a unique identifier to indicate the event has been updated with the result.
        update_identifier = "Match Result Updated"
        
        # Check if the event description already contains the update identifier.
        if existing_event.get('description') and update_identifier in existing_event['description']:
            print(f"Match ID {match_id} event has already been updated with the result.")
            return
        
        # Construct the match result string.
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        home_goals = match['goals']['home']
        away_goals = match['goals']['away']
        match_result = f"Result: {home_team} {home_goals} - {away_goals} {away_team}. {update_identifier}"
        
        # Update the description to include the match result and the update identifier.
        if 'description' in existing_event:
            existing_event['description'] += "\n\n" + match_result
        else:
            existing_event['description'] = match_result
        
        # Update the event on Google Calendar.
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=existing_event['id'],
            body=existing_event
        ).execute()
        
        print(f"Updated event: {updated_event.get('htmlLink')}")
    else:
        print(f"No existing event found for match ID {match_id}. Attempting to add new event.")
        add_match_to_calendar(service, match, calendar_id)

def lambda_handler(event, context):
    service = google_calendar_service()
    matches = fetch_upcoming_matches()
    calendar_id = '63495d25ec0bee2fdf0383cee26f571985a9cc96d8748f634a77b649046ca01d@group.calendar.google.com'
    
    for match in matches:
        # Check if the match is finished before attempting to update.
        if match['fixture']['status']['short'] == "FT":
            update_match_event(service, match, calendar_id)
        else:
            # If the match is not finished, attempt to add it to the calendar.
            add_match_to_calendar(service, match, calendar_id)
    
    return {
        'statusCode': 200,
        'body': 'Successfully processed matches.'
    }