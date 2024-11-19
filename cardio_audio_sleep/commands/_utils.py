import click

ch_name_resp = click.option(
    "--ch-name-resp",
    prompt="Respiration channel name",
    help="Name of the respiration channel in the stream.",
    type=str,
)
ch_name_ecg = click.option(
    "--ch-name-ecg",
    prompt="ECG channel name",
    help="Name of the ECG channel in the stream.",
    type=str,
)
fq_deviant = click.option(
    "--deviant",
    prompt="Deviant frequency (Hz)",
    help="Frequency of the deviant stimulus in Hz.",
    type=float,
)
fq_target = click.option(
    "--target",
    prompt="Target frequency (Hz)",
    help="Frequency of the target stimulus in Hz.",
    type=float,
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
