export type HistoryPoint = { date: string; close: number };
export type HistorySeries = { symbol: string; label: string; name: string; points: HistoryPoint[]; source: string; url: string };
export type QuoteRow = { symbol: string; name: string; price: number | null; change_pct: number | null; volume?: number | null; market_cap?: number | null; source: string; url: string };
export type MacroRow = { series_id: string; name: string; category: string; value: number | null; previous: number | null; change: number | null; date: string; driver: string; source: string; url: string };
export type EtfFlowRow = { symbol: string; asset: string; asset_class?: string; region?: string; segment?: string; issuer: string; as_of: string; nav: number | null; shares_outstanding: number | null; shares_change: number | null; shares_change_pct: number | null; estimated_flow: number | null; flow_5d?: number | null; flow_20d?: number | null; aum?: number | null; flow_intensity?: number | null; method: string; source: string; url: string; data_status?: string; history?: Array<Record<string, string | number | null>> };
export type CommodityRow = { symbol:string; name:string; category:string; market:string; unit:string; price:number|null; volume?:number|null; as_of:string; change_1d:number|null; change_20d:number|null; change_60d:number|null; volatility_20d:number|null; range_percentile:number|null; range_low:number|null; range_high:number|null; source:string; source_type:string; url:string; history?:Array<{date:string;close:number;volume?:number|null}> };
export type CftcRow = { name:string; contract:string; as_of:string; open_interest:number|null; managed_money_long:number; managed_money_short:number; managed_money_net:number; weekly_change:number; net_pct_open_interest:number|null; source:string; frequency:string; url:string };
export type FundFlowRow = { category:string; value_usd:number; as_of:string; frequency:string; scope:string; source:string; url:string };
export type AiChainRow = { segment:string; group:string; constituents?:string; leaders:string; change:number; breadth?:number; relative_volume?:number; valuation_pe?:number|null; turnover_usd?:number; strength:number; signal:string; sample_size?:number; method?:string; as_of?:string };
export type CalendarEvent = { date:string; region:string; event:string; importance:string; assets:string; source:string; source_name?:string };
export type ScoreBacktestRow = { asset:string; symbol:string; sample_size:number; hit_rate_20d:number|null; avg_forward_return_20d:number|null; max_drawdown:number; current_percentile:number; history_days:number; method:string };
export type ScoreFactor = { key:string; bucket:string; label:string; observed:string; as_of:string; source:string; status:string; url:string; weight:number; percentile:number; contribution:number; logic:string; available:boolean };
export type AssetScore = { key:string; asset:string; group:"core"|"equity"; proxy:string; benchmark:string; score:number; percentile:number; view:string; confidence:number; driver:string; description:string; factors:ScoreFactor[]; positives:string[]; risks:string[] };
export type PringProxy = { symbol:string; name:string; weight:number; return20:number; return60:number; blended:number; date:string; source:string; status:string; url:string };
export type PringSignal = { label:string; value:number; return20:number; return60:number; direction:1|-1; agreement:number; expected:number; components:PringProxy[] };
export type PringStageFit = { stage:number; name:string; fit:number; pattern:readonly number[]; matched:number };
export type PringMacroCheck = { id:string; label:string; value:number|null; change:number|null; date:string; source:string; status:string; url:string; verdict:"支持"|"冲突"|"中性"; rationale:string };
export type CorrelationResult = { value:number; sampleSize:number; startDate:string; endDate:string };
export type DashboardData = {
  generated_at?: string;
  pricing_generated_at?: string;
  fmp_quotes?: QuoteRow[];
  fred_macro?: MacroRow[];
  eia_energy?: Array<Record<string, string | number | null>>;
  twelve_fx?: Array<Record<string, string | number | null>>;
  market_history?: HistorySeries[];
  commodity_market?: CommodityRow[];
  cftc_positions?: CftcRow[];
  etf_fund_flows?: EtfFlowRow[];
  ici_weekly_flows?: FundFlowRow[];
  tic_cross_border_flows?: FundFlowRow[];
  gdelt_news?: Array<Record<string, string | number | null>>;
  alpha_news?: Array<Record<string, string | number | null>>;
  ai_model_pricing?: Array<Record<string, string | number | null>>;
  ai_chain_metrics?: AiChainRow[];
  event_calendar?: CalendarEvent[];
  score_backtest?: ScoreBacktestRow[];
  source_status?: Array<Record<string, string | number | null>>;
};

