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
- 东方财富公开行情：网页端继续直接刷新可访问的公开行情。

## 当前模块

- 资产速览
- 全球市场快照
- 主题热力
- AAPL 60日行情
- ETF动能
- 全球AI大模型价格与算力研究表
- AI产业链实时资产表
- 宏观、利率、汇率与商品
- 跨资产新闻线索
- 支撑数据集与 API 状态

## 关键文件

- `index.html`：GitHub Pages 首页。
- `资产配置Dashboard_单文件版.html`：同版单文件页面。
- `data/latest.json`：公开数据快照。
- `data/latest.js`：给本地双击 HTML 使用的公开数据快照。
- `scripts/fetch_data.py`：本地和 GitHub Actions 共用的数据抓取脚本。
- `.github/workflows/update-data.yml`：定时更新数据。
- `.github/workflows/deploy-pages.yml`：部署 GitHub Pages。
