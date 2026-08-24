# 全球资产配置监控台

面向资产配置分析师的跨资产 dashboard，覆盖 A股/港股/美股、ETF、利率、汇率、商品、AI 产业链、AI 模型价格和新闻线索。页面主体是静态 HTML，适合放到 GitHub Pages 做公开成果展示。

## 如何打开

### 本机查看

双击 `打开网站.bat`：脚本会先尝试运行 `scripts/fetch_data.py` 刷新公开数据，然后用 Microsoft Edge 打开 `index.html`。

双击 `打开单文件版.bat`：直接用 Microsoft Edge 打开 `index.html`，使用上一次保存的数据快照。

### GitHub Pages

推荐仓库名：`asset-allocation-dashboard`

发布后固定访问地址通常是：

`https://ronkee520.github.io/asset-allocation-dashboard/`

GitHub Actions 会每 4 小时尝试刷新一次 `data/latest.json` 和 `data/latest.js`。网页只读取生成后的公开数据文件，不会读取 API Key。

## API Key 安全

本地密钥文件夹 `APIkey与使用文档（链接）汇总/` 已加入 `.gitignore`，不会进入公开仓库。

在 GitHub 仓库中需要把 Key 放到 `Settings -> Secrets and variables -> Actions -> New repository secret`：

- `FMP_API_KEY`
- `FRED_API_KEY`
- `EIA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `TWELVE_DATA_API_KEY`

GDELT 不需要 API Key。

## 数据更新策略

- GitHub Actions：每 4 小时运行一次。
- FMP：逐个抓取少量核心资产，控制在免费额度内。
- FRED/EIA：宏观与能源低频数据，失败时保留上一版缓存。
- Alpha Vantage/GDELT：新闻线索，标题可跳转原文。
- Yahoo Finance 公共行情端点：提供六个月 ETF 日线，用于跨资产动量和相关性。
- ETF 发行商官网：读取 SPY、GLD、TLT、EWH、BOTZ 的 NAV 与流通份额，保存最近 31 个交易日快照。
- 模型价格：定时读取各厂商官方价格页；页面不可访问时保留最近缓存或经核验的官方基准。

### ETF 资金流口径

`估算净申赎 = 相邻两个交易日的流通份额变化 × 当日 NAV`

该口径使用 State Street、iShares、Global X 的公开基金数据，可反映 ETF 一级市场创建/赎回，不需要 Choice 或 Wind。它不等同于二级市场成交方向，也无法拆分具体机构；全市场历史、机构维度和盘中申赎仍适合使用商业数据源。

### 数据纪律

- 行情、宏观、能源、汇率、新闻和发行商份额均保留来源链接及数据源状态。
- `online` 表示本轮抓取成功，`cached` 表示本轮失败并沿用上一版，`fallback` 表示没有可用历史缓存。
- 资产打分、宏观象限、产业链强度属于模型输出，不代表收益承诺或投资建议。

## 当前模块

- 全球资产配置总览与八类资产相对打分
- 增长 × 通胀宏观四象限
- 20/60 日跨资产相关性与轮动
- 全球市场与 ETF 成交动能
- ETF 发行商份额及净申赎估算
- AI 产业链景气框架与全球模型 Token 价格
- 全球事件月历、宏观底表和可回溯新闻
- 收藏、搜索、可拖拽工作区及晨报导出

## 关键文件

- `index.html`：GitHub Pages 首页。
- `资产配置Dashboard_单文件版.html`：同版单文件页面。
- `data/latest.json`：公开数据快照。
- `data/latest.js`：给本地双击 HTML 使用的公开数据快照。
- `scripts/fetch_data.py`：本地和 GitHub Actions 共用的数据抓取脚本。
- `.github/workflows/update-data.yml`：定时更新数据。
- `.github/workflows/deploy-pages.yml`：部署 GitHub Pages。
