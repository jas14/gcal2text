from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

import datetime
import argparse
import pytz
from dateutil.tz import tzlocal
from dateutil import parser as dateparse

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'gcal2text'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'gcal2text.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, None)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_date(prompt):
    date = None
    while date is None:
        datestr = raw_input(prompt)
        try:
            date = datetime.datetime.strptime(datestr, "%Y-%m-%d")
        except ValueError:
            print("That date wasn't valid. Please try again.")
            pass
    return date


def get_time(prompt):
    time = None
    while time is None:
        timestr = raw_input(prompt)
        try:
            time = dateparse.parse(timestr)
        except ValueError:
            print("That time wasn't valid. Please try again.")
            pass
    return time


def fetch_events(calendars, service, start_date, end_date, timezone):
    all_evts = []
    for cal_id in calendars.keys():
        events = service.events().list(
            calendarId=cal_id,
            timeMin=start_date.replace(tzinfo=tzlocal()).isoformat(),
            timeMax=end_date.replace(tzinfo=tzlocal()).isoformat(),
            singleEvents=True,
            timeZone=timezone,
            orderBy='startTime').execute().get('items')
        # interested in: start, end
        for evt in events:
            if 'dateTime' in evt['start']:  # make sure evt isn't all-day
                all_evts.append({
                    'start': dateparse.parse(evt['start']['dateTime']).replace(
                        tzinfo=timezone),
                    'end': dateparse.parse(evt['end']['dateTime']).replace(
                        tzinfo=timezone)
                })

    return sorted(all_evts, key=lambda evt: evt['start'])


def main():
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    # parse command-line args
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', dest="start_date",
                        help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument('--end-date', dest="end_date",
                        help="Inclusive end date (YYYY-MM-DD)")
    parser.add_argument('-i', '--interactive', dest="interactive",
                        action="store_true")
    parser.add_argument('--clamp-start', dest='clamp_start',
                        help="Start of time range for each day")
    parser.add_argument('--clamp-end', dest='clamp_end',
                        help="End of time range for each day")
    parser.add_argument('-z', '--tz', dest="tz", help="Timezone")

    args = parser.parse_args()

    # timezone = pytz.timezone('US/Pacific')
    timezone = tzlocal()

    if args.interactive or not (args.start_date or args.end_date):
        start_date = get_date('Enter a start date: ')
        end_date = None
        while end_date is None:
            end_date = (get_date('Enter an end date: ') +
                        datetime.timedelta(days=1))
            if end_date < start_date:
                print("The end date must be after the start date.")
                end_date = None
        clamp_start = get_time('Enter a start time: ')
        clamp_start = start_date.replace(hour=clamp_start.hour,
                                         minute=clamp_start.minute)
        clamp_end = None
        while clamp_end is None:
            clamp_end = get_time('Enter an end time: ')
            clamp_end = start_date.replace(hour=clamp_end.hour,
                                           minute=clamp_end.minute)
            if clamp_end <= clamp_start:
                print("The end time must be after the start time.")
                clamp_end = None
    elif not (args.start_date and args.end_date):
        print("You must specify a start and end date.")
        return 1
    else:
        # ltz = tzlocal()
        start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d")
        # start_date = start_date.replace(tzinfo=ltz)
        end_date = (datetime.datetime.strptime(args.end_date, "%Y-%m-%d") +
                    datetime.timedelta(days=1))
        # end_date = end_date.replace(tzinfo=ltz)
        if start_date >= end_date:
            raise ValueError("end date {0} is before start date {1}".format(
                args.end_date, args.start_date))

        if (not args.clamp_start or not args.clamp_end):
            print("Defaulting to range 9 AM - 6 PM...")
            clamp_start = start_date.replace(hour=9, minute=0)
            clamp_end = start_date.replace(hour=18, minute=0)
        else:
            clamp_start = dateparse.parse(args.clamp_start)
            clamp_start = start_date.replace(hour=clamp_start.hour,
                                             minute=clamp_start.minute)

            clamp_end = dateparse.parse(args.clamp_end)
            clamp_end = start_date.replace(hour=clamp_end.hour,
                                           minute=clamp_end.minute)
        if clamp_end <= clamp_start:
            raise ValueError("end time {0} is before start time {1}".format(
                args.end_date, args.start_date))

    # convert clamps to desired timezone
    clamp_end = clamp_end.replace(tzinfo=tzlocal()).astimezone(timezone)
    clamp_start = clamp_start.replace(tzinfo=tzlocal()).astimezone(timezone)

    calendarList = service.calendarList().list().execute()
    calendars = {cal['id']: cal['summary']
                 for cal in calendarList.get('items')}
    print("Fetching events from:")
    for name in calendars.values():
        print("\t{0}".format(name))

    all_evts = fetch_events(calendars, service, start_date, end_date, timezone)

    print("\n====== YOUR AVAILABILITY IS: ======")
    print("{0} to {1} (all times {2})\n".format(
        start_date.strftime("%-m/%d"),
        end_date.strftime("%-m/%d"),
        timezone.tzname(start_date)))

    ranges = []
    range_start = clamp_start
    for evt in all_evts:
        if evt['end'] <= range_start:
            continue
        elif evt['start'] <= range_start:
            # this event pushes the range start back
            range_start = evt['end']
        else:
            # we've found a gap!
            while evt['start'] > clamp_end:
                ranges.append((range_start, clamp_end))

                clamp_start += datetime.timedelta(days=1)
                clamp_end += datetime.timedelta(days=1)
                range_start = clamp_start

            if evt['start'] >= clamp_start:
                ranges.append((range_start, evt['start']))

            range_start = max(evt['end'], range_start)

        # always make sure the range_start is in the clamp region
        if range_start >= clamp_end:
            clamp_start += datetime.timedelta(days=1)
            clamp_end += datetime.timedelta(days=1)
            range_start = clamp_start

    for (start, end) in ranges:
        # start, end are guaranteed to be same day b/c of clamps
        print(start.strftime("%a, %m/%d from %-I:%M %p"), end='')
        print(end.strftime(" to %-I:%M %p"))


if __name__ == '__main__':
    main()
