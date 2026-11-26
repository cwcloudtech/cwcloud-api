from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler
from prometheus_fastapi_instrumentator import Instrumentator
from asgi_correlation_id import CorrelationIdMiddleware

from restful_resources import import_resources
from exceptions.CwHTTPException import CwHTTPException
from database.postgres_db import dbEngine
from database.postgres_db import Base

from utils.common import get_env_bool
from utils.logger import log_msg
from utils.observability.monitor import monitors
from utils.pulumi_state import start_pulumi_state_upgrade
from utils.observability.cid import get_current_cid
from utils.observability.metrics import metrics
from utils.observability.otel import init_otel_metrics, init_otel_tracer, init_otel_logger
from utils.env_vars import APP_ENV, APP_VERSION

log_msg("INFO", "[main] the application is starting with version = {}".format(APP_VERSION), True)
Base.metadata.create_all(bind = dbEngine)

app = FastAPI(
    docs_url = "/",
    title = "Comwork Cloud API",
    version = APP_VERSION,
    description = "Official Comwork Cloud API Swagger documentation."
)

app.add_middleware(
    CorrelationIdMiddleware,
    header_name = 'x-cwcloud-cid',
    generator = lambda: "{}".format(uuid4())
)

if APP_ENV == 'local' or get_env_bool('ENABLE_CORS_ALLOW_ALL'):
    app.add_middleware(
        CORSMiddleware,
        allow_origins = ["*"],
        allow_credentials = True,
        allow_methods = ["*"],
        allow_headers = ["*"]
    )

instrumentator = Instrumentator()

init_otel_tracer()
init_otel_metrics()
init_otel_logger()
metrics()
monitors()
start_pulumi_state_upgrade()

instrumentator.instrument(app, metric_namespace='cwcloudapi', metric_subsystem='cwcloudapi')
instrumentator.expose(app, endpoint='/v1/metrics')
instrumentator.expose(app, endpoint='/metrics')

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    headers = {'x-cwcloud-cid': get_current_cid()}

    if isinstance(exc, CwHTTPException):
        return JSONResponse(content = exc.message, status_code = exc.status_code, headers = headers)
    return await http_exception_handler(request, HTTPException(500, 'Internal server error', headers = headers))

import_resources(app)
