import click

ch_name_ecg = click.option(
    "--ch-name-ecg",
    prompt="ECG channel name",
    help="Name of the ECG channel in the stream.",
    type=str,
)
stream = click.option(
    "--stream",
    prompt="LSL stream name",
    help="Name of the stream to use for the synchronous task.",
    type=str,
)
verbose = click.option(
    "--verbose",
    help="Verbosity level.",
    type=click.Choice(["DEBUG", "INFO", "WARNING"]),
    default="INFO",
    show_default=True,
)
no_viewer = click.option("--no-viewer", help="Disable the viewer.", is_flag=True)
