"""The standard-library transport, against a local HTTP server (127.0.0.1 only, never the real API)."""

import http.server
import json
import socket
import threading
import time

from helpers import TestCase, dna

from domainnameapi.transport import HttpRequest, TransportError, UrllibTransport


class Handler(http.server.BaseHTTPRequestHandler):
    received = []

    def log_message(self, *args):  # keep test output clean
        pass

    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        Handler.received.append((self.command, self.path, dict(self.headers.items()), body))
        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "/Error/Suspend")
            self.end_headers()
            return
        if self.path.startswith("/slow"):
            time.sleep(1.5)
        status = 404 if self.path.startswith("/missing") else 200
        payload = json.dumps({"path": self.path, "echo": body.decode("utf-8") or None}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Correlation-Id", "srv-1")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = do_DELETE = _answer


class TransportTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.received.clear()
        self.transport = UrllibTransport(connect_timeout=2)

    def test_success_and_headers(self):
        resp = self.transport.send(HttpRequest("POST", self.base + "/api/v1/x?a=1",
                                               {"X-API-KEY": "k", "__reseller": "r", "Content-Type": "application/json"},
                                               b'{"a":1}', timeout=5))
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.header("x-correlation-id"), "srv-1")
        self.assertEqual(json.loads(resp.body)["echo"], '{"a":1}')
        method, path, headers, _ = Handler.received[-1]
        self.assertEqual((method, path), ("POST", "/api/v1/x?a=1"))
        lower = {k.lower(): v for k, v in headers.items()}
        self.assertEqual(lower["x-api-key"], "k")
        self.assertEqual(lower["__reseller"], "r")

    def test_error_statuses_are_responses(self):
        resp = self.transport.send(HttpRequest("GET", self.base + "/missing", {}, None, timeout=5))
        self.assertEqual(resp.status, 404)
        self.assertEqual(json.loads(resp.body)["path"], "/missing")

    def test_redirects_are_not_followed(self):
        resp = self.transport.send(HttpRequest("GET", self.base + "/redirect", {}, None, timeout=5))
        self.assertEqual(resp.status, 302)
        self.assertEqual(len(Handler.received), 1)

    def test_timeout(self):
        with self.assertRaises(TransportError) as ctx:
            self.transport.send(HttpRequest("GET", self.base + "/slow", {}, None, timeout=0.3))
        self.assertTrue(ctx.exception.timeout)

    def test_connection_refused(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        with self.assertRaises(TransportError) as ctx:
            self.transport.send(HttpRequest("GET", "http://127.0.0.1:%d/" % port, {}, None, timeout=2))
        self.assertTrue(ctx.exception.retryable)

    def test_invalid_url(self):
        with self.assertRaises(TransportError) as ctx:
            self.transport.send(HttpRequest("GET", "not a url", {}, None, timeout=2))
        self.assertFalse(ctx.exception.retryable)

    def test_client_end_to_end(self):
        client = dna.Client("rid", "key", base_url=self.base, pacing=False)
        resp = client.send_with_response(dna.DomainInfoRequest("example.com"))
        self.assertEqual(resp.correlation_id, "srv-1")
        self.assertIsInstance(resp.value, dna.DomainInfo)
        self.assertEqual(Handler.received[-1][1], "/api/v1/domains/info?DomainName=example.com")
        with self.assertRaises(dna.AuthenticationError):
            dna.Client("rid", "key", base_url=self.base + "/redirect", pacing=False).account.get()
