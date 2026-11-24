"""The client: construction, environments, headers, validation, read-only mode, retries, pacing, tracing."""

import logging
import os
from dataclasses import dataclass
from unittest import mock

from helpers import CERT_ID, FakeTransport, Reply, TestCase, api_error, dna, fake, ok

from domainnameapi.client import _Pacer
from domainnameapi.model import Model, integer, text, timestamp


class ConstructionTest(TestCase):
    def test_credentials_are_required_and_trimmed(self):
        for rid, key in (("", "k"), ("r", ""), ("  ", " ")):
            with self.assertRaises(dna.MissingCredentialsError) as ctx:
                dna.Client(rid, key)
            self.assertIs(ctx.exception.kind, dna.ErrorKind.AUTH)
            self.assertIsInstance(ctx.exception, ValueError)
        transport = FakeTransport(ok({}))
        client = dna.Client(" rid ", " key ", transport=transport, pacing=False)
        client.account.get()
        self.assertEqual(transport.last.header("X-API-KEY"), "key")
        self.assertEqual(transport.last.header("__reseller"), "rid")

    def test_environments(self):
        self.assertEqual(dna.Client("r", "k").base_url, dna.PRODUCTION_URL)
        ote = dna.Client("r", "k", environment="ote")
        self.assertEqual(ote.base_url, dna.OTE_URL)
        self.assertIs(ote.environment, dna.Environment.OTE)
        self.assertEqual(dna.Client("r", "k", environment=True).base_url, dna.OTE_URL)
        custom = dna.Client("r", "k", base_url="http://localhost:8080/")
        self.assertEqual(custom.base_url, "http://localhost:8080")
        self.assertIs(custom.environment, dna.Environment.PRODUCTION)
        with self.assertRaises(dna.ConfigurationError):
            dna.Client("r", "k", environment="staging")
        with self.assertRaises(dna.ConfigurationError):
            dna.Client("r", "k", base_url="ftp://example.com")
        self.assertNotIn("k", repr(ote).replace("ote", ""))

    def test_parse_environment(self):
        for value in ("", "production", "PROD", "live", "false", "0", "off", "no", False, None):
            self.assertIs(dna.Environment.parse(value), dna.Environment.PRODUCTION, value)
        for value in ("ote", "Test", "sandbox", "true", "1", "on", "yes", True):
            self.assertIs(dna.Environment.parse(value), dna.Environment.OTE, value)

    def test_from_env(self):
        env = {"DNA_RESELLER_ID": "rid", "DNA_API_KEY": "key", "DNA_ENV": "ote"}
        with mock.patch.dict(os.environ, env, clear=True):
            client = dna.Client.from_env()
            self.assertEqual(client.base_url, dna.OTE_URL)
            self.assertEqual(client.reseller_id, "rid")
            self.assertEqual(dna.Client.from_env(environment="production").base_url, dna.PRODUCTION_URL)
        with mock.patch.dict(os.environ, {"DNA_RESELLER_ID": "rid", "DNA_API_KEY": "key", "DNA_TEST_MODE": "true",
                                          "DNA_BASE_URL": "https://proxy.example.test/"}, clear=True):
            self.assertEqual(dna.Client.from_env().base_url, "https://proxy.example.test")
        with mock.patch.dict(os.environ, {"DNA_RESELLER_ID": "rid"}, clear=True):
            with self.assertRaises(dna.MissingCredentialsError) as ctx:
                dna.Client.from_env()
            self.assertIn("DNA_API_KEY", str(ctx.exception))

    def test_services_are_named_like_the_cli(self):
        client = dna.Client("r", "k")
        for name in ("account", "contacts", "domains", "dns", "dnssec", "ssl", "hosting", "orders", "products"):
            self.assertTrue(hasattr(client, name), name)


