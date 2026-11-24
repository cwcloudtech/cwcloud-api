from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils.common import get_src_path, AUTOESCAPE_EXTENSIONS
from schemas.faas.Template import FunctionTemplate
from utils.faas.functions import get_ext_from_language, is_not_supported_language
from utils.observability.cid import get_current_cid

_env = Environment(loader=FileSystemLoader("{}/templates/faas/handle".format(get_src_path())), autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))

def generate_template(payload: FunctionTemplate):
    if is_not_supported_language(payload.language):
        return {
            'status': 'ko',
            'code': 400,
            'message': "Programing language '{}' is not supported".format(payload.content.language),
            'i18n_code': 'faas_language_not_supported',
            'cid': get_current_cid()
        }

    template = _env.get_template("handle.{}.j2".format(get_ext_from_language(payload.language)))

    return {
        'status': 'ok',
        'code': 200,
        'template': template.render(
            args = ', '.join(["{} string".format(a) for a in payload.args]) if "go" == payload.language else ', '.join(payload.args)
        )
    }
