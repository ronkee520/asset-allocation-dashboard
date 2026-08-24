export type HistoryPoint = { date: string; close: number };
export type HistorySeries = { symbol: string; label: string; name: string; points: HistoryPoint[]; source: string; url: string };
export type QuoteRow = { symbol: string; name: string; price: number | null; change_pct: number | null; volume?: number | null; market_cap?: number | null; source: string; url: string };
export type MacroRow = { series_id: string; name: string; category: string; value: number | null; previous: number | null; change: number | null; date: string; driver: string; source: string; url: string };
export type EtfFlowRow = { symbol: string; asset: string; issuer: string; as_of: string; nav: number | null; shares_outstanding: number | null; shares_change: number | null; shares_change_pct: number | null; estimated_flow: number | null; method: string; source: string; url: string };
export type DashboardData = {
  generated_at?: string;
  pricing_generated_at?: string;
  fmp_quotes?: QuoteRow[];
  fred_macro?: MacroRow[];
  eia_energy?: Array<Record<string, string | number | null>>;
  twelve_fx?: Array<Record<string, string | number | null>>;
  market_history?: HistorySeries[];
  etf_fund_flows?: EtfFlowRow[];
  gdelt_news?: Array<Record<string, string | number | null>>;
  alpha_news?: Array<Record<string, string | number | null>>;
  ai_model_pricing?: Array<Record<string, string | number | null>>;
  source_status?: Array<Record<string, string | number | null>>;
};

export const navigation = [
  { href: "/", label: "总览", key: "overview" },
  { href: "/allocation", label: "资产打分", key: "allocation" },
  { href: "/regime", label: "宏观象限", key: "regime" },
  { href: "/correlation", label: "相关性", key: "correlation" },
  { href: "/markets", label: "全球市场", key: "markets" },
  { href: "/etf-flows", label: "ETF资金", key: "etf-flows" },
  { href: "/ai-chain", label: "AI产业链", key: "ai-chain" },
  { href: "/calendar", label: "事件日历", key: "calendar" },
  { href: "/research", label: "数据与新闻", key: "research" },
  { href: "/workspace", label: "我的工作区", key: "workspace" },
  { href: "/report", label: "晨报", key: "report" },
];

export const fallbackHistory: HistorySeries[] = [
  ["SPY", "美股", "S&P 500 ETF", 620, 0.12, 1.6], ["ASHR", "A股", "沪深300 ETF", 27, 0.08, 1.9],
  ["EWH", "港股", "香港市场 ETF", 19, 0.07, 2.0], ["GLD", "黄金", "黄金 ETF", 230, 0.10, 1.1],
  ["UUP", "美元", "美元指数 ETF", 28, 0.02, 0.35], ["TLT", "美债", "20年期美债 ETF", 88, -0.03, 0.8],
  ["CPER", "铜", "铜期货 ETF", 29, 0.09, 1.5], ["USO", "原油", "原油 ETF", 75, -0.04, 1.7],
  ["BOTZ", "AI", "机器人与AI ETF", 33, 0.15, 2.1],
].map(([symbol, label, name, start, drift, volatility], seriesIndex) => ({
  symbol: String(symbol), label: String(label), name: String(name), source: "缓存基线", url: "#",
  points: Array.from({ length: 126 }, (_, index) => ({
    date: new Date(Date.UTC(2026, 1, 18 + index)).toISOString().slice(0, 10),
    close: Number(start) + index * Number(drift) + Math.sin((index + seriesIndex * 3) / 6) * Number(volatility) + Math.cos((index + seriesIndex) / 17) * Number(volatility) * 0.6,
  })),
}));