class SendingTest(TestCase):
    def test_request_headers(self):
        transport, client = fake(ok({"success": True, "info": {}}), user_agent="my-panel/1.4")
        client.domains.search("example.com")
        r = transport.last
        self.assertEqual(r.method, "POST")
        self.assertEqual(r.url, "https://api.example.test/api/v1/domains/search")
        self.assertEqual(r.header("Accept"), "application/json")
        self.assertEqual(r.header("Content-Type"), "application/json")
        self.assertTrue(r.header("User-Agent").startswith("my-panel/1.4 DomainNameAPI-Python/"))
        self.assertEqual(r.header("X-API-KEY"), "test-api-key")
        self.assertEqual(r.header("__reseller"), "00000000-0000-4000-8000-000000000001")
        self.assertEqual(len(r.header("X-Correlation-ID")), 32)
        self.assertEqual(r.timeout, 60.0)

        client.domains.info("example.com")
        self.assertEqual(transport.last.header("Content-Type"), "")
        self.assertEqual(transport.last.body, b"")

    def test_client_info_headers_default(self):
        transport, client = fake(ok({}))
        client.account.get()
        self.assertEqual(transport.last.header("X-App"), "python")
        self.assertEqual(transport.last.header("X-Version"), dna.__version__)
        self.assertEqual(client.app_name, dna.DEFAULT_APP)
        self.assertEqual(client.app_version, dna.__version__)
        self.assertTrue(transport.last.header("User-Agent").startswith("DomainNameAPI-Python/"))

    def test_client_info_headers_override_and_normalization(self):
        transport, client = fake(ok({}), app_name=" WiseCP5 ", app_version="V2.0.20-beta",
                                 user_agent="my-panel/1.4")
        client.account.get()
        self.assertEqual(transport.last.header("X-App"), "wisecp5")
        self.assertEqual(transport.last.header("X-Version"), "2.0.20")
        self.assertTrue(transport.last.header("User-Agent").startswith("my-panel/1.4 DomainNameAPI-Python/"))
        self.assertEqual(client.prepare(dna.AccountGetRequest()).headers["X-App"], "wisecp5")
        for app, version, want_app, want_version in (
            ("WHMCS Module/8", ".8.13.1.", "whmcsmodule8", "8.13.1"),
            ("my_panel-2.x", "1", "my_panel-2.x", "1"),
        ):
            self.assertEqual(dna.Client("r", "k", app_name=app).app_name, want_app)
            self.assertEqual(dna.Client("r", "k", app_version=version).app_version, want_version)

    def test_client_info_headers_empty_fallbacks(self):
        for app, version in (("", ""), ("  ", "   "), ("ŞÇĞ!", "beta"), (None, None)):
            client = dna.Client("r", "k", app_name=app, app_version=version)
            self.assertEqual(client.app_name, "python", app)
            self.assertEqual(client.app_version, dna.__version__, version)

    def test_client_info_headers_from_env(self):
        env = {"DNA_RESELLER_ID": "rid", "DNA_API_KEY": "key", "DNA_APP": "HostBill", "DNA_APP_VERSION": "v4.0.7"}
        with mock.patch.dict(os.environ, env, clear=True):
            client = dna.Client.from_env()
            self.assertEqual((client.app_name, client.app_version), ("hostbill", "4.0.7"))
            client = dna.Client.from_env(app_name="blesta", app_version="5.9")
            self.assertEqual((client.app_name, client.app_version), ("blesta", "5.9"))
        with mock.patch.dict(os.environ, {"DNA_RESELLER_ID": "rid", "DNA_API_KEY": "key"}, clear=True):
            client = dna.Client.from_env()
            self.assertEqual((client.app_name, client.app_version), ("python", dna.__version__))

    def test_client_info_headers_on_retries(self):
        transport, client = fake(Reply(429, "", {"Retry-After": "0"}), ok({}), app_name="FOSSBilling",
                                 app_version="0.6.1")
        client.account.get()
        self.assertEqual(len(transport.requests), 2)
        for r in transport.requests:
            self.assertEqual((r.header("X-App"), r.header("X-Version")), ("fossbilling", "0.6.1"))

    def test_validation_stops_the_request(self):
        transport, client = fake()
        with self.assertRaises(dna.InputError) as ctx:
            client.domains.renew(" ", 11)
        err = ctx.exception
        self.assertEqual(err.request, "DomainRenewRequest")
        self.assertEqual([f.field for f in err.fields], ["domain_name", "years"])
        self.assertIs(err.kind, dna.ErrorKind.INVALID_INPUT)
        self.assertIn("years: must be between 1 and 10", str(err))
        self.assertEqual(transport.requests, [])

    def test_read_only(self):
        transport, client = fake(ok({}), read_only=True)
        self.assertTrue(client.read_only)
        client.account.get()
        with self.assertRaises(dna.ReadOnlyError) as ctx:
            client.domains.lock("example.com")
        self.assertIs(ctx.exception.kind, dna.ErrorKind.READ_ONLY)
        self.assertIn("DomainLockRequest", str(ctx.exception))
        # Reads sent with POST or PUT still go through.
        transport.replies = [ok({"domainName": "example.com"})]
        client.ssl.status(CERT_ID)
        self.assertEqual(len(transport.requests), 2)

    def test_rate_limit_is_retried_even_for_billable_requests(self):
        transport, client = fake(Reply(429, "", {"Retry-After": "1"}), ok({"success": True}))
        client.domains.renew("example.com", 1)
        self.assertEqual(len(transport.requests), 2)
        self.assertAlmostEqual(client.slept[0], 1.05)

    def test_rate_limit_after_retries(self):
        transport, client = fake(Reply(429, "", {"Retry-After": "0"}))
        with self.assertRaises(dna.RateLimitError) as ctx:
            client.account.get()
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual(ctx.exception.code, dna.ErrorCode.RATE_LIMITED)
        self.assertTrue(ctx.exception.retryable)

    def test_long_retry_after_is_not_waited(self):
        transport, client = fake(Reply(429, "", {"Retry-After": "120"}))
        with self.assertRaises(dna.RateLimitError) as ctx:
            client.account.get()
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(ctx.exception.retry_after, 120.0)

    def test_server_errors_are_retried_only_when_safe(self):
        transport, client = fake(Reply(503), ok({"resellerId": "r"}))
        self.assertEqual(client.account.get().reseller_id, "r")
        self.assertEqual(len(transport.requests), 2)

        transport, client = fake(Reply(503), ok({"success": True}))
        with self.assertRaises(dna.ServerError):
            client.domains.renew("example.com", 1)
        self.assertEqual(len(transport.requests), 1, "a billable request was repeated")

        transport, client = fake(Reply(502), ok({}))
        client.domains.lock("example.com")  # idempotent write
        self.assertEqual(len(transport.requests), 2)

        transport, client = fake(Reply(500), ok({}))
        with self.assertRaises(dna.ServerError):
            client.account.get()
        self.assertEqual(len(transport.requests), 1, "500 is not retried")

    def test_network_errors(self):
        transport, client = fake(dna.TransportError("timeout: timed out", timeout=True), ok({"resellerId": "r"}))
        self.assertEqual(client.account.get().reseller_id, "r")
        self.assertEqual(len(transport.requests), 2)

        transport, client = fake(dna.TransportError("connection reset by peer"))
        with self.assertRaises(dna.NetworkError) as ctx:
            client.domains.renew("example.com", 1)
        err = ctx.exception
        self.assertEqual(len(transport.requests), 1)
        self.assertTrue(err.outcome_unknown)
        self.assertIs(err.kind, dna.ErrorKind.NETWORK)
        self.assertIsInstance(err.__cause__, dna.TransportError)

        transport, client = fake(dna.TransportError("timeout", timeout=True))
        with self.assertRaises(dna.NetworkError) as ctx:
            client.account.get()
        self.assertEqual(len(transport.requests), 3)
        self.assertTrue(ctx.exception.timeout)
        self.assertFalse(ctx.exception.outcome_unknown)

        transport, client = fake(dna.TransportError("TLS certificate problem", retryable=False))
        with self.assertRaises(dna.NetworkError):
            client.account.get()
        self.assertEqual(len(transport.requests), 1)

    def test_retries_can_be_turned_off(self):
        transport, client = fake(Reply(503), retries=0)
        with self.assertRaises(dna.ServerError):
            client.account.get()
        self.assertEqual(len(transport.requests), 1)

    def test_redirect_is_an_authentication_error(self):
        _, client = fake(Reply(302, "", {"Location": "/Error/Suspend"}))
        with self.assertRaises(dna.AuthenticationError) as ctx:
            client.account.get()
        self.assertEqual(ctx.exception.code, dna.ErrorCode.INVALID_RESELLER)
        self.assertIn("reseller ID", ctx.exception.hint)

    def test_correlation_id(self):
        transport, client = fake(ok({}))
        with dna.correlation_id("order-4711"):
            client.account.get()
            self.assertEqual(transport.last.header("X-Correlation-ID"), "order-4711")
        client.account.get()
        self.assertNotEqual(transport.last.header("X-Correlation-ID"), "order-4711")

        transport, client = fake(api_error(500, "x", "boom"), retries=0)
        with dna.correlation_id("c-9"):
            with self.assertRaises(dna.ServerError) as ctx:
                client.account.get()
        self.assertEqual(ctx.exception.correlation_id, "c-9")

        transport, client = fake(ok({}, {"X-Correlation-Id": "server-side"}))
        self.assertEqual(client.send_with_response(dna.AccountGetRequest()).correlation_id, "server-side")

    def test_trace_and_logger(self):
        events = []
        transport, client = fake(Reply(503), ok({"resellerId": "r"}), trace=events.append)
        with self.assertLogs("domainnameapi", logging.DEBUG) as logs:
            client.account.get()
        self.assertEqual([e.kind for e in events], ["request", "response", "retry", "request", "response"])
        self.assertEqual(events[1].status_code, 503)
        self.assertEqual(events[-1].attempt, 2)
        self.assertIs(events[0].safety, dna.Safety.READ)
        for e in events:
            self.assertNotIn("test-api-key", repr(e))
        self.assertTrue(any("retrying" in line and line.startswith("WARNING") for line in logs.output))
        self.assertTrue(any("-> 200" in line for line in logs.output))

    def test_send_with_response(self):
        transport, client = fake(ok({"resellerId": "r"}, {
            "X-Quota-Scope": "deposit", "X-Quota-Cost": "1", "X-Quota-Used": "12.5", "X-Quota-Limit": "200",
            "X-Quota-Delay": "0", "X-Quota-Reset": "0"}))
        resp = client.send_with_response(dna.AccountGetRequest())
        self.assertIsInstance(resp.value, dna.Account)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.attempts, 1)
        self.assertEqual(resp.json(), {"resellerId": "r"})
        self.assertEqual(resp.quota, dna.Quota("deposit", 1.0, 12.5, 200.0, 0.0, 0.0))

    def test_decode_error(self):
        _, client = fake(ok("<html>oops</html>"))
        with self.assertRaises(dna.DecodeError):
            client.account.get()

    def test_empty_body_decodes_to_none_or_empty(self):
        _, client = fake(ok(""))
        self.assertIsNone(client.send(dna.DomainInfoRequest("example.com")))
        self.assertEqual(client.dns.list("example.com"), [])

    def test_prepare_does_not_send(self):
        transport, client = fake()
        prepared = client.prepare(dna.DomainRenewRequest("example.com", 2))
        self.assertEqual(transport.requests, [])
        self.assertEqual(prepared.method, "POST")
        self.assertEqual(prepared.url, "https://api.example.test/api/v1/domains/renew")
        self.assertIs(prepared.safety, dna.Safety.BILLABLE)
        self.assertFalse(prepared.idempotent)
        self.assertJSON(prepared.body, {"domainName": "example.com", "period": 2})
        self.assertNotIn("test-api-key", repr(prepared))
        with self.assertRaises(dna.InputError):
            client.prepare(dna.DomainRenewRequest("example.com", 0))

    def test_context_manager_closes_the_transport(self):
        transport = FakeTransport()
        transport.close = mock.Mock()
        with transport.client() as client:
            self.assertIsInstance(client, dna.Client)
        transport.close.assert_called_once_with()


