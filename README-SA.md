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

# python-dna: حزمة SDK للغة Python لواجهة Domain Name API

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

عميل Python مُنمَّط لواجهة REST API الخاصة بالموزّعين في [Domain Name API](https://www.domainnameapi.com): البحث عن
النطاقات وتسجيلها وتجديدها ونقلها، وDNS، وDNSSEC، وجهات الاتصال، وشهادات SSL، والاستضافة، والطلبات، وكتالوج
المنتجات، ورصيدك.

- **جميع عمليات API السبع والستين**، مجمّعة بالطريقة نفسها المتّبعة في [`dna` CLI](https://github.com/domainreseller/cli):
  الأمر `dna domain info` يقابله `client.domains.info`، والأمر `dna dns add` يقابله `client.dns.add`.
- **نتائج وقيم تعداد مُنمَّطة**: فئات بيانات (dataclasses) بحقول `datetime` وحالات مسمّاة
  (`d.status == DomainStatus.PENDING_DELETE`)، بلا قواميس. يُكمل محررك كل حقل تلقائيًا.
- **كل عملية هي فئة طلب** مشتقة من `BaseRequest` وتتحقق من صحة نفسها قبل إرسال أي شيء. يمكنك كتابة طلباتك
  الخاصة بالطريقة نفسها.
- **استثناءات يمكنك التقاطها بحسب معناها**: `NotFoundError` و `InsufficientBalanceError` و `RateLimitError` و
  `OperationError` وغيرها، مع رموز الأخطاء والتلميحات ومعرّفات الارتباط.
- **آمنة افتراضيًا**: لا تُعاد محاولة الطلبات المُحاسَب عليها بشكل أعمى، و`read_only=True` يمنع التغييرات، ويضبط
  العميل وتيرة طلباته بنفسه تحت حدود المعدّل، ويصلح للمشاركة بأمان بين الخيوط (threads).
- **المكتبة القياسية فقط.** يتطلب Python 3.9 أو أحدث. بلا قياس عن بُعد (telemetry): لا شيء يغادر عمليتك سوى
  طلبات API التي ترسلها.

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## المحتويات

- [التثبيت](#التثبيت)
- [بيانات الاعتماد والبيئات](#بيانات-الاعتماد-والبيئات)
- [الخدمات](#الخدمات)
- [الاستخدام](#الاستخدام)
- [الطلبات و BaseRequest](#الطلبات-و-baserequest)
- [الأخطاء](#الأخطاء)
- [الأمان والموثوقية](#الأمان-والموثوقية)
- [خيارات العميل](#خيارات-العميل)
- [اختبار شيفرتك](#اختبار-شيفرتك)
- [الانتقال من v1](#الانتقال-من-v1)
- [التطوير](#التطوير)

## التثبيت

```bash
pip install domainnameapi
```

تجد الحزم المُختبَرة ذات الإصدارات أيضًا في صفحة [Releases](https://github.com/domainreseller/python-dna/releases).
وتجد برامج قابلة للتشغيل في [examples](examples): `quickstart.py` و `register.py` و `expiring.py` و
`dns_zone.py` و `ssl_certificate.py` و `custom_request.py` و `error_handling.py`.

```bash
python examples/quickstart.py example.com
```

## بيانات الاعتماد والبيئات

تحتاج إلى بيانَي اعتماد لـ API من لوحة الموزّع (**API settings**). لا تعمل بيانات الدخول إلى اللوحة.

| بيان الاعتماد | شكله                                   |
|---------------|----------------------------------------|
| Reseller ID   | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key       | سلسلة سرية طويلة                       |

هناك بيئتان. **ابدأ بـ OTE**، وهي بيئة الاختبار: لها بياناتها الخاصة ومفتاح API خاص بها،
ولا يكلّف أي شيء تفعله فيها مالًا ولا يمسّ النطاقات الحية.

```python
# بيئة الاختبار (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# الإنتاج (الافتراضي): تسجيلات حقيقية ورسوم حقيقية
client = dna.Client(reseller_id, api_key)
```

تقرأ `Client.from_env()` المتغيرات نفسها التي يقرأها `dna` CLI:

| المتغير           | المعنى                                                        |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | معرّف الموزّع                                                 |
| `DNA_API_KEY`     | مفتاح API للبيئة المحددة                                      |
| `DNA_ENV`         | `production` (الافتراضي) أو `ote`                             |
| `DNA_TEST_MODE`   | القيمة `true` تختار OTE (كما في حزم DomainNameAPI SDK الأخرى) |
| `DNA_BASE_URL`    | عنوان URL أساسي مخصص، مثل وسيط (proxy)                        |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

يقبل `environment` أيضًا أعلام وضع الاختبار التي تخزّنها اللوحات: القيم `True` و `"true"` و `"1"` و `"on"` و `"yes"`
تعني OTE. يفشل المفتاح الخاطئ أو البيئة الخاطئة عند أول طلب بخطأ `AuthenticationError` مع تلميح؛
و`client.account.get()` هي أرخص طريقة للتحقق.

## الخدمات

| الخدمة            | مجموعة CLI    | العمليات                                                                                                                                                          |
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

تُمرَّر المدخلات المطلوبة كوسائط موضعية (`client.domains.info("example.com")`)، أما الاختيارية فكوسائط
مسمّاة (`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`). تقبل وسائط التعداد القيمة نفسها، أو
اسمها في API بأي حالة أحرف، أو رقمها: `DomainStatus.ACTIVE` و `"active"` و `0` كلها سواء.

## الاستخدام

تفترض جميع المقتطفات وجود `import domainnameapi as dna` و`client`.

### البحث

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

تقسّم `bulk_search` القوائم التي تزيد على 30 نطاقًا إلى عدة طلبات. تُعرض الأسعار بعملة الحساب، أو
بالعملة التي تُحدَّد بـ `dna.Client(..., currency="TRY")` أو `search(..., currency="TRY")`.

### التسجيل

باستخدام معرّفات جهات الاتصال (أنشئ واحدًا بـ `contacts.create`):

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
    handles=handle,  # معرّف واحد للأدوار الأربعة، أو dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

باستخدام جهات اتصال مضمَّنة:

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # Contact واحد للأدوار الأربعة، أو dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

تُنظَّف جهات الاتصال قبل الإرسال: تُقصّ المسافات الزائدة من الحقول، ويُحوَّل رمز الدولة إلى أحرف كبيرة، وتُبقي
حقول الهاتف أرقامها فقط (يصلح `"+90 (555) 123-45-67"`). تحتاج بعض النطاقات العليا (TLD) إلى سمات خاصة بالسجل:
اعثر عليها عبر `client.products.tld("com.tr").required_attributes` ومرّرها بصيغة `tld_attributes={...}`.

إذا ردّت API لكنها رفضت الطلب (`"success": false`)، فإن الدالة تُطلق `dna.OperationError` ومعه
رسالة API.

### التجديد والنقل والاستعادة

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # خلال فترة الاسترداد (redemption)
```

### تفاصيل النطاق وقائمة النطاقات

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# صفحة واحدة
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# كل النطاقات؛ تُجلب الصفحات أثناء التكرار
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### القفل والخصوصية وخوادم الأسماء وخوادم الأسماء الفرعية

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # فقط للنطاقات الموقّعة بـ DNSSEC

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # يُكتشف إصدار IP تلقائيًا
client.domains.delete_host("example.com", "ns1.example.com")
```

### جهات اتصال النطاق

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # جهة الاتصال وحالة التحقق منها
result = client.contacts.update("DNA-1", contact)  # يحدّث كل نطاق يستخدم المعرّف
```

### منطقة DNS

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # يستبدل كل قيم المجموعة
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # مجموعة سجلات واحدة، أو None
res = client.dns.apply("example.com")             # تحويل النطاق إلى خوادم أسماء المنصة
```

يمكن أن تكون الأسماء نسبية (`www`) أو الجذر (`""` أو `"@"`) أو مؤهَّلة بالكامل. أنواع السجلات هنا غير حساسة
لحالة الأحرف (يُرسَل `"txt"` على أنه `TXT`). يلتقط التحقق ما سترفضه API: سجل CNAME عند الجذر، وقيمة CAA
من دون ثلاثة أجزاء، وقيمة MX من دون أولوية. تردّ بيئة الاختبار على كل استدعاء للمنطقة بحالة HTTP
500، لذا لا يمكن تجربة شيفرة المناطق إلا في الإنتاج.

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # كما يعرضه مزوّد DNS لديك
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

تقرأ `dna.DS.parse(...)` صيغة العرض (presentation format)، بما في ذلك أسطر ملفات المنطقة كاملة.

### إعادة توجيه URL

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # None عندما لا يكون للنطاق إعادة توجيه
client.domains.delete_forwarding("example.com")
```

### مستندات السجل (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

تُرمَّز الملفات بـ base64 نيابةً عنك؛ ويُتحقق من الصيغة (PDF وJPG وPNG وDOC وDOCX وODT) والحجم (10 MB لكل ملف، و50 MB
لكل طلب) قبل الرفع.

### شهادات SSL

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
order = client.ssl.initialize("example.com", "PositiveSSL")  # يخصم من الرصيد
cert_id = order.certificate_id  # احتفظ به: كل استدعاء لاحق يحتاج إليه
client.ssl.configure(cert_id, csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status(cert_id)  # استعلم دوريًا حتى تصبح st.is_issued صحيحة
cert = client.ssl.content(cert_id)
open("example.com.crt", "w").write(cert.chain)
```

قد يكون للنطاق الواحد أكثر من شهادة، ولذلك يُشار إلى الشهادة الموجودة بـ**معرّف الشهادة** (GUID) لا باسم النطاق:
الدوال `configure` و`status` و`get` و`content` و`reissue` و`revoke` و`renew` تأخذه كلها. تُعيده `initialize`
و`renew`، وتعثر عليه `list` من جديد. وإذا مُرِّر اسم نطاق في موضع معرّف الشهادة، يُطلَق `InputError` قبل إرسال أي
شيء.

```python
for c in client.ssl.list(domain_name="example.com"):  # الأحدث أولًا؛ و ssl.all(...) تجلب كل الصفحات
    print(c.certificate_id, c.status, c.subscription_expires_at)

client.ssl.approvers(certificate_id=cert_id)  # شهادة موجودة
client.ssl.approvers(domain_name="example.com", package_code="PositiveSSL")  # قبل الشراء

renewal = client.ssl.renew(cert_id)  # يخصم من الرصيد
# التجديد شهادة جديدة لها معرّفها الخاص: اضبط إعدادات هذه الشهادة.
client.ssl.configure(renewal.certificate_id, csr=new_csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
```

اضبط إعدادات الشهادة خلال 15 يومًا من `initialize` أو `renew`، وإلا أُلغيت. يُتاح `renew` ابتداءً من 30 يومًا قبل
انتهاء الاشتراك (`client.ssl.get(cert_id).subscription.expires_at`). للتجديد استدعِ `renew` ثم `configure`
بالمعرّف الذي تُعيده: استدعاء `initialize` مرة أخرى ليس تجديدًا، بل يشتري بسعر الشراء شهادة جديدة لا علاقة لها
بالأولى.

### الاستضافة

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # يخصم من الرصيد

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # يستعلم دوريًا حتى يصبح نشطًا
print(st.panel_address, st.username, st.password)
```

لا تستدعِ `create` مرة أخرى لاستضافة ما زالت قيد التجهيز: فهذا يخصم الرسوم مرتين.

### الرصيد والأسعار والطلبات

```python
account = client.account.get()
usd = account.balance("USD")
profile = client.account.profile()  # الموزّع صاحب بيانات الاعتماد: name و account_currency و status وغيرها

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # سعر تجديد .com لمدة سنتين
order = client.orders.get("ORDER-CODE")
```

## الطلبات و BaseRequest

كل عملية في API هي فئة طلب: `DomainInfoRequest` و `DNSAddRequest` و `SSLConfigureRequest` وغيرها. وجميعها
مشتقة من `dna.BaseRequest`، التي توفّر القيم الافتراضية (لا سلسلة استعلام، ولا جسم، ولا شيء للتحقق منه).
يحدّد الطلب وجهته بسمات الفئة (class attributes) ويتجاوز ما يحتاجه. يبدو طلب من هذه الحزمة هكذا:

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

| العضو         | الافتراضي      | المعنى                                                                              |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | طريقة HTTP                                                                          |
| `path`        | `""`           | المسار تحت عنوان URL الأساسي؛ تُملأ `{placeholders}` من السمات وتُهرَّب             |
| `safety`      | `Safety.READ`  | `READ` أو `WRITE` أو `DESTRUCTIVE` أو `BILLABLE`                                    |
| `idempotent`  | `False`        | آمن للإرسال مرتين (والقراءات كذلك دائمًا)؛ هذه وحدها تُعاد محاولتها بعد أخطاء الشبكة |
| `response`    | `None`         | كيفية فكّ ترميز الردود: فئة فرعية من `Model` أو `list_of(...)` أو `page_of(...)` أو JSON خام |
| `query()`     | `None`         | معاملات الاستعلام: قاموس أو قائمة أزواج                                             |
| `body()`      | `None`         | جسم JSON                                                                            |
| `validate(v)` | لا شيء         | سجّل المشكلات بـ `v.required` و `v.between` و `v.check` وغيرها؛ ولا يُرسَل شيء حينئذٍ |

تبني دوال الخدمات هذه الطلبات نيابةً عنك. ترسل `client.send(request)` أي طلب، بما في ذلك فئاتك الخاصة،
مثلًا لقراءة الحقول التي تحتاجها فقط أو لاستدعاء نقطة نهاية لم تغلّفها هذه الحزمة بعد:

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

يحصل طلبك على كل ما تحصل عليه الطلبات المضمَّنة: بيانات الاعتماد، وإعادة المحاولة، وضبط الوتيرة، وتوحيد
الأخطاء، ومعرّفات الارتباط، والتتبع، وفرض وضع القراءة فقط. تعيد `client.send_with_response(request)` أيضًا الحالة
والترويسات ومعرّف الارتباط والحصة وعدد المحاولات؛ وتبني `client.prepare(request)` طلب HTTP
الفعلي من دون إرساله، لتسجّل طلبًا مُحاسَبًا عليه أو تراجعه قبل خروجه. تحتفظ النماذج (Models) بـ JSON المفكوك ترميزه في `.raw`،
للحقول التي لم تنمذجها هذه الحزمة بعد.

## الأخطاء

كل استثناء مشتق من `dna.DomainNameAPIError` وله `kind`.

| الاستثناء                     | متى                                                        | سمات مفيدة                                                          |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError` (وهو `ValueError`) | رفض التحقق الطلب؛ **لم يُرسَل شيء**                        | `request`, `fields`                                                 |
| `APIError` وفئاته الفرعية     | ردّت API بحالة غير 2xx                                     | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | ردّت API بحالة 2xx مع `"success": false`                   | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | لم يكتمل الطلب (DNS أو TLS أو انتهاء المهلة أو إعادة ضبط الاتصال) | `timeout`, `__cause__`                                        |
| `ReadOnlyError`               | منع عميل للقراءة فقط تغييرًا؛ لم يُرسَل شيء                | `request`, `safety`                                                 |

تميّز الفئات الفرعية من `APIError` بين الحالات الشائعة: `AuthenticationError` و `NotFoundError` و
`ValidationError` و `RejectedError` (ومعها `InsufficientBalanceError`) و `ConflictError` و `RateLimitError` و
`ServerError`.

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # اشحن الرصيد أولًا
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # ربما تمّ التجديد: تحقّق من النطاق قبل المحاولة مرة أخرى
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

فرّع على `code` لا على `message`: فالرسائل مترجَمة محليًا. تبدو رموز API هكذا
`Dna.DomainService:Domain:10007`؛ راجع [مرجع الأخطاء](https://www.domainnameapi.com/docs/reference/errors.md).
تكون `err.kind` إحدى القيم `ErrorKind.AUTH` و `NOT_FOUND` و `VALIDATION` و `REJECTED` و `CONFLICT` و `RATE_LIMITED` و
`SERVER` و `NETWORK` و `INVALID_INPUT` و `READ_ONLY`. اذكر `correlation_id` عند التواصل مع الدعم.

## الأمان والموثوقية

- **فئات الأمان.** كل طلب هو `READ` أو `WRITE` أو `DESTRUCTIVE` أو `BILLABLE`
  (`request.endpoint().safety`). بعض طلبات POST و PUT هي عمليات قراءة (`DomainSearchRequest` و `SSLStatusRequest`).
- **وضع القراءة فقط.** يمنع `dna.Client(..., read_only=True)` كل ما ليس قراءة، لمهام إعداد التقارير ولاستكشاف
  بيئة الإنتاج بأمان.
- **إعادة المحاولة.** تُعاد محاولة استجابات 429 دائمًا مع احترام `Retry-After`: إذ ترفضها API قبل أن تنفّذ
  أي شيء. أما أخطاء الشبكة والاستجابات 502/503/504 فلا تُعاد محاولتها إلا للقراءات والكتابات المتماثلة القوى (idempotent)، فلا
  يُرسَل تسجيل أو تجديد مرتين أبدًا. بعد فشل طلب مُحاسَب عليه، افحص `err.outcome_unknown`.
- **ضبط الوتيرة.** يباعد العميل بين الطلبات ليبقى تحت الحدود المفروضة لكل مفتاح (5 طلبات/ثانية، وبحثان/ثانية،
  واستدعاء واحد للمنطقة كل ثانية). عطّله بـ `pacing=False` إذا كنت تضبط الوتيرة بنفسك.
- **الحصة.** يكشف `send_with_response(...).quota` ترويسات الحصة المرنة. عند تجاوز الحد تبطئ API الاستجابات (حتى
  5 ثوانٍ) بدلًا من رفضها؛ وتترك المهلة الافتراضية البالغة 60 ثانية متسعًا لذلك.
- **معرّفات الارتباط.** يحمل كل طلب ترويسة `X-Correlation-ID`. عيّن معرّفك بنفسك عبر
  `with dna.correlation_id("order-4711"): ...` لربط استدعاءات API بسجلاتك.
- **قابلية المراقبة.** تُسجَّل التبادلات في المسجِّل `domainnameapi` (الطلبات والاستجابات عند مستوى DEBUG،
  وإعادات المحاولة عند مستوى WARNING)؛ ويسلّمك `trace=callback` كل طلب واستجابة ومحاولة إعادة على هيئة `TraceEvent`،
  لأغراض المقاييس أو الإبلاغ عن الأخطاء. ولا يظهر مفتاح API فيها أبدًا.
- **الخيوط (Threads).** الكائن `Client` آمن للمشاركة بين الخيوط. أنشئ واحدًا وأعد استخدامه.
- **فكّ ترميز متسامح.** تُفكّ بنجاح التواريخ بلا منطقة زمنية، و`null`، و`[]` بدل `{}`، والأرقام المرسلة كسلاسل نصية،
  والحالات الرقمية أو المسمّاة والأدوار بأي حالة أحرف (`"registrant"` و `"ADMINISTRATIVE"`). والقيم التي لا تعرفها هذه
  الحزمة بعد لا تُفسد أي استجابة أبدًا.

## خيارات العميل

| الخيار                          | التأثير                                                                                  |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | استخدام بيئة الاختبار (الافتراضي `"production"`)                                         |
| `base_url=url`                  | إرسال الطلبات إلى وسيط (proxy) أو خادم اختبار                                            |
| `timeout=60`                    | مهلة كل محاولة HTTP بالثواني                                                             |
| `retries=2`                     | عدد إعادات المحاولة                                                                      |
| `pacing=False`                  | تعطيل ضبط الوتيرة من جهة العميل                                                          |
| `read_only=True`                | منع كل طلب ليس قراءة                                                                     |
| `currency="TRY"`                | عملة أسعار البحث والكتالوج                                                               |
| `user_agent="app/1.0"`          | وضع اسم منتجك قبل User-Agent                                                             |
| `transport=...`                 | طبقة HTTP الخاصة بك (`requests` أو `httpx` أو وسيط وغيرها)؛ راجع `domainnameapi.transport` |
| `trace=fn`                      | مراقبة كل طلب واستجابة ومحاولة إعادة                                                     |
| `logger=logging.getLogger(...)` | تسجيل التبادلات في مسجِّل آخر                                                            |

يستخدم النقل الافتراضي `urllib` ويحترم متغيرات `HTTPS_PROXY`. وإذا أردت حزمة شهادات CA خاصة بك، فمرّر
`transport=dna.UrllibTransport(ssl_context=ctx)`.

## اختبار شيفرتك

تسجّل `domainnameapi.testing.FakeTransport` الطلبات وتردّ بردود معدّة سلفًا؛ ولا حاجة إلى محاكاة أي شيء آخر:

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # عميل Client يستخدم الناقل الوهمي، مع تعطيل ضبط الوتيرة

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## الانتقال من v1

الإصدار v2 تصميم جديد: نتائج مُنمَّطة بدل القواميس، واستثناءات بدل أغلفة `{"result": "ERROR"}`،
وREST API كاملة بدل مجموعة دوال php-dna. ثبّت `domainnameapi<2` لتبقى على v1 إلى أن تنتقل.

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | لا استثناء                                                             |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts` (أو `contacts.create` + `domains.register`) |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete` (مرة لكل قيمة)         |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | غير موجودة في API المنشورة؛ أرسل [طلبًا من تصميمك](#الطلبات-و-baserequest) إن كان حسابك يتيحها |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`؛ ويجري التحقق مع كل طلب                         |
| `get_request_data`, `get_response_data`, ...        | `trace=`, والمسجِّل `domainnameapi`, و`send_with_response`             |
| القياس عن بُعد (`set_error_reporting_enabled`, Sentry) | أُزيل: لا شيء يغادر عمليتك؛ مرّر أحداث `trace` إلى نظام الإبلاغ الخاص بك |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` مع إعدادات TLS الخاصة بك  |

## التطوير

```bash
python -m unittest discover -s tests -v   # أو: python -m pytest
python -m build                            # حزمتا sdist و wheel
```

لا تستدعي الاختبارات API الحقيقية أبدًا. الملف `tests/testdata/openapi.json` هو مستند OpenAPI الخاص بـ API، وهو نفسه
الذي يضمّنه `dna` CLI. تفحص الاختبارات كل فئة طلب مقابله (الطريقة، والمسار، وأسماء الاستعلام، وحقول الجسم،
والحقول المطلوبة)، وأسماء JSON لكل نموذج استجابة مقابل مخططات الاستجابة، وكل قيمة تعداد، وتفشل
عندما تكتسب API عملية جديدة بلا فئة طلب لها. لتحديثه:

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

راجع [AGENTS.md](AGENTS.md) لمعرفة أعراف هذا المستودع.

## الدعم

- توثيق API: <https://www.domainnameapi.com/docs/>
- CLI وخادم MCP: <https://github.com/domainreseller/cli>
- الموقع: <https://www.domainnameapi.com>

## الترخيص

Apache License 2.0. راجع [LICENSE](LICENSE).
