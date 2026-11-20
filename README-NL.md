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

# python-dna: de Python SDK voor de Domain Name API

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Getypeerde Python-client voor de reseller-REST-API van de [Domain Name API](https://www.domainnameapi.com): domeinen
zoeken, registreren, verlengen en verhuizen, DNS, DNSSEC, contacten, SSL-certificaten, hosting, bestellingen, de
productcatalogus en je saldo.

- **Alle 64 API-operaties**, op dezelfde manier gegroepeerd als in de [`dna` CLI](https://github.com/domainreseller/cli):
  `dna domain info` is `client.domains.info`, `dna dns add` is `client.dns.add`.
- **Getypeerde resultaten en enums**: dataclasses met `datetime`-velden en benoemde statussen
  (`d.status == DomainStatus.PENDING_DELETE`), geen dictionaries. Je editor vult elk veld aan.
- **Elke operatie is een request-klasse**, afgeleid van `BaseRequest`, die zichzelf valideert voordat er iets
  wordt verstuurd. Eigen requests schrijf je op dezelfde manier.
- **Exceptions die je op betekenis kunt afvangen**: `NotFoundError`, `InsufficientBalanceError`, `RateLimitError`,
  `OperationError`, ... met foutcodes, hints en correlation-ID's.
- **Standaard veilig**: kostenplichtige requests worden nooit blind herhaald, `read_only=True` blokkeert
  wijzigingen, de client remt zichzelf af onder de rate limits en is veilig te delen tussen threads.
- **Alleen de standaardbibliotheek.** Python 3.9 of nieuwer. Geen telemetrie: er verlaat niets je proces behalve de
  API-requests die je zelf doet.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## Inhoud

- [Installatie](#installatie)
- [Inloggegevens en omgevingen](#inloggegevens-en-omgevingen)
- [Services](#services)
- [Gebruik](#gebruik)
- [Requests en BaseRequest](#requests-en-baserequest)
- [Fouten](#fouten)
- [Veiligheid en betrouwbaarheid](#veiligheid-en-betrouwbaarheid)
- [Client-opties](#client-opties)
- [Je code testen](#je-code-testen)
- [Migreren van v1](#migreren-van-v1)
- [Ontwikkeling](#ontwikkeling)

## Installatie

```bash
pip install domainnameapi
```

Geversioneerde, geteste pakketten staan ook op de pagina [Releases](https://github.com/domainreseller/python-dna/releases).
Uitvoerbare programma's staan in [examples](examples): `quickstart.py`, `register.py`, `expiring.py`,
`dns_zone.py`, `ssl_certificate.py`, `custom_request.py` en `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Inloggegevens en omgevingen

Je hebt twee API-inloggegevens nodig uit het resellerpaneel (**API settings**). De inloggegevens van het paneel werken niet.

| Inloggegevens | Ziet eruit als                         |
|---------------|----------------------------------------|
| Reseller ID   | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key       | een lange geheime tekenreeks           |

Er zijn twee omgevingen. **Begin met OTE**, de testomgeving: die heeft eigen gegevens en een eigen API-sleutel,
en niets wat je daar doet kost geld of raakt live domeinen.

```python
# Testomgeving (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Productie (de standaard): echte registraties, echte afschrijvingen
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()` leest dezelfde variabelen als de `dna` CLI:

| Variabele         | Betekenis                                                     |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | reseller ID                                                   |
| `DNA_API_KEY`     | API-sleutel van de gekozen omgeving                           |
| `DNA_ENV`         | `production` (standaard) of `ote`                             |
| `DNA_TEST_MODE`   | `true` kiest OTE (zoals in de andere DomainNameAPI-SDK's)     |
| `DNA_BASE_URL`    | een eigen basis-URL, bijv. een proxy                          |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` accepteert ook de testmodus-vlaggen die panelen opslaan: `True`, `"true"`, `"1"`, `"on"`, `"yes"` betekenen OTE.
Een verkeerde sleutel of omgeving mislukt bij de eerste request met een `AuthenticationError` en een hint;
`client.account.get()` is de goedkoopste manier om dit te controleren.

## Services

| Service           | CLI-groep     | Methoden                                                                                                                                                          |
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

Vereiste invoer geef je als positionele argumenten (`client.domains.info("example.com")`), optionele invoer als keyword-argumenten
(`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Enum-argumenten accepteren de enum,
de API-naam ervan in elke schrijfwijze of het nummer ervan: `DomainStatus.ACTIVE`, `"active"` en `0` zijn hetzelfde.

## Gebruik

Alle snippets gaan uit van `import domainnameapi as dna` en een `client`.

### Zoeken

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` splitst lijsten met meer dan 30 domeinen op in meerdere requests. Prijzen gebruiken de valuta van het account of
de valuta die is ingesteld met `dna.Client(..., currency="TRY")` of `search(..., currency="TRY")`.

### Registreren

Met contact-handles (maak er een aan met `contacts.create`):

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
    handles=handle,  # één handle voor alle vier de rollen, of dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

Met inline contacten:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # één Contact voor alle vier de rollen, of dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

Contacten worden vóór het versturen opgeschoond: velden worden getrimd, het land wordt omgezet naar hoofdletters en telefoonvelden behouden alleen
hun cijfers (`"+90 (555) 123-45-67"` werkt). Sommige TLD's vereisen registry-attributen: je vindt ze met
`client.products.tld("com.tr").required_attributes` en geeft ze mee als `tld_attributes={...}`.

Als de API antwoordt maar weigert (`"success": false`), werpt de methode een `dna.OperationError` met de melding
van de API.

### Verlengen, verhuizen, herstellen

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # tijdens de redemption-periode
```

### Domeindetails en de domeinlijst

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# Eén pagina
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Elk domein; de pagina's worden opgehaald terwijl je itereert
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Vergrendeling, privacy, nameservers, child-nameservers

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # alleen voor DNSSEC-getekende domeinen

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # IP-versie wordt herkend
client.domains.delete_host("example.com", "ns1.example.com")
```

### Contacten van een domein

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # het contact en de verificatiestatus ervan
result = client.contacts.update("DNA-1", contact)  # werkt elk domein bij dat de handle gebruikt
```

### DNS-zone

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # vervangt alle waarden van de set
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # één recordset, of None
res = client.dns.apply("example.com")             # zet het domein om naar de nameservers van het platform
```

Namen kunnen relatief (`www`), de apex (`""` of `"@"`) of volledig gekwalificeerd zijn. Recordtypen zijn hier
niet hoofdlettergevoelig (`"txt"` wordt verstuurd als `TXT`). De validatie vangt af wat de API zou weigeren: een CNAME op de apex, een CAA-waarde
zonder drie delen, een MX-waarde zonder prioriteit. De testomgeving beantwoordt elke zone-aanroep met HTTP
500, dus zonecode kan alleen in productie worden uitgeprobeerd.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # zoals je DNS-provider het toont
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` leest het presentatieformaat, inclusief hele regels uit een zonebestand.

### URL-doorstuurfunctie

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # None als het domein er geen heeft
client.domains.delete_forwarding("example.com")
```

### Registrydocumenten (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

Bestanden worden voor je base64-gecodeerd; formaat (PDF, JPG, PNG, DOC, DOCX, ODT) en grootte (10 MB per bestand, 50 MB per
request) worden vóór het uploaden gecontroleerd.

### SSL-certificaten

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
client.ssl.initialize("example.com", "PositiveSSL")  # schrijft af van het saldo
client.ssl.configure("example.com", csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status("example.com")  # blijf pollen tot st.is_issued
cert = client.ssl.content("example.com")
open("example.com.crt", "w").write(cert.chain)
```

### Hosting

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # schrijft af van het saldo

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # pollt tot de hosting actief is
print(st.panel_address, st.username, st.password)
```

Roep `create` nooit opnieuw aan voor een hosting die nog wordt ingericht: dat schrijft twee keer af.

### Saldo, prijzen en bestellingen

```python
account = client.account.get()
usd = account.balance("USD")

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # prijs van een .com-verlenging van 2 jaar
order = client.orders.get("ORDER-CODE")
```

## Requests en BaseRequest

Elke API-operatie is een request-klasse: `DomainInfoRequest`, `DNSAddRequest`, `SSLConfigureRequest`, ... Ze
zijn allemaal afgeleid van `dna.BaseRequest`, die de standaardwaarden levert (geen query string, geen body, niets te valideren).
Een request geeft met klasse-attributen aan waar hij naartoe gaat en overschrijft wat hij nodig heeft. Eén uit dit pakket:

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

| Onderdeel     | Standaard      | Betekenis                                                                           |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | HTTP-methode                                                                        |
| `path`        | `""`           | pad onder de basis-URL; `{placeholders}` worden uit attributen ingevuld en ge-escaped |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` of `BILLABLE`                                        |
| `idempotent`  | `False`        | veilig om twee keer te versturen (leesacties altijd); alleen deze worden na netwerkfouten herhaald |
| `response`    | `None`         | hoe antwoorden worden gedecodeerd: een `Model`-subklasse, `list_of(...)`, `page_of(...)` of ruwe JSON |
| `query()`     | `None`         | queryparameters: een dict of een lijst met paren                                    |
| `body()`      | `None`         | de JSON-body                                                                        |
| `validate(v)` | niets          | leg problemen vast met `v.required`, `v.between`, `v.check`, ...; dan wordt er niets verstuurd |

De servicemethoden bouwen deze requests voor je. `client.send(request)` verstuurt elke request, ook eigen klassen,
bijvoorbeeld om alleen de velden te lezen die je nodig hebt of om een endpoint aan te roepen dat dit pakket nog niet omvat:

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

Je request krijgt alles wat de ingebouwde requests krijgen: inloggegevens, retries, pacing, foutnormalisatie,
correlation-ID's, tracing en read-only-afdwinging. `client.send_with_response(request)` geeft ook de status,
headers, correlation-ID, quota en het aantal pogingen terug; `client.prepare(request)` bouwt de exacte HTTP-request
zonder die te versturen, om een kostenplichtige request te loggen of te controleren voordat hij de deur uit gaat. Modellen bewaren de gedecodeerde JSON in `.raw`,
voor velden die dit pakket nog niet modelleert.

## Fouten

Elke exception is afgeleid van `dna.DomainNameAPIError` en heeft een `kind`.

| Exception                     | Wanneer                                                    | Nuttige attributen                                                  |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (een `ValueError`) | de validatie heeft de request afgewezen; **er is niets verstuurd** | `request`, `fields`                                         |
| `APIError` en subklassen      | de API antwoordde met een niet-2xx-status                  | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | de API antwoordde 2xx met `"success": false`               | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | de request is niet voltooid (DNS, TLS, timeout, reset)     | `timeout`, `__cause__`                                              |
| `ReadOnlyError`               | een read-only-client blokkeerde een wijziging; er is niets verstuurd | `request`, `safety`                                       |

De subklassen van `APIError` onderscheiden de gebruikelijke gevallen: `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (met `InsufficientBalanceError`), `ConflictError`, `RateLimitError` en
`ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # eerst opwaarderen
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # de verlenging is mogelijk doorgegaan: controleer het domein voordat je het opnieuw probeert
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

Vertak op `code`, niet op `message`: meldingen zijn gelokaliseerd. API-codes zien eruit als
`Dna.DomainService:Domain:10007`; zie de [foutenreferentie](https://www.domainnameapi.com/docs/reference/errors.md).
`err.kind` is een van `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Vermeld de `correlation_id` wanneer je contact opneemt met de support.

## Veiligheid en betrouwbaarheid

- **Veiligheidsklassen.** Elke request is `READ`, `WRITE`, `DESTRUCTIVE` of `BILLABLE`
  (`request.endpoint().safety`). Sommige POST- en PUT-requests zijn leesacties (`DomainSearchRequest`, `SSLStatusRequest`).
- **Read-only-modus.** `dna.Client(..., read_only=True)` blokkeert alles wat geen leesactie is, voor rapportagejobs
  en om productie veilig te verkennen.
- **Retries.** 429-responses worden altijd herhaald, met inachtneming van `Retry-After`: de API weigert ze voordat hij
  iets doet. Netwerkfouten en 502/503/504 worden alleen herhaald voor leesacties en idempotente schrijfacties, zodat een registratie
  of verlenging nooit twee keer wordt verstuurd. Controleer na een mislukte kostenplichtige request `err.outcome_unknown`.
- **Pacing.** De client spreidt requests om onder de limieten per sleutel te blijven (5 requests/seconde, 2 zoekopdrachten/seconde,
  één zone-aanroep per seconde). Zet het uit met `pacing=False` als je zelf afremt.
- **Quota.** `send_with_response(...).quota` geeft de soft-quota-headers vrij. Boven de limiet vertraagt de API responses
  (tot 5 s) in plaats van ze te weigeren; de standaard-timeout van 60 s laat daar ruimte voor.
- **Correlation-ID's.** Elke request draagt een `X-Correlation-ID`. Stel er zelf een in met
  `with dna.correlation_id("order-4711"): ...` om API-aanroepen aan je logs te koppelen.
- **Observability.** Uitwisselingen worden gelogd naar de logger `domainnameapi` (requests en responses op DEBUG,
  retries op WARNING); `trace=callback` geeft je elke request, response en retry als `TraceEvent`, voor
  metrics of foutrapportage. De API-sleutel zit er nooit in.
- **Threads.** Een `Client` is veilig te delen tussen threads. Maak er één aan en hergebruik hem.
- **Tolerant decoderen.** Datums zonder tijdzone, `null`, `[]` in plaats van `{}`, als strings verstuurde getallen,
  numerieke of benoemde statussen en rollen in elke schrijfwijze (`"registrant"`, `"ADMINISTRATIVE"`) worden allemaal gedecodeerd. Waarden die dit
  pakket nog niet kent, breken nooit een response.

## Client-opties

| Optie                           | Effect                                                                                   |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | gebruik de testomgeving (standaard `"production"`)                                       |
| `base_url=url`                  | verstuur requests naar een proxy of een testserver                                       |
| `timeout=60`                    | seconden per HTTP-poging                                                                 |
| `retries=2`                     | aantal retries                                                                           |
| `pacing=False`                  | zet pacing aan de clientzijde uit                                                        |
| `read_only=True`                | blokkeer elke request die geen leesactie is                                              |
| `currency="TRY"`                | valuta van zoek- en catalogusprijzen                                                     |
| `user_agent="app/1.0"`          | zet je product vóór de User-Agent                                                        |
| `transport=...`                 | je eigen HTTP-laag (`requests`, `httpx`, een proxy, ...); zie `domainnameapi.transport`  |
| `trace=fn`                      | observeer elke request, response en retry                                                |
| `logger=logging.getLogger(...)` | log uitwisselingen naar een andere logger                                                |

De standaard-transport gebruikt `urllib` en respecteert de `HTTPS_PROXY`-variabelen. Voor je eigen CA-bundel geef je
`transport=dna.UrllibTransport(ssl_context=ctx)` mee.

## Je code testen

`domainnameapi.testing.FakeTransport` legt requests vast en antwoordt met klaargezette antwoorden; verder hoeft er niets
te worden gemockt:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # een Client die de fake gebruikt, met pacing uit

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## Migreren van v1

v2 is een nieuw ontwerp: getypeerde resultaten in plaats van dictionaries, exceptions in plaats van
`{"result": "ERROR"}`-enveloppen en de volledige REST-API in plaats van de methodenset van php-dna. Pin `domainnameapi<2` om v1 te behouden terwijl je
overstapt.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | geen exception                                                         |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (of `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (eenmaal per waarde)   |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | niet in de gepubliceerde API; verstuur een [eigen request](#requests-en-baserequest) als je account ze heeft |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`; validatie draait bij elke request              |
| `get_request_data`, `get_response_data`, ...        | `trace=`, de logger `domainnameapi`, `send_with_response`              |
| telemetry (`set_error_reporting_enabled`, Sentry)   | verwijderd: niets verlaat je proces; stuur `trace`-events door naar je eigen rapportage |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` met je eigen TLS-instellingen |

## Ontwikkeling

```bash
python -m unittest discover -s tests -v   # or: python -m pytest
python -m build                            # sdist and wheel
```

De tests roepen nooit de echte API aan. `tests/testdata/openapi.json` is het OpenAPI-document van de API, hetzelfde als dat de
`dna` CLI embedt. De tests controleren elke request-klasse ertegen (methode, pad, querynamen, body-velden,
verplichte velden), de JSON-namen van elk responsemodel tegen de responseschema's en elke enum-waarde, en falen
als de API een operatie krijgt zonder request-klasse. Zo werk je het bij:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

Zie [AGENTS.md](AGENTS.md) voor de conventies van deze repository.

## Support

- API-documentatie: <https://www.domainnameapi.com/docs/>
- CLI en MCP-server: <https://github.com/domainreseller/cli>
- Website: <https://www.domainnameapi.com>

## Licentie

Apache License 2.0. Zie [LICENSE](LICENSE).
