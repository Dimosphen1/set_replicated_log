import asyncio
import json
import logging
import os

from aiohttp import web

HOST = os.environ.get("HOST")
PORT = os.environ.get("PORT")
MASTER_HOST = os.environ.get("MASTER_HOST")
SECONDARY_SECRET = os.environ.get("SECRET")
SLEEP = os.environ.get("SLEEP")


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = web.Application()
app["messages"] = []


async def get_handler(request):
    logging.info(f"Retrieving messages from Secondary ({HOST}:{PORT})")
    messages = get_messages(request)
    return web.json_response(messages)


def get_messages(request):
    messages = []
    messages_data = request.app["messages"]
    logging.info(f"Present messages data: {messages_data}")

    if not messages_data:
        return messages

    last_message_data = messages_data[-1]

    for index, message_data in enumerate(messages_data):
        if index == 0 or (
            message_data != last_message_data
            and message_data["order"] + 1 == messages_data[index + 1]["order"]
        ) or message_data == last_message_data:
            messages.append(message_data["message"])
            continue
        break

    return messages


async def post_handler(request):
    data = await request.json()
    message = data.get("message")
    secret = None

    if "secret" in data:
        secret = data.pop("secret")

    if request.host != HOST:
        return form_response(f"POST method is only allowed in internal network", 403)

    if secret != SECONDARY_SECRET:
        return form_response("Invalid request, secret should match", 403)

    if not message:
        return form_response("Invalid request, \"message\" should be in JSON format", 400)

    try:
        data["order"] = int(data["order"])
    except KeyError:
        return form_response("Invalid request, \"order\" should be present", 400)
    except ValueError:
        return form_response("Invalid request, \"order\" should be integer", 400)

    if SLEEP:
        await asyncio.sleep(int(SLEEP))

    logging.info(f"Adding message: {message}")
    request.app["messages"].append(data)

    messages = request.app["messages"]
    is_deduplicated = deduplicate_messages(messages)
    order_messages(messages)
    logging.info(f"Present messages data: {messages}")

    if is_deduplicated:
        return form_response(f"Message deduplicated ({HOST}:{PORT}): {message}", 200)
    return form_response(f"Message added ({HOST}:{PORT}): {message}", 200)


async def get_health_handler(request):
    return form_response("OK", 200)


def form_response(text, status):
    logging.info(text)
    return web.Response(text=text, status=status)


def deduplicate_messages(messages):
    initial_messages_length = len(messages)
    serialized_messages = list(map(json.dumps, messages))
    unique_messages = list(set(serialized_messages))
    unique_deserialized_messages = list(map(json.loads, unique_messages))

    messages.clear()
    messages.extend(unique_deserialized_messages)
    deduplicated_messages_length = len(messages)

    return initial_messages_length != deduplicated_messages_length


def order_messages(messages):
    messages.sort(key=lambda data: data["order"])


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

    logging.info(f"Master server started - {HOST}:80, {PORT}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
