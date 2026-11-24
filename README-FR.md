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

# python-dna : le SDK Python pour la Domain Name API

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Client Python typé pour l'API REST revendeur de [Domain Name API](https://www.domainnameapi.com) : recherche de
domaines, enregistrement, renouvellement et transfert, DNS, DNSSEC, contacts, certificats SSL, hébergement,
commandes, catalogue de produits et solde.

- **Les 67 opérations de l'API**, regroupées comme dans la [CLI `dna`](https://github.com/domainreseller/cli) :
  `dna domain info` correspond à `client.domains.info`, `dna dns add` à `client.dns.add`.
- **Résultats et énumérations typés** : des dataclasses avec des champs `datetime` et des statuts nommés
  (`d.status == DomainStatus.PENDING_DELETE`), pas des dictionnaires. Votre éditeur complète chaque champ.
- **Chaque opération est une classe de requête** dérivée de `BaseRequest` qui se valide elle-même avant tout
  envoi. Écrivez les vôtres de la même façon.
- **Des exceptions que l'on peut attraper selon leur sens** : `NotFoundError`, `InsufficientBalanceError`,
  `RateLimitError`, `OperationError`, ... avec codes d'erreur, indications et identifiants de corrélation.
- **Sûr par défaut** : les requêtes facturables ne sont jamais rejouées aveuglément, `read_only=True` bloque les
  modifications, le client se cadence sous les limites de débit et peut être partagé entre plusieurs threads.
- **Bibliothèque standard uniquement.** Python 3.9 ou plus récent. Aucune télémétrie : rien ne quitte votre
  processus, hormis les requêtes d'API que vous effectuez.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## Sommaire

