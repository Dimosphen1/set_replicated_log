import asyncio
import logging
import os

from aiohttp import web

HOST = os.environ.get("HOST")
PORT = os.environ.get("PORT")
MASTER_HOST = os.environ.get("MASTER_HOST")
SECONDARY_SECRET = os.environ.get("SECRET")
SLEEP = os.environ.get("SLEEP")


logging.basicConfig(level=logging.INFO)


async def get_handler(request):
    logging.info(f"Retrieving messages from Secondary ({HOST}:{PORT})")
    messages = [message["message"] for message in request.app["messages"]]
    return web.json_response(messages)


async def post_handler(request):
    data = await request.json()
    message = data.get("message")
    secret = None

    if "secret" in data:
        secret = data.pop("secret")

    if request.host != HOST:
        response_text = f"POST method is only allowed in internal network"
        logging.warning(response_text)
        return web.Response(text=response_text, status=403)

    if not message:
        response_text = "Invalid request, \"message\" should be in JSON format"
        logging.warning(response_text)
        return web.Response(text=response_text, status=400)

    if secret != SECONDARY_SECRET:
        response_text = "Invalid request, secret should match"
        logging.warning(response_text)
        return web.Response(text=response_text, status=403)

    if SLEEP:
        await asyncio.sleep(int(SLEEP))

    logging.info(f"Adding message: {message}")
    request.app["messages"].append(data)

    messages = request.app["messages"]
    messages = deduplicate_messages(messages)
    messages = order_messages(messages)
    request.app["messages"] = messages
    
    response_text = f"Message added to Secondary ({HOST}:{PORT}): {message}"
    logging.info(response_text)
    return web.Response(text=response_text)


def deduplicate_messages(messages):
    checked_timestamps = []
    deduplicated_messages = []
    
    for data in messages:
        if data["timestamp"] not in checked_timestamps:
            deduplicated_messages.append(data)

    return deduplicated_messages


def order_messages(messages):
    return sorted(messages, key=lambda data: data["timestamp"])


async def main():
    app = web.Application()
    app["messages"] = []

    app.router.add_get("/", get_handler)
    app.router.add_post("/", post_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    internal_site = web.TCPSite(runner, HOST, 80)
    await internal_site.start()

    external_site = web.TCPSite(runner, HOST, PORT)
    await external_site.start()

    logging.info(f"Master server started - {HOST}:80, {PORT}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