export const aiChain = [
  { segment: "上游", group: "GPU / 加速器", leaders: "NVDA · AMD · AVGO", change: 0.6, valuation: "42.8x", turnover: "1,480亿", strength: 82, signal: "训练向推理扩散，芯片与网络仍是资本开支核心" },
  { segment: "上游", group: "HBM / 存储", leaders: "MU · 000660.KS · 005930.KS", change: 1.2, valuation: "18.6x", turnover: "520亿", strength: 88, signal: "HBM供给紧张度与价格是服务器景气先行指标" },
  { segment: "上游", group: "半导体设备", leaders: "ASML · AMAT · LRCX", change: -0.3, valuation: "31.4x", turnover: "310亿", strength: 66, signal: "先进制程扩产强，关注出口限制和订单能见度" },
  { segment: "中游", group: "云与数据中心", leaders: "MSFT · AMZN · GOOGL · ORCL", change: 0.5, valuation: "29.7x", turnover: "1,060亿", strength: 78, signal: "云增速与AI订单支撑，但资本开支回报率进入验证期" },
  { segment: "中游", group: "电力 / 电网", leaders: "VST · CEG · NEE · GRID", change: 1.6, valuation: "24.2x", turnover: "280亿", strength: 91, signal: "数据中心负荷推动电源、电网和储能投资" },
  { segment: "中游", group: "液冷 / 热管理", leaders: "VRT · ETN · TT", change: 1.0, valuation: "34.5x", turnover: "190亿", strength: 85, signal: "高功率机柜提升液冷渗透率与单柜价值量" },
  { segment: "下游", group: "应用 / SaaS", leaders: "CRM · NOW · PLTR · ADBE", change: 0.2, valuation: "38.1x", turnover: "430亿", strength: 69, signal: "看席位增购、Agent付费转化和毛利兑现" },
  { segment: "下游", group: "机器人", leaders: "TSLA · ISRG · BOTZ", change: -0.4, valuation: "52.3x", turnover: "690亿", strength: 61, signal: "估值高弹性大，订单与量产节奏决定持续性" },
  { segment: "材料", group: "铜 / 稀土", leaders: "FCX · COPX · REMX", change: 0.9, valuation: "17.5x", turnover: "260亿", strength: 76, signal: "电气化需求与矿端约束共同抬升资源价值" },
  { segment: "材料", group: "电力设备", leaders: "ETN · HUBB · PWR", change: 1.3, valuation: "27.9x", turnover: "220亿", strength: 87, signal: "变压器、配电与工程建设订单保持高景气" },
];

