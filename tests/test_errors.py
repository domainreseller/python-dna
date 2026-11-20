"""Error normalisation, classification and helpers."""

from helpers import TestCase, dna

from domainnameapi.errors import api_error_from_response


def make(status, body=b"", headers=None, method="GET", path="/api/v1/x"):
    if isinstance(body, str):
        body = body.encode("utf-8")
    return api_error_from_response(method, path, status, headers or {}, body)


class NormalisationTest(TestCase):
    def test_cases(self):
        cases = [
            ("abp envelope", 404,
             '{"error":{"code":"Dna.DomainService:Domain:10007","message":"The domain name you requested could not be '
             'found.","details":"The domain could not be found.","data":[],"validationErrors":null}}',
             None, dna.ErrorCode.DOMAIN_NOT_FOUND, "The domain name you requested could not be found.",
             dna.ErrorKind.NOT_FOUND, dna.NotFoundError),
            ("flat object", 409, '{"code":"X:1","message":"busy"}', None, "X:1", "busy", dna.ErrorKind.CONFLICT,
             dna.ConflictError),
            ("validation without code", 400,
             '{"error":{"code":null,"message":"Validation failed.","details":"...","validationErrors":[{"message":'
             '"The DomainName field is required.","members":["$.domainName"]}]}}',
             None, "HTTP_400", "Validation failed.", dna.ErrorKind.VALIDATION, dna.ValidationError),
            ("plain-text missing key", 401, "Unauthorized! API Key is missing.", None, dna.ErrorCode.MISSING_API_KEY,
             "Unauthorized! API Key is missing.", dna.ErrorKind.AUTH, dna.AuthenticationError),
            ("plain-text missing reseller", 401, "Unauthorized! ResellerId is missing.", None,
             dna.ErrorCode.MISSING_RESELLER_ID, None, dna.ErrorKind.AUTH, dna.AuthenticationError),
            ("plain-text invalid key", 401, "Unauthorized! Invalid API Key.", None, dna.ErrorCode.INVALID_API_KEY,
             None, dna.ErrorKind.AUTH, dna.AuthenticationError),
            ("sub-reseller", 401, "Unauthorized! You do not have authorisation for this operation.", None,
             dna.ErrorCode.SUBRESELLER_NOT_ALLOWED, None, dna.ErrorKind.AUTH, dna.AuthenticationError),
            ("empty 401", 401, "", None, dna.ErrorCode.UNAUTHORIZED, "unauthorized", dna.ErrorKind.AUTH,
             dna.AuthenticationError),
            ("redirect", 302, "", None, dna.ErrorCode.INVALID_RESELLER, None, dna.ErrorKind.AUTH,
             dna.AuthenticationError),
            ("rate limited", 429, "", {"Retry-After": "2"}, dna.ErrorCode.RATE_LIMITED,
             "rate limit exceeded (retry after 2s)", dna.ErrorKind.RATE_LIMITED, dna.RateLimitError),
            ("empty 500", 500, "", None, "HTTP_500", "internal server error", dna.ErrorKind.SERVER, dna.ServerError),
            ("html 502", 502, "<html><body>Bad gateway</body></html>", None, "HTTP_502", "bad gateway",
             dna.ErrorKind.SERVER, dna.ServerError),
            ("boilerplate replaced by details", 400,
             '{"error":{"code":"Dna.DomainService:Dns:10024","message":"Exception of type '
             '\'Volo.Abp.BusinessException\' was thrown.","details":"Dna Record already exists."}}',
             None, "Dna.DomainService:Dns:10024", "Record already exists.", dna.ErrorKind.VALIDATION,
             dna.ValidationError),
            ("code echo without details", 400,
             '{"error":{"code":"Dna.DomainService:Dns:10030","message":"Dna.DomainService:Dns:10030","details":null}}',
             None, "Dna.DomainService:Dns:10030", "the operation could not be completed", dna.ErrorKind.VALIDATION,
             dna.ValidationError),
            ("business rule", 403, '{"error":{"code":"","message":"Hosting already exists"}}', None, "HTTP_403",
             "Hosting already exists", dna.ErrorKind.REJECTED, dna.RejectedError),
            ("payment required", 402,
             '{"error":{"code":"Dna.DomainService:Deposit:10001","message":"Insufficient balance","data":'
             '{"usdBalance":1.5,"requiredAmount":11.99}}}',
             None, "Dna.DomainService:Deposit:10001", None, dna.ErrorKind.REJECTED, dna.InsufficientBalanceError),
            ("teapot", 418, "", None, "HTTP_418", "i'm a teapot", dna.ErrorKind.UNKNOWN, dna.APIError),
        ]
        for name, status, body, headers, code, message, kind, cls in cases:
            with self.subTest(name):
                e = make(status, body, headers)
                self.assertEqual(e.code, code)
                if message is not None:
                    self.assertEqual(e.message, message)
                self.assertTrue(e.message)
                self.assertIs(e.kind, kind)
                self.assertIs(dna.kind_of(e), kind)
                self.assertIs(type(e), cls)
                self.assertIsInstance(e, dna.APIError)
                self.assertIsInstance(e, dna.DomainNameAPIError)
                self.assertEqual(e.status_code, status)

    def test_details(self):
        e = make(400, '{"error":{"message":"Validation failed.","validationErrors":[{"message":"The DomainName field '
                      'is required.","members":["$.domainName"]},{"message":"Bad.","members":["Registrant.Country",'
                      '"Admin.Country"]}]}}', {"X-Correlation-Id": "c-1"}, "POST", "/api/v1/domains/search")
        self.assertEqual([f.field for f in e.fields], ["domainName", "Registrant.Country,Admin.Country"])
        self.assertEqual(e.correlation_id, "c-1")
        self.assertEqual(str(e), "POST /api/v1/domains/search: 400 HTTP_400: Validation failed.; domainName: The "
                                 "DomainName field is required.; Registrant.Country,Admin.Country: Bad.")

        e = make(429, "", {"Retry-After": "1.5"})
        self.assertEqual(e.retry_after, 1.5)
        self.assertTrue(e.retryable)
        self.assertTrue(e.hint)

        e = make(402, '{"error":{"code":"Dna.DomainService:Deposit:10001","message":"x","data":{"usdBalance":1.5}}}')
        self.assertEqual(e.data, {"usdBalance": 1.5})
        self.assertTrue(e.insufficient_balance)

        e = make(400, '{"error":{"code":"Dna.DepositService:Deposit:10002","message":"Insufficient balance."}}')
        self.assertIsInstance(e, dna.InsufficientBalanceError)
        self.assertTrue(e.insufficient_balance)
        self.assertIs(e.kind, dna.ErrorKind.REJECTED)

    def test_outcome_unknown(self):
        for code in (dna.ErrorCode.REGISTERED_NOT_RECORDED, dna.ErrorCode.RENEWED_NOT_RECORDED,
                     dna.ErrorCode.TRANSFER_NOT_RECORDED, dna.ErrorCode.SSL_SENT_TO_CA,
                     dna.ErrorCode.SSL_OUTCOME_UNVERIFIED):
            e = make(500, '{"error":{"code":"%s","message":"x"}}' % code)
            self.assertTrue(e.outcome_unknown, code)
            self.assertFalse(e.retryable, code)
            self.assertIn("already", e.hint)
        self.assertFalse(make(500).outcome_unknown)
        self.assertTrue(make(500).retryable)
        self.assertFalse(make(501).retryable)
        self.assertFalse(make(404).retryable)

    def test_hints(self):
        self.assertIn("different API keys", make(401, "Unauthorized! Invalid API Key.").hint)
        self.assertIn("environment", make(404).hint)
        self.assertIn("c-7", make(500, "", {"X-Correlation-Id": "c-7"}).hint)
        self.assertEqual(make(409, '{"code":"x","message":"y"}').hint, "")


