# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-11-26

### Added

- Every request now carries `X-App` and `X-Version` headers that tell the API which integration sent it. They
  default to `python` and the SDK version; set them with `Client(app_name=..., app_version=...)` or, for
  `Client.from_env()`, with `DNA_APP` and `DNA_APP_VERSION`. The name is lowercased and keeps only `a-z`, `0-9`,
  `.`, `_` and `-`; the version keeps only digits and dots (`V2.0.20-beta` becomes `2.0.20`). An empty or invalid
  name falls back to `python`, an empty version to the SDK version. New constants: `DEFAULT_APP`, `ENV_APP`,
  `ENV_APP_VERSION`. The User-Agent is unchanged.

## [2.1.0] - 2026-11-22

**Breaking, forced by the API.** On 2026-11-20 the API changed its SSL endpoints in production and OTE: a domain
can now have several certificates, so an existing certificate is addressed by its certificate id (a GUID) and no
longer by its domain name. The SSL calls of 2.0.0 fail against the API since then; this release follows the API.
Nothing outside `client.ssl` changed incompatibly.

What to change in your code:

- Keep the `certificate_id` that `ssl.initialize` returns and pass it, instead of the domain name, to
  `ssl.configure`, `ssl.status`, `ssl.get`, `ssl.content`, `ssl.reissue` and `ssl.revoke`. For certificates you
  already have, look the id up once with `ssl.list(domain_name="example.com")`.
- Call `ssl.approvers` with keywords: `approvers(certificate_id=...)` for an existing certificate, or
  `approvers(domain_name=..., package_code=...)` before a purchase.
- Renew with `ssl.renew(certificate_id)` followed by `ssl.configure(<the id renew returned>, ...)`. A second
  `ssl.initialize` is not a renewal: it buys an unrelated certificate at the purchase price, and the old
  certificate never becomes `Renewed`.
- Configure a certificate within 15 days of `initialize` or `renew` (the API used to allow 7).

### Changed

- **Breaking:** `ssl.configure`, `ssl.status`, `ssl.get`, `ssl.content`, `ssl.reissue` and `ssl.revoke` take the
  certificate id as their first argument instead of the domain name. `SSLConfigureRequest`, `SSLStatusRequest`,
  `SSLGetRequest`, `SSLContentRequest`, `SSLReissueRequest` and `SSLRevokeRequest` have a `certificate_id` field
  in place of `domain_name`.
- **Breaking:** `ssl.approvers` takes keyword arguments only, `certificate_id` or `domain_name` with
  `package_code`; a domain name without a package code is refused before sending, as the API refuses it.
  `SSLApproversRequest` has `certificate_id` as its first field.
- A certificate id that is not a GUID, such as a domain name passed by code written for 2.0.0, raises
  `InputError` before anything is sent, with a message that says where to get the id.
- `Certificate`, `CertificateStatus` and `CertificateContent` have a `certificate_id` field. It is their first
  field: build these models with keyword arguments.
- `tests/testdata/openapi.json` is the API's current document (67 operations).

### Added

- `ssl.renew(certificate_id)` and `SSLRenewRequest`: renew a certificate from 30 days before its subscription
  ends. It charges the balance and has the safety class of `initialize` (`BILLABLE`): never retried after a
  network error or a 5xx answer, and blocked by a read-only client. The result's `certificate_id` is the id of
  the new renewal certificate.
- `ssl.list(domain_name=..., skip=..., limit=...)` and `ssl.all(domain_name=...)`, with `SSLListRequest` and
  `CertificateListItem`: your certificates, newest first, with their ids, states and expiry dates.
- `account.profile()` with `AccountProfileRequest`, `ResellerProfile` and the enums `AccountCurrency` and
  `ResellerStatus`: the reseller the credentials belong to.

## [2.0.0] - 2026-11-20

