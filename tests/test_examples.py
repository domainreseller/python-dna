"""The examples compile and run against a fake API."""

import contextlib
import glob
import io
import os
import runpy
import sys
from unittest import mock

from helpers import ROOT, TestCase, dna, fake, ok

EXAMPLES = os.path.join(ROOT, "examples")


def run_example(name, argv, *replies, **options):
    transport, client = fake(*replies, **options)
    out = io.StringIO()
    with mock.patch.object(dna.Client, "from_env", side_effect=lambda **kw: client), \
            mock.patch.object(sys, "argv", [name] + list(argv)), contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(io.StringIO()):
        runpy.run_path(os.path.join(EXAMPLES, name), run_name="__main__")
    return transport, out.getvalue()


class ExamplesTest(TestCase):
    def test_all_compile(self):
        files = sorted(glob.glob(os.path.join(EXAMPLES, "*.py")))
        self.assertGreaterEqual(len(files), 7)
        for path in files:
            with open(path, encoding="utf-8") as fh:
                compile(fh.read(), path, "exec")

    def test_quickstart(self):
        _, out = run_example("quickstart.py", ["example.com"],
                             ok({"resellerName": "Acme", "usdBalance": 10, "tryBalance": 5}),
                             ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE",
                                                           "price": 9.99, "currency": "USD", "period": 1}}))
        self.assertIn("Acme", out)
        self.assertIn("example.com is available: 9.99 USD for 1 year(s)", out)

    def test_register_preview_sends_nothing_billable(self):
        transport, out = run_example("register.py", ["my-test-domain-123.com"],
                                     ok({"success": True, "info": {"status": "AVAILABLE", "price": 9.99}}))
        self.assertEqual([r.path for r in transport.requests], ["/api/v1/domains/search"])
        self.assertIn("would send POST", out)

    def test_expiring_is_read_only(self):
        transport, out = run_example("expiring.py", ["--days", "30"],
                                     ok({"totalCount": 2, "items": [
                                         {"domainName": "a.com", "remainingDay": 10,
                                          "expirationDate": "2026-12-01T00:00:00"},
                                         {"domainName": "b.com", "remainingDay": 300}]}))
        self.assertIn("a.com", out)
        self.assertNotIn("b.com", out)
        self.assertIn("1 domain(s) expire within 30 days", out)

    def test_custom_request(self):
        _, out = run_example("custom_request.py", ["example.com"],
                             ok({"domainName": "example.com", "remainingDay": 42}))
        self.assertIn("example.com expires None (42 days)", out)

    def test_error_handling(self):
        _, out = run_example("error_handling.py", ["example.com"],
                             ok({"success": False, "message": "Domain is locked at the registry"}))
        self.assertIn("refused: Domain is locked at the registry", out)
