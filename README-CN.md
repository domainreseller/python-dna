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

# python-dna：Domain Name API 的 Python SDK

[![PyPI](https://img.shields.io/pypi/v/domainnameapi.svg)](https://pypi.org/project/domainnameapi/)
[![CI](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/domainreseller/python-dna/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[Domain Name API](https://www.domainnameapi.com) 经销商 REST API 的带类型 Python 客户端：域名搜索、
注册、续费与转入、DNS、DNSSEC、联系人、SSL 证书、主机托管、订单、产品
目录以及账户余额。

- **全部 64 个 API 操作**，分组方式与 [`dna` CLI](https://github.com/domainreseller/cli) 一致：
  `dna domain info` 对应 `client.domains.info`，`dna dns add` 对应 `client.dns.add`。
- **类型化的结果与枚举**：带有 `datetime` 字段和具名状态的 dataclass
  （`d.status == DomainStatus.PENDING_DELETE`），而不是字典。你的编辑器可以补全每一个字段。
- **每个操作都是一个请求类**，派生自 `BaseRequest`，并在发送任何内容之前先对自身进行校验。
  你也可以用同样的方式编写自己的请求。
- **可按含义捕获的异常**：`NotFoundError`、`InsufficientBalanceError`、`RateLimitError`、
  `OperationError` 等，并附带错误码、提示和关联 ID。
- **默认安全**：计费请求绝不会被盲目重试，`read_only=True` 会阻止任何变更，客户端会自行
  控制请求节奏以遵守速率限制，并且可在线程之间安全共享。
- **仅依赖标准库。** 需要 Python 3.9 或更高版本。无遥测：除了你发出的 API
  请求之外，没有任何数据会离开你的进程。

```python
import domainnameapi as dna

client = dna.Client(reseller_id, api_key, environment="ote")

result = client.domains.search("example.com")
if result.available:
    print(f"{result.domain_name} is available for {result.price:.2f} {result.currency}")
```

## 目录

- [安装](#安装)
- [凭据与环境](#凭据与环境)
- [服务](#服务)
- [用法](#用法)
- [请求与 BaseRequest](#请求与-baserequest)
- [错误](#错误)
- [安全与可靠性](#安全与可靠性)
- [客户端选项](#客户端选项)
- [测试你的代码](#测试你的代码)
- [从 v1 迁移](#从-v1-迁移)
- [开发](#开发)

## 安装

```bash
pip install domainnameapi
```

经过版本管理并测试的软件包也可在 [Releases](https://github.com/domainreseller/python-dna/releases)
页面获取。可运行的程序位于 [examples](examples)：`quickstart.py`、`register.py`、`expiring.py`、
`dns_zone.py`、`ssl_certificate.py`、`custom_request.py` 和 `error_handling.py`。

```bash
python examples/quickstart.py example.com
```

## 凭据与环境

你需要从经销商面板（**API settings**）获取两个 API 凭据。面板的登录信息无法使用。

| 凭据        | 形式                                   |
|-------------|----------------------------------------|
| Reseller ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| API key     | 一长串密钥字符串                       |

共有两个环境。**请先从 OTE 开始**，即测试环境：它有独立的数据和独立的 API key，
在其中的任何操作都不会产生费用，也不会影响线上域名。

```python
# 测试环境 (OTE)
client = dna.Client(reseller_id, ote_api_key, environment="ote")

# 生产环境（默认）：真实注册，真实扣费
client = dna.Client(reseller_id, api_key)
```

`Client.from_env()` 读取与 `dna` CLI 相同的变量：

| 变量              | 含义                                                          |
|-------------------|---------------------------------------------------------------|
| `DNA_RESELLER_ID` | 经销商 ID                                                     |
| `DNA_API_KEY`     | 所选环境的 API key                                            |
| `DNA_ENV`         | `production`（默认）或 `ote`                                  |
| `DNA_TEST_MODE`   | `true` 选择 OTE（与其他 DomainNameAPI SDK 一致）              |
| `DNA_BASE_URL`    | 自定义基础 URL，例如代理                                      |

```python
client = dna.Client.from_env(user_agent="my-panel/1.4")
```

`environment` 也接受面板中保存的测试模式标志：`True`、`"true"`、`"1"`、`"on"`、`"yes"` 均表示 OTE。
密钥或环境错误时，第一次请求就会失败，抛出 `AuthenticationError` 并附带提示；
`client.account.get()` 是最省事的检查方式。

## 服务

| 服务              | CLI 分组      | 方法                                                                                                                                                              |
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

必需的输入以位置参数传入（`client.domains.info("example.com")`），可选输入以关键字参数传入
（`client.domains.list(statuses=[DomainStatus.ACTIVE], limit=50)`）。枚举参数接受枚举值本身、
任意大小写的 API 名称或其编号：`DomainStatus.ACTIVE`、`"active"` 和 `0` 是等价的。

## 用法

以下所有代码片段均假定已有 `import domainnameapi as dna` 和一个 `client`。

### 搜索

```python
a = client.domains.search("example.com")
# a.available, a.price, a.currency, a.is_premium, a.is_document_required, a.reason

for r in client.domains.bulk_search(["example.com", "example.net", "example.org"]):
    print(r.domain_name, r.status, r.price)
```

`bulk_search` 会把超过 30 个域名的列表拆分为多个请求。价格使用账户的币种，或使用
`dna.Client(..., currency="TRY")` 或 `search(..., currency="TRY")` 设置的币种。

### 注册

使用联系人句柄（用 `contacts.create` 创建）：

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
    handles=handle,  # 一个句柄用于全部四种角色，或 dna.ContactHandles(registrant="DNA-1", admin="DNA-2", ...)
)
```

使用内联联系人：

```python
res = client.domains.register_with_contacts(
    "example.com",
    name_servers=["ns1.example.net", "ns2.example.net"],
    contacts=owner,  # 一个 Contact 用于全部四种角色，或 dna.DomainContacts(registrant=owner, admin=admin, ...)
)
```

联系人信息在发送前会先整理：字段会去除首尾空白，国家代码转为大写，电话字段只保留
数字（`"+90 (555) 123-45-67"` 可以直接使用）。部分 TLD 需要注册局属性：用
`client.products.tld("com.tr").required_attributes` 查找，并以 `tld_attributes={...}` 传入。

如果 API 有响应但拒绝了请求（`"success": false`），该方法会抛出 `dna.OperationError`，
其中带有 API 的消息。

### 续费、转入、恢复

```python
check = client.domains.renew_check("example.com", 1)  # check.renewable, check.premium_price
res = client.domains.renew("example.com", 1)

tc = client.domains.transfer_check("example.com", "auth-code")  # tc.transferable, tc.auth_code_valid
res = client.domains.transfer("example.com", "auth-code")
st = client.domains.transfer_status("example.com")

client.domains.restore("example.com")  # 在赎回期内
```

### 域名详情与域名列表

```python
d = client.domains.info("example.com")
print(d.status, d.expiration_date, d.remaining_days, d.locked, d.name_servers, d.auth_code)
owner = d.contact(dna.ContactType.REGISTRANT)
if owner:
    print(owner.email)

# 单页
page = client.domains.list(limit=50)
print(page.total_count, [d.domain_name for d in page])

# 所有域名；分页在你迭代时自动获取
for d in client.domains.all(statuses=[dna.DomainStatus.ACTIVE]):
    print(d.domain_name, d.expiration_date)
```

### 锁定、隐私保护、域名服务器、子域名服务器

```python
client.domains.lock("example.com")
client.domains.unlock("example.com")
client.domains.set_privacy("example.com", True)
code = client.domains.update_auth_code("example.com")

client.domains.set_name_servers("example.com", ["ns1.example.net", "ns2.example.net"])
# dnssec_mode=dna.DNSSECMode.DISABLE  # 仅适用于已启用 DNSSEC 签名的域名

client.domains.add_host("example.com", "ns1.example.com", ["192.0.2.10", "2001:db8::10"])  # 自动识别 IP 版本
client.domains.delete_host("example.com", "ns1.example.com")
```

### 域名的联系人

```python
client.domains.set_contact_handles("example.com", dna.ContactHandles(admin="DNA-2", tech="DNA-2"))
client.domains.update_contacts("example.com", dna.DomainContacts(billing=billing))

details = client.contacts.get("DNA-1")            # 联系人及其验证状态
result = client.contacts.update("DNA-1", contact)  # 更新所有使用该句柄的域名
```

### DNS 区域

```python
client.dns.add("example.com", "www", dna.RecordType.A, "192.0.2.10", ttl=600)
client.dns.update("example.com", "www", "A", ["192.0.2.20"])  # 替换该记录集的所有值
client.dns.delete("example.com", "www", "A", "192.0.2.20")

for s in client.dns.list("example.com"):
    print(s.name, s.type, s.ttl, s.values)

www = client.dns.find("example.com", "www", "A")  # 一个记录集，或 None
res = client.dns.apply("example.com")             # 将域名切换到平台的域名服务器
```

名称可以是相对名称（`www`）、根域（`""` 或 `"@"`）或完全限定名称。此处记录类型不区分
大小写（`"txt"` 会作为 `TXT` 发送）。校验会拦截 API 会拒绝的内容：根域上的 CNAME、
不足三个部分的 CAA 值、缺少优先级的 MX 值。测试环境对每个区域调用都返回 HTTP
500，因此区域相关代码只能在生产环境中试用。

### DNSSEC

```python
results = client.dnssec.add("example.com", "2371 13 2 1F987CC6583E92DF0890718C42...")  # 与你的 DNS 提供商显示的格式一致
info = client.dnssec.get("example.com")  # info.status, info.ds_records
res = client.dnssec.disable("example.com")
```

`dna.DS.parse(...)` 可解析呈现格式，包括整行的区域文件记录。

### URL 转发

```python
client.domains.set_forwarding("example.com", "https://www.example.org", dna.ForwardType.STANDARD)
f = client.domains.forwarding("example.com")  # 域名没有转发时为 None
client.domains.delete_forwarding("example.com")
```

### 注册局文档 (.tr)

```python
doc = dna.DocumentUpload.from_file(dna.DocumentType.IDENTITY_CARD, "id.pdf")
res = client.domains.upload_documents("example.com.tr", doc)
page = client.domains.documents("example.com.tr")
```

文件会自动进行 base64 编码；上传前会检查格式（PDF、JPG、PNG、DOC、DOCX、ODT）和大小（每个文件 10 MB，每次
请求 50 MB）。

### SSL 证书

```python
csr = client.ssl.generate_csr("example.com", country="TR", state="Istanbul", locality="Istanbul",
                              organization="Example Ltd", organization_unit="IT")
client.ssl.initialize("example.com", "PositiveSSL")  # 从余额中扣费
client.ssl.configure("example.com", csr=csr.csr, approver_mail="admin@example.com",
                     authentication_type=dna.AuthenticationType.EMAIL,
                     web_server_type=dna.WebServerType.APACHE, contact=ssl_contact)
st = client.ssl.status("example.com")  # 轮询直到 st.is_issued
cert = client.ssl.content("example.com")
open("example.com.crt", "w").write(cert.chain)
```

### 主机托管

```python
packages = client.hosting.packages()
created = client.hosting.create("example.com", "Linux-Starter")  # 从余额中扣费

st = client.hosting.wait(created.service_id, timeout=30 * 60)  # 轮询直到激活
print(st.panel_address, st.username, st.password)
```

对于仍在开通中的主机托管，切勿再次调用 `create`：这会重复扣费。

### 余额、价格与订单

```python
account = client.account.get()
usd = account.balance("USD")

for tx in client.account.all_transactions(since=month_start):
    print(tx.creation_time, tx.type, tx.change)

tld = client.products.tld("com.tr")
if tld:
    print(tld.name, tld.register_price(1))

info = client.products.info("com", dna.OrderType.RENEW, 2)  # .com 续费 2 年的价格
order = client.orders.get("ORDER-CODE")
```

## 请求与 BaseRequest

每个 API 操作都是一个请求类：`DomainInfoRequest`、`DNSAddRequest`、`SSLConfigureRequest` 等。它们
都派生自 `dna.BaseRequest`，后者提供默认实现（无查询字符串、无请求体、无需校验）。
请求通过类属性声明自己要发往何处，并按需覆盖其他成员。本包中的一个请求如下所示：

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

| 成员          | 默认值         | 含义                                                                                |
|---------------|----------------|-------------------------------------------------------------------------------------|
| `method`      | `"GET"`        | HTTP 方法                                                                           |
| `path`        | `""`           | 基础 URL 之下的路径；`{placeholders}` 由属性填充并经过转义                          |
| `safety`      | `Safety.READ`  | `READ`、`WRITE`、`DESTRUCTIVE` 或 `BILLABLE`                                        |
| `idempotent`  | `False`        | 可安全发送两次（读取操作始终如此）；只有这类请求会在网络错误后重试                  |
| `response`    | `None`         | 响应的解码方式：`Model` 子类、`list_of(...)`、`page_of(...)` 或原始 JSON            |
| `query()`     | `None`         | 查询参数：字典或键值对列表                                                          |
| `body()`      | `None`         | JSON 请求体                                                                         |
| `validate(v)` | 无             | 用 `v.required`、`v.between`、`v.check` 等记录问题；一旦有问题就不会发送任何内容    |

服务方法会为你构建这些请求。`client.send(request)` 可以发送任何请求，包括你自己的类，例如
只读取所需的字段，或调用本包尚未封装的端点：

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

你的请求享有内置请求的全部能力：凭据、重试、节奏控制、错误规范化、
关联 ID、追踪以及只读强制。`client.send_with_response(request)` 还会返回状态码、
响应头、关联 ID、配额和尝试次数；`client.prepare(request)` 会构建出确切的 HTTP
请求但不发送，便于在计费请求发出之前记录或审查。模型会把解码后的 JSON 保留在 `.raw` 中，
供本包尚未建模的字段使用。

## 错误

所有异常都派生自 `dna.DomainNameAPIError`，并带有 `kind`。

| 异常                          | 触发时机                                                   | 常用属性                                                            |
|-------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| `InputError`（一种 `ValueError`） | 校验拒绝了请求；**没有发送任何内容**                       | `request`, `fields`                                                 |
| `APIError` 及其子类           | API 返回了非 2xx 状态码                                    | `status_code`, `code`, `message`, `details`, `fields`, `data`, `correlation_id`, `hint` |
| `OperationError`              | API 返回 2xx，但带有 `"success": false`                    | `code`, `message`, `correlation_id`                                 |
| `NetworkError`                | 请求未完成（DNS、TLS、超时、连接重置）                     | `timeout`, `__cause__`                                              |
| `ReadOnlyError`               | 只读客户端阻止了变更；没有发送任何内容                     | `request`, `safety`                                                 |

`APIError` 的子类可区分常见情形：`AuthenticationError`、`NotFoundError`、
`ValidationError`、`RejectedError`（含 `InsufficientBalanceError`）、`ConflictError`、`RateLimitError` 和
`ServerError`。

```python
try:
    client.domains.renew("example.com", 1)
except dna.InsufficientBalanceError:
    ...  # 先充值
except dna.NotFoundError as err:
    print(err.hint)
except dna.OperationError as err:
    print("refused:", err.message)
except dna.DomainNameAPIError as err:
    if err.outcome_unknown:
        ...  # 续费可能已经成功：再次尝试之前先检查该域名
    elif err.code == dna.ErrorCode.PRIVACY_NOT_SUPPORTED:
        ...
    else:
        raise
```

请根据 `code` 而不是 `message` 来分支处理：消息是本地化的。API 错误码形如
`Dna.DomainService:Domain:10007`；参见[错误参考](https://www.domainnameapi.com/docs/reference/errors.md)。
`err.kind` 是 `ErrorKind.AUTH`、`NOT_FOUND`、`VALIDATION`、`REJECTED`、`CONFLICT`、`RATE_LIMITED`、
`SERVER`、`NETWORK`、`INVALID_INPUT`、`READ_ONLY` 之一。联系支持团队时请提供 `correlation_id`。

## 安全与可靠性

- **安全级别。** 每个请求都属于 `READ`、`WRITE`、`DESTRUCTIVE` 或 `BILLABLE`
  （`request.endpoint().safety`）。部分 POST 和 PUT 请求实际上是读取操作（`DomainSearchRequest`、`SSLStatusRequest`）。
- **只读模式。** `dna.Client(..., read_only=True)` 会阻止所有非读取操作，适用于报表任务，也适合
  安全地探索生产环境。
- **重试。** 429 响应总是会被重试，并遵循 `Retry-After`：API 在处理任何内容之前就拒绝了这类请求。
  网络错误和 502/503/504 仅对读取操作和幂等的写入操作重试，因此注册
  或续费绝不会被发送两次。计费请求失败后，请检查 `err.outcome_unknown`。
- **节奏控制。** 客户端会控制请求间隔，使其低于每个密钥的限制（每秒 5 个请求、每秒 2 次搜索、
  每秒一次区域调用）。如果你自行控制节奏，可用 `pacing=False` 将其关闭。
- **配额。** `send_with_response(...).quota` 暴露软配额响应头。超出限制时，API 会放慢响应（最多
  5 秒）而不是拒绝请求；默认的 60 秒超时为此留有余地。
- **关联 ID。** 每个请求都带有 `X-Correlation-ID`。可用
  `with dna.correlation_id("order-4711"): ...` 设置你自己的值，以便将 API 调用与你的日志关联起来。
- **可观测性。** 交互会记录到 `domainnameapi` 日志记录器（请求和响应为 DEBUG 级别，
  重试为 WARNING 级别）；`trace=callback` 会把每个请求、响应和重试以 `TraceEvent` 的形式交给你，
  用于指标或错误上报。其中绝不包含 API key。
- **线程。** `Client` 可在线程之间安全共享。创建一个并重复使用即可。
- **宽容的解码。** 不带时区的日期、`null`、用 `[]` 代替 `{}`、以字符串形式发送的数字、数字或名称形式的状态，以及
  任意大小写的角色（`"registrant"`、`"ADMINISTRATIVE"`）都可以解码。本包尚未识别的值
  绝不会导致响应解码失败。

## 客户端选项

| 选项                            | 作用                                                                                     |
|---------------------------------|------------------------------------------------------------------------------------------|
| `environment="ote"`             | 使用测试环境（默认为 `"production"`）                                                    |
| `base_url=url`                  | 将请求发送到代理或测试服务器                                                             |
| `timeout=60`                    | 每次 HTTP 尝试的超时秒数                                                                 |
| `retries=2`                     | 重试次数                                                                                 |
| `pacing=False`                  | 关闭客户端节奏控制                                                                       |
| `read_only=True`                | 阻止所有非读取请求                                                                       |
| `currency="TRY"`                | 搜索价格与目录价格的币种                                                                 |
| `user_agent="app/1.0"`          | 将你的产品名放在 User-Agent 前面                                                         |
| `transport=...`                 | 你自己的 HTTP 层（`requests`、`httpx`、代理等）；参见 `domainnameapi.transport`          |
| `trace=fn`                      | 观察每个请求、响应和重试                                                                 |
| `logger=logging.getLogger(...)` | 将交互记录到另一个日志记录器                                                             |

默认传输层使用 `urllib`，并遵循 `HTTPS_PROXY` 等变量。若要使用你自己的 CA 证书包，请传入
`transport=dna.UrllibTransport(ssl_context=ctx)`。

## 测试你的代码

`domainnameapi.testing.FakeTransport` 会记录请求并以预设的回复作答；其他部分都不需要
mock：

```python
from domainnameapi.testing import FakeTransport, api_error, ok

fake = FakeTransport(
    ok({"success": True, "info": {"domainName": "example.com", "status": "AVAILABLE", "price": 11.99}}),
    api_error(404, dna.ErrorCode.DOMAIN_NOT_FOUND, "Domain not found"),
)
client = fake.client()  # 使用该假传输层的 Client，已关闭节奏控制

assert client.domains.search("example.com").available
assert fake.last.json() == {"domainName": "example.com"}
with pytest.raises(dna.NotFoundError):
    client.domains.info("missing.com")
```

## 从 v1 迁移

v2 是全新的设计：用类型化的结果取代字典，用异常取代 `{"result": "ERROR"}`
信封，并提供完整的 REST API，而不再只是 php-dna 的方法集合。在你完成切换之前，
可固定 `domainnameapi<2` 以继续使用 v1。

| v1                                                  | v2                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------|
| `DomainNameAPI(id, key, test_mode=True)`            | `Client(id, key, environment="ote")`                                   |
| `res["result"] == "OK"`                             | 没有异常                                                               |
| `get_reseller_details`, `get_current_balance`       | `account.get()` (+ `account.balance("USD")`)                           |
| `check_availability`                                | `domains.search`, `domains.bulk_search`                                |
| `get_list`                                          | `domains.list`, `domains.all`                                          |
| `get_tld_list`                                      | `products.tlds`, `products.all_tlds`, `products.tld`                   |
| `get_details`, `get_contacts`, `sync_from_registry` | `domains.info`                                                         |
| `register_with_contact_info`                        | `domains.register_with_contacts`（或 `contacts.create` + `domains.register`） |
| `renew`, `transfer`, `check_transfer`               | `domains.renew`, `domains.transfer`, `domains.transfer_check`          |
| `modify_name_server`                                | `domains.set_name_servers`                                             |
| `enable_theft_protection_lock` / `disable_...`      | `domains.lock` / `domains.unlock`                                      |
| `modify_privacy_protection_status`                  | `domains.set_privacy`                                                  |
| `save_contacts`                                     | `domains.update_contacts`, `domains.set_contact_handles`               |
| `add_child_name_server`, `modify_child_name_server`, `delete_child_name_server` | `domains.add_host`, `domains.update_host`, `domains.delete_host` |
| `get_resource_records`                              | `dns.list`, `dns.find`                                                 |
| `add_resource_record`, `add_resource_record_value`  | `dns.add`                                                              |
| `edit_resource_record`, `set_resource_record_set`, `replace_resource_record_value` | `dns.update`                            |
| `delete_resource_record`, `remove_resource_record_value`, `delete_resource_record_set` | `dns.delete`（每个值调用一次）      |
| `apply_resource_records`                            | `dns.apply`                                                            |
| `get_forwarding`, `set_forwarding`, `delete_forwarding` | `domains.forwarding`, `domains.set_forwarding`, `domains.delete_forwarding` |
| `cancel_transfer`, `approve_transfer`, `reject_transfer` | 不在已发布的 API 中；如果你的账户支持这些操作，请发送[你自己的请求](#请求与-baserequest) |
| `is_tr_tld`, `validate_contact`                     | `name.endswith(".tr")`；每个请求都会执行校验                           |
| `get_request_data`, `get_response_data`, ...        | `trace=`、`domainnameapi` 日志记录器、`send_with_response`             |
| 遥测 (`set_error_reporting_enabled`, Sentry)        | 已移除：不会有任何数据离开你的进程；请将 `trace` 事件转发到你自己的上报系统 |
| `set_ssl_verification(False)`                       | `transport=UrllibTransport(ssl_context=...)` 搭配你自己的 TLS 设置     |

## 开发

```bash
python -m unittest discover -s tests -v   # 或：python -m pytest
python -m build                            # sdist 和 wheel
```

测试从不调用真实的 API。`tests/testdata/openapi.json` 是 API 的 OpenAPI 文档，与
`dna` CLI 内嵌的是同一份。测试会对照它检查每个请求类（方法、
路径、查询参数名、请求体字段、必填字段）、每个响应模型的 JSON 字段名是否符合响应
schema，以及每个枚举值；当 API 新增了没有对应请求类的操作时，测试会失败。更新方法：

```bash
curl -fsSL -A "python-dna-spec-update" -o tests/testdata/openapi.json https://api.domainresellerapi.com/swagger/v1/swagger.json
python -m unittest discover -s tests
```

本仓库的约定请参见 [AGENTS.md](AGENTS.md)。

## 支持

- API 文档：<https://www.domainnameapi.com/docs/>
- CLI 与 MCP 服务器：<https://github.com/domainreseller/cli>
- 网站：<https://www.domainnameapi.com>

## 许可证

Apache License 2.0。参见 [LICENSE](LICENSE)。
