<div align="center">
  <a href="README-TR.md">TR <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/TR.png" alt="TR" height="20" /></a>
  <a href="README.md"> | EN <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/US.png" alt="EN" height="20" /></a>
  <a href="README-DE.md"> | DE <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/DE.png" alt="DE" height="20" /></a>
  <a href="README-SA.md"> | SA <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/SA.png" alt="AR" height="20" /></a>
  <a href="README-NL.md"> | NL <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/NL.png" alt="NL" height="20" /></a>
  <a href="README-AZ.md"> | AZ <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/AZ.png" alt="AZ" height="20" /></a>
  <a href="README-CN.md"> | CN <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/CN.png" alt="CN" height="20" /></a>
  <a href="README-FR.md"> | FR <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/FR.png" alt="FR" height="20" /></a>
  <a href="README-IT.md"> | IT <img style="padding-top: 8px" src="https://raw.githubusercontent.com/yammadev/flag-icons/master/png/IT.png" alt="IT" height="20" /></a>
</div>

# python-dna: the Python SDK for the Domain Name API

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Typed Python client for the [Domain Name API](https://www.domainnameapi.com) reseller REST API: domain search,
registration, renewal and transfer, DNS, DNSSEC, contacts, SSL certificates, hosting, orders, the product
catalogue and your balance.

- **All 64 API operations**, grouped the same way as the [`dna` CLI](https://github.com/domainreseller/cli):
  `dna domain info` is `client.domains.info`, `dna dns add` is `client.dns.add`.
- **Typed results and enums**: dataclasses with `datetime` fields and named statuses
  (`d.status == DomainStatus.PENDING_DELETE`), not dictionaries. Your editor completes every field.
- **Every operation is a request class** derived from `BaseRequest` that validates itself before anything is
  sent. Write your own the same way.
- **Exceptions you can catch by meaning**: `NotFoundError`, `InsufficientBalanceError`, `RateLimitError`,
  `OperationError`, ... with error codes, hints and correlation IDs.
- **Safe by default**: billable requests are never retried blindly, `read_only=True` blocks changes, the client
  paces itself under the rate limits and is safe to share between threads.
- **Standard library only.** Python 3.9 or newer. No telemetry: nothing leaves your process except the API
  requests you make.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## Contents

- [Install](#install)
- [Credentials and environments](#credentials-and-environments)
- [Services](#services)
- [Usage](#usage)
- [Requests and BaseRequest](#requests-and-baserequest)
- [Errors](#errors)
- [Safety and reliability](#safety-and-reliability)
- [Client options](#client-options)
- [Testing your code](#testing-your-code)
- [Migrating from v1](#migrating-from-v1)
- [Development](#development)

## Install

```bash
pip install domainnameapi
```

Versioned, tested packages are also on the [Releases](https://github.com/domainreseller/python-dna/releases)
page. Runnable programs are in [examples](examples): `quickstart.py`, `register.py`, `expiring.py`,
`dns_zone.py`, `ssl_certificate.py`, `custom_request.py` and `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Credentials and environments

You need two API credentials from the reseller panel (**API settings**). Panel login details do not work.

| Credential  | Looks like                             |
|-------------|----------------------------------------|
| Reseller ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key     | a long secret string                   |

There are two environments. **Start with OTE**, the test environment: it has its own data and its own API key,
and nothing you do there costs money or touches live domains.

```python
# Test environment (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Production (the default): real registrations, real charges
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()` reads the same variables as the `dna` CLI:

| Variable          | Meaning                                                       |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | reseller ID                                                   |
| `DNA_API_KEY`     | API key of the selected environment                           |
| `DNA_ENV`         | `production` (default) or `ote`                               |
| `DNA_TEST_MODE`   | `true` selects OTE (as in the other DomainNameAPI SDKs)       |
| `DNA_BASE_URL`    | a custom base URL, e.g. a proxy                               |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` also accepts the test-mode flags panels store: `True`, `"true"`, `"1"`, `"on"`, `"yes"` mean OTE.
A wrong key or environment fails on the first request with an `AuthenticationError` and a hint;
`client.account.get()` is the cheapest way to check.

## Services

| Service           | CLI group     | Methods                                                                                                                                                           |
|-------------------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `client.account`  | `dna account` | `get`, `transactions`, `all_transactions`                                                                                                                         |
| `client.contacts` | `dna contact` | `get`, `create`, `update`, `verification`, `resend_verification`                                                                                                  |
| `client.domains`  | `dna domain`  | `search`, `bulk_search`, `list`, `all`, `info`, `register`, `register_with_contacts`, `renew`, `renew_check`, `restore`, `transfer`, `transfer_check`, `transfer_status`, `lock`, `unlock`, `set_privacy`, `update_auth_code`, `set_name_servers`, `add_host`, `update_host`, `delete_host`, `update_contacts`, `set_contact_handles`, `documents`, `upload_documents`, `forwarding`, `set_forwarding`, `delete_forwarding` |
| `client.dns`      | `dna dns`     | `list`, `find`, `add`, `update`, `delete`, `apply`                                                                                                                |
| `client.dnssec`   | `dna dnssec`  | `get`, `add`, `remove`, `disable`                                                                                                                                 |
| `client.ssl`      | `dna ssl`     | `generate_csr`, `check_csr`, `initialize`, `configure`, `status`, `get`, `content`, `reissue`, `approvers`, `revoke`                                              |
| `client.hosting`  | `dna hosting` | `packages`, `plans`, `create`, `wait`, `get`, `get_by_token`, `status`                                                                                            |
| `client.orders`   | `dna order`   | `get`                                                                                                                                                             |
| `client.products` | `dna product` | `list`, `info`, `tlds`, `all_tlds`, `tld`, `ssls`                                                                                                                 |

Required inputs are positional arguments (`client.domains.info("example.com")`), optional ones are keyword
arguments (`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Enum arguments accept the enum,
its API name in any case or its number: `DomainStatus.ACTIVE`, `"active"` and `0` are the same.

## Usage

All snippets assume `import domainnameapi as dna` and a `client`.

### Search

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` splits lists longer than 30 domains into several requests. Prices use the account's currency, or
the one set with `dna.Client(..., currency="TRY")` or `search(..., currency="TRY")`.

### Register

With contact handles (create one with `contacts.create`):

```python
handle = client.contacts.create(dna.Contact(
    first_name="Ada", last_name="Lovelace", email="ada@example.com",
    address="1 Example Street", city="Istanbul", state="Istanbul", postal_code="34000",
    country="TR", phone_country_code="90", phone="5551234567",
))

res = client.domains.register(
    "example.com",
    years=1,
    name_servers=["ns1.example.net", "ns2.example.net"],
    handles=handle,  # one handle for all four roles, or dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

With inline contacts:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # one Contact for all four roles, or dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

Contacts are tidied before sending: fields are trimmed, the country is upper-cased and phone fields keep only
their digits (`"+90 (555) 123-45-67"` works). Some TLDs need registry attributes: find them with
`client.products.tld("com.tr").required_attributes` and pass them as `tld_attributes={...}`.

If the API answers but refuses (`"success": false`), the method raises `dna.OperationError` with the API's
message.

### Renew, transfer, restore

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # during the redemption period
```

### Domain details and the domain list

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# One page
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Every domain; pages are fetched as you iterate
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Lock, privacy, nameservers, child nameservers

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # only for DNSSEC-signed domains

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # IP version detected
client.domains.delete_host("example.com", "ns1.example.com")
```

### Contacts of a domain

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # the contact and its verification state
result = client.contacts.update("DNA-1", contact)  # updates every domain using the handle
```

### DNS zone

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # replaces all values of the set
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # one record set, or None
res = client.dns.apply("example.com")             # switch the domain to the platform nameservers
```

Names can be relative (`www`), the apex (`""` or `"@"`) or fully qualified. Record types are case-insensitive
here (`"txt"` is sent as `TXT`). Validation catches what the API would reject: a CNAME at the apex, a CAA value
without three parts, an MX value without a priority. The test environment answers every zone call with HTTP
500, so zone code can only be tried in production.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # as your DNS provider shows it
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` reads the presentation format, including whole zone-file lines.

### URL forwarding

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # None when the domain has none
client.domains.delete_forwarding("example.com")
```

### Registry documents (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

Files are base64-encoded for you; format (PDF, JPG, PNG, DOC, DOCX, ODT) and size (10 MB per file, 50 MB per
request) are checked before upload.

### SSL certificates

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
client.ssl.initialize("example.com", "PositiveSSL")  # charges the balance
client.ssl.configure("example.com", csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status("example.com")  # poll until st.is_issued
cert = client.ssl.content("example.com")
open("example.com.crt", "w").write(cert.chain)
```

### Hosting

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # charges the balance

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # polls until active
print(st.panel_address, st.username, st.password)
```

Never call `create` again for a hosting that is still provisioning: that charges twice.

### Balance, prices and orders

```python
account = client.account.get()
usd = account.balance("USD")

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # price of a 2-year .com renewal
order = client.orders.get("ORDER-CODE")
```

## Requests and BaseRequest

Every API operation is a request class: `DomainInfoRequest`, `DNSAddRequest`, `SSLConfigureRequest`, ... They
all derive from `dna.BaseRequest`, which supplies the defaults (no query string, no body, nothing to validate).
A request says where it goes with class attributes and overrides what it needs. One from this package:

```python
@dataclass
class DomainRenewRequest(BaseRequest):
    """Renew a domain. Charges your balance. CLI: dna domain renew"""

    method = "POST"
    path = "/api/v1/domains/renew"
    safety = Safety.BILLABLE
    response = DomainOperationResult

    domain_name: str = ""
    years: int = 0

    def body(self):
        return domain_body(self.domain_name).set("period", self.years)

    def validate(self, v: Validator) -> None:
        v.required("domain_name", self.domain_name)
        v.between("years", self.years, 1, 10, optional=False)
```

| Member        | Default        | Meaning                                                                             |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | HTTP method                                                                         |
| `path`        | `""`           | path below the base URL; `{placeholders}` are filled from attributes and escaped    |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` or `BILLABLE`                                        |
| `idempotent`  | `False`        | safe to send twice (reads always are); only these are retried after network errors |
| `response`    | `None`         | how answers are decoded: a `Model` subclass, `list_of(...)`, `page_of(...)` or raw JSON |
| `query()`     | `None`         | query parameters: a dict or a list of pairs                                         |
| `body()`      | `None`         | the JSON body                                                                       |
| `validate(v)` | nothing        | record problems with `v.required`, `v.between`, `v.check`, ...; nothing is sent then |

Service methods build these for you. `client.send(request)` sends any request, including classes of your own,
for example to read only the fields you need or to call an endpoint this package does not wrap yet:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import domainnameapi as dna
from domainnameapi.model import Model, integer, text, timestamp

@dataclass
class Expiry(Model):
    domain_name: str = text("domainName")
    expiration_date: Optional[datetime] = timestamp("expirationDate")
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

expiry = client.send(ExpiryRequest("example.com"))
```

Your request gets everything the built-in ones get: credentials, retries, pacing, error normalisation,
correlation IDs, tracing and read-only enforcement. `client.send_with_response(request)` also returns the status,
headers, correlation ID, quota and attempt count; `client.prepare(request)` builds the exact HTTP request without
sending it, to log or review a billable request before it goes out. Models keep the decoded JSON in `.raw`, for
fields this package does not model yet.

## Errors

Every exception derives from `dna.DomainNameAPIError` and has a `kind`.

| Exception                     | When                                                       | Useful attributes                                                   |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (a `ValueError`) | validation rejected the request; **nothing was sent**      | `request`, `fields`                                                 |
| `APIError` and subclasses     | the API answered with a non-2xx status                     | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | the API answered 2xx with `"success": false`               | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | the request did not complete (DNS, TLS, timeout, reset)    | `timeout`, `__cause__`                                              |
| `ReadOnlyError`               | a read-only client blocked a change; nothing was sent      | `request`, `safety`                                                 |

The `APIError` subclasses tell the common cases apart: `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (with `InsufficientBalanceError`), `ConflictError`, `RateLimitError` and
`ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # top up first
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # the renewal may have gone through: check the domain before trying again
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

Branch on `code`, not on `message`: messages are localised. API codes look like
`Dna.DomainService:Domain:10007`; see the [error reference](https://www.domainnameapi.com/docs/reference/errors.md).
`err.kind` is one of `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Quote the `correlation_id` when contacting support.

## Safety and reliability

- **Safety classes.** Every request is `READ`, `WRITE`, `DESTRUCTIVE` or `BILLABLE`
  (`request.endpoint().safety`). Some POST and PUT requests are reads (`DomainSearchRequest`, `SSLStatusRequest`).
- **Read-only mode.** `dna.Client(..., read_only=True)` blocks everything that is not a read, for reporting jobs
  and for exploring production safely.
- **Retries.** 429 answers are always retried, honouring `Retry-After`: the API rejects them before doing
  anything. Network errors and 502/503/504 are retried only for reads and idempotent writes, so a registration
  or renewal is never sent twice. After a failed billable request, check `err.outcome_unknown`.
- **Pacing.** The client spaces requests to stay under the per-key limits (5 requests/second, 2 searches/second,
  one zone call per second). Turn it off with `pacing=False` if you pace yourself.
- **Quota.** `send_with_response(...).quota` exposes the soft-quota headers. Over the limit the API slows
  responses down (up to 5 s) instead of rejecting them; the default 60 s timeout leaves room for that.
- **Correlation IDs.** Each request carries an `X-Correlation-ID`. Set your own with
  `with dna.correlation_id("order-4711"): ...` to tie API calls to your logs.
- **Observability.** Exchanges are logged to the `domainnameapi` logger (requests and responses at DEBUG,
  retries at WARNING); `trace=callback` hands you every request, response and retry as a `TraceEvent`, for
  metrics or error reporting. The API key is never in them.
- **Threads.** A `Client` is safe to share between threads. Create one and reuse it.
- **Tolerant decoding.** Dates without a timezone, `null`, `[]` instead of `{}`, numbers sent as strings,
  numeric or named statuses and roles in any case (`"registrant"`, `"ADMINISTRATIVE"`) all decode. Values this
  package does not know yet never break a response.

## Client options

| Option                          | Effect                                                                                   |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | use the test environment (default `"production"`)                                        |
| `base_url=url`                  | send requests to a proxy or a test server                                                |
| `timeout=60`                    | seconds per HTTP attempt                                                                 |
| `retries=2`                     | retry count                                                                              |
| `pacing=False`                  | turn client-side pacing off                                                              |
| `read_only=True`                | block every non-read request                                                             |
| `currency="TRY"`                | currency of search and catalogue prices                                                  |
| `user_agent="app/1.0"`          | put your product in front of the User-Agent                                              |
| `transport=...`                 | your own HTTP layer (`requests`, `httpx`, a proxy, ...); see `domainnameapi.transport`    |
| `trace=fn`                      | observe every request, response and retry                                                |
| `logger=logging.getLogger(...)` | log exchanges to another logger                                                          |

The default transport uses `urllib` and honours the `HTTPS_PROXY` variables. For your own CA bundle, pass
`transport=dna.UrllibTransport(ssl_context=ctx)`.

## Testing your code

`domainnameapi.testing.FakeTransport` records requests and answers with canned replies; nothing else needs
mocking:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # a Client using the fake, with pacing off

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## Migrating from v1

v2 is a new design: typed results instead of dictionaries, exceptions instead of `{"result": "ERROR"}`
envelopes, and the full REST API instead of the php-dna method set. Pin `domainnameapi<2` to keep v1 while you
switch.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | no exception                                                           |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (or `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (once per value)       |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | not in the published API; send a [request of your own](#requests-and-baserequest) if your account has them |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`; validation runs on every request               |
| `get_request_data`, `get_response_data`, ...        | `trace=`, the `domainnameapi` logger, `send_with_response`             |
| telemetry (`set_error_reporting_enabled`, Sentry)   | removed: nothing leaves your process; forward `trace` events to your own reporting |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` with your own TLS settings |

## Development

```bash
python -m unittest discover -s tests -v   # or: python -m pytest
python -m build                            # sdist and wheel
```

The tests never call the real API. `tests/testdata/openapi.json` is the API's OpenAPI document, the same one the
`dna` CLI embeds. The tests check every request class against it (method, path, query names, body fields,
required fields), every response model's JSON names against the response schemas and every enum value, and fail
when the API gains an operation without a request class. To update it:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

See [AGENTS.md](AGENTS.md) for the conventions of this repository.

## Support

- API documentation: <https://www.domainnameapi.com/docs/>
- CLI and MCP server: <https://github.com/domainreseller/cli>
- Website: <https://www.domainnameapi.com>

## License

Apache License 2.0. See [LICENSE](LICENSE).
