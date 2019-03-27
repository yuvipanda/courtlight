import backoff
import subprocess


@backoff.on_exception(backoff.expo, Exception, max_time=120, jitter=backoff.full_jitter)
async def download_file(session, url, target_path):
    async with session.get(url) as response:
        with open(target_path, 'wb') as f:
            while True:
                # 32KB chunking is a guesstimate
                chunk = await response.content.read(32 * 1024)
                if not chunk:
                    break
                f.write(chunk)


def pdf_to_text(pdf_path):
    """
    Return text content from given PDF on disk.

    Requires pdftotext from poppler-utils to be installed
    """
    return subprocess.check_output(['pdftotext', pdf_path, '-']).decode()