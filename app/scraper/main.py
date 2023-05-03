import anyio
import httpx
from loguru import logger

from app import models
from app.database import AsyncSession, async_session
from app.scraper.exceptions import (
    PageNotFoundError,
    PageUnavailableError,
    PageErrorTypeEnum,
    ScrapingIssuedAtError,
    ScrapingNotFoundError,
    ScrapingValidationError,
)
from app.scraper.pages import PageMapping, handle_page_error
from app.scraper.sessions import SessionMapping, session_mappings
from app.scraper.utils import fetch_page
from app.utils.datetime import now


async def handle_processing_page_mapping_error(
    db_session, mapping, error: tuple[PageErrorTypeEnum, Exception]
) -> None:
    error_type, exc = error
    await handle_page_error(
        db_session,
        url=mapping.url,
        description=error_type.value,
        exc=str(exc),
        html=getattr(exc, "html", None),
        raw_data=getattr(exc, "raw_data", None),
        errors=getattr(exc, "errors", None),
    )
    raise exc


async def process_page_mapping(db_session: AsyncSession, mapping: PageMapping):
    error = None

    # grab the HTML
    try:
        html = await fetch_page(mapping)
    except httpx.TimeoutException as e:
        error = (PageErrorTypeEnum.TIMEOUT, e)
    except PageUnavailableError as e:
        error = (PageErrorTypeEnum.UNAUHTORIZED, e)
    except PageNotFoundError:
        error = (PageErrorTypeEnum.NOT_FOUND, e)
    except Exception as e:
        logger.exception("Unexpected error fetching page: %s" % str(e))
        error = (PageErrorTypeEnum.INTERNAL_ERROR, e)

    if error:
        await handle_processing_page_mapping_error(db_session, mapping, error)

    # process the HTML
    try:
        issued_at, data = await mapping.process(html)
    except ScrapingNotFoundError as e:
        error = (PageErrorTypeEnum.DATA_NOT_FOUND, e)
    except ScrapingValidationError as e:
        error = (PageErrorTypeEnum.DATA_NOT_VALID, e)
    except ScrapingIssuedAtError as e:
        error = (PageErrorTypeEnum.ISSUED_NOT_FOUND, e)
    except Exception as e:
        logger.exception("Unexpected error processing page: %s" % str(e))
        error = (PageErrorTypeEnum.INTERNAL_ERROR, e)

    if error:
        await handle_processing_page_mapping_error(db_session, mapping, error)

    return issued_at, data


# async def handle_processing_session_mapping_error ???


async def process_session_mapping(session_mapping: SessionMapping):
    # TODO do I want to check if session completed recently then ignore due to rate limits?
    # - then I don't need to check page completed recently in `process_page_mapping`

    # create session
    async with async_session() as db_session:
        session = models.Session(name=session_mapping.name.value)
        db_session.add(session)
        await db_session.commit()
        await db_session.flush()
        await db_session.refresh(session)

    # process page set -- do work
    try:
        async with async_session() as db_session, db_session.begin():
            pages = []
            # TODO fetch each url async in task group
            for mapping in session_mapping.pages:
                logger.info(f"page url {mapping.url}")
                issued_at, raw_data = await process_page_mapping(db_session, mapping)
                if issued_at == -1:  # warning page did not provide issued_at
                    issued_at = session.fetched_at
                page = models.Page(
                    path=mapping.path,
                    raw_data=raw_data,
                    session_id=session.id,
                    issued_at=issued_at,
                )
                db_session.add(page)
                pages.append(page)

            await session_mapping.process(db_session, session, pages)

            session.completed_at = now()
            db_session.add(session)
            await db_session.flush()
    except Exception as exc:
        # handle any errors - maybe add `errors` and `count` to Session table
        # TODO better handling
        logger.exception("Session failed: %s" % str(exc), traceback=True)
    finally:
        pass


async def run_process_all_sessions() -> None:
    """CLI entrypoint."""
    async with anyio.create_task_group() as tg:
        for session_mapping in session_mappings:
            tg.start_soon(process_session_mapping, session_mapping)


async def process_all_sessions() -> None:
    async with anyio.create_task_group() as tg:
        for session_mapping in session_mappings:
            tg.start_soon(process_session_mapping, session_mapping)


if __name__ == "__main__":
    anyio.run(process_all_sessions())
