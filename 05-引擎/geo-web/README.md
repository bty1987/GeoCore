# geo-web

GEO 业务的 Web 工具集（纯前端、无后端、单文件 SPA 风格）。

## 文件与部署分级

| 文件 | 用途 | 可否公开部署 |
|---|---|---|
| `index.html` | 分析流程演示版（AI 未接入，全模拟数据，页面带演示徽标） | 可 |
| `quotation.html` | 客户版在线询价（选方案/平台/周期 → 零售价 + 复制询价链接） | 可 |
| `quotation-config.js` | 客户侧配置（品牌/联系方式/零售价/市场参考价/选项） | 可 |
| `quotation-dealer.html` | 渠道版报价助手（底价/毛利/提成测算 + 量阶梯 + 口令帘） | **禁止** |
| `quotation-dealer.config.js` | 渠道底价配置（底价/阶梯/提成/口令） | **禁止** |

**部署红线：公网只上传前三行白名单文件。** 渠道版两件绝不随公网部署、不发给客户；口令帘只是防随手点开，不是安全机制。底价与真实成本口径只存在于仓库与渠道私发件中。

## 本地预览

```bash
cd 05-引擎/geo-web && python3 -m http.server 8777
# 演示版   http://127.0.0.1:8777/index.html
# 客户询价 http://127.0.0.1:8777/quotation.html
# 渠道助手 http://127.0.0.1:8777/quotation-dealer.html（口令在 quotation-dealer.config.js）
```

## 上线前占位符清单

- `quotation-config.js`：`brand`、`brandSub`、`contact.wechat`、`contact.phone`（全部带【】标记）
- `quotation-dealer.config.js`：`pin`（渠道口令，默认 6800，上线前必改）
- 调价只改配置文件，两个页面自动生效；客户版页面永远不出现"底价"

## 客户版 URL 参数协议

客户点"复制询价信息"得到的链接自带配置，发回给销售即可还原客户所选：

```
?plan=std|lite|rpt&p=doubao,qianwen&c=m|q&ind=<行业>&city=<城市>
```

## 测试钩子

页面控制台：客户版 `window.Q`（`state`/`calc`/`buildLink`/`summaryText`）；渠道版 `window.D`（`state`/`calc`）。算价规则：季付 = 月价 ×3 − 季付立减；多平台 = 基础价 + (N−1)×加 platform 价；渠道档位见配置 tiers。

## 改版记录

- 2026-09-22：新增报价工具（客户版 + 渠道版 + 双配置文件防底价泄漏）。设计语言沿用主蓝 #3B7BFF / 底 #F7F8FA 渐变头。
