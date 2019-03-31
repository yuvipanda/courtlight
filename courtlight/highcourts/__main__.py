#!/usr/bin/env python3
"""
Scrape data from Delhi High Court Website.

The website is in PHP, and makes extremely heavy use of
PHP Server Side Sessions. The way it does pagination is:

1. You visit the 'home' page. This makes a new PHP session for you.
2. You send a POST request to a query URL with your search
   query
3. You get first page of results, and in the server-side session
   your query info is saved
4. For the following pages, you send a GET request to the same URL,
   with just an offset param - nothing at all about the original query!
   So you can only linearly ask for pages for one judge at a time,
   one period at a time, per cookie jar. 
We first gather the list of all judges, and use a new ClientSession
for each judge. This lets us cleanly separate cookie jars, and 
increase concurrency in the future if we need.
"""

import logging
import asyncio
import argparse
import orm
from scraper import scrape_cases
from populate_contents import populate_contents
from sqlalchemy import create_engine

async def main():
    argparser = argparse.ArgumentParser()

    argparser.add_argument(
        'db_path',
        help='Path to sqlite database for writing data into'
    )
    subparsers = argparser.add_subparsers(dest='action')

    scrape_parser = subparsers.add_parser(
        'scrape-cases',
        help='Scrape case info for all judges '
    )
    
    scrape_parser.add_argument(
        'from_date',
        help='Date to start looking for judgements from, in format dd/mm/yyyy'
    )
    scrape_parser.add_argument(
        'to_date',
        help='Date to look for judgements till, in format dd/mm/yyyy'
    )

    populate_contents_parser = subparsers.add_parser(
        'populate-contents',
        help='Populate text content for all judgements missing text content'
    )

    args = argparser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    db_session = orm.get_session(args.db_path)

    action = args.action

    if action == 'scrape-cases':
        await scrape_cases(db_session, args.from_date, args.to_date)
    elif action == 'populate-contents':
        await populate_contents(db_session)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())