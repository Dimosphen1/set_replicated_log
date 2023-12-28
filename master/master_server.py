import asyncio
import enum
import logging
import os
from datetime import datetime

import aiohttp
from aiohttp import web

HOST = os.environ.get("HOST")
PORT = os.environ.get("PORT")
SECONDARY_SECRET = os.environ.get("SECRET")
SECONDARY_HOSTS = os.environ.get("SECONDARY_HOSTS", "").split(",")
WRITE_CONCERN = int(os.environ.get("WRITE_CONCERN", 1))


logging.basicConfig(level=logging.INFO)


class ReplicationStatus(enum.Enum):
    SUCCESS = 1
    FAILURE = 2


async def get_handler(request):
    logging.info("Retrieving messages")
    return web.json_response(request.app['messages'].copy())


async def post_handler(request):
    data = await request.json()
    message = data.get('message')

    if not message:
        response_text = "Invalid request, \"message\" should be in JSON format"
        logging.warning(response_text)
        return web.Response(text=response_text, status=400)

    logging.info(f"Adding message: {message}")
    timestamp = datetime.utcnow().timestamp()

    tasks = [asyncio.create_task(replicate_message(host, message, timestamp))
             for host in request.app['secondary_hosts']]
    request.app['messages'].append(message)

    if WRITE_CONCERN == 1:
        return web.Response(text=f"Write to Master succeeded, message: {message}")

    replication_status = await perform_replication(tasks)
    if replication_status == ReplicationStatus.SUCCESS:
        response_text = f"Replication succeeded, message: {message}"
        logging.info(response_text)
        return web.Response(text=response_text)

    response_text = f"Replication failed, message: {message}"
    logging.warning(response_text)
    return web.Response(text=response_text, status=400)


async def perform_replication(tasks):
    successful_writes = 0

    for task in asyncio.as_completed(tasks):
        host, response_status = await task
        logging.info(f"Replication to {host} completed with status {response_status}")

        if response_status == 200:
            successful_writes += 1

            if successful_writes >= WRITE_CONCERN - 1:
                return ReplicationStatus.SUCCESS


async def replicate_message(host, message, timestamp):
    payload = {
        "message": message,
        "secret": SECONDARY_SECRET,
        "timestamp": timestamp
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{host}/", json=payload) as response:
                return host, response.status
    except aiohttp.ClientError as e:
        logging.error(f"Error in replicate_message for {host} with {message}: {e}")
        return host, 500


async def main():
    app = web.Application()
    app['messages'] = []
    app['secondary_hosts'] = SECONDARY_HOSTS

    app.router.add_get("/", get_handler)
    app.router.add_post("/", post_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    internal_site = web.TCPSite(runner, HOST, 80)
    await internal_site.start()

    external_site = web.TCPSite(runner, HOST, PORT)
    await external_site.start()

    logging.info(f"Master server started - {HOST}:80, {PORT}")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
