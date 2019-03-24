#!/usr/bin/env python3
"""
Scrape data from Delhi High Court Website
"""

import aiohttp
import asyncio
import backoff
import json
from lxml import html
from functools import partial


async def fetch_judges():
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

def parse_judgements(judge_name, doc):
    for tr in doc.cssselect('table[align="center"] tr'):
        link = tr[1][0]
        if 'href' in link.attrib:
            download_link = link.attrib['href']
            case_number = link.text_content().strip()

            date = tr[2].text_content()

            party = tr[3].text_content()

            judgement = {
                'download_link': download_link,
                'case_number': case_number,
                'date': date,
                'party': party,
                'judge_name': judge_name
            }
            
            yield judgement

@backoff.on_exception(backoff.expo, Exception, max_time=120, jitter=backoff.full_jitter)
async def fetch_judgements(judge_name, judge_id):
    async with aiohttp.ClientSession() as session:
        # Get ourselves a session cokie
        initial_url = 'http://lobis.nic.in/dhcindex.php?cat=1&hc=31'
        async with session.get(initial_url) as response:
            await response.text()
        judgements_url = 'http://lobis.nic.in/judname1.php?scode=31&fflag=1'

        post_data = {
            'ctype': judge_id,
            'frdate': '01/01/2018',
            'todate': '31/12/2018',
            'Submit': 'Submit'
        }
        async with session.post(judgements_url, data=post_data) as response:
            text = await response.text()
            doc = html.document_fromstring(text)
            doc.make_links_absolute(judgements_url)

            for judgement in parse_judgements(judge_name, doc):
                yield judgement

            # check for a 'next' URL
            while True:
                next_url_el = doc.xpath('//a[text() = "NEXT >>"]')
                if not next_url_el:
                    break
                next_url = next_url_el[0].attrib['href']
                async with session.get(next_url) as get_response:
                    doc = html.document_fromstring(await get_response.text())
                    doc.make_links_absolute(next_url)
                    for judgement in parse_judgements(judge_name, doc):
                        yield judgement

                
async def main():
    async for name, judge_id in fetch_judges():
        async for judgement in fetch_judgements(name, judge_id):
            print(json.dumps(judgement))


loop = asyncio.get_event_loop()
loop.run_until_complete(main())