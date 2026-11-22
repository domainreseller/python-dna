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

# python-dna: das Python-SDK für die Domain Name API

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Typisierter Python-Client für die Reseller-REST-API der [Domain Name API](https://www.domainnameapi.com): Domainsuche,
Registrierung, Verlängerung und Transfer, DNS, DNSSEC, Kontakte, SSL-Zertifikate, Hosting, Bestellungen, der
Produktkatalog und Ihr Guthaben.

- **Alle 67 API-Operationen**, genauso gruppiert wie in der [`dna`-CLI](https://github.com/domainreseller/cli):
  `dna domain info` entspricht `client.domains.info`, `dna dns add` entspricht `client.dns.add`.
- **Typisierte Ergebnisse und Enums**: Dataclasses mit `datetime`-Feldern und benannten Status
  (`d.status == DomainStatus.PENDING_DELETE`), keine Dictionaries. Ihr Editor vervollständigt jedes Feld.
- **Jede Operation ist eine Request-Klasse**, abgeleitet von `BaseRequest`, die sich selbst validiert, bevor
  etwas gesendet wird. Eigene Requests schreiben Sie auf dieselbe Weise.
- **Exceptions, die Sie nach Bedeutung abfangen können**: `NotFoundError`, `InsufficientBalanceError`, `RateLimitError`,
  `OperationError`, ... mit Fehlercodes, Hinweisen und Correlation-IDs.
- **Sicher von Haus aus**: kostenpflichtige Requests werden nie blind wiederholt, `read_only=True` blockiert
  Änderungen, der Client drosselt sich selbst unter den Rate Limits und ist threadsicher nutzbar.
- **Nur die Standardbibliothek.** Python 3.9 oder neuer. Keine Telemetrie: Nichts verlässt Ihren Prozess außer den
  API-Requests, die Sie selbst senden.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## Inhalt

- [Installation](#installation)
- [Zugangsdaten und Umgebungen](#zugangsdaten-und-umgebungen)
- [Services](#services)
- [Verwendung](#verwendung)
- [Requests und BaseRequest](#requests-und-baserequest)
- [Fehler](#fehler)
- [Sicherheit und Zuverlässigkeit](#sicherheit-und-zuverlässigkeit)
- [Client-Optionen](#client-optionen)
- [Den eigenen Code testen](#den-eigenen-code-testen)
- [Migration von v1](#migration-von-v1)
- [Entwicklung](#entwicklung)

## Installation

```bash
pip install domainnameapi
```

Versionierte, getestete Pakete finden Sie auch auf der Seite [Releases](https://github.com/domainreseller/python-dna/releases).
Lauffähige Programme finden Sie in [examples](examples): `quickstart.py`, `register.py`, `expiring.py`,
`dns_zone.py`, `ssl_certificate.py`, `custom_request.py` und `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Zugangsdaten und Umgebungen

Sie benötigen zwei API-Zugangsdaten aus dem Reseller-Panel (**API settings**). Die Anmeldedaten des Panels funktionieren nicht.

| Zugangsdaten | Sieht so aus                           |
|--------------|----------------------------------------|
| Reseller ID  | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key      | eine lange geheime Zeichenfolge        |

Es gibt zwei Umgebungen. **Beginnen Sie mit OTE**, der Testumgebung: Sie hat eigene Daten und einen eigenen API-Schlüssel,
und nichts, was Sie dort tun, kostet Geld oder berührt Live-Domains.

```python
# Testumgebung (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Produktion (Standard): echte Registrierungen, echte Abbuchungen
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()` liest dieselben Variablen wie die `dna`-CLI:

| Variable          | Bedeutung                                                     |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | Reseller ID                                                   |
| `DNA_API_KEY`     | API-Schlüssel der gewählten Umgebung                          |
| `DNA_ENV`         | `production` (Standard) oder `ote`                            |
| `DNA_TEST_MODE`   | `true` wählt OTE (wie in den anderen DomainNameAPI-SDKs)      |
| `DNA_BASE_URL`    | eine eigene Basis-URL, z. B. ein Proxy                        |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` akzeptiert auch die Testmodus-Flags, die Panels speichern: `True`, `"true"`, `"1"`, `"on"`, `"yes"` bedeuten OTE.
Ein falscher Schlüssel oder eine falsche Umgebung schlägt beim ersten Request mit einem `AuthenticationError` und einem Hinweis fehl;
`client.account.get()` ist die günstigste Möglichkeit zur Prüfung.

## Services

| Service           | CLI-Gruppe    | Methoden                                                                                                                                                          |
|-------------------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `client.account`  | `dna account` | `get`, `profile`, `transactions`, `all_transactions`                                                                                                              |
| `client.contacts` | `dna contact` | `get`, `create`, `update`, `verification`, `resend_verification`                                                                                                  |
| `client.domains`  | `dna domain`  | `search`, `bulk_search`, `list`, `all`, `info`, `register`, `register_with_contacts`, `renew`, `renew_check`, `restore`, `transfer`, `transfer_check`, `transfer_status`, `lock`, `unlock`, `set_privacy`, `update_auth_code`, `set_name_servers`, `add_host`, `update_host`, `delete_host`, `update_contacts`, `set_contact_handles`, `documents`, `upload_documents`, `forwarding`, `set_forwarding`, `delete_forwarding` |
| `client.dns`      | `dna dns`     | `list`, `find`, `add`, `update`, `delete`, `apply`                                                                                                                |
| `client.dnssec`   | `dna dnssec`  | `get`, `add`, `remove`, `disable`                                                                                                                                 |
| `client.ssl`      | `dna ssl`     | `generate_csr`, `check_csr`, `initialize`, `configure`, `status`, `get`, `content`, `list`, `all`, `reissue`, `renew`, `approvers`, `revoke`                      |
| `client.hosting`  | `dna hosting` | `packages`, `plans`, `create`, `wait`, `get`, `get_by_token`, `status`                                                                                            |
| `client.orders`   | `dna order`   | `get`                                                                                                                                                             |
| `client.products` | `dna product` | `list`, `info`, `tlds`, `all_tlds`, `tld`, `ssls`                                                                                                                 |

Erforderliche Eingaben sind Positionsargumente (`client.domains.info("example.com")`), optionale sind Schlüsselwortargumente
(`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Enum-Argumente akzeptieren das Enum,
seinen API-Namen in beliebiger Schreibweise oder seine Nummer: `DomainStatus.ACTIVE`, `"active"` und `0` sind dasselbe.

## Verwendung

Alle Snippets setzen `import domainnameapi as dna` und einen `client` voraus.

### Suche

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` teilt Listen mit mehr als 30 Domains auf mehrere Requests auf. Preise verwenden die Währung des Kontos oder
die mit `dna.Client(..., currency="TRY")` oder `search(..., currency="TRY")` gesetzte.

### Registrieren

Mit Kontakt-Handles (eines erstellen Sie mit `contacts.create`):

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
    handles=handle,  # ein Handle für alle vier Rollen, oder dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

Mit Inline-Kontakten:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # ein Contact für alle vier Rollen, oder dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

Kontakte werden vor dem Senden bereinigt: Felder werden getrimmt, das Land wird in Großbuchstaben umgewandelt und Telefonfelder behalten nur
ihre Ziffern (`"+90 (555) 123-45-67"` funktioniert). Einige TLDs benötigen Registry-Attribute: Sie finden sie mit
`client.products.tld("com.tr").required_attributes` und übergeben sie als `tld_attributes={...}`.

Antwortet die API, lehnt die Operation aber ab (`"success": false`), löst die Methode eine `dna.OperationError` mit der Meldung
der API aus.

### Verlängern, transferieren, wiederherstellen

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # während der Redemption-Phase
```

### Domain-Details und Domainliste

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# Eine Seite
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Alle Domains; die Seiten werden beim Iterieren abgerufen
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Sperre, Datenschutz, Nameserver, Child-Nameserver

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # nur für DNSSEC-signierte Domains

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # IP-Version wird erkannt
client.domains.delete_host("example.com", "ns1.example.com")
```

### Kontakte einer Domain

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # der Kontakt und sein Verifizierungsstatus
result = client.contacts.update("DNA-1", contact)  # aktualisiert jede Domain, die das Handle verwendet
```

### DNS-Zone

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # ersetzt alle Werte des Sets
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # ein Record-Set oder None
res = client.dns.apply("example.com")             # stellt die Domain auf die Nameserver der Plattform um
```

Namen können relativ (`www`), der Apex (`""` oder `"@"`) oder vollqualifiziert sein. Record-Typen sind hier nicht
von der Groß-/Kleinschreibung abhängig (`"txt"` wird als `TXT` gesendet). Die Validierung fängt ab, was die API ablehnen würde: einen CNAME am Apex, einen CAA-Wert
ohne drei Teile, einen MX-Wert ohne Priorität. Die Testumgebung beantwortet jeden Zonenaufruf mit HTTP
500, Zonen-Code lässt sich daher nur in der Produktion ausprobieren.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # so, wie Ihr DNS-Anbieter ihn anzeigt
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` liest das Präsentationsformat, einschließlich ganzer Zeilen einer Zonendatei.

### URL-Weiterleitung

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # None, wenn die Domain keine hat
client.domains.delete_forwarding("example.com")
```

### Registry-Dokumente (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

Dateien werden für Sie Base64-kodiert; Format (PDF, JPG, PNG, DOC, DOCX, ODT) und Größe (10 MB pro Datei, 50 MB pro
Request) werden vor dem Upload geprüft.

### SSL-Zertifikate

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
order = client.ssl.initialize("example.com", "PositiveSSL")  # belastet das Guthaben
cert_id = order.certificate_id  # aufbewahren: jeder spätere Aufruf benötigt sie
client.ssl.configure(cert_id, csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status(cert_id)  # abfragen, bis st.is_issued gilt
cert = client.ssl.content(cert_id)
open("example.com.crt", "w").write(cert.chain)
```

Eine Domain kann mehrere Zertifikate haben. Ein vorhandenes Zertifikat wird deshalb über seine **Zertifikats-ID**
(eine GUID) angesprochen, nicht über den Domainnamen: `configure`, `status`, `get`, `content`, `reissue`,
`revoke` und `renew` erwarten sie. `initialize` und `renew` geben sie zurück, `list` findet sie wieder. Wird
statt einer Zertifikats-ID ein Domainname übergeben, wird `InputError` ausgelöst, bevor etwas gesendet wird.

```python
for c in client.ssl.list(domain_name="example.com"):  # neueste zuerst; ssl.all(...) lädt alle Seiten
    print(c.certificate_id, c.status, c.subscription_expires_at)

client.ssl.approvers(certificate_id=cert_id)  # ein vorhandenes Zertifikat
client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL")  # vor dem Kauf

renewal = client.ssl.renew(cert_id)  # belastet das Guthaben
# Die Verlängerung ist ein neues Zertifikat mit eigener ID: Konfigurieren Sie dieses.
client.ssl.configure(renewal.certificate_id, csr=new_csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
```

Konfigurieren Sie ein Zertifikat innerhalb von 15 Tagen nach `initialize` oder `renew`, sonst wird es storniert.
`renew` ist ab 30 Tagen vor dem Ende des Abonnements möglich (`client.ssl.get(cert_id).subscription.expires_at`).
Zum Verlängern rufen Sie `renew` und danach `configure` mit der zurückgegebenen ID auf: Ein erneuter Aufruf von
`initialize` ist keine Verlängerung, sondern kauft ein unabhängiges Zertifikat zum Kaufpreis.

### Hosting

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # belastet das Guthaben

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # fragt ab, bis das Hosting aktiv ist
print(st.panel_address, st.username, st.password)
```

Rufen Sie `create` nie erneut für ein Hosting auf, das noch bereitgestellt wird: Das belastet Ihr Guthaben doppelt.

### Guthaben, Preise und Bestellungen

```python
account = client.account.get()
usd = account.balance("USD")
profile = client.account.profile()  # der Reseller hinter den Zugangsdaten: name, account_currency, status, ...

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # Preis einer 2-jährigen .com-Verlängerung
order = client.orders.get("ORDER-CODE")
```

## Requests und BaseRequest

Jede API-Operation ist eine Request-Klasse: `DomainInfoRequest`, `DNSAddRequest`, `SSLConfigureRequest`, ... Sie
leiten alle von `dna.BaseRequest` ab, das die Standardwerte liefert (kein Query-String, kein Body, nichts zu validieren).
Ein Request legt über Klassenattribute fest, wohin er geht, und überschreibt, was er benötigt. Einer aus diesem Paket:

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

| Element       | Standard       | Bedeutung                                                                           |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | HTTP-Methode                                                                        |
| `path`        | `""`           | Pfad unterhalb der Basis-URL; `{placeholders}` werden aus Attributen befüllt und maskiert |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` oder `BILLABLE`                                      |
| `idempotent`  | `False`        | darf zweimal gesendet werden (Lesezugriffe immer); nur diese werden nach Netzwerkfehlern wiederholt |
| `response`    | `None`         | wie Antworten dekodiert werden: eine `Model`-Unterklasse, `list_of(...)`, `page_of(...)` oder rohes JSON |
| `query()`     | `None`         | Query-Parameter: ein Dict oder eine Liste von Paaren                                |
| `body()`      | `None`         | der JSON-Body                                                                       |
| `validate(v)` | nichts         | Probleme mit `v.required`, `v.between`, `v.check`, ... festhalten; dann wird nichts gesendet |

Die Service-Methoden erstellen diese Requests für Sie. `client.send(request)` sendet jeden Request, auch eigene Klassen,
zum Beispiel, um nur die benötigten Felder zu lesen oder einen Endpoint aufzurufen, den dieses Paket noch nicht abdeckt:

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

Ihr Request erhält alles, was die eingebauten erhalten: Zugangsdaten, Retries, Pacing, Fehlernormalisierung,
Correlation-IDs, Tracing und Read-only-Durchsetzung. `client.send_with_response(request)` liefert zusätzlich Status,
Header, Correlation-ID, Quota und Anzahl der Versuche; `client.prepare(request)` baut den exakten HTTP-Request,
ohne ihn zu senden, um einen kostenpflichtigen Request vor dem Absenden zu protokollieren oder zu prüfen. Modelle behalten das dekodierte JSON in `.raw`,
für Felder, die dieses Paket noch nicht modelliert.

## Fehler

Jede Exception leitet von `dna.DomainNameAPIError` ab und hat eine `kind`.

| Exception                     | Wann                                                       | Nützliche Attribute                                                 |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (ein `ValueError`) | die Validierung hat den Request abgelehnt; **es wurde nichts gesendet** | `request`, `fields`                                        |
| `APIError` und Unterklassen   | die API hat mit einem Nicht-2xx-Status geantwortet         | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | die API hat mit 2xx und `"success": false` geantwortet     | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | der Request wurde nicht abgeschlossen (DNS, TLS, Timeout, Reset) | `timeout`, `__cause__`                                        |
| `ReadOnlyError`               | ein Read-only-Client hat eine Änderung blockiert; es wurde nichts gesendet | `request`, `safety`                                 |

Die Unterklassen von `APIError` unterscheiden die häufigen Fälle: `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (mit `InsufficientBalanceError`), `ConflictError`, `RateLimitError` und
`ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # erst aufladen
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # die Verlängerung ist möglicherweise durchgegangen: Prüfen Sie die Domain, bevor Sie es erneut versuchen
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

Verzweigen Sie nach `code`, nicht nach `message`: Meldungen sind lokalisiert. API-Codes sehen so aus:
`Dna.DomainService:Domain:10007`; siehe die [Fehlerreferenz](https://www.domainnameapi.com/docs/reference/errors.md).
`err.kind` ist einer von `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Nennen Sie die `correlation_id`, wenn Sie den Support kontaktieren.

## Sicherheit und Zuverlässigkeit

- **Sicherheitsklassen.** Jeder Request ist `READ`, `WRITE`, `DESTRUCTIVE` oder `BILLABLE`
  (`request.endpoint().safety`). Einige POST- und PUT-Requests sind Lesezugriffe (`DomainSearchRequest`, `SSLStatusRequest`).
- **Read-only-Modus.** `dna.Client(..., read_only=True)` blockiert alles, was kein Lesezugriff ist, für Reporting-Jobs
  und um die Produktion gefahrlos zu erkunden.
- **Retries.** 429-Antworten werden immer wiederholt und berücksichtigen `Retry-After`: Die API weist sie ab, bevor sie
  etwas tut. Netzwerkfehler und 502/503/504 werden nur für Lesezugriffe und idempotente Schreibzugriffe wiederholt, sodass eine Registrierung
  oder Verlängerung nie zweimal gesendet wird. Prüfen Sie nach einem fehlgeschlagenen kostenpflichtigen Request `err.outcome_unknown`.
- **Pacing.** Der Client verteilt Requests zeitlich, um unter den Limits pro Schlüssel zu bleiben (5 Requests/Sekunde, 2 Suchen/Sekunde,
  ein Zonenaufruf pro Sekunde). Schalten Sie es mit `pacing=False` ab, wenn Sie selbst drosseln.
- **Quota.** `send_with_response(...).quota` stellt die Soft-Quota-Header bereit. Bei Überschreitung des Limits verlangsamt die API die
  Antworten (bis zu 5 s), statt sie abzuweisen; das Standard-Timeout von 60 s lässt dafür Spielraum.
- **Correlation-IDs.** Jeder Request trägt einen `X-Correlation-ID`. Setzen Sie eine eigene mit
  `with dna.correlation_id("order-4711"): ...`, um API-Aufrufe mit Ihren Logs zu verknüpfen.
- **Observability.** Austausche werden in den Logger `domainnameapi` geschrieben (Requests und Responses auf DEBUG,
  Retries auf WARNING); `trace=callback` liefert Ihnen jeden Request, jede Response und jeden Retry als `TraceEvent`, für
  Metriken oder Fehlerberichte. Der API-Schlüssel ist nie darin enthalten.
- **Threads.** Ein `Client` ist threadsicher nutzbar. Erstellen Sie einen und verwenden Sie ihn wieder.
- **Tolerantes Dekodieren.** Datumsangaben ohne Zeitzone, `null`, `[]` statt `{}`, als Strings gesendete Zahlen,
  numerische oder benannte Status und Rollen in beliebiger Schreibweise (`"registrant"`, `"ADMINISTRATIVE"`) werden alle dekodiert. Werte, die dieses
  Paket noch nicht kennt, brechen nie eine Antwort.

## Client-Optionen

| Option                          | Wirkung                                                                                  |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | die Testumgebung verwenden (Standard `"production"`)                                     |
| `base_url=url`                  | Requests an einen Proxy oder einen Testserver senden                                     |
| `timeout=60`                    | Sekunden pro HTTP-Versuch                                                                |
| `retries=2`                     | Anzahl der Retries                                                                       |
| `pacing=False`                  | clientseitiges Pacing abschalten                                                         |
| `read_only=True`                | jeden Request blockieren, der kein Lesezugriff ist                                       |
| `currency="TRY"`                | Währung der Such- und Katalogpreise                                                      |
| `user_agent="app/1.0"`          | Ihr Produkt dem User-Agent voranstellen                                                  |
| `transport=...`                 | Ihre eigene HTTP-Schicht (`requests`, `httpx`, ein Proxy, ...); siehe `domainnameapi.transport` |
| `trace=fn`                      | jeden Request, jede Response und jeden Retry beobachten                                  |
| `logger=logging.getLogger(...)` | Austausche in einen anderen Logger protokollieren                                        |

Der Standard-Transport verwendet `urllib` und berücksichtigt die `HTTPS_PROXY`-Variablen. Für ein eigenes CA-Bundle übergeben Sie
`transport=dna.UrllibTransport(ssl_context=ctx)`.

## Den eigenen Code testen

`domainnameapi.testing.FakeTransport` zeichnet Requests auf und antwortet mit vorbereiteten Antworten; sonst muss nichts
gemockt werden:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # ein Client, der das Fake verwendet, mit abgeschaltetem Pacing

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## Migration von v1

v2 ist ein neues Design: typisierte Ergebnisse statt Dictionaries, Exceptions statt `{"result": "ERROR"}`-
Umschläge und die vollständige REST-API statt des Methodensatzes von php-dna. Legen Sie die Version mit `domainnameapi<2` fest, um v1 beizubehalten,
während Sie umsteigen.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | keine Exception                                                        |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (oder `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (einmal pro Wert)      |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | nicht in der veröffentlichten API; senden Sie einen [eigenen Request](#requests-und-baserequest), falls Ihr Konto sie hat |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`; die Validierung läuft bei jedem Request        |
| `get_request_data`, `get_response_data`, ...        | `trace=`, der Logger `domainnameapi`, `send_with_response`             |
| telemetry (`set_error_reporting_enabled`, Sentry)   | entfernt: nichts verlässt Ihren Prozess; leiten Sie `trace`-Events an Ihr eigenes Reporting weiter |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` mit Ihren eigenen TLS-Einstellungen |

## Entwicklung

```bash
python -m unittest discover -s tests -v   # or: python -m pytest
python -m build                            # sdist and wheel
```

Die Tests greifen nie auf die echte API zu. `tests/testdata/openapi.json` ist das OpenAPI-Dokument der API, dasselbe, das die
`dna`-CLI einbettet. Die Tests prüfen jede Request-Klasse dagegen (Methode, Pfad, Query-Namen, Body-Felder,
Pflichtfelder), die JSON-Namen jedes Response-Modells gegen die Response-Schemas sowie jeden Enum-Wert und schlagen fehl,
wenn die API eine Operation ohne Request-Klasse erhält. So aktualisieren Sie es:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

Die Konventionen dieses Repositorys finden Sie in [AGENTS.md](AGENTS.md).

## Support

- API-Dokumentation: <https://www.domainnameapi.com/docs/>
- CLI und MCP-Server: <https://github.com/domainreseller/cli>
- Website: <https://www.domainnameapi.com>

## Lizenz

Apache License 2.0. Siehe [LICENSE](LICENSE).
