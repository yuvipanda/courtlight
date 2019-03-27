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

import aiohttp
import asyncio
import argparse
import backoff
import json
from lxml import html
from datetime import datetime
from urllib.parse import quote
import os
import subprocess
import hashlib

def filename_for_download_link(download_link):
    return os.path.join(
        'judgements',
        quote(download_link, safe='.')
    )

async def fetch_judges():
    """
    Yield list of judges in the Delhi High Court.

    Yields (judge_name, judge_id) pairs
    """
    async with aiohttp.ClientSession() as session:
        # Get ourselves a session cokie
        initial_url = 'http://lobis.nic.in/dhcindex.php?cat=1&hc=31'
        async with session.get(initial_url) as response:
            await response.text()
        judges_url = 'http://lobis.nic.in/judname.php?scode=31'
        async with session.get(judges_url) as response:
            doc = html.document_fromstring(await response.text())
            for judge in doc.cssselect('select[name="ctype"] option[value!=""]'):
                name = judge.text_content()
                judge_id = judge.attrib['value'].strip()
                yield (name, judge_id)

def cases_from_page(judge_name, doc):
    """
    Yield cases from a page listing cases for a judge

    Returns a dict with case information.
    """
    for tr in doc.cssselect('table[align="center"] tr'):
        link = tr[1][0]
        if 'href' in link.attrib:
            # Only care about table rows with a PDF Link
            # Rest are presentational
            pdf_link = link.attrib['href']
            case_number = link.text_content().strip()

            # FIXME: Mark this TZ as IST?
            date = datetime.strptime(tr[2].text_content(), '%d/%m/%Y')

            party = tr[3].text_content()

            case = {
                'pdf_link': pdf_link,
                'case_number': case_number,
                'date': date.isoformat(),
                'party': party,
                'judge_name': judge_name,
            }
            
            yield case


@backoff.on_exception(backoff.expo, Exception, max_time=120, jitter=backoff.full_jitter)
async def fetch_cases(judge_name, judge_id, from_date, to_date):
    """
    Yield list of all cases for given judge in timeframe
    """
    async with aiohttp.ClientSession() as session:
        # Get ourselves a session cokie
        initial_url = 'http://lobis.nic.in/dhcindex.php?cat=1&hc=31'
        async with session.get(initial_url) as response:
            await response.text()
        judgements_url = 'http://lobis.nic.in/judname1.php?scode=31&fflag=1'

        post_data = {
            'ctype': judge_id,
            'frdate': from_date,
            'todate': to_date,
            'Submit': 'Submit'
        }
        async with session.post(judgements_url, data=post_data) as response:
            text = await response.text()
            doc = html.document_fromstring(text)
            doc.make_links_absolute(judgements_url)

            for case in cases_from_page(judge_name, doc):
                yield case

            # check for a 'next' URL
            while True:
                next_url_el = doc.xpath('//a[text() = "NEXT >>"]')
                if not next_url_el:
                    break
                next_url = next_url_el[0].attrib['href']
                async with session.get(next_url) as get_response:
                    doc = html.document_fromstring(await get_response.text())
                    doc.make_links_absolute(next_url)
                    for case in cases_from_page(judge_name, doc):
                        yield case

                
async def main():
    args = parse_args()
    async for name, judge_id in fetch_judges():
        async for case in fetch_cases(name, judge_id, args.from_date, args.to_date):
            print(json.dumps(case))


def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'from_date',
        help='Date to start looking for judgements from, in format dd/mm/yyyy'
    )
    argparser.add_argument(
        'to_date',
        help='Date to look for judgements till, in format dd/mm/yyyy'
    )
    return argparser.parse_args()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())