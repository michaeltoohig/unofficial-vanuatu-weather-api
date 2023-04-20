

from pathlib import Path

from app import config


def _save_html(html: str, fp: Path) -> Path:
    vmgd_directory = Path(config.ROOT_DIR) / "data" / "vmgd"
    if fp.is_absolute():
        if not fp.is_relative_to(vmgd_directory):
            raise Exception(f"Bad path for saving html {fp}")
    else:
        fp = vmgd_directory / fp
        if not fp.parent.exists():
            fp.parent.mkdir(parents=True)
    fp.write_text(html)

