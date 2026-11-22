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

# python-dna: l'SDK Python per la Domain Name API

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Client Python tipizzato per l'API REST per rivenditori di [Domain Name API](https://www.domainnameapi.com): ricerca
di domini, registrazione, rinnovo e trasferimento, DNS, DNSSEC, contatti, certificati SSL, hosting, ordini,
catalogo prodotti e saldo.

- **Tutte le 67 operazioni dell'API**, raggruppate come nella [CLI `dna`](https://github.com/domainreseller/cli):
  `dna domain info` corrisponde a `client.domains.info`, `dna dns add` a `client.dns.add`.
- **Risultati ed enumerazioni tipizzati**: dataclass con campi `datetime` e stati con nome
  (`d.status == DomainStatus.PENDING_DELETE`), non dizionari. Il tuo editor completa ogni campo.
- **Ogni operazione è una classe di richiesta** derivata da `BaseRequest` che si valida da sola prima
  dell'invio. Scrivi le tue allo stesso modo.
- **Eccezioni che puoi intercettare in base al significato**: `NotFoundError`, `InsufficientBalanceError`,
  `RateLimitError`, `OperationError`, ... con codici di errore, suggerimenti e ID di correlazione.
- **Sicuro per impostazione predefinita**: le richieste a pagamento non vengono mai ritentate alla cieca,
  `read_only=True` blocca le modifiche, il client regola il proprio ritmo entro i limiti di frequenza ed è sicuro
  da condividere tra thread.
- **Solo libreria standard.** Python 3.9 o successivo. Nessuna telemetria: nulla lascia il tuo processo, a parte
  le richieste API che effettui.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## Indice

