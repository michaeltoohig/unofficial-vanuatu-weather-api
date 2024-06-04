from app.scraper.main import process_all_sessions

import anyio


def run_process_all_sessions():
    anyio.run(process_all_sessions)


if __name__ == "__main__":
    run_process_all_sessions()
