import typer

from krelix_agent import __version__

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Krelix host agent CLI."""


@app.command()
def version() -> None:
    """Print the agent version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