- [Installazione](#installazione)
- [Credenziali e ambienti](#credenziali-e-ambienti)
- [Servizi](#servizi)
- [Utilizzo](#utilizzo)
- [Richieste e BaseRequest](#richieste-e-baserequest)
- [Errori](#errori)
- [Sicurezza e affidabilità](#sicurezza-e-affidabilità)
- [Opzioni del client](#opzioni-del-client)
- [Testare il proprio codice](#testare-il-proprio-codice)
- [Migrare dalla v1](#migrare-dalla-v1)
- [Sviluppo](#sviluppo)

## Installazione

```bash
pip install domainnameapi
```

Pacchetti versionati e testati sono disponibili anche nella pagina [Releases](https://github.com/domainreseller/python-dna/releases).
I programmi eseguibili si trovano in [examples](examples): `quickstart.py`, `register.py`, `expiring.py`,
`dns_zone.py`, `ssl_certificate.py`, `custom_request.py` e `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Credenziali e ambienti

Servono due credenziali API, disponibili nel pannello rivenditore (**API settings**). Le credenziali di accesso
al pannello non funzionano.

| Credenziale | Aspetto                                |
|-------------|----------------------------------------|
| Reseller ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key     | una lunga stringa segreta              |

Esistono due ambienti. **Inizia con OTE**, l'ambiente di test: ha dati propri e una propria chiave API, e nulla
di ciò che fai lì costa denaro o tocca domini reali.

```python
# Ambiente di test (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Produzione (predefinito): registrazioni reali, addebiti reali
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()` legge le stesse variabili della CLI `dna`:

| Variabile         | Significato                                                      |
|-------------------|------------------------------------------------------------------|
| `DNA_RESELLER_ID` | ID rivenditore                                                   |
| `DNA_API_KEY`     | chiave API dell'ambiente selezionato                             |
| `DNA_ENV`         | `production` (predefinito) oppure `ote`                          |
| `DNA_TEST_MODE`   | `true` seleziona OTE (come negli altri SDK DomainNameAPI)        |
| `DNA_BASE_URL`    | un URL di base personalizzato, ad es. un proxy                   |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` accetta anche i flag di modalità test che i pannelli memorizzano: `True`, `"true"`, `"1"`, `"on"`,
`"yes"` significano OTE. Una chiave o un ambiente errati falliscono alla prima richiesta con un
`AuthenticationError` e un suggerimento; `client.account.get()` è il modo meno costoso per verificare.

## Servizi

| Servizio          | Gruppo CLI    | Metodi                                                                                                                                                            |
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

Gli input obbligatori sono argomenti posizionali (`client.domains.info("example.com")`), quelli facoltativi
argomenti con nome (`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Gli argomenti di tipo
enumerazione accettano l'enumerazione, il suo nome API in qualsiasi maiuscolo/minuscolo o il suo numero:
`DomainStatus.ACTIVE`, `"active"` e `0` sono equivalenti.

## Utilizzo

Tutti gli snippet presuppongono `import domainnameapi as dna` e un `client`.

### Ricerca

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` divide le liste di più di 30 domini in più richieste. I prezzi usano la valuta dell'account, oppure
quella impostata con `dna.Client(..., currency="TRY")` o `search(..., currency="TRY")`.

### Registrazione

Con gli handle dei contatti (creane uno con `contacts.create`):

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
    handles=handle,  # un handle per tutti e quattro i ruoli, oppure dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

Con contatti inline:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # un Contact per tutti e quattro i ruoli, oppure dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

I contatti vengono normalizzati prima dell'invio: gli spazi nei campi vengono rimossi, il paese viene portato in
maiuscolo e i campi telefonici conservano solo le cifre (`"+90 (555) 123-45-67"` funziona). Alcuni TLD richiedono
attributi di registro: trovali con `client.products.tld("com.tr").required_attributes` e passali come
`tld_attributes={...}`.

Se l'API risponde ma rifiuta l'operazione (`"success": false`), il metodo solleva un `dna.OperationError` con il
messaggio dell'API.

### Rinnovo, trasferimento, ripristino

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # durante il periodo di redemption
```

### Dettagli del dominio ed elenco dei domini

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# Una pagina
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Tutti i domini; le pagine vengono recuperate man mano che iteri
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Blocco, privacy, nameserver, nameserver figli

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # solo per i domini firmati con DNSSEC

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # versione IP rilevata
client.domains.delete_host("example.com", "ns1.example.com")
```

### Contatti di un dominio

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # il contatto e il suo stato di verifica
result = client.contacts.update("DNA-1", contact)  # aggiorna tutti i domini che usano l'handle
```

### Zona DNS

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # sostituisce tutti i valori del set
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # un set di record, oppure None
res = client.dns.apply("example.com")             # passa il dominio ai nameserver della piattaforma
```

I nomi possono essere relativi (`www`), l'apex (`""` o `"@"`) o completi (FQDN). Qui i tipi di record non
distinguono tra maiuscole e minuscole (`"txt"` viene inviato come `TXT`). La validazione intercetta ciò che l'API
rifiuterebbe: un CNAME all'apex, un valore CAA senza tre parti, un valore MX senza priorità. L'ambiente di test
risponde a ogni chiamata di zona con HTTP 500, quindi il codice per le zone può essere provato solo in
produzione.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # come lo mostra il tuo provider DNS
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` legge il formato di presentazione, comprese intere righe di un file di zona.

### Inoltro URL

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # None quando il dominio non ne ha
client.domains.delete_forwarding("example.com")
```

### Documenti del registro (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

I file vengono codificati in base64 per te; il formato (PDF, JPG, PNG, DOC, DOCX, ODT) e la dimensione (10 MB
per file, 50 MB per richiesta) vengono verificati prima del caricamento.

### Certificati SSL

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
order = client.ssl.initialize("example.com", "PositiveSSL")  # addebita il saldo
cert_id = order.certificate_id  # conservalo: ogni chiamata successiva lo richiede
client.ssl.configure(cert_id, csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status(cert_id)  # interroga finché st.is_issued
cert = client.ssl.content(cert_id)
open("example.com.crt", "w").write(cert.chain)
```

Un dominio può avere più certificati, quindi un certificato esistente si indica con il suo **id del certificato**
(un GUID), non con il nome di dominio: `configure`, `status`, `get`, `content`, `reissue`, `revoke` e `renew` lo
richiedono tutti. `initialize` e `renew` lo restituiscono, e `list` lo ritrova. Passare un nome di dominio dove è
atteso un id del certificato solleva un `InputError` prima che venga inviato qualcosa.

```python
for c in client.ssl.list(domain_name="example.com"):  # dal più recente; ssl.all(...) recupera tutte le pagine
    print(c.certificate_id, c.status, c.subscription_expires_at)

client.ssl.approvers(certificate_id=cert_id)  # un certificato esistente
client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL")  # prima di un acquisto

renewal = client.ssl.renew(cert_id)  # addebita il saldo
# Il rinnovo è un nuovo certificato con un proprio id: configura quello.
client.ssl.configure(renewal.certificate_id, csr=new_csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
```

Configura un certificato entro 15 giorni da `initialize` o `renew`, altrimenti viene annullato. `renew` è
consentito a partire da 30 giorni prima della scadenza dell'abbonamento
(`client.ssl.get(cert_id).subscription.expires_at`). Per rinnovare, chiama `renew` e poi `configure` con l'id
restituito: chiamare di nuovo `initialize` non è un rinnovo, ma acquista un certificato indipendente al prezzo di
acquisto.

### Hosting

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # addebita il saldo

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # interroga finché non è attivo
print(st.panel_address, st.username, st.password)
```

Non chiamare mai `create` di nuovo per un hosting ancora in fase di provisioning: l'addebito avverrebbe due
volte.

### Saldo, prezzi e ordini

```python
account = client.account.get()
usd = account.balance("USD")
profile = client.account.profile()  # il rivenditore delle credenziali: name, account_currency, status, ...

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # prezzo di un rinnovo biennale di un .com
order = client.orders.get("ORDER-CODE")
```

## Richieste e BaseRequest

Ogni operazione dell'API è una classe di richiesta: `DomainInfoRequest`, `DNSAddRequest`,
`SSLConfigureRequest`, ... Tutte derivano da `dna.BaseRequest`, che fornisce i valori predefiniti (nessuna query
string, nessun corpo, nulla da validare). Una richiesta indica dove va tramite attributi di classe e sovrascrive
ciò di cui ha bisogno. Un esempio tratto da questo pacchetto:

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

| Membro        | Predefinito    | Significato                                                                         |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | metodo HTTP                                                                         |
| `path`        | `""`           | percorso sotto l'URL di base; i `{placeholders}` vengono riempiti dagli attributi e sottoposti a escape |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` o `BILLABLE`                                         |
| `idempotent`  | `False`        | può essere inviata due volte senza rischi (le letture lo sono sempre); solo queste vengono ritentate dopo errori di rete |
| `response`    | `None`         | come vengono decodificate le risposte: una sottoclasse di `Model`, `list_of(...)`, `page_of(...)` o JSON grezzo |
| `query()`     | `None`         | parametri di query: un dict o una lista di coppie                                   |
| `body()`      | `None`         | il corpo JSON                                                                       |
| `validate(v)` | nulla          | registra i problemi con `v.required`, `v.between`, `v.check`, ...; in tal caso non viene inviato nulla |

I metodi dei servizi le costruiscono per te. `client.send(request)` invia qualsiasi richiesta, comprese le tue
classi, ad esempio per leggere solo i campi che ti servono o per chiamare un endpoint che questo pacchetto non
incapsula ancora:

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

La tua richiesta ottiene tutto ciò che ottengono quelle integrate: credenziali, tentativi ripetuti, controllo
del ritmo, normalizzazione degli errori, ID di correlazione, tracciamento e applicazione della modalità di sola
lettura. `client.send_with_response(request)` restituisce inoltre lo stato, gli header, l'ID di correlazione, la
quota e il numero di tentativi; `client.prepare(request)` costruisce l'esatta richiesta HTTP senza inviarla, per
registrare o rivedere una richiesta a pagamento prima che parta. I modelli conservano il JSON decodificato in
`.raw`, per i campi che questo pacchetto non modella ancora.

## Errori

Ogni eccezione deriva da `dna.DomainNameAPIError` e ha un `kind`.

| Eccezione                     | Quando                                                     | Attributi utili                                                     |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (una `ValueError`) | la validazione ha rifiutato la richiesta; **non è stato inviato nulla** | `request`, `fields`                                      |
| `APIError` e sottoclassi      | l'API ha risposto con uno stato non 2xx                    | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | l'API ha risposto 2xx con `"success": false`               | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | la richiesta non è stata completata (DNS, TLS, timeout, reset) | `timeout`, `__cause__`                                          |
| `ReadOnlyError`               | un client di sola lettura ha bloccato una modifica; non è stato inviato nulla | `request`, `safety`                           |

Le sottoclassi di `APIError` distinguono i casi più comuni: `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (con `InsufficientBalanceError`), `ConflictError`, `RateLimitError` e
`ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # ricarica prima il saldo
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # il rinnovo potrebbe essere andato a buon fine: controlla il dominio prima di riprovare
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

Distingui i casi in base a `code`, non a `message`: i messaggi sono localizzati. I codici dell'API hanno questo
aspetto: `Dna.DomainService:Domain:10007`; vedi il [riferimento degli errori](https://www.domainnameapi.com/docs/reference/errors.md).
`err.kind` è uno tra `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Indica il `correlation_id` quando contatti il supporto.

## Sicurezza e affidabilità

- **Classi di sicurezza.** Ogni richiesta è `READ`, `WRITE`, `DESTRUCTIVE` o `BILLABLE`
  (`request.endpoint().safety`). Alcune richieste POST e PUT sono letture (`DomainSearchRequest`,
  `SSLStatusRequest`).
- **Modalità di sola lettura.** `dna.Client(..., read_only=True)` blocca tutto ciò che non è una lettura, per i
  job di reportistica e per esplorare la produzione in sicurezza.
- **Tentativi ripetuti.** Le risposte 429 vengono sempre ritentate, rispettando `Retry-After`: l'API le rifiuta
  prima di fare qualsiasi cosa. Gli errori di rete e i 502/503/504 vengono ritentati solo per le letture e per le
  scritture idempotenti, così una registrazione o un rinnovo non viene mai inviato due volte. Dopo il fallimento
  di una richiesta a pagamento, controlla `err.outcome_unknown`.
- **Controllo del ritmo.** Il client distanzia le richieste per restare entro i limiti per chiave (5
  richieste/secondo, 2 ricerche/secondo, una chiamata di zona al secondo). Disattivalo con `pacing=False` se
  regoli tu il ritmo.
- **Quota.** `send_with_response(...).quota` espone gli header della quota soft. Oltre il limite l'API rallenta
  le risposte (fino a 5 s) invece di rifiutarle; il timeout predefinito di 60 s lascia margine per questo.
- **ID di correlazione.** Ogni richiesta porta un `X-Correlation-ID`. Imposta il tuo con
  `with dna.correlation_id("order-4711"): ...` per collegare le chiamate API ai tuoi log.
- **Osservabilità.** Gli scambi vengono registrati nel logger `domainnameapi` (richieste e risposte a DEBUG,
  nuovi tentativi a WARNING); `trace=callback` ti consegna ogni richiesta, risposta e nuovo tentativo come
  `TraceEvent`, per metriche o segnalazione degli errori. La chiave API non vi compare mai.
- **Thread.** Un `Client` è sicuro da condividere tra thread. Creane uno e riutilizzalo.
- **Decodifica tollerante.** Vengono decodificati le date senza fuso orario, `null`, `[]` al posto di `{}`, i
  numeri inviati come stringhe, gli stati numerici o con nome e i ruoli in qualsiasi maiuscolo/minuscolo
  (`"registrant"`, `"ADMINISTRATIVE"`). I valori che questo pacchetto non conosce ancora non fanno mai fallire
  una risposta.

## Opzioni del client

| Opzione                         | Effetto                                                                                  |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | usa l'ambiente di test (predefinito `"production"`)                                      |
| `base_url=url`                  | invia le richieste a un proxy o a un server di test                                      |
| `timeout=60`                    | secondi per tentativo HTTP                                                               |
| `retries=2`                     | numero di tentativi                                                                      |
| `pacing=False`                  | disattiva il controllo del ritmo lato client                                             |
| `read_only=True`                | blocca ogni richiesta che non sia di lettura                                             |
| `currency="TRY"`                | valuta dei prezzi di ricerca e del catalogo                                              |
| `user_agent="app/1.0"`          | antepone il tuo prodotto allo User-Agent                                                 |
| `transport=...`                 | il tuo livello HTTP (`requests`, `httpx`, un proxy, ...); vedi `domainnameapi.transport` |
| `trace=fn`                      | osserva ogni richiesta, risposta e nuovo tentativo                                       |
| `logger=logging.getLogger(...)` | registra gli scambi su un altro logger                                                   |

Il transport predefinito usa `urllib` e rispetta le variabili `HTTPS_PROXY`. Per un tuo bundle di CA, passa
`transport=dna.UrllibTransport(ssl_context=ctx)`.

## Testare il proprio codice

`domainnameapi.testing.FakeTransport` registra le richieste e risponde con risposte predefinite; non serve
simulare nient'altro:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # un Client che usa il finto transport, senza controllo del ritmo

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## Migrare dalla v1

La v2 è un nuovo progetto: risultati tipizzati al posto dei dizionari, eccezioni al posto delle buste
`{"result": "ERROR"}` e l'API REST completa al posto dell'insieme di metodi di php-dna. Fissa
`domainnameapi<2` per mantenere la v1 mentre fai il passaggio.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | nessuna eccezione                                                      |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (oppure `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (una volta per valore) |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | non presenti nell'API pubblicata; invia una [richiesta personalizzata](#richieste-e-baserequest) se il tuo account le prevede |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`; la validazione viene eseguita a ogni richiesta |
| `get_request_data`, `get_response_data`, ...        | `trace=`, il logger `domainnameapi`, `send_with_response`              |
| telemetria (`set_error_reporting_enabled`, Sentry)  | rimossa: nulla lascia il tuo processo; inoltra gli eventi di `trace` al tuo sistema di segnalazione |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` con le tue impostazioni TLS |

## Sviluppo

```bash
python -m unittest discover -s tests -v   # oppure: python -m pytest
python -m build                            # sdist e wheel
```

I test non chiamano mai la vera API. `tests/testdata/openapi.json` è il documento OpenAPI dell'API, lo stesso che
incorpora la CLI `dna`. I test verificano ogni classe di richiesta rispetto ad esso (metodo, percorso, nomi delle
query, campi del corpo, campi obbligatori), i nomi JSON di ogni modello di risposta rispetto agli schemi di
risposta e ogni valore di enumerazione, e falliscono quando l'API acquisisce un'operazione senza una classe di
richiesta. Per aggiornarlo:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

Vedi [AGENTS.md](AGENTS.md) per le convenzioni di questo repository.

## Supporto

- Documentazione dell'API: <https://www.domainnameapi.com/docs/>
- CLI e server MCP: <https://github.com/domainreseller/cli>
- Sito web: <https://www.domainnameapi.com>

## Licenza

Apache License 2.0. Vedi [LICENSE](LICENSE).
