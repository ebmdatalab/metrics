import textwrap

from click.testing import CliRunner

from metrics.cli import cli


def test_github():
    runner = CliRunner()
    result = runner.invoke(cli, ["github", "--help"])

    assert result.exit_code == 0

    expected = textwrap.dedent(
        """
        Usage: cli github [OPTIONS]

        Options:
          --help  Show this message and exit.
        """
    ).lstrip()  # lstrip so dedent works and we retain the leading newline
    assert result.output == expected, result.output
