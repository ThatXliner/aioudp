from __future__ import annotations

import os
import socket

import pytest
from hypothesis import HealthCheck, Phase, settings

HOST = "127.0.0.1"
PROFILE = os.environ.get("HYPOTHESIS_PROFILE", "default")

# Each failing example of a hang costs a full timeout, so the explain phase's
# dozens of replays would turn one regression into minutes of CI time.
PHASES = [phase for phase in Phase if phase is not Phase.explain]
# Every example of a test reuses its free_port. Each example closes its sockets.
SUPPRESSED = [HealthCheck.function_scoped_fixture]

settings.register_profile(
    "default",
    deadline=None,
    stateful_step_count=20,
    phases=PHASES,
    suppress_health_check=SUPPRESSED,
)
settings.register_profile(
    "fuzz",
    max_examples=2000,
    stateful_step_count=100,
    deadline=None,
    phases=PHASES,
    suppress_health_check=SUPPRESSED,
    print_blob=True,
)
settings.load_profile(PROFILE)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if PROFILE == "fuzz":
        for item in items:
            item.add_marker(pytest.mark.timeout(0))


@pytest.fixture()
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]