export const navigation = [
  { href: "/", label: "总览", key: "overview" },
  { href: "/allocation", label: "资产打分", key: "allocation" },
  { href: "/regime", label: "普林格时钟", key: "regime" },
  { href: "/correlation", label: "相关性", key: "correlation" },
  { href: "/markets", label: "全球市场", key: "markets" },
  { href: "/etf-flows", label: "全球资金流", key: "etf-flows" },
  { href: "/ai-chain", label: "AI产业链", key: "ai-chain" },
  { href: "/calendar", label: "事件日历", key: "calendar" },
  { href: "/research", label: "大宗商品", key: "research" },
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

export function aiChainRows(data: DashboardData): AiChainRow[] { return data.ai_chain_metrics?.length ? data.ai_chain_metrics : aiChain.map(item=>({...item,valuation_pe:Number.parseFloat(item.valuation),turnover_usd:null as unknown as number})) }
export function eventRows(data: DashboardData): CalendarEvent[] { const today=new Date().toISOString().slice(0,10);const live=(data.event_calendar??[]).filter(item=>item.date>=today);return live.length?live:calendarEvents.filter(item=>item.date>=today) }

export function returns(series: HistorySeries, days: number) { const closes = series.points.map((p) => p.close).filter(Number.isFinite).slice(-(days + 1)); return closes.slice(1).map((v, i) => (v / closes[i] - 1) * 100) }
export function correlation(a: number[], b: number[]) { const n = Math.min(a.length, b.length); if (n < 3) return 0; const x = a.slice(-n), y = b.slice(-n), mx = x.reduce((s,v)=>s+v,0)/n, my=y.reduce((s,v)=>s+v,0)/n; let num=0,dx=0,dy=0; for(let i=0;i<n;i++){const vx=x[i]-mx,vy=y[i]-my;num+=vx*vy;dx+=vx*vx;dy+=vy*vy} return dx&&dy?num/Math.sqrt(dx*dy):0 }
export function correlationForSeries(a:HistorySeries,b:HistorySeries,days:number):CorrelationResult {
  if(a.symbol===b.symbol){const points=a.points.slice(-(days+1));return {value:1,sampleSize:Math.max(0,points.length-1),startDate:points[0]?.date??"-",endDate:points.at(-1)?.date??"-"}}
  const right=new Map(b.points.map(point=>[point.date,point.close])),common=a.points.filter(point=>right.has(point.date)).map(point=>({date:point.date,left:point.close,right:right.get(point.date)!})).slice(-(days+1));
  const leftReturns=common.slice(1).map((point,index)=>(point.left/common[index].left-1)*100),rightReturns=common.slice(1).map((point,index)=>(point.right/common[index].right-1)*100);
  return {value:correlation(leftReturns,rightReturns),sampleSize:leftReturns.length,startDate:common[0]?.date??"-",endDate:common.at(-1)?.date??"-"};
}
export function correlationUniverse(history:HistorySeries[]) {
  const definitions=[['SPY','美股'],['ASHR','A股'],['GLD','黄金'],['UUP','美元'],['AGG','债券'],['CPER','铜'],['USO','原油']] as const;
  return definitions.flatMap(([symbol,label])=>{const series=history.find(item=>item.symbol===symbol)??(symbol==='AGG'?history.find(item=>item.symbol==='TLT'):undefined);return series?[{...series,label:String(label)} as HistorySeries]:[]});
}
export function lastChange(series: HistorySeries, days = 1) { const p=series.points; return p.length>days?(p.at(-1)!.close/p.at(-(days+1))!.close-1)*100:0 }
export function clamp(value: number, min=0,max=100){return Math.min(max,Math.max(min,value))}

const scoreDefinitions = [
  { key:"equity", asset:"全球股票", group:"core" as const, symbols:["ACWI","SPY"], proxy:"ACWI / SPY", benchmark:"全球多资产", description:"全球股票核心仓位；优先采用ACWI，数据缺失时以SPY代表发达市场权益。" },
  { key:"bonds", asset:"债券", group:"core" as const, symbols:["AGG","TLT"], proxy:"AGG / IEF / TLT", benchmark:"全球股票", description:"综合债券配置方向；同时观察综合债、期限利率、通胀和信用压力，而非只代表长久期美债。" },
  { key:"commodities", asset:"商品", group:"core" as const, symbols:["DBC","CPER","USO"], proxy:"DBC / 商品篮子", benchmark:"全球股票", description:"黄金以外的大宗商品组合，覆盖能源、工业金属、农产品与黑色系的趋势和仓位。" },
  { key:"gold", asset:"黄金", group:"core" as const, symbols:["GLD"], proxy:"GLD", benchmark:"全球股票", description:"黄金战略与战术配置，重点观察实际利率、美元、资金申赎、仓位和价格趋势。" },
  { key:"usd", asset:"美元", group:"core" as const, symbols:["UUP"], proxy:"UUP / 美元广义指数", benchmark:"全球股票", description:"美元及现金类防御暴露，反映利差、避险需求和美元自身趋势。" },
  { key:"ai", asset:"AI", group:"equity" as const, symbols:["BOTZ","SOXX"], proxy:"BOTZ / SOXX", benchmark:"全球股票", description:"权益卫星方向，评价AI主题相对大盘的趋势、产业宽度、估值、资金流和利率敏感度。" },
  { key:"hk", asset:"港股", group:"equity" as const, symbols:["EWH"], proxy:"EWH", benchmark:"全球股票", description:"权益卫星方向，结合港股趋势、全球流动性、人民币环境与ETF资金流。" },
  { key:"china-a", asset:"A股", group:"equity" as const, symbols:["ASHR"], proxy:"ASHR", benchmark:"全球股票", description:"权益卫星方向，结合A股趋势、国内增长代理、人民币环境和中国股票ETF资金流。" },
] as const;

export const defaultPortfolioWeights: Record<string, number> = { equity:30, bonds:30, commodities:10, gold:10, usd:5, ai:5, hk:5, "china-a":5 };

function percentileRank(values:number[], current:number) {
  const clean=values.filter(Number.isFinite); return clean.length ? clean.filter(value=>value<=current).length/clean.length*100 : 50;
}
function rollingChanges(series:HistorySeries|undefined, days:number) {
  if (!series || series.points.length<=days) return [];
  return series.points.slice(days).map((point,index)=>(point.close/series.points[index].close-1)*100).filter(Number.isFinite);
}
function momentumFactor(series:HistorySeries|undefined, days:number) {
  const values=rollingChanges(series,days), current=values.at(-1)??0;
  return { value:current, score:percentileRank(values,current), available:Boolean(series&&values.length>=20), observed:`${current>=0?"+":""}${current.toFixed(2)}%`, asOf:series?.points.at(-1)?.date??"无数据", source:series?.source??"待更新", url:series?.url??"#" };
}
function volatilityFactor(series:HistorySeries|undefined) {
  if (!series || series.points.length<42) return { value:0,score:50,available:false,observed:"无数据",asOf:"无数据",source:"待更新",url:"#" };
  const daily=returns(series,series.points.length-1), windows:number[]=[];
  for(let index=19;index<daily.length;index++){const sample=daily.slice(index-19,index+1),mean=sample.reduce((sum,value)=>sum+value,0)/sample.length;windows.push(Math.sqrt(sample.reduce((sum,value)=>sum+(value-mean)**2,0)/sample.length)*Math.sqrt(252));}
  const current=windows.at(-1)??0;
  return { value:current,score:100-percentileRank(windows,current),available:windows.length>=20,observed:`${current.toFixed(1)}% 年化`,asOf:series.points.at(-1)?.date??"无数据",source:series.source,url:series.url };
}
function relativeFactor(series:HistorySeries|undefined, benchmark:HistorySeries|undefined) {
  if(!series||!benchmark) return {value:0,score:50,available:false,observed:"无数据",asOf:"无数据",source:"待更新",url:"#"};
  if(series.symbol===benchmark.symbol) return {value:0,score:50,available:true,observed:"基准资产",asOf:series.points.at(-1)?.date??"无数据",source:`${series.source}配置基准`,url:series.url};
  const asset=rollingChanges(series,20),base=rollingChanges(benchmark,20),length=Math.min(asset.length,base.length),values=asset.slice(-length).map((value,index)=>value-base.slice(-length)[index]),current=values.at(-1)??0;
  return {value:current,score:percentileRank(values,current),available:length>=20,observed:`${current>=0?"+":""}${current.toFixed(2)}pct`,asOf:series.points.at(-1)?.date??"无数据",source:`${series.source}相对强弱`,url:series.url};
}
function scaledScore(value:number|null|undefined, scale:number, direction=1){return Number.isFinite(value)?clamp(50+direction*Number(value)/scale*25):50}

export function assetScores(data: DashboardData, history: HistorySeries[]):AssetScore[] {
  const bySymbol=new Map(history.map(item=>[item.symbol,item])), macro=new Map((data.fred_macro??[]).map(item=>[item.series_id,item])), flows=data.etf_fund_flows??[], commodityRows=data.commodity_market??[], cftc=data.cftc_positions??[],statuses=new Map((data.source_status??[]).map(row=>[String(row.key),String(row.status??"unknown")]));
  const benchmark=bySymbol.get("ACWI")??bySymbol.get("SPY");
  const seriesFor=(symbols:readonly string[])=>symbols.map(symbol=>bySymbol.get(symbol)).find(Boolean);
  const flowFactor=(symbols:string[])=>{const selected=flows.filter(row=>symbols.includes(row.symbol)),all=flows.map(row=>Number(row.flow_intensity??(row.aum?Number(row.flow_5d??row.estimated_flow??0)/row.aum*100:null))).filter(Number.isFinite),value=selected.length?selected.reduce((sum,row)=>sum+Number(row.flow_intensity??(row.aum?Number(row.flow_5d??row.estimated_flow??0)/row.aum*100:0)),0)/selected.length:null;return {score:value===null?50:percentileRank(all,value),available:value!==null,observed:value===null?"无数据":`${value>=0?"+":""}${value.toFixed(3)}% AUM`,asOf:selected.map(row=>row.as_of).sort().at(-1)??"无数据",source:"基金公司公开份额 / NAV",url:selected[0]?.url??"#"};};
  const macroFactor=(ids:string[],scale:number,direction:number,label:string)=>{const rows=ids.map(id=>macro.get(id)).filter((row):row is MacroRow=>Boolean(row)),value=rows.length?rows.reduce((sum,row)=>sum+Number(row.change??0),0)/rows.length:null;return {score:scaledScore(value,scale,direction),available:value!==null,observed:value===null?"无数据":`${value>=0?"+":""}${value.toFixed(3)}`,asOf:rows.map(row=>row.date).sort().at(-1)??"无数据",source:`FRED · ${label}`,url:rows[0]?.url??"#"};};
  const positionFactor=(names:string[])=>{const rows=cftc.filter(row=>names.some(name=>row.name.includes(name))),values=cftc.map(row=>row.net_pct_open_interest).filter((value):value is number=>Number.isFinite(value)),value=rows.length?rows.reduce((sum,row)=>sum+Number(row.net_pct_open_interest??0),0)/rows.length:null;return {score:value===null?50:percentileRank(values,value),available:value!==null,observed:value===null?"无数据":`${value>=0?"+":""}${value.toFixed(1)}% OI`,asOf:rows.map(row=>row.as_of).sort().at(-1)??"无数据",source:"CFTC管理基金仓位",url:rows[0]?.url??"#"};};
  const chainBreadth=()=>{const rows=data.ai_chain_metrics??[],value=rows.length?rows.reduce((sum,row)=>sum+Number(row.breadth??50),0)/rows.length:null;return {score:value??50,available:value!==null,observed:value===null?"无数据":`${value.toFixed(0)}%成分上涨`,asOf:rows.map(row=>row.as_of??"").sort().at(-1)??"无数据",source:"AI产业链成分行情",url:"/ai-chain"};};
  return scoreDefinitions.map(definition=>{
    const series=seriesFor(definition.symbols),m20=momentumFactor(series,20),m60=momentumFactor(series,60),relative=relativeFactor(series,benchmark),vol=volatilityFactor(series);
    let macroInput=macroFactor(["DGS10","BAMLH0A0HYM2"],.2,-1,"利率与信用"); let thematic=flowFactor([...definition.symbols]); let thematicLabel="ETF资金流"; let thematicLogic="同批代表性ETF资金流强度的横向分位";
    if(definition.key==="bonds") macroInput=macroFactor(["DGS10","CPIAUCSL"],.2,-1,"利率与通胀");
    if(definition.key==="commodities"){macroInput=macroFactor(["INDPRO"],.5,1,"工业生产");thematic=positionFactor(["原油","铜","玉米","大豆","小麦"]);thematicLabel="管理基金仓位";thematicLogic="CFTC净仓占未平仓比例的跨品种分位";}
    if(definition.key==="gold"){macroInput=macroFactor([macro.has("DFII10")?"DFII10":"DGS10"],.2,-1,macro.has("DFII10")?"实际利率":"名义利率代理");thematic=positionFactor(["黄金"]);thematicLabel="黄金管理基金仓位";thematicLogic="CFTC黄金净仓占未平仓比例的跨品种分位";}
    if(definition.key==="usd") macroInput=macroFactor(["DGS2"],.2,1,"美国短端利率");
    if(definition.key==="ai"){macroInput=macroFactor([macro.has("DFII10")?"DFII10":"DGS10"],.2,-1,"长端折现率");thematic=chainBreadth();thematicLabel="AI产业宽度";thematicLogic="AI产业链各分组成分上涨比例均值";}
    if(definition.key==="hk"||definition.key==="china-a") macroInput=macroFactor(["INDPRO"],.5,1,"增长动能代理");
    const inputs=[
      {key:"trend20",bucket:"趋势",label:"20日趋势",weight:25,...m20,logic:"当前20日收益在该代理历史滚动20日收益中的分位"},
      {key:"trend60",bucket:"趋势",label:"60日趋势",weight:15,...m60,logic:"当前60日收益在该代理历史滚动60日收益中的分位"},
      {key:"macro",bucket:"宏观",label:"宏观适配度",weight:20,...macroInput,logic:"按公开宏观指标变化和预设风险方向映射；阈值与方向在模型说明中公开"},
      {key:"flow",bucket:"资金/仓位",label:thematicLabel,weight:15,...thematic,logic:thematicLogic},
      {key:"relative",bucket:"相对价值",label:"相对全球股票强弱",weight:15,...relative,logic:"代理资产20日收益减全球股票20日收益的历史分位"},
      {key:"risk",bucket:"风险",label:"波动率约束",weight:10,...vol,logic:"20日年化波动率历史分位取反，波动越低得分越高"},
    ];
    const factors:ScoreFactor[]=inputs.map(input=>{const sourceKey=input.key==="macro"?"fred_macro":input.key==="flow"?(definition.key==="commodities"||definition.key==="gold"?"cftc_positions":definition.key==="ai"?"ai_chain_quotes":"etf_fund_flows"):"market_history",status=statuses.get(sourceKey)??(input.available?"unverified":"missing");return {key:input.key,bucket:input.bucket,label:input.label,observed:input.observed,as_of:input.asOf,source:input.source,status,url:input.url,weight:input.weight,percentile:Math.round(input.score),contribution:Number((input.score*input.weight/100).toFixed(1)),logic:input.logic,available:input.available}});
    const quality=(status:string)=>status==="online"||status==="local"?1:["cached","baseline","unverified"].includes(status)?.7:.35,percentile=factors.reduce((sum,factor)=>sum+factor.contribution,0),score=Math.round(60+percentile*.3),coverage=factors.reduce((sum,factor)=>sum+(factor.available?factor.weight*quality(factor.status):0),0),confidence=Math.min(95,Math.round(coverage*(.65+Math.min(1,(series?.points.length??0)/756)*.35)));
    const sorted=factors.slice().sort((a,b)=>b.contribution-a.contribution),positives=factors.filter(factor=>factor.percentile>=60).sort((a,b)=>b.percentile-a.percentile).slice(0,3).map(factor=>`${factor.label} ${factor.percentile}分位`),risks=factors.filter(factor=>factor.percentile<=40).sort((a,b)=>a.percentile-b.percentile).slice(0,3).map(factor=>`${factor.label} ${factor.percentile}分位`);
    const view=score>=85?"强超配":score>=79?"超配":score>=73?"中性":score>=67?"谨慎":"低配";
    return {key:definition.key,asset:definition.asset,group:definition.group,proxy:definition.proxy,benchmark:definition.benchmark,score,percentile:Math.round(percentile),view,confidence,driver:`主要支撑：${sorted[0]?.label??"建立数据"}；主要约束：${factors.slice().sort((a,b)=>a.percentile-b.percentile)[0]?.label??"建立数据"}`,description:definition.description,factors,positives,risks};
  });
}

export function marketRiskAppetite(data:DashboardData,history:HistorySeries[]){
  const scores=assetScores(data,history),get=(key:string)=>scores.find(item=>item.key===key)?.percentile??50,factor=(key:string,names:string[])=>{const item=scores.find(score=>score.key===key),selected=item?.factors.filter(entry=>names.includes(entry.key))??[];return selected.length?selected.reduce((sum,entry)=>sum+entry.percentile,0)/selected.length:50},macro=new Map((data.fred_macro??[]).map(item=>[item.series_id,item])),equity=["equity","hk","china-a"].reduce((sum,key)=>sum+factor(key,["trend20","trend60"]),0)/3,credit=scaledScore(macro.get("BAMLH0A0HYM2")?.change,.2,-1),vol=volatilityFactor(history.find(item=>item.symbol==="ACWI")??history.find(item=>item.symbol==="SPY")).score,cycle=(factor("commodities",["trend20","trend60"])+equity)/2,usd=100-factor("usd",["trend20","trend60"]),riskFlows=(data.etf_fund_flows??[]).filter(row=>row.asset_class==="股票"&&row.estimated_flow!==null),flow=riskFlows.length?riskFlows.filter(row=>Number(row.estimated_flow)>0).length/riskFlows.length*100:50;
  const factors=[{label:"权益趋势与宽度",weight:25,value:equity},{label:"信用环境",weight:20,value:credit},{label:"波动率环境",weight:20,value:vol},{label:"周期资产强弱",weight:15,value:cycle},{label:"美元融资压力",weight:10,value:usd},{label:"风险ETF资金广度",weight:10,value:flow}].map(item=>({...item,value:Math.round(item.value),contribution:Number((item.value*item.weight/100).toFixed(1))})),score=Math.round(factors.reduce((sum,item)=>sum+item.contribution,0));
  return {score,label:score>=65?"风险偏好偏强":score<40?"风险偏好偏弱":"风险偏好中性",factors};
}

export function portfolioRiskAnalytics(weights:Record<string,number>,scores:AssetScore[],history:HistorySeries[]){
  const mapping:Record<string,string[]>={equity:["ACWI","SPY"],bonds:["AGG","TLT"],commodities:["DBC","CPER"],gold:["GLD"],usd:["UUP"],ai:["BOTZ"],hk:["EWH"],"china-a":["ASHR"]},keys=scoreDefinitions.map(item=>item.key),series=keys.map(key=>mapping[key].map(symbol=>history.find(item=>item.symbol===symbol)).find(Boolean)),daily=series.map(item=>item?returns(item,Math.min(252,item.points.length-1)):[]),length=Math.min(...daily.filter(item=>item.length).map(item=>item.length)),w=keys.map(key=>Number(weights[key]??0)/100),matrix=daily.map(item=>item.slice(-length).map(value=>value/100)),means=matrix.map(row=>row.reduce((sum,value)=>sum+value,0)/Math.max(1,row.length)),cov=matrix.map((row,i)=>matrix.map((other,j)=>row.reduce((sum,value,index)=>sum+(value-means[i])*(other[index]-means[j]),0)/Math.max(1,length-1))),portfolioReturns=Array.from({length},(_,day)=>matrix.reduce((sum,row,index)=>sum+(row[day]??0)*w[index],0)),variance=w.reduce((sum,wi,i)=>sum+wi*w.reduce((inner,wj,j)=>inner+wj*(cov[i]?.[j]??0),0),0),volatility=Math.sqrt(Math.max(0,variance))*Math.sqrt(252)*100;
  let wealth=1,peak=1,maxDrawdown=0;portfolioReturns.forEach(value=>{wealth*=1+value;peak=Math.max(peak,wealth);maxDrawdown=Math.min(maxDrawdown,(wealth/peak-1)*100)});
  const marginal=w.map((_,i)=>w.reduce((sum,wj,j)=>sum+wj*(cov[i]?.[j]??0),0)),rawRisk=w.map((wi,i)=>wi*marginal[i]),riskTotal=rawRisk.reduce((sum,value)=>sum+value,0),riskContributions=keys.map((key,index)=>({key,label:scoreDefinitions.find(item=>item.key===key)!.asset,value:riskTotal>0?rawRisk[index]/riskTotal*100:0})),allocationScore=scores.reduce((sum,item)=>sum+item.score*Number(weights[item.key]??0)/100,0),hhi=w.reduce((sum,value)=>sum+value*value,0)*100;
  return {allocationScore:Math.round(allocationScore),volatility:Number(volatility.toFixed(1)),maxDrawdown:Number(maxDrawdown.toFixed(1)),concentration:Number(hhi.toFixed(1)),riskContributions:riskContributions.sort((a,b)=>b.value-a.value),sampleDays:length,label:volatility>=18?"高风险":volatility>=11?"中高风险":volatility>=7?"中等风险":"稳健风险"};
}

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

export const pringStages = [
  { stage:1, name:"筑底", pattern:[1,-1,-1], focus:"债券、黄金、高质量资产", avoid:"周期商品与高贝塔股票" },
  { stage:2, name:"早期复苏", pattern:[1,1,-1], focus:"债券、股票、成长风格", avoid:"周期商品" },
  { stage:3, name:"全面复苏", pattern:[1,1,1], focus:"股票、商品、周期与小盘", avoid:"现金与纯防御资产" },
  { stage:4, name:"过热", pattern:[-1,1,1], focus:"商品、资源、价值与通胀受益资产", avoid:"长久期债券" },
  { stage:5, name:"滞胀", pattern:[-1,-1,1], focus:"商品、黄金、能源与防御股", avoid:"成长股与信用债" },
  { stage:6, name:"衰退", pattern:[-1,-1,-1], focus:"债券、美元、黄金与现金", avoid:"股票、工业品与高收益债" },
] as const;

export function pringCycle(data: DashboardData, history: HistorySeries[]) {
  const sourceStatuses=new Map((data.source_status??[]).map(item=>[String(item.key),String(item.status??"unknown")])),historyStatus=sourceStatuses.get("market_history")??"unverified",commodityStatus=sourceStatuses.get("commodity_market")??"unverified",macroStatus=sourceStatuses.get("fred_macro")??"unverified";
  const makeProxy=(symbol:string,name:string,weight:number):PringProxy|null=>{const series=history.find(item=>item.symbol===symbol);if(!series)return null;const return20=lastChange(series,20),return60=lastChange(series,60);return {symbol,name,weight,return20,return60,blended:return20*.35+return60*.65,date:series.points.at(-1)?.date??"-",source:series.source,status:historyStatus,url:series.url}};
  const makeSignal=(label:string,definitions:Array<[string,string,number]>,synthetic?:PringProxy):PringSignal=>{const components=definitions.map(item=>makeProxy(...item)).filter((item):item is PringProxy=>Boolean(item));if(synthetic)components.push(synthetic);const total=components.reduce((sum,item)=>sum+item.weight,0)||1,return20=components.reduce((sum,item)=>sum+item.return20*item.weight/total,0),return60=components.reduce((sum,item)=>sum+item.return60*item.weight/total,0),value=return20*.35+return60*.65,direction=(value>=0?1:-1) as 1|-1,agreement=components.reduce((sum,item)=>sum+(((item.blended>=0?1:-1)===direction)?item.weight:0),0)/total*100;return {label,value,return20,return60,direction,agreement,expected:0,components}};
  const commodityRows=data.commodity_market??[],commodity20=commodityRows.map(item=>item.change_20d).filter((value):value is number=>Number.isFinite(value)),commodity60=commodityRows.map(item=>item.change_60d).filter((value):value is number=>Number.isFinite(value)),basket20=commodity20.length?commodity20.reduce((sum,value)=>sum+value,0)/commodity20.length:0,basket60=commodity60.length?commodity60.reduce((sum,value)=>sum+value,0)/commodity60.length:0,basket:PringProxy|undefined=commodityRows.length?{symbol:"COMPOSITE",name:`公开商品篮子（${commodityRows.length}品种）`,weight:.2,return20:basket20,return60:basket60,blended:basket20*.35+basket60*.65,date:commodityRows.map(item=>item.as_of).sort().at(-1)??"-",source:"商品公开日线组合",status:commodityStatus,url:commodityRows[0]?.url??"#"}:undefined;
  const signals=[
    makeSignal("债券",[["AGG","综合债券 ETF",.5],["IEF","7-10年美债 ETF",.25],["TLT","长期美债 ETF",.25]]),
    makeSignal("股票",[["ACWI","全球股票 ETF",.4],["SPY","美国股票 ETF",.25],["ASHR","A股 ETF",.175],["EWH","港股 ETF",.175]]),
    makeSignal("商品",[["DBC","综合商品 ETF",.45],["CPER","铜 ETF",.2],["USO","原油 ETF",.15]],basket),
  ];
  const stageFits:PringStageFit[]=pringStages.map(stage=>{const componentFits=signals.map((signal,index)=>50+50*Math.tanh(stage.pattern[index]*signal.value/6)),fit=componentFits.reduce((sum,value)=>sum+value,0)/componentFits.length,matched=signals.filter((signal,index)=>signal.direction===stage.pattern[index]).length;return {stage:stage.stage,name:stage.name,fit:Number(fit.toFixed(1)),pattern:stage.pattern,matched}}).sort((a,b)=>b.fit-a.fit),current=pringStages.find(stage=>stage.stage===stageFits[0].stage)!,runnerUp=stageFits[1];
  const expectedPattern=[...current.pattern];signals.forEach((signal,index)=>signal.expected=expectedPattern[index]);
  const statusQuality=(status:string)=>status==="online"||status==="local"?100:["cached","baseline","unverified"].includes(status)?70:35,proxyQuality=signals.flatMap(signal=>signal.components).reduce((sum,item)=>sum+statusQuality(item.status),0)/Math.max(1,signals.flatMap(signal=>signal.components).length),agreement=signals.reduce((sum,signal)=>sum+signal.agreement,0)/signals.length,margin=Math.min(100,Math.max(0,(stageFits[0].fit-runnerUp.fit)*5)),confidence=Math.round(clamp(stageFits[0].fit*.45+agreement*.25+proxyQuality*.2+margin*.1,40,95));
  const macroMap=new Map((data.fred_macro??[]).map(item=>[item.series_id,item])),growthExpected=current.stage>=2&&current.stage<=4?1:-1,inflationExpected=current.stage>=3&&current.stage<=5?1:-1,creditExpected=current.stage>=2&&current.stage<=4?-1:1;
  const macroCheck=(ids:string[],label:string,expected:number,rationale:string):PringMacroCheck=>{const rows=ids.map(id=>macroMap.get(id)).filter((item):item is MacroRow=>Boolean(item)),changes=rows.map(item=>item.change).filter((value):value is number=>Number.isFinite(value)),change=changes.length?changes.reduce((sum,value)=>sum+value,0)/changes.length:null,value=rows[0]?.value??null,verdict=change===null||Math.abs(change)<1e-9?"中性":Math.sign(change)===expected?"支持":"冲突";return {id:ids.join("+"),label,value,change,date:rows.map(item=>item.date).sort().at(-1)??"-",source:rows.map(item=>item.source).filter(Boolean).join(" / ")||"待更新",status:macroStatus,url:rows[0]?.url??"#",verdict,rationale}};
  const macroChecks=[macroCheck(["INDPRO"],"工业生产",growthExpected,"检验实体增长方向"),macroCheck(["CPIAUCSL","PPIACO"],"通胀与上游价格",inflationExpected,"检验通胀方向"),macroCheck(["BAMLH0A0HYM2"],"高收益债利差",creditExpected,"检验信用扩张或压力"),macroCheck(["DGS10"],"美国10年期收益率",current.stage===4||current.stage===5?1:-1,"检验利率周期方向")];
  const actualPattern=signals.map(signal=>signal.direction),supports=signals.filter(signal=>signal.direction===signal.expected).map(signal=>`${signal.label}${signal.direction>0?"上行":"下行"}`),conflicts=signals.filter(signal=>signal.direction!==signal.expected).map(signal=>`${signal.label}${signal.direction>0?"上行":"下行"}`),asOf=signals.flatMap(signal=>signal.components.map(item=>item.date)).sort().at(-1)??"-";
  return {...current,confidence,fit:stageFits[0].fit,runnerUp,stageFits,signals,macroChecks,actualPattern,supports,conflicts,asOf,formula:"综合趋势 = 35% × 20日收益 + 65% × 60日收益；阶段拟合 = 三类资产方向模板的双曲正切相似度均值"};
}

export function macroRegime(data: DashboardData, history: HistorySeries[]=fallbackHistory){const cycle=pringCycle(data,history);return{quadrant:`阶段${cycle.stage} · ${cycle.name}`,growthUp:cycle.stage>=2&&cycle.stage<=4,inflationUp:cycle.stage>=3&&cycle.stage<=5,focus:cycle.focus,avoid:cycle.avoid}}
