import nats
import json
import asyncio

from utils.consumer import CONSUMER_SLEEP_TIME
from utils.eventloop import get_event_loop
from utils.logger import log_msg
from utils.nats import close_nats, get_creds_file_if_exists, get_nats_url
import sys

class JetstreamClient():
    async def stream(self, group, channel):
        _nc = await nats.connect(get_nats_url(), user_credentials = get_creds_file_if_exists())
        _js = _nc.jetstream()
        await _js.add_stream(name = channel, subjects = [group])
        return _nc, _js

    async def apublish(self, group, channel, payload):
        _nc, _js = await self.stream(group, channel)
        await _js.publish(channel, json.dumps(payload).encode('UTF-8'))
        await close_nats(_nc)

    async def aconsume(self, group, channel, handler):
        _nc, _js = await self.stream(group, channel)
        try:
            await _js.subscribe(channel, group, durable = group, cb = handler)
            await asyncio.sleep(CONSUMER_SLEEP_TIME)
        finally:
            await close_nats(_nc)
            log_msg("DEBUG", "[JetstreamClient][aconsume] Shutdown...")
            sys.exit(1)

    def publish(self, group, channel, payload):
        asyncio.run(self.apublish(group, channel, payload))

    def consume(self, group, channel, handler):
        loop = get_event_loop()
        loop.run_until_complete(self.aconsume(group, channel, handler))
        loop.run_forever()
