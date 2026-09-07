from __future__ import annotations

import sys

from invoke import task

PYTHON = f'"{sys.executable}"'
PYTHON_PATHS = "tasks.py scripts tests"


@task
def setup(context):
    """Install development dependencies and the repository pre-commit hook."""
    context.run(f"{PYTHON} -m pip install -r requirements-dev.txt", echo=True)
    context.run(f"{PYTHON} -m pre_commit install", echo=True)


@task
def format(context):
    """Format the maintained Python sources."""
    context.run(f"{PYTHON} -m black {PYTHON_PATHS}", echo=True)


@task
def lint(context):
    """Run static style and error checks on the maintained Python sources."""
    context.run(f"{PYTHON} -m flake8 {PYTHON_PATHS}", echo=True)


@task
def test(context):
    """Run the Python test suite."""
    context.run(f"{PYTHON} -m pytest", echo=True)


@task
def check(context):
    """Run non-mutating formatting, lint, and test checks."""
    context.run(f"{PYTHON} -m black --check {PYTHON_PATHS}", echo=True)
    lint(context)
    test(context)


@task
def precommit(context):
    """Run all pre-commit hooks; format hooks may modify files."""
    context.run(f"{PYTHON} -m pre_commit run --all-files", echo=True)


@task(name="install-agents")
def install_agents(context):
    """Install the agent suite into the default global OpenCode configuration."""
    context.run(f"{PYTHON} scripts/install_opencode_agents.py", echo=True)