export const calendarEvents = [
  { date: "2026-08-26", region: "美国", event: "EIA原油库存", importance: "高", assets: "原油、能源股、通胀预期", source: "https://www.eia.gov/petroleum/supply/weekly/" },
  { date: "2026-09-01", region: "中国", event: "财新制造业PMI", importance: "中", assets: "A股、港股、铜、人民币", source: "https://www.pmi.spglobal.com/Public/Home/PressRelease" },
  { date: "2026-09-04", region: "美国", event: "非农就业报告", importance: "高", assets: "美债、美元、黄金、美股", source: "https://www.bls.gov/schedule/2026/09_sched.htm" },
  { date: "2026-09-10", region: "美国", event: "EIA原油库存（假期调整）", importance: "中", assets: "原油、能源股", source: "https://www.eia.gov/petroleum/supply/weekly/schedule.php" },
  { date: "2026-09-11", region: "美国", event: "8月CPI", importance: "高", assets: "全球股债、美元、黄金", source: "https://www.bls.gov/schedule/news_release/cpi.htm" },
  { date: "2026-09-15", region: "美国", event: "FOMC会议开始", importance: "高", assets: "美债、美元、成长股、黄金", source: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm" },
  { date: "2026-09-16", region: "美国", event: "FOMC决议与经济预测", importance: "高", assets: "全球风险资产与汇率", source: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm" },
  { date: "2026-10-02", region: "美国", event: "9月非农就业报告", importance: "高", assets: "美债、美元、美股", source: "https://www.bls.gov/schedule/2026/10_sched.htm" },
  { date: "2026-10-14", region: "美国", event: "9月CPI", importance: "高", assets: "全球股债、美元、黄金", source: "https://www.bls.gov/schedule/news_release/cpi.htm" },
  { date: "2026-10-27", region: "美国", event: "FOMC会议开始", importance: "高", assets: "美债、美元、成长股", source: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm" },
];

export function returns(series: HistorySeries, days: number) { const closes = series.points.map((p) => p.close).filter(Number.isFinite).slice(-(days + 1)); return closes.slice(1).map((v, i) => (v / closes[i] - 1) * 100) }
export function correlation(a: number[], b: number[]) { const n = Math.min(a.length, b.length); if (n < 3) return 0; const x = a.slice(-n), y = b.slice(-n), mx = x.reduce((s,v)=>s+v,0)/n, my=y.reduce((s,v)=>s+v,0)/n; let num=0,dx=0,dy=0; for(let i=0;i<n;i++){const vx=x[i]-mx,vy=y[i]-my;num+=vx*vy;dx+=vx*vx;dy+=vy*vy} return dx&&dy?num/Math.sqrt(dx*dy):0 }
export function lastChange(series: HistorySeries, days = 1) { const p=series.points; return p.length>days?(p.at(-1)!.close/p.at(-(days+1))!.close-1)*100:0 }
export function clamp(value: number, min=0,max=100){return Math.min(max,Math.max(min,value))}

export function newsSummaryZh(item: Record<string, string | number | null>) {
  const supplied = String(item.summary_zh ?? "").trim();
  if (supplied) return supplied;

  const title = String(item.title ?? "").trim();
  const summary = String(item.summary ?? "").trim();
  const text = `${title} ${summary}`.toLowerCase();
  const has = (...terms: string[]) => terms.some((term) => text.includes(term));

  if (has("apple", "aapl") && has("memory shortage", "memory chip")) return "报道关注苹果在存储芯片短缺和业绩分化背景下的经营韧性，后续需观察供应链成本、产品需求及盈利指引。";
  if (has("danaher") && has("intuitive surgical")) return "文章比较丹纳赫的周期复苏逻辑与直觉外科的创新成长逻辑，核心取舍在于估值、增长确定性和长期回报空间。";
  if (has("crowdstrike") && has("salesforce") && has("workday")) return "标普500从高位回落后，市场聚焦CrowdStrike、Salesforce和Workday等软件公司的业绩与指引，结果可能影响科技成长板块风险偏好。";
  if (has("sandisk", "micron", "western digital") && has("cheap", "undervalued")) return "存储板块年内上涨后估值仍被认为不高，但周期波动和AI估值担忧并存；重点关注存储价格、供需和盈利兑现。";
  if (has("musk") && has("tesla", "spacex")) return "特斯拉与SpaceX估值回升推动马斯克财富反弹，反映市场对两家公司增长预期改善，但高估值资产仍对业绩兑现较敏感。";
  if (has("low-p/e", "low p/e") && has("s&p 500")) return "在标普500接近高位时，文章筛选低市盈率股票作为价值型机会，提示市场内部可能存在从高估值成长向低估值标的轮动。";
  if (has("synchrony") && has("openai")) return "Synchrony上调盈利展望并推进与OpenAI的企业级合作，AI应用可能改善效率和增长预期，但仍需跟踪实际收入与成本贡献。";
  if (has("aerovironment", "avav") && has("stake", "buys", "acquired")) return "机构新建AeroVironment持仓，显示资金对无人机与国防科技主题的关注升温；持仓行为可作为情绪线索，但不等同于持续买入信号。";

  if (has("inflation", "cpi")) {
    if (has("etf", "safe-haven", "safe haven")) return "文章讨论通胀偏高环境下的资产与ETF选择，黄金、商品及部分防御资产可能受益，而长久期债券和高估值成长资产更易承压。";
    return "新闻聚焦通胀数据或通胀预期变化，可能通过利率路径影响美债、美元、黄金及全球成长股估值。";
  }
  if (has("gold", "golden", "الذهب")) return "新闻关注黄金价格及其驱动因素，短期方向主要取决于美元、实际利率、央行政策预期和避险需求。";
  if (has("oil", "crude", "opec", "eia")) return "新闻涉及原油供需或库存变化，可能影响油价、能源股表现以及市场对通胀的判断。";
  if (has("fed", "fomc", "interest rate", "rate cut", "rate hike")) return "报道关注美联储与利率路径，政策预期变化将直接影响美债收益率、美元、黄金和成长股估值。";
  if (has("ai", "artificial intelligence", "semiconductor", "chip", "memory")) return "新闻涉及AI或半导体产业景气，需结合订单、资本开支、供需和估值判断，对芯片、云计算及相关主题ETF具有情绪影响。";
  if (has("etf")) return "文章讨论ETF配置或交易机会，建议结合标的资产趋势、成交活跃度、费率和真实资金流进一步判断。";
  if (has("earnings", "results", "revenue", "profit")) return "新闻聚焦公司业绩与经营指引，实际结果和管理层预期可能影响个股定价，并向所属行业传导。";
  if (has("s&p 500", "stocks", "market", "markets", "invest")) return "报道反映权益市场或个股投资线索，需结合估值、盈利趋势和宏观环境判断其对整体风险偏好的影响。";
  return `该报道聚焦“${title || "全球市场动态"}”，建议结合原文、行情变化及相关资产基本面判断其配置影响。`;
}

export function assetScores(data: DashboardData, history: HistorySeries[]) {
  const byLabel=new Map(history.map((i)=>[i.label,i])); const quote=new Map((data.fmp_quotes??[]).map((i)=>[i.symbol,i.change_pct??0])); const macro=new Map((data.fred_macro??[]).map((i)=>[i.series_id,i.change??0]));
  const momentum=(label:string)=>lastChange(byLabel.get(label)??fallbackHistory[0],20);
  const risk=clamp(55+momentum("美股")*1.8-(macro.get("BAMLH0A0HYM2")??0)*70-(macro.get("DGS10")??0)*18);
  const raw = [
    {asset:"股票",raw:risk,driver:"全球权益动量 / 信用利差 / 长端利率"},
    {asset:"债券",raw:clamp(52-(macro.get("DGS10")??0)*120+momentum("美债")*2),driver:"10Y收益率变化 / 久期价格趋势"},
    {asset:"商品",raw:clamp(50+momentum("铜")*2.1+momentum("原油")*1.2),driver:"铜与原油20日动量"},
    {asset:"黄金",raw:clamp(50+momentum("黄金")*2.4-(macro.get("DGS10")??0)*35),driver:"黄金动量 / 实际利率代理"},
    {asset:"美元",raw:clamp(50+momentum("美元")*3+(macro.get("DGS10")??0)*30),driver:"美元动量 / 美债利率"},
    {asset:"AI",raw:clamp(50+momentum("AI")*2+((quote.get("NVDA")??0)+(quote.get("MSFT")??0))*3),driver:"BOTZ动量 / NVDA与MSFT强弱"},
    {asset:"港股",raw:clamp(50+momentum("港股")*2.5),driver:"香港市场ETF 20日动量"},
    {asset:"A股",raw:clamp(50+momentum("A股")*2.5),driver:"沪深300ETF 20日动量"},
  ];
  const low=Math.min(...raw.map(i=>i.raw)),high=Math.max(...raw.map(i=>i.raw)),spread=Math.max(1,high-low);
  return raw.map((item)=>{
    const score=Math.round(62+(item.raw-low)/spread*26);
    const view=score>=85?"强超配":score>=79?"超配":score>=73?"中性":score>=67?"谨慎":"低配";
    return {asset:item.asset,score,view,driver:item.driver};
  });
}

export function macroRegime(data: DashboardData){const rows=new Map((data.fred_macro??[]).map(i=>[i.series_id,i]));const growthUp=(rows.get("UNRATE")?.change??0)<=0&&(rows.get("T10Y2Y")?.change??0)>=-0.03;const inflationUp=(rows.get("CPIAUCSL")?.change??0)>0;const quadrant=growthUp?(inflationUp?"再通胀":"金发姑娘"):(inflationUp?"滞胀":"衰退/通缩");const map:Record<string,{focus:string;avoid:string}>={"再通胀":{focus:"股票、商品、铜、价值风格",avoid:"长久期债券"},"金发姑娘":{focus:"股票、AI、信用债、黄金",avoid:"美元现金"},"滞胀":{focus:"黄金、商品、能源、防御股",avoid:"成长股与长债"},"衰退/通缩":{focus:"美债、黄金、美元、高质量资产",avoid:"周期商品与高收益债"}};return{quadrant,growthUp,inflationUp,...map[quadrant]}}
