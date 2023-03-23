#! /usr/bin/env python
from pathlib import Path
import signal
import subprocess
import click


def run(cmdline):
    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()
    

@click.group()
def cli():
    pass


@cli.command()
@click.option("-w", "--watch", is_flag=True, default=False)
def compile_scss(watch):
    if watch:
        cmdline = ["boussole", "watch"]
    else:
        cmdline = ["boussole", "compile"]
    run(cmdline)
        

@cli.command(context_settings={"ignore_unknown_options": True})
def dev():
    run(["uvicorn", "app.main:app", "--reload"])
    


if __name__ == "__main__":
    cli()