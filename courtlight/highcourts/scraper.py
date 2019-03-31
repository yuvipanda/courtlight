#!/usr/bin/env python3
import aiohttp
import logging
import backoff
from lxml import html
from datetime import datetime
import orm
import utils
from sqlalchemy import exists


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
                'date': date,
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

async def scrape_cases(db_session, from_date, to_date):
    async for name, judge_id in fetch_judges():
        # Check if judge exists, if not create
        logging.info(f'Started scraping cases for {name}')
        judge = db_session.query(orm.Judge).filter_by(name=name).first()
        if not judge:
            judge = orm.Judge(name=name)
            db_session.add(judge)

        async for case_data in fetch_cases(name, judge_id, from_date, to_date):
            case_number = case_data['case_number']
            pdf_link = case_data['pdf_link'] 
            date = case_data['date'] 
            

            # Create Judgement if it doesn't exist
            judgement = db_session.query(orm.Judgement).filter_by(pdf_link=pdf_link).first()
            if not judgement:
                judgement = orm.Judgement(pdf_link=pdf_link, date=date, judges=[judge])
                db_session.add(judgement)
            else:
                if judge not in judgement.judges:
                    judgement.judges.append(judge)
                    db_session.add(judgement)
                    logging.info(f'Added judge {name} to case {case_number}')

            # If case number exists, we skip
            if not db_session.query(exists().where(orm.Case.case_number==case_number)).scalar():
                case = orm.Case(case_number=case_data['case_number'], party=case_data['party'], judgement=judgement)
                db_session.add(case)
                logging.info(f'Added case entry for {case_number}')
            else:
                logging.info(f'{case_number} skipped, already exists')

    # Commit only on success. This keeps our db churn small
    db_session.commit()