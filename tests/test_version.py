from pathlib import Path

import toml

from aioudp import __version__

project_dir = Path(__file__).parent.parent


def test_version():
    assert (
        __version__
        == toml.loads(project_dir.joinpath("pyproject.toml").read_text())["tool"][
            "poetry"
        ]["version"]
    )
