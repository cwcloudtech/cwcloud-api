import nats
import json
import asyncio

from utils.consumer import CONSUMER_GROUP, CONSUMER_SLEEP_TIME
from utils.eventloop import get_event_loop

from utils.logger import log_msg
from utils.nats import close_nats, get_creds_file_if_exists, get_nats_url
import sys

class NatsClient():
    async def connect(self):
        _nc = await nats.connect(get_nats_url(), user_credentials = get_creds_file_if_exists())
        return _nc

    async def apublish(self, channel, payload):
        _nc = await self.connect()
        await _nc.publish(channel, json.dumps(payload).encode('UTF-8'))
        await close_nats(_nc)

    async def aconsume(self, channel, handler):
        _nc = await self.connect()
        try:
            await _nc.subscribe(channel, CONSUMER_GROUP, cb = handler)
            await asyncio.sleep(CONSUMER_SLEEP_TIME)
        finally:
            await close_nats(_nc)
            log_msg("DEBUG", "[NatsClient][aconsume] Shutdown...")
            sys.exit(1)

    def publish(self, channel, payload):
        asyncio.run(self.apublish(channel, payload))

    def consume(self, channel, handler):
        loop = get_event_loop()
        loop.run_until_complete(self.aconsume(channel, handler))
        loop.run_forever()