- [Installation](#installation)
- [Identifiants et environnements](#identifiants-et-environnements)
- [Services](#services)
- [Utilisation](#utilisation)
- [Requêtes et BaseRequest](#requêtes-et-baserequest)
- [Erreurs](#erreurs)
- [Sécurité et fiabilité](#sécurité-et-fiabilité)
- [Options du client](#options-du-client)
- [Tester votre code](#tester-votre-code)
- [Migrer depuis la v1](#migrer-depuis-la-v1)
- [Développement](#développement)

## Installation

```bash
pip install domainnameapi
```

Des paquets versionnés et testés se trouvent également sur la page [Releases](https://github.com/domainreseller/python-dna/releases).
Des programmes exécutables se trouvent dans [examples](examples) : `quickstart.py`, `register.py`, `expiring.py`,
`dns_zone.py`, `ssl_certificate.py`, `custom_request.py` et `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Identifiants et environnements

Vous avez besoin de deux identifiants d'API, disponibles dans le panneau revendeur (**API settings**). Les
identifiants de connexion au panneau ne fonctionnent pas.

| Identifiant | Aspect                                 |
|-------------|----------------------------------------|
| Reseller ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key     | une longue chaîne secrète              |

Il existe deux environnements. **Commencez par OTE**, l'environnement de test : il possède ses propres données et
sa propre clé d'API, et rien de ce que vous y faites ne coûte d'argent ni n'affecte de domaines en production.

```python
# Environnement de test (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Production (par défaut) : vrais enregistrements, vraie facturation
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()` lit les mêmes variables que la CLI `dna` :

| Variable          | Signification                                                    |
|-------------------|------------------------------------------------------------------|
| `DNA_RESELLER_ID` | ID revendeur                                                     |
| `DNA_API_KEY`     | clé d'API de l'environnement sélectionné                         |
| `DNA_ENV`         | `production` (par défaut) ou `ote`                               |
| `DNA_TEST_MODE`   | `true` sélectionne OTE (comme dans les autres SDK DomainNameAPI) |
| `DNA_BASE_URL`    | une URL de base personnalisée, par ex. un proxy                  |
| `DNA_APP`         | votre application, envoyée dans `X-App` (par ex. `whmcs`)        |
| `DNA_APP_VERSION` | la version de votre application, envoyée dans `X-Version`        |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` accepte aussi les indicateurs de mode test que stockent les panneaux : `True`, `"true"`, `"1"`,
`"on"`, `"yes"` signifient OTE. Une clé ou un environnement incorrect échoue dès la première requête avec une
`AuthenticationError` et une indication ; `client.account.get()` est le moyen le moins coûteux de vérifier.

## Services

| Service           | Groupe CLI    | Méthodes                                                                                                                                                          |
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

Les entrées obligatoires sont des arguments positionnels (`client.domains.info("example.com")`), les entrées
facultatives des arguments nommés (`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Les
arguments d'énumération acceptent l'énumération, son nom d'API quelle que soit la casse, ou son numéro :
`DomainStatus.ACTIVE`, `"active"` et `0` sont équivalents.

## Utilisation

Tous les extraits supposent `import domainnameapi as dna` et un `client`.

### Recherche

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` découpe les listes de plus de 30 domaines en plusieurs requêtes. Les prix sont exprimés dans la
devise du compte, ou dans celle définie avec `dna.Client(..., currency="TRY")` ou `search(..., currency="TRY")`.

### Enregistrement

Avec des identifiants de contact (créez-en un avec `contacts.create`) :

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
    handles=handle,  # un identifiant pour les quatre rôles, ou dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

Avec des contacts en ligne :

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # un Contact pour les quatre rôles, ou dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

Les contacts sont normalisés avant l'envoi : les champs sont débarrassés des espaces superflus, le pays est mis
en majuscules et les champs de téléphone ne conservent que leurs chiffres (`"+90 (555) 123-45-67"` fonctionne).
Certains TLD exigent des attributs de registre : trouvez-les avec
`client.products.tld("com.tr").required_attributes` et transmettez-les sous la forme `tld_attributes={...}`.

Si l'API répond mais refuse l'opération (`"success": false`), la méthode lève une `dna.OperationError` portant le
message de l'API.

### Renouvellement, transfert, restauration

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # pendant la période de rédemption
```

### Détails d'un domaine et liste des domaines

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# Une page
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Tous les domaines ; les pages sont récupérées au fil de l'itération
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Verrouillage, confidentialité, serveurs de noms, serveurs de noms enfants

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # uniquement pour les domaines signés avec DNSSEC

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # version IP détectée
client.domains.delete_host("example.com", "ns1.example.com")
```

### Contacts d'un domaine

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # le contact et son état de vérification
result = client.contacts.update("DNA-1", contact)  # met à jour tous les domaines utilisant l'identifiant
```

### Zone DNS

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # remplace toutes les valeurs du jeu
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # un jeu d'enregistrements, ou None
res = client.dns.apply("example.com")             # bascule le domaine sur les serveurs de noms de la plateforme
```

Les noms peuvent être relatifs (`www`), l'apex (`""` ou `"@"`) ou complets (FQDN). Les types d'enregistrement ne
sont pas sensibles à la casse ici (`"txt"` est envoyé comme `TXT`). La validation détecte ce que l'API
rejetterait : un CNAME à l'apex, une valeur CAA sans trois parties, une valeur MX sans priorité. L'environnement
de test répond à chaque appel de zone par un HTTP 500 ; le code de zone ne peut donc être essayé qu'en
production.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # tel que l'affiche votre fournisseur DNS
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` lit le format de présentation, y compris des lignes entières de fichier de zone.

### Redirection d'URL

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # None lorsque le domaine n'en a pas
client.domains.delete_forwarding("example.com")
```

### Documents du registre (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

Les fichiers sont encodés en base64 pour vous ; le format (PDF, JPG, PNG, DOC, DOCX, ODT) et la taille (10 Mo
par fichier, 50 Mo par requête) sont vérifiés avant l'envoi.

### Certificats SSL

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
order = client.ssl.initialize("example.com", "PositiveSSL")  # débite le solde
cert_id = order.certificate_id  # conservez-le : chaque appel ultérieur le prend
client.ssl.configure(cert_id, csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status(cert_id)  # interrogez jusqu'à st.is_issued
cert = client.ssl.content(cert_id)
open("example.com.crt", "w").write(cert.chain)
```

Un domaine peut avoir plusieurs certificats ; un certificat existant est donc désigné par son
**identifiant de certificat** (un GUID), et non par son nom de domaine : `configure`, `status`, `get`, `content`,
`reissue`, `revoke` et `renew` le prennent tous. `initialize` et `renew` le renvoient, et `list` permet de le
retrouver. Passer un nom de domaine là où un identifiant de certificat est attendu lève une `InputError` avant
tout envoi.

```python
for c in client.ssl.list(domain_name="example.com"):  # le plus récent d'abord ; ssl.all(...) parcourt toutes les pages
    print(c.certificate_id, c.status, c.subscription_expires_at)

client.ssl.approvers(certificate_id=cert_id)  # un certificat existant
client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL")  # avant un achat

renewal = client.ssl.renew(cert_id)  # débite le solde
# Le renouvellement est un nouveau certificat doté de son propre identifiant : configurez celui-ci.
client.ssl.configure(renewal.certificate_id, csr=new_csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
```

Configurez un certificat dans les 15 jours qui suivent `initialize` ou `renew`, faute de quoi il est annulé.
`renew` est possible à partir de 30 jours avant la fin de l'abonnement
(`client.ssl.get(cert_id).subscription.expires_at`). Pour renouveler, appelez `renew` puis `configure` avec
l'identifiant renvoyé : rappeler `initialize` n'est pas un renouvellement, cela achète au prix d'achat un
certificat sans lien avec le premier.

### Hébergement

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # débite le solde

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # interroge jusqu'à l'activation
print(st.panel_address, st.username, st.password)
```

N'appelez jamais `create` une seconde fois pour un hébergement encore en cours de provisionnement : cela
facture deux fois.

### Solde, prix et commandes

```python
account = client.account.get()
usd = account.balance("USD")
profile = client.account.profile()  # le revendeur associé aux identifiants : name, account_currency, status, ...

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # prix d'un renouvellement de .com sur 2 ans
order = client.orders.get("ORDER-CODE")
```

## Requêtes et BaseRequest

Chaque opération de l'API est une classe de requête : `DomainInfoRequest`, `DNSAddRequest`,
`SSLConfigureRequest`, ... Toutes dérivent de `dna.BaseRequest`, qui fournit les valeurs par défaut (pas de
chaîne de requête, pas de corps, rien à valider). Une requête indique où elle va au moyen d'attributs de classe
et redéfinit ce dont elle a besoin. Un exemple tiré de ce paquet :

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

| Membre        | Par défaut     | Signification                                                                       |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | méthode HTTP                                                                        |
| `path`        | `""`           | chemin sous l'URL de base ; les `{placeholders}` sont remplis à partir des attributs et échappés |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` ou `BILLABLE`                                        |
| `idempotent`  | `False`        | peut être envoyée deux fois sans risque (les lectures le sont toujours) ; seules celles-ci sont rejouées après des erreurs réseau |
| `response`    | `None`         | comment les réponses sont décodées : une sous-classe de `Model`, `list_of(...)`, `page_of(...)` ou du JSON brut |
| `query()`     | `None`         | paramètres de requête : un dict ou une liste de paires                              |
| `body()`      | `None`         | le corps JSON                                                                       |
| `validate(v)` | rien           | enregistre les problèmes avec `v.required`, `v.between`, `v.check`, ... ; rien n'est alors envoyé |

Les méthodes des services les construisent pour vous. `client.send(request)` envoie n'importe quelle requête, y
compris vos propres classes, par exemple pour ne lire que les champs dont vous avez besoin ou pour appeler un
endpoint que ce paquet n'encapsule pas encore :

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

Votre requête bénéficie de tout ce dont bénéficient les requêtes intégrées : identifiants, nouvelles tentatives,
cadencement, normalisation des erreurs, identifiants de corrélation, traçage et application du mode lecture
seule. `client.send_with_response(request)` renvoie en plus le statut, les en-têtes, l'identifiant de
corrélation, le quota et le nombre de tentatives ; `client.prepare(request)` construit la requête HTTP exacte
sans l'envoyer, pour journaliser ou relire une requête facturable avant son départ. Les modèles conservent le
JSON décodé dans `.raw`, pour les champs que ce paquet ne modélise pas encore.

## Erreurs

Chaque exception dérive de `dna.DomainNameAPIError` et possède un `kind`.

| Exception                     | Quand                                                      | Attributs utiles                                                    |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (une `ValueError`) | la validation a rejeté la requête ; **rien n'a été envoyé** | `request`, `fields`                                               |
| `APIError` et sous-classes    | l'API a répondu avec un statut non 2xx                     | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | l'API a répondu 2xx avec `"success": false`                | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | la requête n'a pas abouti (DNS, TLS, délai dépassé, réinitialisation) | `timeout`, `__cause__`                                   |
| `ReadOnlyError`               | un client en lecture seule a bloqué une modification ; rien n'a été envoyé | `request`, `safety`                                 |

Les sous-classes de `APIError` distinguent les cas courants : `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (avec `InsufficientBalanceError`), `ConflictError`, `RateLimitError` et
`ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # rechargez d'abord le solde
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # le renouvellement a peut-être abouti : vérifiez le domaine avant de réessayer
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

Branchez-vous sur `code`, pas sur `message` : les messages sont localisés. Les codes de l'API ressemblent à
`Dna.DomainService:Domain:10007` ; voir la [référence des erreurs](https://www.domainnameapi.com/docs/reference/errors.md).
`err.kind` vaut l'un de `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Indiquez le `correlation_id` lorsque vous contactez le support.

## Sécurité et fiabilité

- **Classes de sécurité.** Chaque requête est `READ`, `WRITE`, `DESTRUCTIVE` ou `BILLABLE`
  (`request.endpoint().safety`). Certaines requêtes POST et PUT sont des lectures (`DomainSearchRequest`,
  `SSLStatusRequest`).
- **Mode lecture seule.** `dna.Client(..., read_only=True)` bloque tout ce qui n'est pas une lecture, pour les
  tâches de reporting et pour explorer la production en toute sécurité.
- **Nouvelles tentatives.** Les réponses 429 sont toujours rejouées, en respectant `Retry-After` : l'API les
  rejette avant de rien faire. Les erreurs réseau et les 502/503/504 ne sont rejouées que pour les lectures et
  les écritures idempotentes, de sorte qu'un enregistrement ou un renouvellement n'est jamais envoyé deux fois.
  Après l'échec d'une requête facturable, vérifiez `err.outcome_unknown`.
- **Cadencement.** Le client espace les requêtes pour rester sous les limites par clé (5 requêtes/seconde,
  2 recherches/seconde, un appel de zone par seconde). Désactivez-le avec `pacing=False` si vous cadencez
  vous-même.
- **Quota.** `send_with_response(...).quota` expose les en-têtes de quota souple. Au-delà de la limite, l'API
  ralentit les réponses (jusqu'à 5 s) au lieu de les rejeter ; le délai d'expiration par défaut de 60 s laisse de
  la marge pour cela.
- **Identifiants de corrélation.** Chaque requête porte un `X-Correlation-ID`. Définissez le vôtre avec
  `with dna.correlation_id("order-4711"): ...` pour relier les appels d'API à vos journaux.
- **Observabilité.** Les échanges sont journalisés dans le logger `domainnameapi` (requêtes et réponses en DEBUG,
  nouvelles tentatives en WARNING) ; `trace=callback` vous transmet chaque requête, réponse et nouvelle tentative
  sous forme de `TraceEvent`, pour les métriques ou le suivi des erreurs. La clé d'API n'y figure jamais.
- **Threads.** Un `Client` peut être partagé entre plusieurs threads. Créez-en un et réutilisez-le.
- **Décodage tolérant.** Les dates sans fuseau horaire, `null`, `[]` au lieu de `{}`, les nombres envoyés sous
  forme de chaînes, les statuts numériques ou nommés et les rôles quelle que soit la casse (`"registrant"`,
  `"ADMINISTRATIVE"`) sont tous décodés. Les valeurs que ce paquet ne connaît pas encore ne font jamais échouer
  une réponse.

## Options du client

| Option                          | Effet                                                                                    |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | utilise l'environnement de test (par défaut `"production"`)                              |
| `base_url=url`                  | envoie les requêtes à un proxy ou à un serveur de test                                   |
| `timeout=60`                    | secondes par tentative HTTP                                                              |
| `retries=2`                     | nombre de nouvelles tentatives                                                           |
| `pacing=False`                  | désactive le cadencement côté client                                                     |
| `read_only=True`                | bloque toute requête qui n'est pas une lecture                                           |
| `currency="TRY"`                | devise des prix de recherche et du catalogue                                             |
| `user_agent="app/1.0"`          | place votre produit devant le User-Agent                                                 |
| `app_name="whmcs"`              | nomme votre application dans l'en-tête `X-App` (par défaut `"python"`)                   |
| `app_version="8.13.1"`          | la version de votre application dans l'en-tête `X-Version` (par défaut : celle du SDK)   |
| `transport=...`                 | votre propre couche HTTP (`requests`, `httpx`, un proxy, ...) ; voir `domainnameapi.transport` |
| `trace=fn`                      | observe chaque requête, réponse et nouvelle tentative                                    |
| `logger=logging.getLogger(...)` | journalise les échanges dans un autre logger                                             |

Le transport par défaut utilise `urllib` et respecte les variables `HTTPS_PROXY`. Pour votre propre bundle de
certificats CA, passez `transport=dna.UrllibTransport(ssl_context=ctx)`.

### Identifier votre application

Chaque requête porte deux en-têtes qui indiquent à l'API quelle intégration l'a envoyée :

- `X-App` : l'application qui utilise le SDK, `python` par défaut. La valeur est mise en minuscules et seuls
  `a-z`, `0-9`, `.`, `_` et `-` sont conservés.
- `X-Version` : la version de cette application, celle de ce SDK par défaut. Seuls les chiffres et les points
  sont conservés : `V2.0.20-beta` devient `2.0.20`.

Les panels et modules construits sur le SDK devraient se nommer :

```python
client = dna.Client(reseller_id, api_key, app_name="WiseCP5", app_version="V2.0.20-beta")
# X-App: wisecp5, X-Version: 2.0.20
```

`Client.from_env()` lit aussi `DNA_APP` et `DNA_APP_VERSION`. Un nom vide ou invalide revient à `python`, une
version vide à celle du SDK. Le User-Agent ne change pas ; `user_agent=` en définit toujours le préfixe.

## Tester votre code

`domainnameapi.testing.FakeTransport` enregistre les requêtes et répond avec des réponses préparées ; rien
d'autre n'a besoin d'être simulé :

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # un Client utilisant le faux transport, sans cadencement

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## Migrer depuis la v1

La v2 est une nouvelle conception : des résultats typés au lieu de dictionnaires, des exceptions au lieu
d'enveloppes `{"result": "ERROR"}`, et l'API REST complète au lieu de l'ensemble de méthodes de php-dna. Épinglez
`domainnameapi<2` pour conserver la v1 le temps de la transition.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | aucune exception                                                       |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (ou `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (une fois par valeur)  |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | absent de l'API publiée ; envoyez une [requête personnalisée](#requêtes-et-baserequest) si votre compte les propose |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")` ; la validation s'exécute sur chaque requête    |
| `get_request_data`, `get_response_data`, ...        | `trace=`, le logger `domainnameapi`, `send_with_response`              |
| télémétrie (`set_error_reporting_enabled`, Sentry)  | supprimée : rien ne quitte votre processus ; transmettez les événements `trace` à votre propre outil de suivi |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` avec vos propres paramètres TLS |

## Développement

```bash
python -m unittest discover -s tests -v   # ou : python -m pytest
python -m build                            # sdist et wheel
```

Les tests n'appellent jamais la vraie API. `tests/testdata/openapi.json` est le document OpenAPI de l'API, le même
que celui qu'embarque la CLI `dna`. Les tests vérifient chaque classe de requête par rapport à lui (méthode,
chemin, noms de query, champs du corps, champs obligatoires), les noms JSON de chaque modèle de réponse par rapport
aux schémas de réponse ainsi que chaque valeur d'énumération, et échouent lorsque l'API gagne une opération sans
classe de requête. Pour le mettre à jour :

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

Voir [AGENTS.md](AGENTS.md) pour les conventions de ce dépôt.

## Support

- Documentation de l'API : <https://www.domainnameapi.com/docs/>
- CLI et serveur MCP : <https://github.com/domainreseller/cli>
- Site web : <https://www.domainnameapi.com>

## Licence

Apache License 2.0. Voir [LICENSE](LICENSE).
