import asyncio
import enum
import logging
import os
import random
from collections import defaultdict
from datetime import datetime

import aiohttp
from aiohttp import web

HOST = os.environ.get("HOST")
PORT = os.environ.get("PORT")

SECONDARY_SECRET = os.environ.get("SECRET")
SECONDARY_HOSTS = os.environ.get("SECONDARY_HOSTS", "").split(",")
WRITE_CONCERN = int(os.environ.get("WRITE_CONCERN", 1))

QUORUM = int(os.environ.get("QUORUM", 1))
REPLICATE_TIMEOUT = float(os.environ.get("REPLICATE_TIMEOUT", 1))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES")) if os.environ.get("MAX_RETRIES") else float("inf")

HEALTHCHECK_INTERVAL = int(os.environ.get("HEALTHCHECK_INTERVAL", 2))
HEALTHCHECK_REQUEST_TIMEOUT = float(os.environ.get("HEALTHCHECK_REQUEST_TIMEOUT", 1))
HEALTHCHECK_SUSPECT_THRESHOLD = int(os.environ.get("HEALTHCHECK_SUSPECT_THRESHOLD", 2))


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = web.Application()
app["messages"] = []
app["secondary_health"] = defaultdict(dict)
app["secondary_messages"] = defaultdict(list)


class ReplicationStatus(enum.Enum):
    SUCCESS = 1
    FAILURE = 2


class SecondaryHealth(enum.Enum):
    HEALTHY = 1
    SUSPECTED = 2
    UNHEALTHY = 3


async def get_handler(request):
    logging.info("Retrieving messages")
    messages = get_messages()
    return web.json_response(messages)


def get_messages():
    messages_data = app["messages"]
    logging.info(f"Present messages data: {messages_data}")
    return [data["message"] for data in messages_data]


async def post_handler(request):
    data = await request.json()
    message = data.get("message")
    write_concern = data.get("write_concern") or WRITE_CONCERN

    if not message:
        return form_response("Invalid request, \"message\" should be in JSON format", 400)

    if not check_quorum():
        return form_response("Quorum is not reached, master available in read-only mode", 403)

    logging.info(f"Adding message: {message}")
    timestamp = datetime.utcnow().timestamp()
    message_order = len(request.app["messages"]) + 1

    message_data = {
        "message": message,
        "order": message_order,
        "timestamp": timestamp
    }

    request.app["messages"].append(message_data)

    tasks = [asyncio.create_task(replicate_message(host, message, message_order, timestamp))
             for host in SECONDARY_HOSTS
             if app["secondary_health"][host].get("health") != SecondaryHealth.UNHEALTHY]

    if write_concern == 1:
        return form_response(f"Write to Master succeeded, message: {message}", 200)

    replication_status = await perform_replication(tasks, write_concern)
    if replication_status == ReplicationStatus.SUCCESS:
        return form_response(f"Replication succeeded, message: {message}", 200)

    return form_response(f"Replication failed, message: {message}", 400)


def check_quorum():
    healthy_secondary_hosts = [host for host, host_data in app["secondary_health"].items()
                               if host_data["health"] == SecondaryHealth.HEALTHY]
    return len(healthy_secondary_hosts) >= QUORUM


async def perform_replication(tasks, write_concern):
    successful_writes = 0

    for task in asyncio.as_completed(tasks):
        response_status = await task

        if response_status == 200:
            successful_writes += 1

            if successful_writes >= write_concern - 1:
                return ReplicationStatus.SUCCESS


