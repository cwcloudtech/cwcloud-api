import qrcode

from pathlib import Path
from io import BytesIO
from typing import Annotated
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

from schemas.User import UserSchema
from middleware.auth_guard import get_current_active_user
from database.postgres_db import get_db
from entities.Apikeys import ApiKeys

from utils.api_url import get_api_url
from utils.provider import get_providers, get_provider_infos
from utils.observability.otel import get_otel_tracer
from utils.observability.traces import span_format
from utils.observability.counter import create_counter, increment_counter
from utils.observability.enums import Action, Method
from utils.common import AUTOESCAPE_EXTENSIONS

router = APIRouter()

_span_prefix = "config"
_counter = create_counter("config_api", "Config API counter")

@router.get("/{key_id}/qr")
def get_qr_code(current_user: Annotated[UserSchema, Depends(get_current_active_user)], key_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET)):
        increment_counter(_counter, Method.GET)
        apiKey = ApiKeys.getUserApiKey(current_user.id, key_id, db)
        if not apiKey:
            return JSONResponse(content = {
                "error": "api key not found",
                "i18n_code": "api_key_not_found"
            }, status_code = 404)

        qr_value = f"{get_api_url()}={apiKey.secret_key}"
        qr_image = qrcode.make(qr_value)

        image_buffer = BytesIO()
        qr_image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        return StreamingResponse(image_buffer, media_type="image/png")

@router.get("/{key_id}")
def download_config_file(current_user: Annotated[UserSchema, Depends(get_current_active_user)], key_id: str, db: Session = Depends(get_db)):
    with get_otel_tracer().start_as_current_span(span_format(_span_prefix, Method.GET, Action.DOWNLOAD)):
        increment_counter(_counter, Method.GET, Action.DOWNLOAD)
        apiKey = ApiKeys.getUserApiKey(current_user.id, key_id, db)
        if not apiKey:
            return JSONResponse(content = {
                "error": "api key not found",
                "i18n_code": "api_key_not_found"
            }, status_code = 404)
        providers = get_providers()
        first_provider = providers[0]["name"]
        first_provider_region = get_provider_infos(first_provider, "regions")[0]["name"]

        file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[2]) + '/templates')
        env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
        template = env.get_template("config_file.j2")
        config_content = template.render(
            endpoint=get_api_url(),
            provider=first_provider,
            region=first_provider_region,
            format="pretty",
            access_key=apiKey.access_key,
            secret_key=apiKey.secret_key
        )

        with open("config", "w") as file:
            file.write(config_content)

        return FileResponse("config", filename="config", headers={"Content-Disposition": "attachment;filename=config"})
