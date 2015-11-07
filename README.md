gcal2text
=========

Get your availability in text from Google Calendar.

Requirements
------------

To install requirements, run:

    pip install -r requirements.txt

Usage
-----

You give gcal2text:
* a start date
* an end date
* a start time
* an end time
* optionally, a timezone

gcal2text will find all events in your Google calendar in the given date range
and print your _availability_ for each of those days between the given start
and end times, in the timezone you indicated (or in your Gcal's default time
zone if you didn't provide one).

For CLI option details, run:

    python gcal2text.py -h

