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

# python-dna: Domain Name API üçün Python SDK-sı

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[Domain Name API](https://www.domainnameapi.com) reseller REST API-si üçün tipli Python klienti: domen axtarışı,
qeydiyyat, yenilənmə və transfer, DNS, DNSSEC, kontaktlar, SSL sertifikatları, hosting, sifarişlər, məhsul
kataloqu və balansınız.

- **API-nin bütün 67 əməliyyatı**, [`dna` CLI](https://github.com/domainreseller/cli) ilə eyni şəkildə qruplaşdırılıb:
  `dna domain info` əmri `client.domains.info`, `dna dns add` əmri `client.dns.add` qarşılığıdır.
- **Tipli nəticələr və enum-lar**: lüğətlər deyil, `datetime` sahələri olan dataclass-lar və adlandırılmış statuslar
  (`d.status == DomainStatus.PENDING_DELETE`). Redaktorunuz hər sahəni tamamlayır.
- **Hər əməliyyat `BaseRequest`-dən törəyən bir sorğu sinfidir** və hər hansı bir şey göndərilməzdən əvvəl
  özünü yoxlayır. Öz sorğularınızı da eyni qaydada yaza bilərsiniz.
- **Mənasına görə tuta biləcəyiniz istisnalar**: `NotFoundError`, `InsufficientBalanceError`, `RateLimitError`,
  `OperationError`, ... xəta kodları, işarələr (hint) və korrelyasiya ID-ləri ilə.
- **Susmaya görə təhlükəsiz**: ödənişli sorğular kor-koranə təkrarlanmır, `read_only=True` dəyişiklikləri
  bloklayır, klient özünü sürət limitlərinin altında saxlayır və thread-lər arasında paylaşılması təhlükəsizdir.
- **Yalnız standart kitabxana.** Python 3.9 və ya daha yeni. Telemetriya yoxdur: etdiyiniz API sorğularından başqa
  prosesinizdən kənara heç nə çıxmır.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## Mündəricat

- [Quraşdırma](#quraşdırma)
- [Giriş məlumatları və mühitlər](#giriş-məlumatları-və-mühitlər)
- [Servislər](#servislər)
- [Nümunələr](#nümunələr)
- [Sorğular və BaseRequest](#sorğular-və-baserequest)
- [Xətalar](#xətalar)
- [Təhlükəsizlik və etibarlılıq](#təhlükəsizlik-və-etibarlılıq)
- [Client seçimləri](#client-seçimləri)
- [Kodunuzun test edilməsi](#kodunuzun-test-edilməsi)
- [v1-dən keçid](#v1-dən-keçid)
- [Layihənin hazırlanması](#layihənin-hazırlanması)

## Quraşdırma

```bash
pip install domainnameapi
```

Versiyalı, test edilmiş paketlər həmçinin [Releases](https://github.com/domainreseller/python-dna/releases)
səhifəsindədir. İşlək proqramlar [examples](examples) qovluğundadır: `quickstart.py`, `register.py`,
`expiring.py`, `dns_zone.py`, `ssl_certificate.py`, `custom_request.py` və `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Giriş məlumatları və mühitlər

Reseller panelindən (**API settings**) iki API giriş məlumatı götürməlisiniz. Panelə giriş məlumatları işləmir.

| Giriş məlumatı | Necə görünür                           |
|----------------|----------------------------------------|
| Reseller ID    | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key        | uzun gizli sətir                       |

İki mühit var. **Test mühiti olan OTE ilə başlayın**: onun öz məlumatları və öz API açarı var; orada
etdiyiniz heç bir şey pul tutmur və canlı domenlərə toxunmur.

```python
# Test mühiti (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Production (susmaya görə): real qeydiyyatlar, real ödənişlər
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()`, `dna` CLI ilə eyni dəyişənləri oxuyur:

| Dəyişən           | Mənası                                                        |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | reseller ID                                                   |
| `DNA_API_KEY`     | seçilmiş mühitin API açarı                                    |
| `DNA_ENV`         | `production` (susmaya görə) və ya `ote`                       |
| `DNA_TEST_MODE`   | `true` OTE-ni seçir (digər DomainNameAPI SDK-larındakı kimi)  |
| `DNA_BASE_URL`    | xüsusi baza URL, məsələn proksi                               |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` həmçinin panellərin saxladığı test rejimi bayraqlarını qəbul edir: `True`, `"true"`, `"1"`, `"on"`,
`"yes"` OTE deməkdir. Yanlış açar və ya mühit ilk sorğuda `AuthenticationError` və bir işarə (hint) ilə uğursuz
olur; yoxlamağın ən ucuz yolu `client.account.get()` çağırışıdır.

## Servislər

| Servis            | CLI qrupu     | Metodlar                                                                                                                                                          |
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

Məcburi girişlər mövqeli arqumentdir (`client.domains.info("example.com")`), isteğe bağlı olanlar isə açar
sözlü arqumentdir (`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Enum arqumentləri enum-u,
API adını (böyük/kiçik hərf fərq etmir) və ya nömrəsini qəbul edir: `DomainStatus.ACTIVE`, `"active"` və `0`
eynidir.

## Nümunələr

Bütün kod parçaları `import domainnameapi as dna` sətrini və bir `client` olduğunu fərz edir.

### Axtarış

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` 30 domendən uzun siyahıları bir neçə sorğuya bölür. Qiymətlər hesabın valyutası ilə və ya
`dna.Client(..., currency="TRY")` yaxud `search(..., currency="TRY")` ilə təyin edilmiş valyuta ilə gəlir.

### Qeydiyyat

Kontakt handle-ları ilə (birini `contacts.create` ilə yaradın):

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
    handles=handle,  # dörd rolun hamısı üçün bir handle və ya dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

Sətir daxili kontaktlarla:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # dörd rolun hamısı üçün bir Contact və ya dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

Kontaktlar göndərilməzdən əvvəl səliqəyə salınır: sahələrin əvvəlindəki və sonundakı boşluqlar silinir, ölkə
kodu böyük hərflərə çevrilir, telefon sahələrində isə yalnız rəqəmlər saxlanılır (`"+90 (555) 123-45-67"`
işləyir). Bəzi TLD-lər reyestr (registry) atributları tələb edir: onları
`client.products.tld("com.tr").required_attributes` ilə tapın və `tld_attributes={...}` kimi ötürün.

API cavab verib sorğunu rədd edərsə (`"success": false`), metod API-nin mesajını daşıyan `dna.OperationError`
istisnasını qaldırır.

### Yenilənmə, transfer, bərpa

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # bərpa (redemption) dövründə
```

### Domen təfərrüatları və domen siyahısı

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# Bir səhifə
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Bütün domenlər; siz üzərində gəzdikcə səhifələr gətirilir
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Kilid, məxfilik, name server-lər, child name server-lər

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # yalnız DNSSEC ilə imzalanmış domenlər üçün

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # IP versiyası avtomatik aşkarlanır
client.domains.delete_host("example.com", "ns1.example.com")
```

### Domenin kontaktları

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # kontakt və onun doğrulama vəziyyəti
result = client.contacts.update("DNA-1", contact)  # handle-dan istifadə edən bütün domenləri yeniləyir
```

### DNS zonası

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # çoxluqdakı bütün dəyərləri əvəz edir
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # bir qeyd çoxluğu və ya None
res = client.dns.apply("example.com")             # domeni platformanın name server-lərinə keçirir
```

Adlar nisbi (`www`), kök (`""` və ya `"@"`) ya da tam ixtisaslaşmış ola bilər. Qeyd növləri burada böyük/kiçik
hərfə həssas deyil (`"txt"`, `TXT` kimi göndərilir). Doğrulama API-nin rədd edəcəyi halları tutur: kökdə
CNAME, üç hissəsi olmayan CAA dəyəri, prioriteti olmayan MX dəyəri. Test mühiti hər zona çağırışına HTTP 500
ilə cavab verir; buna görə zona kodunu yalnız production-da sınamaq mümkündür.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # DNS provayderinizin göstərdiyi şəkildə
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` təqdimat formatını, o cümlədən bütün zona faylı sətirlərini oxuyur.

### URL yönləndirmə

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # domendə yönləndirmə yoxdursa None
client.domains.delete_forwarding("example.com")
```

### Reyestr sənədləri (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

Fayllar sizin üçün base64 ilə kodlaşdırılır; format (PDF, JPG, PNG, DOC, DOCX, ODT) və ölçü (hər fayl üçün 10 MB,
hər sorğu üçün 50 MB) yükləmədən əvvəl yoxlanılır.

### SSL sertifikatları

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
order = client.ssl.initialize("example.com", "PositiveSSL")  # balansdan ödəniş çıxır
cert_id = order.certificate_id  # saxlayın: sonrakı hər çağırışda lazımdır
client.ssl.configure(cert_id, csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status(cert_id)  # st.is_issued olana qədər sorğulayın
cert = client.ssl.content(cert_id)
open("example.com.crt", "w").write(cert.chain)
```

Bir domenin bir neçə sertifikatı ola bilər; buna görə mövcud sertifikat domen adı ilə deyil,
**sertifikat identifikatoru** (GUID) ilə göstərilir: `configure`, `status`, `get`, `content`, `reissue`, `revoke`
və `renew` metodlarının hamısı onu qəbul edir. `initialize` və `renew` bu identifikatoru qaytarır, `list` isə onu
yenidən tapır. Sertifikat identifikatoru gözlənilən yerə domen adı verilərsə, heç nə göndərilmədən `InputError`
istisnası qaldırılır.

```python
for c in client.ssl.list(domain_name="example.com"):  # ən yenidən köhnəyə; ssl.all(...) bütün səhifələri gətirir
    print(c.certificate_id, c.status, c.subscription_expires_at)

client.ssl.approvers(certificate_id=cert_id)  # mövcud sertifikat
client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL")  # satın almadan əvvəl

renewal = client.ssl.renew(cert_id)  # balansdan ödəniş çıxır
# Yenilənmə öz identifikatoru olan yeni sertifikatdır: məhz onu konfiqurasiya edin.
client.ssl.configure(renewal.certificate_id, csr=new_csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
```

Sertifikatı `initialize` və ya `renew` çağırışından sonrakı 15 gün ərzində konfiqurasiya edin; əks halda o ləğv
edilir. `renew` abunəliyin bitmə tarixindən (`client.ssl.get(cert_id).subscription.expires_at`) 30 gün əvvəldən
başlayaraq mümkündür. Yeniləmək üçün əvvəlcə `renew`, sonra isə onun qaytardığı identifikatorla `configure`
çağırın: `initialize`-i yenidən çağırmaq yenilənmə deyil, satınalma qiyməti ilə əlaqəsi olmayan yeni sertifikat
alır.

### Hosting

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # balansdan ödəniş çıxır

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # aktiv olana qədər sorğulayır
print(st.panel_address, st.username, st.password)
```

Hələ hazırlanmaqda olan hosting üçün `create`-i bir daha çağırmayın: iki dəfə ödəniş çıxılır.

### Balans, qiymətlər və sifarişlər

```python
account = client.account.get()
usd = account.balance("USD")
profile = client.account.profile()  # giriş məlumatlarının aid olduğu reseller: name, account_currency, status, ...

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # 2 illik .com yenilənməsinin qiyməti
order = client.orders.get("ORDER-CODE")
```

## Sorğular və BaseRequest

Hər API əməliyyatı bir sorğu sinfidir: `DomainInfoRequest`, `DNSAddRequest`, `SSLConfigureRequest`, ... Hamısı
`dna.BaseRequest`-dən törəyir; bu sinif susmaya görə davranışları təmin edir (query sətri yoxdur, gövdə yoxdur,
doğrulanacaq bir şey yoxdur). Sorğu hara getdiyini sinif atributları ilə bildirir və ehtiyac duyduqlarını əvəz
edir. Bu paketdən bir nümunə:

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

| Üzv           | Susmaya görə   | Mənası                                                                              |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | HTTP metodu                                                                         |
| `path`        | `""`           | baza URL-in altındakı yol; `{placeholders}` atributlardan doldurulur və escape edilir |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` və ya `BILLABLE`                                     |
| `idempotent`  | `False`        | iki dəfə göndərmək təhlükəsizdir (oxumalar həmişə belədir); şəbəkə xətalarından sonra yalnız bunlar təkrarlanır |
| `response`    | `None`         | cavabların necə dekodlandığı: `Model` alt sinfi, `list_of(...)`, `page_of(...)` və ya xam JSON |
| `query()`     | `None`         | query parametrləri: dict və ya cüt siyahısı                                         |
| `body()`      | `None`         | JSON gövdəsi                                                                        |
| `validate(v)` | heç nə         | problemləri `v.required`, `v.between`, `v.check`, ... ilə qeyd edir; bu halda heç nə göndərilmir |

Servis metodları bunları sizin üçün yaradır. `client.send(request)`, öz siniflərinizlə birlikdə istənilən
sorğunu göndərir; məsələn, yalnız lazım olan sahələri oxumaq və ya bu paketin hələ əhatə etmədiyi endpoint-i
çağırmaq üçün:

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

Sorğunuz daxili sorğuların aldığı hər şeyi alır: giriş məlumatları, təkrar cəhdlər, sürət tənzimi, xətaların
normallaşdırılması, korrelyasiya ID-ləri, izləmə və yalnız oxumaq məhdudiyyəti. `client.send_with_response(request)`
həmçinin statusu, başlıqları, korrelyasiya ID-sini, kvotanı və cəhd sayını qaytarır; `client.prepare(request)`
ödənişli sorğunu göndərilməzdən əvvəl loglamaq və ya nəzərdən keçirmək üçün dəqiq HTTP sorğusunu göndərmədən
qurur. Modellər dekodlanmış JSON-u `.raw` daxilində saxlayır; bu paketin hələ modelləşdirmədiyi sahələr üçün
istifadə edilə bilər.

## Xətalar

Hər istisna `dna.DomainNameAPIError`-dan törəyir və bir `kind` dəyərinə malikdir.

| İstisna                       | Nə vaxt                                                    | Faydalı atributlar                                                  |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (bir `ValueError`) | doğrulama sorğunu rədd etdi; **heç nə göndərilmədi**     | `request`, `fields`                                                 |
| `APIError` və alt sinifləri   | API 2xx olmayan status ilə cavab verdi                     | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | API 2xx və `"success": false` ilə cavab verdi              | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | sorğu tamamlanmadı (DNS, TLS, vaxt aşımı, bağlantının kəsilməsi) | `timeout`, `__cause__`                                        |
| `ReadOnlyError`               | yalnız oxumaq rejimindəki klient dəyişikliyi blokladı; heç nə göndərilmədi | `request`, `safety`                                 |

`APIError` alt sinifləri geniş yayılmış halları bir-birindən ayırır: `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (`InsufficientBalanceError` ilə birlikdə), `ConflictError`, `RateLimitError`
və `ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # əvvəlcə balansı artırın
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # yenilənmə həyata keçmiş ola bilər: yenidən cəhd etməzdən əvvəl domeni yoxlayın
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

`message` üzrə yox, `code` üzrə budaqlandırın: mesajlar lokallaşdırılır. API kodları
`Dna.DomainService:Domain:10007` kimi görünür; [xəta sorğu-məlumatına](https://www.domainnameapi.com/docs/reference/errors.md) baxın.
`err.kind` bunlardan biridir: `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Dəstək xidmətinə müraciət edərkən `correlation_id` dəyərini qeyd edin.

## Təhlükəsizlik və etibarlılıq

- **Təhlükəsizlik sinifləri.** Hər sorğu `READ`, `WRITE`, `DESTRUCTIVE` və ya `BILLABLE` sinfindədir
  (`request.endpoint().safety`). Bəzi POST və PUT sorğuları oxumadır (`DomainSearchRequest`, `SSLStatusRequest`).
- **Yalnız oxumaq rejimi.** `dna.Client(..., read_only=True)` oxuma olmayan hər şeyi bloklayır; hesabat işləri və
  production-u təhlükəsiz araşdırmaq üçündür.
- **Təkrar cəhdlər.** 429 cavabları həmişə, `Retry-After` nəzərə alınmaqla təkrarlanır: API onları heç bir
  əməliyyat etmədən rədd edir. Şəbəkə xətaları və 502/503/504 yalnız oxumalar və idempotent yazmalar üçün
  təkrarlanır; beləliklə qeydiyyat və ya yenilənmə heç vaxt iki dəfə göndərilmir. Ödənişli sorğu uğursuz
  olduqdan sonra `err.outcome_unknown` dəyərini yoxlayın.
- **Sürət tənzimi.** Klient açar başına limitlərin altında qalmaq üçün sorğular arasında fasilə qoyur (saniyədə 5 sorğu,
  saniyədə 2 axtarış, saniyədə bir zona çağırışı). Sürəti özünüz tənzimləyirsinizsə, `pacing=False` ilə söndürün.
- **Kvota.** `send_with_response(...).quota` yumşaq kvota başlıqlarını təqdim edir. Limit aşıldıqda API cavabları
  rədd etmək əvəzinə yavaşladır (ən çoxu 5 san); susmaya görə 60 san vaxt aşımı buna yer buraxır.
- **Korrelyasiya ID-ləri.** Hər sorğu `X-Correlation-ID` daşıyır. API çağırışlarını loglarınızla əlaqələndirmək üçün
  `with dna.correlation_id("order-4711"): ...` ilə öz dəyərinizi təyin edin.
- **Müşahidə oluna bilmə.** Mübadilələr `domainnameapi` logger-inə loglanır (sorğular və cavablar DEBUG,
  təkrar cəhdlər WARNING səviyyəsində); `trace=callback` sizə hər sorğunu, cavabı və təkrar cəhdi `TraceEvent`
  kimi ötürür; metrikalar və ya xəta hesabatı üçün istifadə edilə bilər. API açarı onların heç birində yer almır.
- **Thread-lər.** `Client` thread-lər arasında paylaşılması təhlükəsizdir. Bir dənə yaradın və təkrar istifadə edin.
- **Tolerant dekodlama.** Saat qurşağı olmayan tarixlər, `null`, `{}` əvəzinə `[]`, sətir kimi göndərilən rəqəmlər,
  rəqəmli və ya adlı statuslar və istənilən hərf registrində rollar (`"registrant"`, `"ADMINISTRATIVE"`)
  dekodlanır. Bu paketin hələ tanımadığı dəyərlər cavabı heç vaxt pozmur.

## Client seçimləri

| Seçim                           | Təsiri                                                                                   |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | test mühitindən istifadə edir (susmaya görə `"production"`)                              |
| `base_url=url`                  | sorğuları proksiyə və ya test serverinə göndərir                                         |
| `timeout=60`                    | HTTP cəhdi başına saniyə                                                                 |
| `retries=2`                     | təkrar cəhd sayı                                                                         |
| `pacing=False`                  | klient tərəfi sürət tənzimini söndürür                                                   |
| `read_only=True`                | oxuma olmayan hər sorğunu bloklayır                                                      |
| `currency="TRY"`                | axtarış və kataloq qiymətlərinin valyutası                                               |
| `user_agent="app/1.0"`          | məhsulunuzu User-Agent-in əvvəlinə əlavə edir                                            |
| `transport=...`                 | öz HTTP qatınız (`requests`, `httpx`, proksi, ...); bax `domainnameapi.transport`        |
| `trace=fn`                      | hər sorğunu, cavabı və təkrar cəhdi müşahidə edir                                        |
| `logger=logging.getLogger(...)` | mübadilələri başqa logger-ə loglayır                                                     |

Susmaya görə transport `urllib` istifadə edir və `HTTPS_PROXY` dəyişənlərinə riayət edir. Öz CA paketiniz üçün
`transport=dna.UrllibTransport(ssl_context=ctx)` ötürün.

## Kodunuzun test edilməsi

`domainnameapi.testing.FakeTransport` sorğuları qeyd edir və hazır cavablarla cavab verir; başqa heç nəyi
mock etmək lazım deyil:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # saxta transportdan istifadə edən, sürət tənzimi söndürülmüş Client

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## v1-dən keçid

v2 yeni dizayndır: lüğətlər əvəzinə tipli nəticələr, `{"result": "ERROR"}` zərfləri əvəzinə
istisnalar və php-dna metod dəsti əvəzinə bütün REST API. Siz keçid edərkən v1-də qalmaq üçün
`domainnameapi<2` versiyasına sabitləyin.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | istisna yoxdur                                                         |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (və ya `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (hər dəyər üçün bir dəfə) |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | dərc edilmiş API-də yoxdur; hesabınızda varsa [öz sorğunuzu](#sorğular-və-baserequest) göndərin |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`; doğrulama hər sorğuda işləyir                  |
| `get_request_data`, `get_response_data`, ...        | `trace=`, `domainnameapi` logger-i, `send_with_response`               |
| telemetriya (`set_error_reporting_enabled`, Sentry) | silindi: prosesinizdən kənara heç nə çıxmır; `trace` hadisələrini öz hesabat sisteminizə yönləndirin |
| `set_ssl_verification(False)`                       | öz TLS tənzimləmələrinizlə `transport=UrllibTransport(ssl_context=...)` |

## Layihənin hazırlanması

```bash
python -m unittest discover -s tests -v   # və ya: python -m pytest
python -m build                            # sdist və wheel
```

Testlər real API-ni heç vaxt çağırmır. `tests/testdata/openapi.json` API-nin OpenAPI sənədidir; `dna` CLI-nin
özünə daxil etdiyi sənədin eynisidir. Testlər hər sorğu sinfini bu sənədə qarşı (metod, yol, query adları,
gövdə sahələri, məcburi sahələr), hər cavab modelinin JSON adlarını cavab sxemlərinə qarşı və hər enum
dəyərini yoxlayır; API-yə sorğu sinfi olmayan yeni əməliyyat əlavə olunduqda uğursuz olur. Yeniləmək üçün:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

Bu depozitarinin qaydaları üçün [AGENTS.md](AGENTS.md) faylına baxın.

## Dəstək

- API sənədləşməsi: <https://www.domainnameapi.com/docs/>
- CLI və MCP serveri: <https://github.com/domainreseller/cli>
- Veb sayt: <https://www.domainnameapi.com>

## Lisenziya

Apache License 2.0. [LICENSE](LICENSE) faylına baxın.