class OtherErrorsTest(TestCase):
    def test_kinds(self):
        self.assertIsNone(dna.kind_of(None))
        self.assertIs(dna.kind_of(RuntimeError()), dna.ErrorKind.UNKNOWN)
        self.assertIs(dna.OperationError("POST", "/x").kind, dna.ErrorKind.REJECTED)
        self.assertIs(dna.NetworkError("GET", "/x", "boom").kind, dna.ErrorKind.NETWORK)
        self.assertIs(dna.InputError("R", []).kind, dna.ErrorKind.INVALID_INPUT)
        self.assertIs(dna.ReadOnlyError("R", "POST", "/x", dna.Safety.WRITE).kind, dna.ErrorKind.READ_ONLY)
        self.assertIs(dna.MissingCredentialsError().kind, dna.ErrorKind.AUTH)

    def test_operation_error(self):
        e = dna.OperationError("POST", "/api/v1/domains/register", " 2306 ", " Domain is taken ", "c-1")
        self.assertEqual(e.code, "2306")
        self.assertEqual(e.message, "Domain is taken")
        self.assertEqual(str(e), "POST /api/v1/domains/register: 2306: Domain is taken")
        self.assertIn("operation failed", str(dna.OperationError("POST", "/x")))
        self.assertFalse(e.outcome_unknown)

    def test_network_error_outcome(self):
        self.assertFalse(dna.NetworkError("GET", "/x", "t", safety=dna.Safety.READ).outcome_unknown)
        self.assertTrue(dna.NetworkError("POST", "/x", "t", safety=dna.Safety.BILLABLE).outcome_unknown)
        self.assertTrue(dna.NetworkError("POST", "/x", "t").retryable)

    def test_input_error_is_a_value_error(self):
        e = dna.InputError("DomainRenewRequest", [dna.FieldError("years", "must be between 1 and 10"),
                                                  dna.FieldError("", "something else")])
        self.assertIsInstance(e, ValueError)
        self.assertEqual(str(e), "invalid DomainRenewRequest: years: must be between 1 and 10; something else")

    def test_wait_timeout_is_a_timeout_error(self):
        e = dna.WaitTimeoutError("still provisioning", last="state")
        self.assertIsInstance(e, TimeoutError)
        self.assertEqual(e.last, "state")