A new SDK, designed for Python and for the REST API instead of ported from php-dna, and modelled on the
[`dna` CLI](https://github.com/domainreseller/cli) like go-dna and dotnet-dna v2. See "Migrating from v1" in the
README. pip on Python 3.8 keeps installing 1.x; pin `domainnameapi<2` to stay on v1 elsewhere.

### Added

- All 64 operations of the REST API, grouped like the `dna` CLI: `client.account`, `contacts`, `domains`, `dns`,
  `dnssec`, `ssl`, `hosting`, `orders` and `products`. New compared to v1: contact handles and verification,
  registration with handles, renew check, restore, auth code update, registry documents, DNSSEC, SSL
  certificates, hosting, orders, balance transactions and product prices.
- Typed results: dataclass models with `datetime` fields, `IntEnum`/`str` enums with the API's names
  (`DomainStatus.PENDING_DELETE`), and tolerant decoding of the API's quirks: dates without a timezone, `[]`
  instead of `{}`, numbers sent as strings, numeric or named statuses, roles in any case, unknown values. Every
  model keeps its JSON in `.raw`.
- A request class per operation (`DomainRegisterRequest`, `DNSAddRequest`, ...) derived from `BaseRequest`, with
  a safety class (`READ`, `WRITE`, `DESTRUCTIVE`, `BILLABLE`) and validation that runs before anything is sent.
  `client.send` sends your own request classes too; `client.send_with_response` adds status, headers,
  correlation ID, quota and attempts; `client.prepare` previews a request without sending it.
- `domainnameapi.model`: `Model` and field helpers (`text`, `integer`, `timestamp`, `model_list`, ...) to declare
  your own response models.
- Exceptions by meaning: `InputError`, `ReadOnlyError`, `APIError` with `AuthenticationError`, `NotFoundError`,
  `ValidationError`, `RejectedError`, `InsufficientBalanceError`, `ConflictError`, `RateLimitError`,
  `ServerError`, plus `OperationError` for `"success": false` and `NetworkError`. Each has a `kind`, a `code`,
  `outcome_unknown` and `retryable`; `APIError` adds `hint`, `fields`, `data` and `correlation_id`.
- Iterators over paged lists: `domains.all`, `account.all_transactions`, `products.all_tlds`.
- `Client.from_env()` with the CLI's environment variables, `read_only=True`, `currency=`, `trace=`, logging to
  the `domainnameapi` logger, `dna.correlation_id(...)`, `hosting.wait` and `dns.find`.
- Retries on 429 for every request and on network errors and 502/503/504 only for requests that are safe to
  repeat; client-side pacing under the rate limits; a client that is safe to share between threads.
- A pluggable `transport=` (any object with `send(HttpRequest) -> HttpResponse`) and
  `domainnameapi.testing.FakeTransport` to test your own code without the network.
- Tests that check every request class, response model and enum against the API's OpenAPI document, and run
  the examples against a fake API.

### Removed

- The php-dna compatible API: `DomainNameAPI`/`DomainNameApi`, `DNARest`, the dictionary results, the
  `{"result": "ERROR"}` envelopes, the camelCase aliases and the diagnostics getters (`get_request_data`, ...).
  Use `trace=`, the `domainnameapi` logger or `send_with_response` instead.
- Telemetry: the SDK no longer sends anything to Sentry. Forward `trace` events to your own reporting.
- `cancel_transfer`, `approve_transfer` and `reject_transfer`, which called endpoints that are not part of the
  published API, and the php-dna conformance fixtures.
- Python 3.8 support. Python 3.9 or newer is required.

## [1.0.1] - 2026-11-14

### Changed

- Error reporting now has its own Sentry project: `DEFAULT_SENTRY_DSN` points to DomainNameAPI's
  python-dna project, so telemetry is active by default as documented. Turn it off with
  `set_error_reporting_enabled(False)`; `sentry_dsn=` still overrides the target.

## [1.0.0] - 2026-11-09

First release: a faithful Python port of [php-dna](https://github.com/domainreseller/php-dna) 4.0.4.

### Added

- `DomainNameAPI` client (alias `DomainNameApi`) with all 45 php-dna methods in snake_case;
  the php-dna camelCase/PascalCase names work as aliases.
  - Account: `get_reseller_details`, `get_current_balance`.
  - Search and lists: `check_availability`, `get_list`, `get_tld_list`.
  - Domains: `get_details`, `sync_from_registry`, `get_contacts`, `save_contacts`, `modify_name_server`,
    `enable_theft_protection_lock`, `disable_theft_protection_lock`, `modify_privacy_protection_status`,
    `renew`, `register_with_contact_info` (including `.tr` TRABIS attribute normalisation).
  - Child nameservers: `add_child_name_server`, `delete_child_name_server`, `modify_child_name_server`.
  - Transfers: `transfer`, `cancel_transfer`, `approve_transfer`, `reject_transfer`, `check_transfer`.
  - DNS zone: `get_resource_records`, `add/edit/delete_resource_record`, `apply_resource_records`,
    `set_resource_record_set`, `delete_resource_record_set`, `add/remove/replace_resource_record_value`,
    with zone call pacing against the gateway's rate limit.
  - URL forwarding: `get_forwarding`, `set_forwarding`, `delete_forwarding`.
  - Utilities: `is_tr_tld`, `validate_contact`; diagnostics (`get_request_data`, `get_response_data`, ...)
    and settings (`set_error_reporting_enabled`, `set_telemetry_minimal`, `set_ssl_verification`).
- Same return values as php-dna (plain `dict`/`list`, string flags, formatted prices) and the same error
  envelope; gateway and network failures are returned, never raised.
- Ported from php-dna's latest fixes (conformance fixture set of 134):
  - errors carry `API_<status>` plus the gateway's own `GatewayCode`; transport failures use
    `CURL_<errno>` (`CURL_28` timeout, `CURL_6` DNS, ...); messages never fall back to the raw JSON body;
  - registration, transfer and renewal answered with `success: false` return `REGISTER_DOMAIN`,
    `TRANSFER_DOMAIN` or `RENEW_DOMAIN` errors instead of a false success;
  - DNS zone writes return the apply error when the automatic apply fails and report the upper-cased type
    and clamped TTL that were sent;
  - `get_forwarding` treats only "Redirect information not found" as disabled; `delete_forwarding` reports
    `Removed` and succeeds when nothing was set;
  - `get_current_balance` returns `BALANCE` for currencies the account does not report; reseller balances
    use two decimals; `modify_name_server` echoes the normalised list that was sent;
  - `modify_privacy_protection_status` accepts `1`/`"on"`/`"true"`/`"yes"`; its reason is not sent;
  - `check_availability` strips only the trailing `.tld`; `get_contacts` matches types case-insensitively
    and keeps unknown ones; `validate_contact` keeps a number's own `+country` code and lets a missing
    State fall back to the city.
- `transfer(domain, epp_code, period)` never sends contacts (the registrar takes them over); it has no
  contacts parameter.
- Zero runtime dependencies: standard-library `urllib` transport with 30 s / 10 s connect timeouts, no
  redirect following, `User-Agent: DomainNameAPI-Python/1.0.0`; the transport is injectable.
- Test mode (OTE) with string values (`"true"`, `"1"`, `"on"`, `"yes"`) understood.
- Telemetry port (background, credentials masked, minimal mode, opt-out). The built-in Sentry DSN is
  empty until the python-dna Sentry project exists, so nothing is sent by default yet; `sentry_dsn=`
  overrides it.
- Test suite: all 134 php-dna conformance fixtures, extra php-dna edge cases, and unit tests for the HTTP
  layer, error mapping, telemetry and utilities. Runnable examples for every method.
- README in English, Turkish, German, French, Italian, Dutch, Azerbaijani, Arabic and Simplified Chinese.

[1.0.0]: https://github.com/domainreseller/python-dna/releases/tag/v1.0.0
