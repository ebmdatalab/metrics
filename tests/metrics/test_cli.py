import textwrap

from click.testing import CliRunner

from metrics.cli import cli


def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli)

    assert result.exit_code == 0

    suffix = textwrap.dedent(
        """
        Commands:
          github
          slack
        """
    )
    assert result.output.endswith(suffix)