async def replicate_message(host, message, message_order, timestamp, retry=0):
    payload = {
        "message": message,
        "order": message_order,
        "secret": SECONDARY_SECRET,
        "timestamp": timestamp
    }

    host_health = app["secondary_health"][host].get("health")
    if host_health == SecondaryHealth.UNHEALTHY:
        logging.info(f"Stop replicating message {message} to {host} (unavailable)")
        return 503

    try:
        logging.info(f"Replicating message {message} to {host}")

        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{host}/", json=payload, timeout=REPLICATE_TIMEOUT) as response:
                response_status = response.status

                if response_status != 200:
                    logging.warning(f"Replication failed for {host} with {message}. Status code: {response_status}")
                elif response_status == 200:
                    payload.pop("secret")
                    app["secondary_messages"][host].append(payload)
                    logging.info(f"Replication to {host} with {message} completed. Status code: {response_status}")

                return response_status
    except aiohttp.ClientError as ce:
        logging.error(f"AIOHTTP Client Error in message replication for {host} with {message}: {ce}")
    except Exception as e:
        logging.error(f"Error in message replication for {host} with {message}: {e}")

    if retry < MAX_RETRIES:

        delay = 2 ** retry + random.uniform(0, 1)
        logging.info(f"Retrying in {delay} seconds for {host} with {message} (retry {retry + 1}).")

        retry_task = asyncio.create_task(
            replicate_message(
                host=host,
                message=message,
                message_order=message_order,
                timestamp=timestamp,
                retry=retry + 1
            )
        )
        await asyncio.sleep(delay)
        return await retry_task

    else:
        logging.error(f"Max retries reached for {host} with {message}. Aborting.")
        return 503


def form_response(text, status):
    logging.info(text)
    return web.Response(text=text, status=status)


async def get_health_handler(request):
    response_data = [
        {host: host_data["health"].name.lower()}
        for host, host_data
        in app["secondary_health"].items()
    ]

    return web.json_response(response_data)


async def check_health():
    while True:
        asyncio.ensure_future(check_secondaries_health())
        await asyncio.sleep(HEALTHCHECK_INTERVAL)


async def check_secondaries_health():
    logging.info("Checking secondaries health")
    previous_secondary_health = {host: host_data["health"]
                                 for host, host_data
                                 in app["secondary_health"].items()}

    for host in SECONDARY_HOSTS:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{host}/health", timeout=HEALTHCHECK_REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        app["secondary_health"][host] = {
                            "health": SecondaryHealth.HEALTHY,
                            "retries": 0
                        }

                        if previous_secondary_health[host] == SecondaryHealth.UNHEALTHY:
                            await replicate_missed_messages(host)

        except Exception:
            retries = app["secondary_health"][host].get("retries", 0)

            if retries < HEALTHCHECK_SUSPECT_THRESHOLD:
                app["secondary_health"][host]["health"] = SecondaryHealth.SUSPECTED
            else:
                app["secondary_health"][host]["health"] = SecondaryHealth.UNHEALTHY

            retries += 1
            app["secondary_health"][host]["retries"] = retries
    logging.info(f"Secondary health: {app['secondary_health']}")


async def replicate_missed_messages(host):
    current_messages = app["messages"]
    host_messages = app["secondary_messages"][host]

    missed_messages = [message for message in current_messages
                       if message not in host_messages]

    if not missed_messages:
        return

    logging.info(f"Starting replication of missed messages to {host}")
    tasks = []

    for message_data in missed_messages:
        message_text = message_data["message"]
        message_order = message_data["order"]
        message_timestamp = message_data["timestamp"]

        tasks.append(asyncio.create_task(replicate_message(
            host=host,
            message=message_text,
            message_order=message_order,
            timestamp=message_timestamp,
        )))

    try:
        for task in asyncio.as_completed(tasks):
            response_status = await task

            if response_status == 200 and app["messages"] == app["secondary_messages"][host]:
                logging.info(f"Replication of missed messages to {host} succeeded")
                return
    except Exception:
        logging.error(f"Replication of missed messages to {host} failed. Trying again")
        return await replicate_missed_messages(host)


async def main():
    app.router.add_get("/", get_handler)
    app.router.add_post("/", post_handler)
    app.router.add_get("/health", get_health_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    internal_site = web.TCPSite(runner, HOST, 80)
    await internal_site.start()

    external_site = web.TCPSite(runner, HOST, PORT)
    await external_site.start()

    asyncio.ensure_future(check_health())
    logging.info(f"Master server started - {HOST}:80, {PORT}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
