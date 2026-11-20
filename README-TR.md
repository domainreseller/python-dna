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

# python-dna: Domain Name API için Python SDK'sı

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[Domain Name API](https://www.domainnameapi.com) bayi REST API'si için tip güvenli Python istemcisi: alan adı
sorgulama, kayıt, yenileme ve transfer, DNS, DNSSEC, iletişim kayıtları, SSL sertifikaları, hosting, siparişler,
ürün kataloğu ve bakiyeniz.

- **API'nin 64 işleminin tamamı**, [`dna` CLI](https://github.com/domainreseller/cli) ile aynı şekilde gruplanmıştır:
  `dna domain info` komutu `client.domains.info`, `dna dns add` komutu `client.dns.add` karşılığıdır.
- **Tip güvenli sonuçlar ve enum'lar**: sözlük değil, `datetime` alanlı dataclass'lar ve adlandırılmış durumlar
  (`d.status == DomainStatus.PENDING_DELETE`). Editörünüz her alanı tamamlar.
- **Her işlem, `BaseRequest`'ten türeyen bir istek sınıfıdır** ve herhangi bir şey gönderilmeden önce kendini
  doğrular. Kendi isteklerinizi de aynı şekilde yazabilirsiniz.
- **Anlamına göre yakalayabileceğiniz istisnalar**: `NotFoundError`, `InsufficientBalanceError`, `RateLimitError`,
  `OperationError`, ... hata kodları, ipuçları ve korelasyon ID'leri ile.
- **Varsayılan olarak güvenli**: ücretlendirilen istekler körlemesine yeniden denenmez, `read_only=True`
  değişiklikleri engeller, istemci hız sınırlarının altında kalacak şekilde kendini ayarlar ve thread'ler arasında
  paylaşılması güvenlidir.
- **Yalnızca standart kütüphane.** Python 3.9 veya üzeri. Telemetri yok: yaptığınız API istekleri dışında
  süreciniz dışına hiçbir şey çıkmaz.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## İçindekiler

- [Kurulum](#kurulum)
- [Kimlik bilgileri ve ortamlar](#kimlik-bilgileri-ve-ortamlar)
- [Servisler](#servisler)
- [Kullanım](#kullanım)
- [API istekleri ve BaseRequest](#api-istekleri-ve-baserequest)
- [Hatalar](#hatalar)
- [Güvenlik ve güvenilirlik](#güvenlik-ve-güvenilirlik)
- [Client seçenekleri](#client-seçenekleri)
- [Kodunuzu test etme](#kodunuzu-test-etme)
- [v1'den geçiş](#v1den-geçiş)
- [Geliştirme](#geliştirme)

## Kurulum

```bash
pip install domainnameapi
```

Sürümlü, test edilmiş paketler ayrıca [Releases](https://github.com/domainreseller/python-dna/releases)
sayfasındadır. Çalıştırılabilir programlar [examples](examples) klasöründedir: `quickstart.py`, `register.py`,
`expiring.py`, `dns_zone.py`, `ssl_certificate.py`, `custom_request.py` ve `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## Kimlik bilgileri ve ortamlar

Bayi panelinden (**API ayarları**) iki API kimlik bilgisi almanız gerekir. Panel giriş bilgileri çalışmaz.

| Kimlik bilgisi | Görünümü                               |
|----------------|----------------------------------------|
| Reseller ID    | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key        | uzun bir gizli dize                    |

İki ortam vardır. **Test ortamı olan OTE ile başlayın**: kendi verisi ve kendi API anahtarı vardır; orada
yaptığınız hiçbir şey ücret doğurmaz ve canlı alan adlarına dokunmaz.

```python
# Test ortamı (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# Production (varsayılan): gerçek kayıtlar, gerçek ücretlendirme
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()`, `dna` CLI ile aynı değişkenleri okur:

| Değişken          | Anlamı                                                        |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | reseller ID                                                   |
| `DNA_API_KEY`     | seçilen ortamın API anahtarı                                  |
| `DNA_ENV`         | `production` (varsayılan) veya `ote`                          |
| `DNA_TEST_MODE`   | `true` OTE'yi seçer (diğer DomainNameAPI SDK'larındaki gibi)  |
| `DNA_BASE_URL`    | özel bir temel URL, ör. bir proxy                             |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` ayrıca panellerin sakladığı test modu bayraklarını da kabul eder: `True`, `"true"`, `"1"`, `"on"`,
`"yes"` OTE anlamına gelir. Yanlış bir anahtar veya ortam, ilk istekte `AuthenticationError` ile ve bir ipucuyla
başarısız olur; kontrol etmenin en ucuz yolu `client.account.get()` çağrısıdır.

## Servisler

| Servis            | CLI grubu     | Metotlar                                                                                                                                                          |
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

Zorunlu girdiler konumsal argümandır (`client.domains.info("example.com")`), isteğe bağlı olanlar anahtar
sözcük argümanıdır (`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). Enum argümanları enum'u,
API adını (büyük/küçük harf fark etmez) veya numarasını kabul eder: `DomainStatus.ACTIVE`, `"active"` ve `0`
aynıdır.

## Kullanım

Tüm kod parçaları `import domainnameapi as dna` satırını ve bir `client` olduğunu varsayar.

### Arama

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search`, 30 alan adından uzun listeleri birkaç isteğe böler. Fiyatlar hesabın para birimiyle ya da
`dna.Client(..., currency="TRY")` veya `search(..., currency="TRY")` ile ayarlanan para birimiyle gelir.

### Kayıt

İletişim handle'ları ile (bir tane `contacts.create` ile oluşturun):

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
    handles=handle,  # dört rolün hepsi için tek handle veya dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

Satır içi iletişim bilgileri ile:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # dört rolün hepsi için tek Contact veya dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

İletişim bilgileri gönderilmeden önce düzenlenir: alanların baş ve sonundaki boşluklar silinir, ülke kodu büyük
harfe çevrilir ve telefon alanlarında yalnızca rakamlar tutulur (`"+90 (555) 123-45-67"` çalışır). Bazı TLD'ler
sicil (registry) öznitelikleri ister: bunları `client.products.tld("com.tr").required_attributes` ile bulun ve
`tld_attributes={...}` olarak iletin.

API yanıt verip isteği reddederse (`"success": false`), metot API'nin mesajını taşıyan `dna.OperationError`
fırlatır.

### Yenileme, transfer, geri alma

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # itfa (redemption) döneminde
```

### Alan adı ayrıntıları ve alan adı listesi

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# Tek sayfa
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# Tüm alan adları; sayfalar siz üzerinde gezindikçe getirilir
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### Kilit, gizlilik, name server'lar, child name server'lar

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # yalnızca DNSSEC imzalı alan adları için

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # IP sürümü otomatik algılanır
client.domains.delete_host("example.com", "ns1.example.com")
```

### Bir alan adının iletişim kayıtları

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # iletişim kaydı ve doğrulama durumu
result = client.contacts.update("DNA-1", contact)  # handle'ı kullanan tüm alan adlarını günceller
```

### DNS bölgesi

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # kümedeki tüm değerleri değiştirir
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # tek bir kayıt kümesi veya None
res = client.dns.apply("example.com")             # alan adını platformun name server'larına geçirir
```

İsimler göreli (`www`), kök (`""` veya `"@"`) ya da tam nitelikli olabilir. Kayıt türleri burada büyük/küçük
harfe duyarsızdır (`"txt"`, `TXT` olarak gönderilir). Doğrulama, API'nin reddedeceği durumları yakalar: kökte
CNAME, üç parçası olmayan CAA değeri, önceliği olmayan MX değeri. Test ortamı her bölge çağrısına HTTP 500
yanıtı verir; bu yüzden bölge kodu yalnızca production'da denenebilir.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # DNS sağlayıcınızın gösterdiği haliyle
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)`, tüm bölge dosyası satırları dahil sunum biçimini okur.

### URL yönlendirme

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # alan adında yönlendirme yoksa None
client.domains.delete_forwarding("example.com")
```

### Sicil belgeleri (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

Dosyalar sizin için base64 ile kodlanır; biçim (PDF, JPG, PNG, DOC, DOCX, ODT) ve boyut (dosya başına 10 MB,
istek başına 50 MB) yüklemeden önce kontrol edilir.

### SSL sertifikaları

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
client.ssl.initialize("example.com", "PositiveSSL")  # bakiyeden ücret keser
client.ssl.configure("example.com", csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status("example.com")  # st.is_issued olana kadar sorgulayın
cert = client.ssl.content("example.com")
open("example.com.crt", "w").write(cert.chain)
```

### Hosting

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # bakiyeden ücret keser

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # aktif olana kadar sorgular
print(st.panel_address, st.username, st.password)
```

Hâlâ hazırlanmakta olan bir hosting için `create` işlevini bir daha çağırmayın: iki kez ücret alınır.

### Bakiye, fiyatlar ve siparişler

```python
account = client.account.get()
usd = account.balance("USD")

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # 2 yıllık .com yenilemesinin fiyatı
order = client.orders.get("ORDER-CODE")
```

## API istekleri ve BaseRequest

Her API işlemi bir istek sınıfıdır: `DomainInfoRequest`, `DNSAddRequest`, `SSLConfigureRequest`, ... Hepsi
`dna.BaseRequest`'ten türer; bu sınıf varsayılanları sağlar (sorgu dizesi yok, gövde yok, doğrulanacak bir şey
yok). Bir istek nereye gideceğini sınıf öznitelikleriyle belirtir ve ihtiyaç duyduklarını geçersiz kılar. Bu
paketten bir örnek:

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

| Üye           | Varsayılan     | Anlamı                                                                              |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | HTTP metodu                                                                         |
| `path`        | `""`           | temel URL'nin altındaki yol; `{placeholders}` özniteliklerden doldurulur ve kaçışlanır |
| `safety`      | `Safety.READ`  | `READ`, `WRITE`, `DESTRUCTIVE` veya `BILLABLE`                                      |
| `idempotent`  | `False`        | iki kez göndermek güvenlidir (okumalar her zaman öyledir); ağ hatalarından sonra yalnızca bunlar yeniden denenir |
| `response`    | `None`         | yanıtların nasıl çözümleneceği: bir `Model` alt sınıfı, `list_of(...)`, `page_of(...)` veya ham JSON |
| `query()`     | `None`         | sorgu parametreleri: bir dict veya bir çift listesi                                 |
| `body()`      | `None`         | JSON gövdesi                                                                        |
| `validate(v)` | hiçbir şey     | sorunları `v.required`, `v.between`, `v.check`, ... ile kaydeder; bu durumda hiçbir şey gönderilmez |

Servis metotları bunları sizin için oluşturur. `client.send(request)`, kendi sınıflarınız dahil herhangi bir
isteği gönderir; örneğin yalnızca ihtiyacınız olan alanları okumak ya da bu paketin henüz sarmalamadığı bir uç
noktayı çağırmak için:

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

İsteğiniz, yerleşik isteklerin sahip olduğu her şeye sahip olur: kimlik bilgileri, yeniden denemeler, hız ayarı,
hata normalleştirme, korelasyon ID'leri, izleme ve salt okunur kısıtlama. `client.send_with_response(request)`
ayrıca durumu, başlıkları, korelasyon ID'sini, kotayı ve deneme sayısını döndürür; `client.prepare(request)`,
ücretlendirilen bir isteği gönderilmeden önce loglamak veya gözden geçirmek için tam HTTP isteğini göndermeden
oluşturur. Modeller, çözümlenmiş JSON'u `.raw` içinde tutar; bu paketin henüz modellemediği alanlar için
kullanılabilir.

## Hatalar

Her istisna `dna.DomainNameAPIError`'dan türer ve bir `kind` değerine sahiptir.

| İstisna                       | Ne zaman                                                   | Faydalı öznitelikler                                                |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (bir `ValueError`) | doğrulama isteği reddetti; **hiçbir şey gönderilmedi**   | `request`, `fields`                                                 |
| `APIError` ve alt sınıfları   | API 2xx olmayan bir durum koduyla yanıt verdi              | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | API 2xx ve `"success": false` ile yanıt verdi              | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | istek tamamlanmadı (DNS, TLS, zaman aşımı, bağlantı kopması) | `timeout`, `__cause__`                                            |
| `ReadOnlyError`               | salt okunur bir istemci bir değişikliği engelledi; hiçbir şey gönderilmedi | `request`, `safety`                                 |

`APIError` alt sınıfları yaygın durumları birbirinden ayırır: `AuthenticationError`, `NotFoundError`,
`ValidationError`, `RejectedError` (`InsufficientBalanceError` ile birlikte), `ConflictError`, `RateLimitError`
ve `ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # önce bakiye yükleyin
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # yenileme gerçekleşmiş olabilir: tekrar denemeden önce alan adını kontrol edin
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

`message` üzerinden değil, `code` üzerinden dallanın: mesajlar yerelleştirilir. API kodları
`Dna.DomainService:Domain:10007` gibi görünür; [hata başvurusuna](https://www.domainnameapi.com/docs/reference/errors.md) bakın.
`err.kind` şunlardan biridir: `ErrorKind.AUTH`, `NOT_FOUND`, `VALIDATION`, `REJECTED`, `CONFLICT`, `RATE_LIMITED`,
`SERVER`, `NETWORK`, `INVALID_INPUT`, `READ_ONLY`. Destekle iletişime geçerken `correlation_id` değerini belirtin.

## Güvenlik ve güvenilirlik

- **Güvenlik sınıfları.** Her istek `READ`, `WRITE`, `DESTRUCTIVE` veya `BILLABLE` sınıfındandır
  (`request.endpoint().safety`). Bazı POST ve PUT istekleri okumadır (`DomainSearchRequest`, `SSLStatusRequest`).
- **Salt okunur mod.** `dna.Client(..., read_only=True)`, okuma olmayan her şeyi engeller; raporlama işleri ve
  production'ı güvenle keşfetmek içindir.
- **Yeniden denemeler.** 429 yanıtları her zaman, `Retry-After` değerine uyularak yeniden denenir: API bunları
  herhangi bir işlem yapmadan reddeder. Ağ hataları ve 502/503/504 yalnızca okumalar ve idempotent yazmalar için
  yeniden denenir; böylece bir kayıt veya yenileme asla iki kez gönderilmez. Ücretlendirilen bir istek
  başarısız olduktan sonra `err.outcome_unknown` değerini kontrol edin.
- **Hız ayarı.** İstemci, anahtar başına sınırların altında kalmak için istekleri aralıklandırır (saniyede 5 istek,
  saniyede 2 arama, saniyede bir bölge çağrısı). Hız ayarını kendiniz yapıyorsanız `pacing=False` ile kapatın.
- **Kota.** `send_with_response(...).quota`, yumuşak kota başlıklarını sunar. Sınır aşıldığında API yanıtları
  reddetmek yerine yavaşlatır (en fazla 5 sn); varsayılan 60 sn zaman aşımı buna yer bırakır.
- **Korelasyon ID'leri.** Her istek bir `X-Correlation-ID` taşır. API çağrılarını loglarınızla ilişkilendirmek için
  `with dna.correlation_id("order-4711"): ...` ile kendi değerinizi ayarlayın.
- **Gözlemlenebilirlik.** Alışverişler `domainnameapi` logger'ına loglanır (istekler ve yanıtlar DEBUG,
  yeniden denemeler WARNING düzeyinde); `trace=callback` size her isteği, yanıtı ve yeniden denemeyi bir
  `TraceEvent` olarak iletir; metrikler veya hata raporlama için kullanılabilir. API anahtarı bunların hiçbirinde
  yer almaz.
- **Thread'ler.** Bir `Client`, thread'ler arasında paylaşılması güvenlidir. Bir tane oluşturun ve yeniden kullanın.
- **Toleranslı çözümleme.** Saat dilimi olmayan tarihler, `null`, `{}` yerine `[]`, dize olarak gönderilen sayılar,
  sayısal veya adlandırılmış durumlar ve herhangi bir harf biçimindeki roller (`"registrant"`, `"ADMINISTRATIVE"`)
  çözümlenir. Bu paketin henüz bilmediği değerler bir yanıtı asla bozmaz.

## Client seçenekleri

| Seçenek                         | Etkisi                                                                                   |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | test ortamını kullanır (varsayılan `"production"`)                                       |
| `base_url=url`                  | istekleri bir proxy'ye veya test sunucusuna gönderir                                     |
| `timeout=60`                    | HTTP denemesi başına saniye                                                              |
| `retries=2`                     | yeniden deneme sayısı                                                                    |
| `pacing=False`                  | istemci tarafı hız ayarını kapatır                                                       |
| `read_only=True`                | okuma olmayan her isteği engeller                                                        |
| `currency="TRY"`                | arama ve katalog fiyatlarının para birimi                                                |
| `user_agent="app/1.0"`          | ürününüzü User-Agent'ın başına ekler                                                     |
| `transport=...`                 | kendi HTTP katmanınız (`requests`, `httpx`, bir proxy, ...); bkz. `domainnameapi.transport` |
| `trace=fn`                      | her isteği, yanıtı ve yeniden denemeyi gözlemler                                         |
| `logger=logging.getLogger(...)` | alışverişleri başka bir logger'a loglar                                                  |

Varsayılan transport `urllib` kullanır ve `HTTPS_PROXY` değişkenlerine uyar. Kendi CA paketiniz için
`transport=dna.UrllibTransport(ssl_context=ctx)` iletin.

## Kodunuzu test etme

`domainnameapi.testing.FakeTransport` istekleri kaydeder ve hazır yanıtlarla cevap verir; başka hiçbir şeyi
mock'lamanız gerekmez:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # sahte transport'u kullanan, hız ayarı kapalı bir Client

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## v1'den geçiş

v2 yeni bir tasarımdır: sözlükler yerine tip güvenli sonuçlar, `{"result": "ERROR"}` zarfları yerine
istisnalar ve php-dna metot kümesi yerine REST API'nin tamamı. Siz geçiş yaparken v1'de kalmak için
`domainnameapi<2` sürümüne sabitleyin.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | istisna yok                                                            |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (veya `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (her değer için bir kez) |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | yayımlanan API'de yok; hesabınızda varsa [kendi isteğinizi](#api-istekleri-ve-baserequest) gönderin |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`; doğrulama her istekte çalışır                  |
| `get_request_data`, `get_response_data`, ...        | `trace=`, `domainnameapi` logger'ı, `send_with_response`               |
| telemetri (`set_error_reporting_enabled`, Sentry)   | kaldırıldı: süreciniz dışına hiçbir şey çıkmaz; `trace` olaylarını kendi raporlama sisteminize iletin |
| `set_ssl_verification(False)`                       | kendi TLS ayarlarınızla `transport=UrllibTransport(ssl_context=...)`   |

## Geliştirme

```bash
python -m unittest discover -s tests -v   # veya: python -m pytest
python -m build                            # sdist ve wheel
```

Testler gerçek API'yi asla çağırmaz. `tests/testdata/openapi.json`, API'nin OpenAPI belgesidir; `dna` CLI'nin
gömdüğü belgenin aynısıdır. Testler her istek sınıfını bu belgeye göre (metot, yol, sorgu adları, gövde alanları,
zorunlu alanlar), her yanıt modelinin JSON adlarını yanıt şemalarına göre ve her enum değerini kontrol eder; API,
istek sınıfı olmayan bir işlem kazandığında başarısız olur. Güncellemek için:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

Bu deponun kuralları için [AGENTS.md](AGENTS.md) dosyasına bakın.

## Destek

- API dokümantasyonu: <https://www.domainnameapi.com/docs/>
- CLI ve MCP sunucusu: <https://github.com/domainreseller/cli>
- Web sitesi: <https://www.domainnameapi.com>

## Lisans

Apache License 2.0. [LICENSE](LICENSE) dosyasına bakın.
