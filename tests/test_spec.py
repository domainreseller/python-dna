"""Every request class is checked against the API's OpenAPI document (testdata/openapi.json).

- the method and path exist, and every operation of the API has exactly one request class;
- query parameters and body fields have the exact names the API uses, and required ones are sent;
- the JSON names read by the response models exist in the response schemas;
- every integer enum of the API has a named Python enum with every value.

To update the document, download it from
https://api.domainresellerapi.com/swagger/v1/swagger.json and run the tests.
"""

import dataclasses
import json
import os
import re
from datetime import datetime, timezone

from helpers import CERT_ID, TESTDATA, TestCase, dna, sample_contact, sample_ssl_contact

from domainnameapi.model import Converter, Model, _Nested, _Page
from domainnameapi.request import BaseRequest

with open(os.path.join(TESTDATA, "openapi.json"), encoding="utf-8") as fh:
    SPEC = json.load(fh)

SCHEMAS = SPEC["components"]["schemas"]


def spec_cases():
    c = sample_contact()
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ds = dna.DS(2371, dna.DNSSECAlgorithm.ECDSAP256SHA256, dna.DSDigestType.SHA256, "1F98")
    return [
        # account
        (dna.AccountGetRequest(), dna.Account),
        (dna.AccountProfileRequest(), dna.ResellerProfile),
        (dna.AccountTransactionsRequest(
            transaction_types=[dna.TransactionType.REGISTER, dna.TransactionType.RENEW],
            product_types=[dna.ProductType.DOMAIN], charge_type=dna.ChargeType.SUBTRACT, currencies=["USD"],
            since=since, until=since.replace(month=2), trace_id="abc", description="renew", filter_text="example",
            amount=9.99, skip=10, limit=20, sort="creationTime desc"), dna.AccountTransactionsRequest.response),
        # contact
        (dna.ContactGetRequest("DNA-1"), dna.ContactDetails),
        (dna.ContactCreateRequest(c), dna.ContactCreateResult),
        (dna.ContactUpdateRequest("DNA-1", c), dna.ContactUpdateResult),
        (dna.ContactVerificationRequest("DNA-1"), dna.ContactVerificationRequest.response),
        (dna.ContactResendVerificationRequest("DNA-1"), None),
        # domain
        (dna.DomainSearchRequest("example.com", "USD"), dna.DomainSearchResult),
        (dna.DomainBulkSearchRequest(["example.com", "example.net"], "USD"), dna.DomainBulkSearchResult),
        (dna.DomainListRequest("example", [dna.DomainStatus.ACTIVE, dna.DomainStatus.PENDING_DELETE], 5, 50,
                               "expirationDate"), dna.DomainListRequest.response),
        (dna.DomainInfoRequest("example.com"), dna.DomainInfo),
        (dna.DomainRegisterRequest("example.com", dna.ContactHandles.same("DNA-1"),
                                   ["ns1.example.net", "ns2.example.net"], 2, {"x": "y"}), dna.DomainOperationResult),
        (dna.DomainRegisterWithContactsRequest("example.com", dna.DomainContacts.same(c), ["ns1.example.net"], 1,
                                               {"x": "y"}, True), dna.DomainOperationResult),
        (dna.DomainRenewRequest("example.com", 1), dna.DomainOperationResult),
        (dna.DomainRenewCheckRequest("example.com", 1), dna.RenewCheck),
        (dna.DomainRestoreRequest("example.com"), None),
        (dna.DomainTransferRequest("example.com", "Xy7!kP2q", 1), dna.DomainOperationResult),
        (dna.DomainTransferCheckRequest("example.com", "Xy7!kP2q"), dna.TransferCheck),
        (dna.DomainTransferStatusRequest("example.com"), dna.TransferStatus),
        (dna.DomainLockRequest("example.com"), None),
        (dna.DomainUnlockRequest("example.com"), None),
        (dna.DomainPrivacyRequest("example.com", True), None),
        (dna.DomainUpdateAuthCodeRequest("example.com"), dna.AuthCode),
        (dna.DomainNameServersSetRequest("example.com", ["ns1.example.net"], dna.DNSSECMode.KEEP), None),
        (dna.DomainHostAddRequest("example.com", "ns1.example.com", ["192.0.2.1", "2001:db8::1"]), None),
        (dna.DomainHostUpdateRequest("example.com", "ns1.example.com", ["192.0.2.2"], "ns3.example.com"), None),
        (dna.DomainHostDeleteRequest("example.com", "ns1.example.com"), None),
        (dna.DomainContactsUpdateRequest("example.com", dna.DomainContacts.same(c)), None),
        (dna.DomainContactsSetHandlesRequest("example.com", dna.ContactHandles.same("DNA-1")), None),
        (dna.DomainDocumentsListRequest("example.com.tr", [dna.DocumentType.IDENTITY_CARD], 0, 10),
         dna.DomainDocumentsListRequest.response),
        (dna.DomainDocumentsUploadRequest("example.com.tr", [
            dna.DocumentUpload(dna.DocumentType.IDENTITY_CARD, "id.pdf", b"%PDF-1.4")]), dna.DocumentUploadResult),
        (dna.DomainForwardGetRequest("example.com"), dna.Forwarding),
        (dna.DomainForwardSetRequest("example.com", "https://www.example.org", dna.ForwardType.FRAME), None),
        (dna.DomainForwardDeleteRequest("example.com"), None),
        # dns
        (dna.DNSListRequest("example.com"), dna.DNSListRequest.response),
        (dna.DNSAddRequest("example.com", "www", "a", ["192.0.2.1"], 600), None),
        (dna.DNSUpdateRequest("example.com", "www", dna.RecordType.A, ["192.0.2.2"], "web", 600), None),
        (dna.DNSDeleteRequest("example.com", "www", dna.RecordType.A, "192.0.2.1"), None),
        (dna.DNSApplyRequest("example.com"), dna.ZoneApplyResult),
        # dnssec
        (dna.DNSSECGetRequest("example.com"), dna.DNSSECInfo),
        (dna.DNSSECAddRequest("example.com", [ds]), dna.DNSSECAddRequest.response),
        (dna.DNSSECRemoveRequest("example.com", ds), dna.DNSSECOperationResult),
        (dna.DNSSECDisableRequest("example.com"), dna.DNSSECOperationResult),
        # ssl
        (dna.SSLGenerateCSRRequest("example.com", "TR", "Istanbul", "Istanbul", "Example Ltd", "IT",
                                   ["www.example.com"]), dna.CSR),
        (dna.SSLCheckCSRRequest("-----BEGIN CERTIFICATE REQUEST-----"), dna.CSRInfo),
        (dna.SSLInitializeRequest("example.com", "PositiveSSL"), dna.SSLOperationResult),
        (dna.SSLRenewRequest(CERT_ID), dna.SSLOperationResult),
        (dna.SSLConfigureRequest(CERT_ID, "csr", sample_ssl_contact(), "key", "admin@example.com",
                                 dna.AuthenticationType.EMAIL, dna.WebServerType.APACHE, ["a.example.com"],
                                 ["*.example.com"]), dna.SSLOperationResult),
        (dna.SSLStatusRequest(CERT_ID), dna.CertificateStatus),
        (dna.SSLGetRequest(CERT_ID), dna.Certificate),
        (dna.SSLContentRequest(CERT_ID), dna.CertificateContent),
        (dna.SSLListRequest("example.com", 5, 50), dna.SSLListRequest.response),
        (dna.SSLReissueRequest(CERT_ID, "admin@example.com", "csr", "key"), dna.SSLOperationResult),
        (dna.SSLApproversRequest(CERT_ID, "example.com", "PositiveSSL"), dna.SSLApproversRequest.response),
        (dna.SSLRevokeRequest(CERT_ID), dna.SSLOperationResult),
        # hosting
        (dna.HostingPackagesRequest(), dna.HostingPackagesRequest.response),
        (dna.HostingPlansRequest("6f1c0000-0000-4000-8000-000000000001"), dna.HostingPlansRequest.response),
        (dna.HostingCreateRequest("example.com", "Linux-Starter"), dna.HostingCreateResult),
        (dna.HostingGetRequest(service_id="HST-1"), dna.Hosting),
        (dna.HostingGetByTokenRequest("tok"), dna.Hosting),
        (dna.HostingStatusRequest(domain_name="example.com"), dna.HostingStatus),
        # order
        (dna.OrderGetRequest("ORD-1"), dna.Order),
        # product
        (dna.ProductListRequest("com", dna.ProductType.DOMAIN, 0, 10), dna.ProductListRequest.response),
        (dna.ProductInfoRequest("com", dna.OrderType.RENEW, 2), dna.ProductInfo),
        (dna.TLDListRequest("com.tr", "USD", 0, 10), dna.TLDListRequest.response),
        (dna.SSLProductListRequest("ssl", "Sectigo", "USD", 1, True, False, 0, 10),
         dna.SSLProductListRequest.response),
    ]


