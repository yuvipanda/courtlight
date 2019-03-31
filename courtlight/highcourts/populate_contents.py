import aiohttp
import logging
import asyncio
import argparse
from urllib.parse import quote
import os
import subprocess
import hashlib
import orm


async def populate_contents(session):
    judgements = session.query(orm.Judgement).all()

    async with aiohttp.ClientSession() as http_session:
        for judgement in judgements:
            if len(judgement.contents) == 0:
                download_path = os.path.join('judgements', quote(judgement.pdf_link, safe='.'))
                if not os.path.exists(download_path):
                    await utils.download_file(http_session, judgement.pdf_link, download_path)
                else:
                    logging.info(f'Skipped downloading {judgement.pdf_link}, exists')
                text = utils.pdf_to_text(download_path)
                hash = hashlib.sha256()
                hash.update(text.encode('utf-8'))
                content = orm.JudgementContent(
                    judgement=judgement, content_type='text/plain', content=text, content_hash=hash.hexdigest()
                )
                session.add(judgement)
                session.commit()
                logging.info(f'Populated content for judgement {judgement.pdf_link}')