@dataclass
class Expiry(Model):
    domain_name: str = text("domainName")
    expiration_date: object = timestamp("expirationDate")
    remaining_days: int = integer("remainingDay")


@dataclass
class ExpiryRequest(dna.BaseRequest):
    method = "GET"
    path = "/api/v1/domains/info"
    safety = dna.Safety.READ
    response = Expiry

    domain_name: str = ""

    def query(self):
        return {"DomainName": self.domain_name}

    def validate(self, v):
        v.required("domain_name", self.domain_name)


class NoteRequest(dna.BaseRequest):
    """Not a dataclass, a placeholder path, a dict body and a plain ValueError in validate."""

    method = "put"
    path = "/api/v1/notes/{handle}"
    safety = dna.Safety.WRITE

    def __init__(self, handle, note):
        self.handle = handle
        self.note = note

    def body(self):
        return {"note": self.note, "tags": ("a", "b")}

    def validate(self, v):
        if not self.note:
            raise ValueError("note is required")


class OwnRequestTest(TestCase):
    def test_send_own_request(self):
        transport, client = fake(ok({"domainName": "example.com", "expirationDate": "2027-03-04T05:06:07",
                                     "remainingDay": 30}))
        out = client.send(ExpiryRequest("example.com"))
        self.assertIsInstance(out, Expiry)
        self.assertEqual(out.remaining_days, 30)
        self.assertEqual(out.expiration_date.year, 2027)
        self.assertEqual(transport.last.param("DomainName"), "example.com")
        with self.assertRaises(dna.InputError) as ctx:
            client.send(ExpiryRequest())
        self.assertEqual(ctx.exception.request, "ExpiryRequest")

    def test_plain_subclass_with_path_placeholder(self):
        transport, client = fake(ok(""), read_only=False)
        self.assertIsNone(client.send(NoteRequest("DNA 1/2", "hello")))
        self.assertEqual(transport.last.method, "PUT")
        self.assertEqual(transport.last.path, "/api/v1/notes/DNA%201%2F2")
        self.assertJSON(transport.last.body, {"note": "hello", "tags": ["a", "b"]})
        with self.assertRaises(dna.InputError) as ctx:
            client.send(NoteRequest("x", ""))
        self.assertIn("note is required", str(ctx.exception))
        self.assertEqual(str(NoteRequest("h", "n")), "PUT /api/v1/notes/h")

    def test_raw_json_without_response_spec(self):
        @dataclass
        class Raw(dna.BaseRequest):
            path = "/api/v1/deposit/accounts/me"

        _, client = fake(ok({"resellerId": "r", "extra": [1, 2]}))
        self.assertEqual(client.send(Raw()), {"resellerId": "r", "extra": [1, 2]})