#: Python fields deliberately not in a response schema (the model is shared with a request).
RESPONSE_FIELDS_NOT_IN_SPEC = {
    "Certificate.contacts[].title",  # SSLContact is also the configure input, which has a title
}


def resolve(schema):
    while schema:
        if "$ref" in schema:
            schema = SCHEMAS[schema["$ref"].rsplit("/", 1)[1]]
            continue
        if isinstance(schema.get("allOf"), list) and len(schema["allOf"]) == 1:
            schema = schema["allOf"][0]
            continue
        return schema
    return None


def find_operation(method, path):
    for template, ops in SPEC["paths"].items():
        pattern = "^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(template)) + "$"
        if re.match(pattern, path) and method.lower() in ops:
            return template, ops[method.lower()]
    return None, None


def first_schema(content):
    for ct in ("application/json", "text/json", "text/plain"):
        if ct in content:
            return content[ct].get("schema")
    for value in content.values():
        return value.get("schema")
    return None


def check_json(value, schema, path):
    schema = resolve(schema)
    if schema is None:
        return []
    errors = []
    if isinstance(value, dict):
        props = schema.get("properties")
        if props is None:
            return []  # a free-form map such as tldAttributes
        for key, sub in value.items():
            if key not in props:
                errors.append("%s.%s is not in the spec (want one of %s)" % (path, key, sorted(props)))
                continue
            errors.extend(check_json(sub, props[key], path + "." + key))
        for required in schema.get("required", []):
            if required not in value:
                errors.append("%s.%s is required by the spec but not sent" % (path, required))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            errors.extend(check_json(item, schema.get("items"), "%s[%d]" % (path, i)))
    return errors


