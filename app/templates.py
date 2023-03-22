from fastapi.templating import Jinja2Templates

_templates = Jinja2Templates(
    directory=["app/templates"],  # type: ignore  # bad typing
    trim_blocks=True,
    lstrip_blocks=True,
)