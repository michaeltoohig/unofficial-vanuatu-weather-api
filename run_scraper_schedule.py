import time

from app.scraper.main import process_all_sessions

import anyio
import schedule
from loguru import logger


def run_process_all_sessions():
    anyio.run(process_all_sessions)


if __name__ == "__main__":
    schedule.every().day.at("07:00:00", "Pacific/Efate").do(run_process_all_sessions)
    schedule.every().day.at("11:00:00", "Pacific/Efate").do(run_process_all_sessions)
    schedule.every().day.at("16:00:00", "Pacific/Efate").do(run_process_all_sessions)

    logger.info("Starting scraping schedule")

    while True:
        schedule.run_pending()
        time.sleep(10)