def check_response(spec, schema, path):
    """Check that every JSON name a model reads exists in its schema."""
    schema = resolve(schema)
    if schema is None:
        return []
    if isinstance(spec, type) and issubclass(spec, Model):
        spec = _Nested(spec)
    if isinstance(spec, _Page):
        props = schema.get("properties") or {}
        errors = [] if "items" in props and "totalCount" in props else ["%s is a page, but the schema is not" % path]
        if "items" in props:
            errors.extend(check_response(dna.model.list_of(spec.item), props["items"], path + ".items"))
        return errors
    if not isinstance(spec, Converter):
        return ["%s: unknown response spec %r" % (path, spec)]
    if spec.many:
        if schema.get("type") != "array" and "items" not in schema:
            return ["%s is a list, but the spec has no array" % path]
        item = getattr(spec, "item", None)
        return check_response(item, schema.get("items"), path + "[]") if item is not None else []
    if spec.nested is None:
        return []
    props = schema.get("properties") or {}
    errors = []
    for f in dataclasses.fields(spec.nested):
        api = f.metadata.get("api")
        if api is None:
            continue
        field_path = path + "." + api
        if api not in props:
            if field_path not in RESPONSE_FIELDS_NOT_IN_SPEC:
                errors.append("%s (%s) is not in the response schema (want one of %s)" % (
                    field_path, f.name, sorted(props)))
            continue
        errors.extend(check_response(f.metadata["conv"], props[api], field_path))
    return errors


