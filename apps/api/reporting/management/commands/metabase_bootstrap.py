"""Provision Metabase via its REST API (post-v1 #4).

Usage:
    uv run python manage.py metabase_bootstrap \\
        [--base-url http://localhost:3000] \\
        [--admin-email admin@hhps.demo] \\
        [--admin-password demo1234]

Idempotent: if an admin already exists, the script logs and exits 0.
On a fresh boot it creates the admin user, registers the platform's
Postgres DB through the read-only `metabase_ro` role, builds an
"Agency overview" dashboard, marks it public, and prints the public
URL to stdout.
"""

from __future__ import annotations

from typing import Any

import requests
from django.core.management.base import BaseCommand

from reporting.metabase_bootstrap import BootstrapConfig, bootstrap


class Command(BaseCommand):
    help = "Bootstrap Metabase: admin user, DB connection, dashboard, public link."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--base-url", default="http://localhost:3000")
        parser.add_argument("--admin-email", default="admin@hhps.demo")
        parser.add_argument("--admin-password", default="demo1234")

    def handle(self, *args: Any, **opts: Any) -> None:
        cfg = BootstrapConfig(
            base_url=opts["base_url"],
            admin_email=opts["admin_email"],
            admin_password=opts["admin_password"],
        )
        with requests.Session() as session:
            url = bootstrap(session, cfg)
        if url is None:
            self.stdout.write(
                self.style.WARNING("Metabase already bootstrapped (no setup-token available).")
            )
            return
        self.stdout.write(self.style.SUCCESS(f"Public dashboard: {url}"))
