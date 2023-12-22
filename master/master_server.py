import asyncio
import enum
import logging
import os

import aiohttp
from aiohttp import web

HOST = os.environ.get("HOST")
PORT = os.environ.get("PORT")
SECONDARY_SECRET = os.environ.get("SECRET")
SECONDARY_HOSTS = os.environ.get("SECONDARY_HOSTS", "").split(",")


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
    replication_status = await perform_replication(request.app, message)

    if replication_status == ReplicationStatus.SUCCESS:
        logging.info(f"Replication succeeded, message: {message}")
        request.app['messages'].append(message)
        response_text = f"Message added to Master: {message}"
        logging.info(response_text)
        return web.Response(text=response_text)

    response_text = f"Replication failed, message: {message}"
    logging.warning(response_text)
    return web.Response(text=response_text, status=400)


async def perform_replication(app, message):
    replication_status = {host: ReplicationStatus.FAILURE for host in app['secondary_hosts']}

    for host in app['secondary_hosts']:
        logging.info(f"Replication to {host} started, message: {message}")
        host_status = await replicate_message(host, message)

        if host_status == 200:
            logging.info(f"Replication to {host} succeeded, message: {message}")
            replication_status[host] = ReplicationStatus.SUCCESS
        else:
            logging.warning(f"Replication to {host} failed, message: {message}")

    if all(status == ReplicationStatus.SUCCESS for status in replication_status.values()):
        return ReplicationStatus.SUCCESS
    return ReplicationStatus.FAILURE


async def replicate_message(secondary_url, message):
    async with aiohttp.ClientSession() as session:
        payload = {"message": message, "secret": SECONDARY_SECRET}

        try:
            async with session.post(f"http://{secondary_url}/", json=payload) as response:
                return response.status
        except aiohttp.ClientError as e:
            logging.error(f"Error replicating message to {secondary_url}: {e}")
            return 500


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