class SpecTest(TestCase):
    def setUp(self):
        self.client = dna.Client("r", "k", base_url="https://api.example.test", pacing=False)

    def test_every_operation_has_one_request_class(self):
        covered = {}
        for req, _ in spec_cases():
            ep = req.endpoint()
            template, op = find_operation(ep.method, ep.path)
            self.assertIsNotNone(op, "%s: %s %s is not in the OpenAPI document" % (type(req).__name__, ep.method,
                                                                                    ep.path))
            key = ep.method + " " + template
            self.assertNotIn(key, covered, "%s and %s both cover %s" % (covered.get(key), type(req).__name__, key))
            covered[key] = type(req).__name__
        missing = sorted("%s %s" % (m.upper(), p) for p, ops in SPEC["paths"].items() for m in ops
                         if "%s %s" % (m.upper(), p) not in covered)
        self.assertEqual(missing, [], "the API has operations without a request class")

    def test_every_request_class_is_checked(self):
        exported = {name for name in dna.__all__ if name.endswith("Request") and name not in ("BaseRequest",)
                    and isinstance(getattr(dna, name), type) and issubclass(getattr(dna, name), BaseRequest)}
        checked = {type(req).__name__ for req, _ in spec_cases()}
        self.assertEqual(sorted(exported - checked), [])
        for name in exported:
            cls = getattr(dna, name)
            self.assertTrue(dataclasses.is_dataclass(cls), name + " is not a dataclass")

    def test_requests_match_the_spec(self):
        for req, response in spec_cases():
            name = type(req).__name__
            with self.subTest(name):
                ep = req.endpoint()
                _, op = find_operation(ep.method, ep.path)
                if op is None:
                    self.skipTest("reported by test_every_operation_has_one_request_class")
                prepared = self.client.prepare(req)  # validates the complete sample
                if ep.method == "GET":
                    self.assertIs(ep.safety, dna.Safety.READ, "a GET request must be a read")

                from urllib.parse import parse_qs, urlsplit

                sent = parse_qs(urlsplit(prepared.url).query, keep_blank_values=True)
                params = {p["name"]: p for p in op.get("parameters", []) if p["in"] == "query"}
                for key in sent:
                    self.assertIn(key, params, "query parameter %r is not in the spec (want one of %s)"
                                  % (key, sorted(params)))
                for key, p in params.items():
                    if p.get("required"):
                        self.assertIn(key, sent, "required query parameter %r is not sent" % key)

                body = req.body()
                if op.get("requestBody") is None:
                    self.assertIsNone(body, "sends a body, but the operation takes none")
                else:
                    self.assertIsNotNone(body, "sends no body, but the operation takes one")
                    value = json.loads(prepared.body)
                    errors = check_json(value, first_schema(op["requestBody"]["content"]), "body")
                    self.assertEqual(errors, [])

                if response is None:
                    continue
                schema = None
                for code in ("200", "201", "202"):
                    if code in op.get("responses", {}):
                        schema = first_schema(op["responses"][code].get("content", {}))
                        break
                self.assertIsNotNone(schema, "the spec has no response body, but the request decodes one")
                root = response.__name__ if isinstance(response, type) else "response"
                self.assertEqual(check_response(response, schema, root), [])

    def test_spec_enums(self):
        domains = "Dna.DomainService.Domains."
        dnssec = "Dna.DomainService.Dnssec."
        deposit = "Dna.DepositService.Accounts."
        reseller = "Dna.ResellerService.Resellers."
        orders = "Dna.OrderService.Orders."
        product = "Dna.ProductService.Products."
        known = {
            domains + "DomainDto.status": dna.DomainStatus,
            domains + "DomainDocumentInfoDto.status": dna.DocumentStatus,
            domains + "DomainDocumentInfoDto.type": dna.DocumentType,
            domains + "DomainDocumentInfoDto.operationType": dna.DocumentOperationType,
            domains + "DomainDocumentUploadItemInput.documentType": dna.DocumentType,
            domains + "DomainDocumentUploadedItemDto.type": dna.DocumentType,
            dnssec + "DnssecInfoBaseDto.status": dna.DNSSECStatus,
            dnssec + "DsRecordBaseDto.status": dna.DSRecordStatus,
            dnssec + "DnssecOperationResultBaseDto.operationType": dna.DNSSECOperationType,
            "Dna.DomainService.Dns.DnsEditNameServerInput.dnssecMode": dna.DNSSECMode,
            deposit + "AccountTransactionDto.type": dna.TransactionType,
            deposit + "AccountTransactionDto.status": dna.TransactionStatus,
            deposit + "AccountTransactionDto.chargeType": dna.ChargeType,
            deposit + "AccountTransactionDto.productType": dna.ProductType,
            reseller + "ResellerMeDto.accountCurrency": dna.AccountCurrency,
            reseller + "ResellerMeDto.status": dna.ResellerStatus,
            orders + "OrderDto.status": dna.OrderStatus,
            orders + "OrderProductDto.status": dna.OrderProductStatus,
            orders + "OrderProductDto.orderType": dna.OrderType,
            orders + "OrderProductDto.productType": dna.ProductType,
            product + "ProductDto.productType": dna.ProductType,
            product + "ProductInfoDto.productType": dna.ProductType,
            product + "SubproductDto.productType": dna.ProductType,
        }
        seen = set()
        for schema_name, schema in SCHEMAS.items():
            for prop, p in (schema.get("properties") or {}).items():
                values = p.get("enum") if isinstance(p, dict) else None
                if not values:
                    continue
                key = schema_name + "." + prop
                self.assertIn(key, known, "%s is an enum without a Python enum here" % key)
                seen.add(key)
                for value in values:
                    self.assertIn(int(value), {int(m) for m in known[key]}, "%s: value %s has no name" % (key, value))
        self.assertEqual(sorted(set(known) - seen), [], "no longer enums in the spec")
