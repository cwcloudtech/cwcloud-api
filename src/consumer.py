from consume.handler import handle, pubsub_adapter
from utils.consumer import CONSUMER_CHANNEL, CONSUMER_GROUP
from utils.observability.otel import init_otel_metrics, init_otel_tracer, init_otel_logger
from utils.workers import wait_startup_time
from utils.pulumi_state import upgrade_pulumi_state

wait_startup_time()
init_otel_tracer()
init_otel_metrics()
init_otel_logger()
upgrade_pulumi_state()

while True:
  pubsub_adapter().consume(CONSUMER_GROUP, CONSUMER_CHANNEL, handle)
