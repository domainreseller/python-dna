"""Shared test helpers. No test touches the network: every client uses a FakeTransport."""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import domainnameapi as dna  # noqa: E402
from domainnameapi.testing import FakeTransport, Reply, api_error, ok  # noqa: E402,F401

TESTDATA = os.path.join(ROOT, "tests", "testdata")


def fake(*replies, **options):
    """A FakeTransport and a client using it (pacing off, retries without real sleeping)."""
    transport = FakeTransport(*replies)
    client = transport.client(**options)
    client.slept = []
    client._sleep = client.slept.append
    return transport, client


def sample_contact(**overrides):
    values = dict(
        first_name="Ada", last_name="Lovelace", company_name="Example Ltd", email="ada@example.com",
        address="1 Example Street", city="Istanbul", state="Istanbul", postal_code="34000", country="TR",
        phone_country_code="90", phone="5551234567", fax_country_code="90", fax="2121234567", disclose_flag=False,
    )
    values.update(overrides)
    return dna.Contact(**values)


def sample_ssl_contact(**overrides):
    values = dict(
        title="IT", first_name="Ada", last_name="Lovelace", company_name="Example Ltd", email="ada@example.com",
        address="1 Example Street", city="Istanbul", state="Istanbul", postal_code="34000", country="TR",
        phone_country_code="90", phone="5551234567", fax_country_code="90", fax="2121234567",
    )
    values.update(overrides)
    return dna.SSLContact(**values)


class TestCase(unittest.TestCase):
    maxDiff = None

    def assertJSON(self, body, expected):
        """Compare a request body (bytes) with an expected JSON value."""
        self.assertEqual(json.loads(body) if body else None, expected)