class PacingTest(TestCase):
    def test_pace_classes(self):
        self.assertEqual(_Pacer.pace_class("/api/v1/domains/zones/apply"), ("zones", 1.0))
        self.assertEqual(_Pacer.pace_class("/api/v1/domains/bulk-search"), ("search", 0.5))
        self.assertEqual(_Pacer.pace_class("/api/v1/domains/info"), ("", 0.0))
        self.assertEqual(_Pacer.pace_class("/api/v1/products/tlds"), ("", 0.0))
        self.assertEqual(_Pacer.pace_class("/api/v1/domains/renew"), ("general", 0.2))

    def test_pacer_spaces_requests(self):
        now = [100.0]
        slept = []

        def sleep(seconds):
            slept.append(round(seconds, 3))
            now[0] += seconds

        pacer = _Pacer(lambda: now[0], sleep)
        for _ in range(3):
            pacer.wait("/api/v1/domains/zones")
        self.assertEqual(slept, [1.0, 1.0])
        slept.clear()
        pacer.wait("/api/v1/domains/info")
        self.assertEqual(slept, [])
        pacer.wait("/api/v1/domains/search")
        pacer.wait("/api/v1/domains/search")
        self.assertEqual(slept, [0.5])

    def test_client_paces_by_default(self):
        transport = FakeTransport(ok({}))
        client = transport.client(pacing=True)
        client._sleep = lambda s: None
        self.assertIsNotNone(client._pacer)
        self.assertIsNone(transport.client()._pacer)
