"""The examples compile and run against a fake API."""

import contextlib
import glob
import io
import os
import runpy
import sys
import tempfile
from unittest import mock

from helpers import CERT_ID, ROOT, TestCase, dna, fake, ok

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

    def test_ssl_certificate_preview_buys_nothing(self):
        transport, out = run_example(
            "ssl_certificate.py", ["example.com"],
            ok({"totalCount": 1, "items": [{"productCode": "PositiveSSL", "validationType": "DV"}]}),
            ok({"totalCount": 1, "items": [{"certificateId": CERT_ID, "packageCode": "PositiveSSL",
                                            "status": "Active"}]}))
        self.assertEqual([(r.method, r.path) for r in transport.requests],
                         [("GET", "/api/v1/products/ssls"), ("GET", "/api/v1/ssls")])
        self.assertEqual(transport.last.param("DomainName"), "example.com")
        self.assertIn("example.com has certificate %s: PositiveSSL, Active" % CERT_ID, out)

    def test_ssl_certificate_uses_the_certificate_id(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)  # the example writes the key and the certificate to the current directory
            try:
                transport, out = run_example(
                    "ssl_certificate.py",
                    ["example.com", "--package", "PositiveSSL", "--approver", "admin@example.com", "--yes"],
                    ok({"csr": "CSR", "privateKey": "KEY"}),
                    ok({"success": True, "certificateId": CERT_ID, "status": "WaitingForInstall"}),
                    ok({"success": True, "certificateId": CERT_ID, "status": "ConfirmationSent"}),
                    ok({"certificateId": CERT_ID, "status": "Active", "isIssued": True}),
                    ok({"certificateId": CERT_ID, "certificate": "CERT", "intermediateCertificate1": "INT1"}))
                with open("example.com.crt") as fh:
                    certificate = fh.read()
            finally:
                os.chdir(cwd)
        self.assertEqual([r.path for r in transport.requests], [
            "/api/v1/ssls/generate-csr", "/api/v1/ssls/initialize", "/api/v1/ssls/configure",
            "/api/v1/ssls/check-status", "/api/v1/ssls/certificate-content"])
        configure, status, content = transport.requests[2:]
        self.assertEqual(configure.json()["certificateId"], CERT_ID)
        self.assertNotIn("domainName", configure.json())
        self.assertEqual(status.json(), {"certificateId": CERT_ID})
        self.assertEqual(content.param("CertificateId"), CERT_ID)
        self.assertEqual(certificate, "CERT\nINT1\n")
        self.assertIn("certificate id: " + CERT_ID, out)

    def test_custom_request(self):
        _, out = run_example("custom_request.py", ["example.com"],
                             ok({"domainName": "example.com", "remainingDay": 42}))
        self.assertIn("example.com expires None (42 days)", out)

    def test_error_handling(self):
        _, out = run_example("error_handling.py", ["example.com"],
                             ok({"success": False, "message": "Domain is locked at the registry"}))
        self.assertIn("refused: Domain is locked at the registry", out)
