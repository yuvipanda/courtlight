import aiohttp
import logging
import asyncio
import argparse
from urllib.parse import quote
import os
import subprocess
import hashlib
from orm import Judgement
import utils


async def populate_contents(session):
    judgements = session.query(Judgement).filter(Judgement.text_content == None).order_by(Judgement.date)

    judgements_count = judgements.count()

    async with aiohttp.ClientSession() as http_session:
        for i, judgement in enumerate(judgements):
            download_path = os.path.join('judgements', quote(judgement.pdf_link, safe='.'))
            if not os.path.exists(download_path):
                await utils.download_file(http_session, judgement.pdf_link, download_path)
            else:
                logging.info(f'Skipped downloading {judgement.pdf_link}, exists')
            text = utils.pdf_to_text(download_path)
            hash = hashlib.sha256()
            hash.update(text.encode('utf-8'))
            judgement.text_content = text
            judgement.text_content_hash = hash.hexdigest()
            session.add(judgement)
            session.commit()
            logging.info(f'{i+1} of {judgements_count} judgement content populated from {judgement.pdf_link}')