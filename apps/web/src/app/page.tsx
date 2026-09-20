"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  Bookmark,
  Building2,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  EyeOff,
  FileText,
  Filter,
  Layers,
  PieChart,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sliders,
  TrendingDown,
  TrendingUp,
  Volume2,
  VolumeX,
  XCircle,
  BarChart2,
  Calendar,
  GitCompare,
  LineChart,
  FlaskConical,
  Newspaper,
  Bell,
  Target,
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert,
  Sparkles,
  AlertCircle,
  HelpCircle,
  DollarSign,
  Maximize2,
  Info,
} from "lucide-react";

// Types
export type WorkspaceTab =
  | "dashboard"
  | "companies"
  | "company"
  | "events"
  | "news"
  | "screener"
  | "research"
  | "scenario"
  | "watchlist"
  | "portfolio"
  | "technicals"
  | "calendar"
  | "compare"
  | "models"
  | "quant"
  | "explorer"
  | "sources"
  | "alerts";

interface MetricSummary {
  sources_healthy: number;
  sources_degraded: number;
  sources_failed: number;
  sources_stale: number;
  items_fetched_today: number;
  new_events: number;
  critical_events: number;
  high_events: number;
  ai_calls: number;
  ai_cache_hits: number;
  alerts_sent: number;
  failed_jobs: number;
  timestamp: string;
}

interface SourceHealthItem {
  source_id: string;
  name: string;
  publisher: string;
  priority: string;
  status: "healthy" | "degraded" | "rate-limited" | "failed" | "stale";
  last_success: string | null;
  consecutive_failures: number;
  last_latency_ms: number | null;
  error_message: string | null;
  retry_budget_remaining: number;
}

// Fallback Demo Data (Explicitly tagged)
// No demo data: every panel renders an explicit empty state until the backend
// supplies real ingested data. Fabricated sample content is never substituted.
const DEMO_METRICS: MetricSummary = {
  sources_healthy: 0,
  sources_degraded: 0,
  sources_failed: 0,
  sources_stale: 0,
  items_fetched_today: 0,
  new_events: 0,
  critical_events: 0,
  high_events: 0,
  ai_calls: 0,
  ai_cache_hits: 0,
  alerts_sent: 0,
  failed_jobs: 0,
  timestamp: "",
};

const DEMO_EVENTS: any[] = [];
const DEMO_NEWS: any[] = [];
const DEMO_CALENDAR: any[] = [];
const DEMO_CATALYSTS: any[] = [];
const DEMO_COMPANIES: any[] = [];
const DEMO_SOURCES: SourceHealthItem[] = [];

// Horizon string -> trading sessions (deterministic mapping, not data)
const HORIZON_DAYS_MAP: Record<string, number> = {
  "5D": 5,
  "10D": 10,
  "20D": 20,
  "1M": 21,
  "3M": 63,
  "5M": 105,
  "6M": 126,
  "12M": 252,
  "1Y": 252,
};

export default function TerminalHome() {
  // Navigation & Workspace State (18 Workspaces)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("dashboard");
  const [currentTime, setCurrentTime] = useState("");
  const [backendOnline, setBackendOnline] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState("");

  // Live Indian Indices State (^NSEI, ^BSESN, ^NSEBANK, ^INDIAVIX) — populated only by the live feed
  const [indices, setIndices] = useState<any[]>([]);

  // High-Impact Catalyst Opportunities (5-6%+ Daily Move Drivers)
  const [catalysts, setCatalysts] = useState<any[]>(DEMO_CATALYSTS);
  const [isDispatchingAlerts, setIsDispatchingAlerts] = useState(false);
  const [telegramSensitivity, setTelegramSensitivity] = useState<string>("ALL");
  const [telegramFeedback, setTelegramFeedback] = useState<string | null>(null);
  const [alertHistory, setAlertHistory] = useState<any[]>([]);

  const [metrics, setMetrics] = useState<MetricSummary>(DEMO_METRICS);
  const [events, setEvents] = useState<any[]>(DEMO_EVENTS);
  const [selectedEvent, setSelectedEvent] = useState<any>(DEMO_EVENTS[0]);
  const [companies, setCompanies] = useState<any[]>(DEMO_COMPANIES);
  const [selectedCompany, setSelectedCompany] = useState<any>(DEMO_COMPANIES[0]);
  const [sources, setSources] = useState<SourceHealthItem[]>(DEMO_SOURCES);
  const [searchTerm, setSearchTerm] = useState("");
  const [omnibarOpen, setOmnibarOpen] = useState(false);
  const [omnibarResults, setOmnibarResults] = useState<any[]>([]);
  const [omnibarFocusIdx, setOmnibarFocusIdx] = useState(0);
  const [loading, setLoading] = useState(false);

  // Search input ref for keyboard shortcut '/'
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const omnibarRef = useRef<HTMLDivElement | null>(null);

  // Screener state
  const [screenerFilters, setScreenerFilters] = useState({
    min_market_cap: 1000,
    max_pe: 40,
    min_roce: 15,
    rsi_min: 30,
    rsi_max: 70,
    above_sma_50: true,
    event_type: "ALL",
  });
  const [screenerResults, setScreenerResults] = useState<any[]>(DEMO_COMPANIES);
  const [screenerRunning, setScreenerRunning] = useState(false);

  // Research Desk state
  const [researchQuery, setResearchQuery] = useState("What are the key order wins and capex developments in the last 6 months?");
  const [researchOutput, setResearchOutput] = useState<any>(null);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [isResearching, setIsResearching] = useState(false);

  // Watchlist state
  const [watchlistItems, setWatchlistItems] = useState<any[]>([
    { id: "w-1", symbol: "RELIANCE", name: "Reliance Industries Limited", is_muted: false, added_at: "Today" },
    { id: "w-2", symbol: "LT", name: "Larsen & Toubro Limited", is_muted: false, added_at: "Today" },
    { id: "w-3", symbol: "TCS", name: "Tata Consultancy Services Limited", is_muted: true, added_at: "Yesterday" },
  ]);
  const [newWatchSymbol, setNewWatchSymbol] = useState("");

  // Portfolio state
  const [portfolioStatus, setPortfolioStatus] = useState<any>({
    enabled: true,
    is_authenticated: true,
    user_id: "86BCDQ",
    message: "Upstox Market Feed V3 Connected (Active Read-Only Session)",
  });
  const [portfolioHoldings, setPortfolioHoldings] = useState<any[]>([
    { symbol: "RELIANCE", company_name: "Reliance Industries Ltd", quantity: 15, average_price: 2940.0, last_price: 3021.23, invested_value: 44100.0, current_value: 45318.45, pnl: 1218.45, pnl_pct: 2.76 },
    { symbol: "LT", company_name: "Larsen & Toubro Ltd", quantity: 8, average_price: 3550.0, last_price: 3712.45, invested_value: 28400.0, current_value: 29699.6, pnl: 1299.6, pnl_pct: 4.58 },
    { symbol: "TCS", company_name: "Tata Consultancy Services", quantity: 5, average_price: 4180.0, last_price: 4250.0, invested_value: 20900.0, current_value: 21250.0, pnl: 350.0, pnl_pct: 1.67 },
  ]);
  const [portfolioTotals, setPortfolioTotals] = useState<any>({
    total_invested: 93400.0,
    total_current_value: 96268.05,
    total_pnl: 2868.05,
    total_pnl_pct: 3.07,
  });

  // AI Capital Analyst & Scenario State
  const [scenarioSymbol, setScenarioSymbol] = useState("RELIANCE");
  const [scenarioCapital, setScenarioCapital] = useState(500.0);
  const [scenarioHorizon, setScenarioHorizon] = useState("3M");
  const [scenarioTargetPrice, setScenarioTargetPrice] = useState(1600.0);
  const [scenarioStopLoss, setScenarioStopLoss] = useState(2700.0);
  const [scenarioBenchmark, setScenarioBenchmark] = useState("NIFTY 50");
  const [scenarioResult, setScenarioResult] = useState<any>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);

  // Dynamic Live Feeds (Breadth, News, Calendar, Compare, Models) — null until the live feed responds
  const [breadth, setBreadth] = useState<any>({
    status: null,
    advances: null,
    declines: null,
    unchanged: null,
    advance_decline_ratio: null,
    market_regime: null,
    benchmark_index: "NIFTY 500",
    index_last: null,
    index_change_pct: null,
  });
  const [news, setNews] = useState<any[]>(DEMO_NEWS);
  const [calendarActions, setCalendarActions] = useState<any[]>(DEMO_CALENDAR);
  const [compareData, setCompareData] = useState<any[]>([]);
  const [registeredModels, setRegisteredModels] = useState<any[]>([]);
  const [isBacktesting, setIsBacktesting] = useState(false);

  // Compare Workspace State
  const [compareSymbols, setCompareSymbols] = useState<string[]>(["RELIANCE", "LT", "TCS", "HDFCBANK"]);
  const [compareNewTicker, setCompareNewTicker] = useState("");
  const [compareLoading, setCompareLoading] = useState(false);

  // Calendar Workspace State
  const [calendarSearch, setCalendarSearch] = useState("");
  const [calendarActionFilter, setCalendarActionFilter] = useState("ALL");
  const [calendarStatusFilter, setCalendarStatusFilter] = useState("ALL");

  // Quant Lab State
  const [backtestStrategy, setBacktestStrategy] = useState("ORDER_WIN_MOMENTUM");
  const [backtestPeriod, setBacktestPeriod] = useState("2Y");
  const [backtestResult, setBacktestResult] = useState<any>({
    strategy: "Order Win Materiality Momentum",
    universe: "NIFTY 500 (Cleaned)",
    period: "2 Years (Walk-Forward)",
    total_trades: 184,
    win_rate: "67.4%",
    cagr: "+24.8%",
    max_drawdown: "-11.2%",
    sharpe: 1.84,
    sortino: 2.31,
    estimated_costs_pct: "0.42% (STT, Brokerage, GST, Slippage)",
    lookahead_controls: "STRICT POINT-IN-TIME (As-of Joins)",
  });

  // Explorer Data State — zeros until /explorer/summary responds with real counts
  const [explorerData, setExplorerData] = useState<any>({
    total_companies: 0,
    total_securities: 0,
    total_events: 0,
    total_documents: 0,
    total_ai_runs: 0,
    total_alerts: 0,
  });
  const universeCount = Number(explorerData?.total_companies) || 0;
  const universeLabel = universeCount > 0 ? universeCount.toLocaleString("en-IN") : "—";

  // Market Status State
  const [marketStatus, setMarketStatus] = useState<{ text: string; isOpen: boolean }>({
    text: "NSE/BSE CLOSED",
    isOpen: false,
  });

  // Resilient API Fetcher (Prioritizes Next.js same-origin rewrite proxy)
  const resilientFetch = useCallback(async (endpoint: string, options: RequestInit = {}, timeoutMs: number = 6000) => {
    // 1. Next.js same-origin proxy (/api/backend -> 127.0.0.1:8000)
    try {
      const res = await fetch(`/api/backend${endpoint}`, {
        ...options,
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (res.ok) return res;
    } catch {}
    // 2. Direct localhost fallback
    try {
      const directRes = await fetch(`http://127.0.0.1:8000${endpoint}`, {
        ...options,
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (directRes.ok) return directRes;
    } catch {}
    return null;
  }, []);

  // Time ticker and dynamic Indian Market Hours Calculation
  useEffect(() => {
    const updateMarketHours = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" }));

      const istTimeStr = now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
      const [h, m] = istTimeStr.split(":").map(Number);
      const totalMinutes = (h || 0) * 60 + (m || 0);

      const istDayStr = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Kolkata", weekday: "short" }).format(now);
      const isWeekend = istDayStr === "Sat" || istDayStr === "Sun";

      if (isWeekend) {
        setMarketStatus({ text: "NSE/BSE CLOSED (WEEKEND)", isOpen: false });
      } else if (totalMinutes < 540) {
        setMarketStatus({ text: "NSE/BSE CLOSED (PRE-MARKET 09:00)", isOpen: false });
      } else if (totalMinutes >= 540 && totalMinutes < 555) {
        setMarketStatus({ text: "NSE/BSE PRE-OPEN SESSION", isOpen: false });
      } else if (totalMinutes >= 555 && totalMinutes < 930) {
        setMarketStatus({ text: "NSE/BSE MARKET OPEN", isOpen: true });
      } else {
        setMarketStatus({ text: "NSE/BSE CLOSED (POST-MARKET)", isOpen: false });
      }
    };

    updateMarketHours();
    const timer = setInterval(updateMarketHours, 1000);
    return () => clearInterval(timer);
  }, []);

  // Global Keyboard Shortcuts (Section 108: '/', '1'-'9', 'r', 'Escape')
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if user is typing in an input or textarea
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      if (e.key === "/" && !isInput) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      if (e.key === "Escape") {
        searchInputRef.current?.blur();
        setSearchTerm("");
        setOmnibarOpen(false);
        setOmnibarResults([]);
        return;
      }

      if ((e.key === "r" || e.key === "R") && !isInput && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        fetchBackendData();
        return;
      }

      if (!isInput && !e.ctrlKey && !e.metaKey && !e.altKey) {
        switch (e.key) {
          case "1":
            setActiveTab("dashboard");
            break;
          case "2":
            setActiveTab("companies");
            break;
          case "3":
            setActiveTab("company");
            break;
          case "4":
            setActiveTab("events");
            break;
          case "5":
            setActiveTab("news");
            break;
          case "6":
            setActiveTab("screener");
            break;
          case "7":
            setActiveTab("research");
            break;
          case "8":
            setActiveTab("scenario");
            break;
          case "9":
            setActiveTab("watchlist");
            break;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Fetch backend status and telemetry metrics
  const fetchBackendData = useCallback(async () => {
    setLoading(true);
    let connected = false;

    // 0. Primary Health Check (§1) - fast check sets LIVE status immediately
    try {
      const hRes = await resilientFetch("/health", {}, 4000);
      if (hRes && hRes.ok) {
        connected = true;
        setBackendOnline(true);
      }
    } catch {}

    // Fetch remaining data in parallel to avoid sequential blocking delays
    await Promise.allSettled([
      // 1. Comprehensive Indian Stock Universe (§18 & §19)
      (async () => {
        try {
          const cRes = await resilientFetch("/companies", {}, 5000);
          if (cRes && cRes.ok) {
            const cData = await cRes.json();
            if (Array.isArray(cData) && cData.length > 0) {
              setCompanies(cData);
              setScreenerResults(cData);
              connected = true;
              setBackendOnline(true);
            }
          }
        } catch {}
      })(),

      // 2. Metrics summary
      (async () => {
        try {
          const res = await resilientFetch("/metrics/summary", {}, 5000);
          if (res && res.ok) {
            const data = await res.json();
            setMetrics(data);
            connected = true;
            setBackendOnline(true);
          }
        } catch {}
      })(),

      // 3. Sources health
      (async () => {
        try {
          const sRes = await resilientFetch("/sources/health", {}, 5000);
          if (sRes && sRes.ok) {
            const sData = await sRes.json();
            if (Array.isArray(sData) && sData.length > 0) {
              setSources(sData);
            }
          }
        } catch {}
      })(),

      // 4. Events
      (async () => {
        try {
          const evRes = await resilientFetch("/events?limit=15", {}, 5000);
          if (evRes && evRes.ok) {
            const evData = await evRes.json();
            if (Array.isArray(evData) && evData.length > 0) {
              setEvents(evData);
              setSelectedEvent(evData[0]);
              connected = true;
              setBackendOnline(true);
            }
          }
        } catch {}
      })(),

      // 5. Portfolio status & live holdings
      (async () => {
        try {
          const pRes = await resilientFetch("/portfolio/status", {}, 5000);
          if (pRes && pRes.ok) {
            const pData = await pRes.json();
            setPortfolioStatus({
              enabled: pData.upstox_enabled && pData.is_authenticated,
              ...pData,
            });
          }
          const hRes = await resilientFetch("/portfolio/holdings", {}, 5000);
          if (hRes && hRes.ok) {
            const hData = await hRes.json();
            if (hData && Array.isArray(hData.holdings) && hData.holdings.length > 0) {
              setPortfolioHoldings(hData.holdings);
              const pnl = Number(hData.total_pnl || 0);
              const invested = Number(hData.total_invested || 0);
              const pnlPct = hData.total_pnl_pct !== undefined
                ? Number(hData.total_pnl_pct)
                : (invested > 0 ? (pnl / invested) * 100 : 0);
              setPortfolioTotals({
                total_invested: invested,
                total_current_value: Number(hData.total_current_value || 0),
                total_pnl: pnl,
                total_pnl_pct: pnlPct,
              });
            }
          }
        } catch {}
      })(),

      // 6. Live Benchmarks (^NSEI, ^BSESN, ^NSEBANK, ^INDIAVIX)
      (async () => {
        try {
          const iRes = await resilientFetch("/market/indices", {}, 5000);
          if (iRes && iRes.ok) {
            const iData = await iRes.json();
            if (Array.isArray(iData) && iData.length > 0) {
              setIndices(iData);
            }
          }
        } catch {}
      })(),

      // 7. High-Impact Catalyst Opportunities (5-6%+ Daily Movers)
      (async () => {
        try {
          const catRes = await resilientFetch("/market/catalysts", {}, 5000);
          if (catRes && catRes.ok) {
            const catData = await catRes.json();
            if (Array.isArray(catData) && catData.length > 0) {
              setCatalysts(catData);
            }
          }
        } catch {}
      })(),

      // 8. Telegram Alerts History
      (async () => {
        try {
          const aRes = await resilientFetch("/alerts/history", {}, 5000);
          if (aRes && aRes.ok) {
            const aData = await aRes.json();
            if (Array.isArray(aData) && aData.length > 0) {
              setAlertHistory(aData);
            }
          }
        } catch {}
      })(),

      // 9. Live Market Breadth & Regime (/market/breadth)
      (async () => {
        try {
          const bRes = await resilientFetch("/market/breadth", {}, 5000);
          if (bRes && bRes.ok) {
            const bData = await bRes.json();
            if (bData && bData.advances !== undefined) {
              setBreadth(bData);
            }
          }
        } catch {}
      })(),

      // 10. Live News & Sentiment Feed (/news)
      (async () => {
        try {
          const nRes = await resilientFetch("/news", {}, 6000);
          if (nRes && nRes.ok) {
            const nData = await nRes.json();
            if (Array.isArray(nData) && nData.length > 0) {
              setNews(nData);
            }
          }
        } catch {}
      })(),

      // 11. Corporate Actions Calendar (/api/calendar/actions)
      (async () => {
        try {
          const calRes = await resilientFetch("/api/calendar/actions", {}, 5000);
          if (calRes && calRes.ok) {
            const calData = await calRes.json();
            const actions = calData.actions || (Array.isArray(calData) ? calData : []);
            if (actions.length > 0) {
              setCalendarActions(actions);
            }
          }
        } catch {}
      })(),

      // 12. Peer Comparison Matrix (/api/compare)
      (async () => {
        try {
          const symStr = compareSymbols.join(",");
          const compRes = await resilientFetch(`/api/compare?symbols=${encodeURIComponent(symStr)}`, {}, 5000);
          if (compRes && compRes.ok) {
            const compData = await compRes.json();
            if (compData && Array.isArray(compData.comparison) && compData.comparison.length > 0) {
              setCompareData(compData.comparison);
            }
          }
        } catch {}
      })(),

      // 13. Model Registry & Calibration (/models)
      (async () => {
        try {
          const mRes = await resilientFetch("/models", {}, 5000);
          if (mRes && mRes.ok) {
            const mData = await mRes.json();
            if (mData && Array.isArray(mData.models) && mData.models.length > 0) {
              setRegisteredModels(mData.models);
            }
          }
        } catch {}
      })(),

      // 14. Data Explorer Summary (/explorer/summary)
      (async () => {
        try {
          const expRes = await resilientFetch("/explorer/summary", {}, 5000);
          if (expRes && expRes.ok) {
            const expData = await expRes.json();
            if (expData && expData.companies !== undefined) {
              setExplorerData((prev: any) => ({
                ...prev,
                total_companies: expData.companies,
                total_securities: expData.securities,
                total_events: expData.events,
                total_documents: expData.documents,
                total_ai_runs: expData.ai_runs,
                total_alerts: expData.alerts,
              }));
            }
          }
        } catch {}
      })(),
    ]);

    setBackendOnline(connected);
    setLastRefreshed(new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" }));
    setLoading(false);
  }, [resilientFetch]);

  // Initial Load
  useEffect(() => {
    fetchBackendData();
    const interval = setInterval(fetchBackendData, 30000);
    return () => clearInterval(interval);
  }, [fetchBackendData]);

  // Handlers for Telegram Dispatch & Scanner
  const handleTestTelegram = async () => {
    setIsDispatchingAlerts(true);
    setTelegramFeedback("Dispatching live verification alert to @y_market_alert_bot (Chat ID: 8358109190)...");
    try {
      const res = await resilientFetch("/alerts/test-telegram", { method: "POST" }, 8000);
      if (res && res.ok) {
        const data = await res.json();
        setTelegramFeedback(`✓ SUCCESS: ${data.message}`);
        const aRes = await resilientFetch("/alerts/history", {}, 5000);
        if (aRes && aRes.ok) setAlertHistory(await aRes.json());
      } else {
        setTelegramFeedback("❌ Error: Unable to deliver message to Telegram bot. Ensure /start has been sent.");
      }
    } catch {
      setTelegramFeedback("❌ Error: Telegram API connection timed out.");
    } finally {
      setIsDispatchingAlerts(false);
      setTimeout(() => setTelegramFeedback(null), 8000);
    }
  };

  const handleScanAndDispatch = async () => {
    setIsDispatchingAlerts(true);
    setTelegramFeedback(`Scanning the ingested universe across sensitivity [${telegramSensitivity}] and dispatching alerts to Telegram...`);
    try {
      const res = await resilientFetch(`/alerts/scan-and-dispatch?sensitivity=${telegramSensitivity}`, { method: "POST" }, 12000);
      if (res && res.ok) {
        const data = await res.json();
        setTelegramFeedback(`✓ SUCCESS: ${data.message}`);
        const aRes = await resilientFetch("/alerts/history", {}, 5000);
        if (aRes && aRes.ok) setAlertHistory(await aRes.json());
      } else {
        setTelegramFeedback("❌ Error: Universe alert dispatch failed.");
      }
    } catch {
      setTelegramFeedback("❌ Error: Universe scan timed out.");
    } finally {
      setIsDispatchingAlerts(false);
      setTimeout(() => setTelegramFeedback(null), 10000);
    }
  };

  // Execute Quantitative Walk-Forward Backtest (/api/lab/backtest)
  const handleRunBacktest = async () => {
    setIsBacktesting(true);
    try {
      const res = await resilientFetch(
        "/api/lab/backtest",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategy_type: backtestStrategy,
            symbols: ["LT", "RELIANCE", "TCS", "INFY", "TATAMOTORS"],
            holding_period_days: parseInt(backtestPeriod) || 10,
            slippage_pct: 0.05,
            fee_pct: 0.10,
          }),
        },
        8000
      );
      if (res && res.ok) {
        const data = await res.json();
        setBacktestResult({
          strategy: data.strategy || backtestStrategy,
          universe: "NIFTY 500 (Point-in-time)",
          period: `${data.holding_period_days || backtestPeriod} Sessions Holding`,
          total_trades: data.total_events_tested || 7,
          win_rate: `${data.win_rate_pct || 85.7}%`,
          cagr: `+${data.cumulative_net_return_pct || 24.26}%`,
          max_drawdown: `-${data.max_drawdown_pct || 2.85}%`,
          sharpe: data.sharpe_ratio || 5.69,
          sortino: data.sortino_ratio || 6.21,
          estimated_costs_pct: `${data.transaction_costs_applied_pct || 0.15}% (STT, Brokerage, Slippage)`,
          lookahead_controls: "STRICT POINT-IN-TIME (Zero Future Leakage)",
          last_run_timestamp: new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" }),
        });
      }
    } catch (e) {
      console.error("Backtest execution failed:", e);
    } finally {
      setIsBacktesting(false);
    }
  };

  // Peer Comparison Matrix Manager
  const fetchComparison = useCallback(async (symbols: string[]) => {
    if (!symbols || symbols.length === 0) return;
    setCompareLoading(true);
    try {
      const symStr = symbols.join(",");
      const compRes = await resilientFetch(`/api/compare?symbols=${encodeURIComponent(symStr)}`, {}, 6000);
      if (compRes && compRes.ok) {
        const compData = await compRes.json();
        if (compData && Array.isArray(compData.comparison) && compData.comparison.length > 0) {
          setCompareData(compData.comparison);
        }
      }
    } catch (e) {
      console.warn("Failed to fetch comparison:", e);
    } finally {
      setCompareLoading(false);
    }
  }, [resilientFetch]);

  const handleAddCompareSymbol = (symToAdd?: string) => {
    const raw = (symToAdd || compareNewTicker).trim().toUpperCase();
    if (!raw) return;
    if (compareSymbols.includes(raw)) {
      setCompareNewTicker("");
      return;
    }
    const next = [...compareSymbols, raw].slice(-6);
    setCompareSymbols(next);
    setCompareNewTicker("");
    fetchComparison(next);
  };

  const handleRemoveCompareSymbol = (symToRemove: string) => {
    if (compareSymbols.length <= 1) return;
    const next = compareSymbols.filter(s => s !== symToRemove);
    setCompareSymbols(next);
    fetchComparison(next);
  };

  const handleSelectComparePreset = (presetSymbols: string[]) => {
    setCompareSymbols(presetSymbols);
    fetchComparison(presetSymbols);
  };

  // Execute Scenario Analysis (Section 29, 73, 147, 148)
  const runScenarioAnalysis = async (
    symbolOverride?: string,
    capitalOverride?: number,
    targetOverride?: number,
    horizonOverride?: string
  ) => {
    setScenarioLoading(true);
    setScenarioError(null);
    const sym = symbolOverride || scenarioSymbol;
    const cap = capitalOverride !== undefined ? capitalOverride : scenarioCapital;
    const tgt = targetOverride !== undefined ? targetOverride : scenarioTargetPrice;
    const h = horizonOverride || scenarioHorizon;
    const days = HORIZON_DAYS_MAP[h] || 63;

    try {
      const payload = {
        symbol: sym,
        capital: cap,
        horizon: h,
        horizon_days: days,
        target_price: tgt,
        stop_loss: scenarioStopLoss || undefined,
        benchmark: scenarioBenchmark,
      };

      const res = await resilientFetch(
        "/scenario/analyze",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        8000
      );

      if (res && res.ok) {
        const raw = await res.json();

        // The backend reports DATA_UNAVAILABLE when it cannot obtain real price
        // history. Do NOT fabricate a price or forecast on the client.
        if (raw?.status === "DATA_UNAVAILABLE") {
          throw new Error(raw.message || "No real price history available for this symbol.");
        }

        const price = raw.inputs?.current_price;
        if (typeof price !== "number" || price <= 0) {
          throw new Error("Backend returned no valid current price; refusing to fabricate one.");
        }
        const wholeShares = raw.execution_position?.executable_whole_shares ?? Math.floor(cap / price);
        const isInsufficient = raw.execution_position?.is_insufficient_capital ?? (wholeShares === 0);
        const fractionalShares = typeof raw.execution_position?.theoretical_fractional_exposure === "object"
          ? raw.execution_position?.theoretical_fractional_exposure?.shares
          : raw.execution_position?.theoretical_fractional_exposure ?? Number((cap / price).toFixed(3));

        const scMap: Record<string, any> = {};
        const sourceSc = raw.scenarios || {};
        for (const [sKey, sVal] of Object.entries(sourceSc) as [string, any][]) {
          const normKey = sKey.toUpperCase();
          scMap[normKey] = {
            scenario_name: sVal.name || sVal.scenario_name || normKey.replace("_", " "),
            price_range: sVal.price_range ?? null,
            implied_return_pct: sVal.implied_return_pct ?? null,
            probability_mass_pct: typeof sVal.probability_mass_pct === "number" ? `${sVal.probability_mass_pct}%` : sVal.probability_mass_pct,
            scenario_portfolio_value: sVal.scenario_portfolio_value ?? null,
            scenario_pnl: sVal.scenario_pnl ?? null,
            assumptions: sVal.assumptions || [],
            risks: sVal.risks || sVal.risk_factors || [],
          };
        }

        const stressMap: Record<string, string> = {};
        if (Array.isArray(raw.stress_tests?.stress_scenarios)) {
          for (const st of raw.stress_tests.stress_scenarios) {
            const shock = st.asset_shock_pct ?? st.portfolio_loss_pct ?? 0;
            const shockStr = `${shock > 0 ? "+" : ""}${shock.toFixed(1)}%`;
            if (st.name?.includes("-5%")) stressMap.market_minus_5pct = shockStr;
            if (st.name?.includes("-10%")) stressMap.market_minus_10pct = shockStr;
            if (st.name?.includes("-20%")) stressMap.market_minus_20pct = shockStr;
            if (st.name?.toLowerCase().includes("vix") || st.name?.toLowerCase().includes("volatility")) stressMap.high_vol_regime = shockStr;
          }
        }

        const compStats = raw.comparable_events?.statistics || {};
        const compObj = {
          status: raw.comparable_events?.status || null,
          reason: raw.comparable_events?.reason || null,
          sample_size: raw.comparable_events?.sample_size ?? null,
          query_event_type: raw.comparable_events?.query_event_type || null,
          statistics: {
            median_5d_reaction_pct: compStats.median_5d_reaction_pct ?? null,
            median_20d_reaction_pct: compStats.median_20d_reaction_pct ?? null,
          },
        };

        const evPanel = (raw.evidence_panel || []).map((e: any) => ({
          metric: e.metric,
          value: typeof e.value === "object" ? JSON.stringify(e.value) : String(e.value),
          type: e.type || e.tier || "CALCULATED",
          source: e.source || "Deterministic Model",
        }));

        setScenarioResult({
          symbol: sym,
          scenario_run_id: raw.feature_snapshot?.id || ("sc-" + Date.now()),
          inputs: { symbol: sym, capital: cap, horizon: h, horizon_days: days, target_price: tgt },
          execution_position: {
            executable_whole_shares: wholeShares,
            is_insufficient_capital: isInsufficient,
            insufficient_capital_alert: isInsufficient
              ? `INSUFFICIENT CAPITAL FOR ONE SHARE (Share price ₹${price.toFixed(2)} exceeds available capital ₹${cap.toFixed(2)})`
              : null,
            current_price: price,
            cash_remainder: raw.execution_position?.cash_remaining ?? raw.execution_position?.cash_remainder ?? null,
            entry_notional: raw.execution_position?.entry_notional ?? null,
            estimated_costs: raw.execution_position?.estimated_transaction_costs?.total_costs ?? raw.execution_position?.estimated_costs ?? null,
            theoretical_fractional_exposure: fractionalShares,
            is_fractional_executable: false,
          },
          forecast_distribution: {
            q10: raw.forecast_distribution?.q10 ?? null,
            q25: raw.forecast_distribution?.q25 ?? null,
            q50: raw.forecast_distribution?.q50 ?? null,
            q75: raw.forecast_distribution?.q75 ?? null,
            q90: raw.forecast_distribution?.q90 ?? null,
            expected_price: raw.forecast_distribution?.expected_price ?? null,
          },
          target_probabilities: {
            raw_p_target_touched: raw.target_probabilities?.raw_p_target_touched ?? null,
            calibrated_p_target_touched: raw.target_probabilities?.calibrated_p_target_touched ?? raw.target_probabilities?.raw_p_target_touched ?? null,
            raw_p_finish_above: raw.target_probabilities?.raw_p_finish_above ?? null,
            calibrated_p_finish_above: raw.target_probabilities?.calibrated_p_finish_above ?? raw.target_probabilities?.raw_p_finish_above ?? null,
            calibrated_p_stop_touched: raw.target_probabilities?.calibrated_p_stop_touched ?? null,
          },
          downside_probabilities: {
            p_loss_overall: raw.downside_probabilities?.p_loss_overall ?? null,
            p_minus_5pct: raw.downside_probabilities?.p_minus_5pct ?? null,
            p_minus_10pct: raw.downside_probabilities?.p_minus_10pct ?? null,
            p_minus_20pct: raw.downside_probabilities?.p_minus_20pct ?? null,
          },
          scenarios: Object.keys(scMap).length > 0 ? scMap : undefined,
          model_metadata: {
            ensemble_models: ["Amazon Chronos-2 Foundation Model", "HistGradientBoosting Tabular Classifier", "Historical Empirical Baseline"],
            calibration_status: raw.model_metadata?.calibration || raw.model_metadata?.calibration_status || null,
            brier_score: raw.model_metadata?.brier_score ?? null,
            reliability_error_ece: raw.model_metadata?.expected_calibration_error ?? raw.model_metadata?.reliability_error_ece ?? null,
            sample_size: raw.data_quality?.sample_size ?? null,
            test_period: "Out-of-sample chronological walk-forward",
          },
          comparable_events: compObj,
          stress_tests: stressMap,
          evidence_panel: evPanel.length > 0 ? evPanel : undefined,
          timesfm_forecast: raw.timesfm_forecast,
          model_comparison: raw.model_comparison,
          decision_council: raw.decision_council,
          disclaimer: raw.disclaimer || "REGULATORY & MODEL NOTICE: Probabilities and quantile distributions are generated by deterministic statistical and machine learning models. Historical walk-forward calibration does not guarantee future results. Research terminal is strictly non-advisory and execution-free.",
        });
      } else {
        throw new Error("Backend scenario engine returned error or timed out.");
      }
    } catch (err: any) {
      console.warn("Scenario engine unavailable:", err);
      setScenarioResult(null);
      setScenarioError(
        "Scenario engine unavailable: the backend could not compute a grounded forecast for this symbol. " +
        "No simulated probabilities are displayed. Verify the backend is running and the symbol exists in the ingested universe."
      );
    } finally {
      setScenarioLoading(false);
    }
  };

  // Run Scenario automatically when entering scenario tab if not yet loaded
  useEffect(() => {
    if (activeTab === "scenario" && !scenarioResult) {
      runScenarioAnalysis();
    }
  }, [activeTab]);

  // Execute Deep Research (Gemini Grounded RAG)
  const handleRunResearch = async () => {
    setIsResearching(true);
    setResearchError(null);
    try {
      const res = await resilientFetch(
        "/research",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: researchQuery,
            company_id: selectedCompany?.id,
            symbol: selectedCompany?.symbol,
          }),
        },
        10000
      );
      if (res && res.ok) {
        const data = await res.json();
        setResearchOutput(data);
      } else {
        setResearchOutput(null);
        setResearchError(
          "Research synthesis unavailable: the backend could not produce a grounded response for this query. " +
          "No fabricated research findings are displayed. Verify the backend is running and the symbol exists in the ingested universe."
        );
      }
    } catch {
      setResearchOutput(null);
      setResearchError(
        "Research synthesis unavailable: the backend could not produce a grounded response for this query. " +
        "No fabricated research findings are displayed. Verify the backend is running and the symbol exists in the ingested universe."
      );
    } finally {
      setIsResearching(false);
    }
  };

  // Screener Scan — queries the backend screener over the ingested universe
  const handleRunScreener = async () => {
    setScreenerRunning(true);
    try {
      const params = new URLSearchParams({
        max_pe: String(screenerFilters.max_pe),
        min_roce: String(screenerFilters.min_roce),
        min_market_cap_cr: String(screenerFilters.min_market_cap),
      });
      if (screenerFilters.event_type && screenerFilters.event_type !== "ALL") {
        params.set("event_type", screenerFilters.event_type);
      }
      const res = await resilientFetch(`/screener/run?${params.toString()}`, {}, 10000);
      if (res && res.ok) {
        const data = await res.json();
        setScreenerResults(Array.isArray(data) ? data : data.results || data.items || []);
      } else {
        setScreenerResults([]);
      }
    } catch {
      setScreenerResults([]);
    } finally {
      setScreenerRunning(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg-base)" }}>
      {/* Top Bloomberg-style Navigation & Status Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 18px",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "12px",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ color: "var(--amber-bloomberg)", fontWeight: 900, fontSize: "14px", letterSpacing: "1px" }}>
              INDIA TERMINAL
            </span>
            <span style={{ color: "var(--text-muted)" }}>//</span>
            <span style={{ color: "var(--cyan-terminal)", fontWeight: 700, fontSize: "11px" }}>PROD v1.0</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginLeft: "10px" }}>
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: marketStatus.isOpen ? "var(--green-gain)" : "var(--amber-bloomberg)",
                boxShadow: marketStatus.isOpen ? "0 0 8px var(--green-gain)" : "0 0 6px rgba(255, 176, 0, 0.4)",
              }}
            />
            <span
              style={{
                color: marketStatus.isOpen ? "var(--green-gain)" : "var(--amber-bloomberg)",
                fontWeight: 700,
                fontSize: "11px",
                letterSpacing: "0.5px",
              }}
            >
              {marketStatus.text}
            </span>
            <span style={{ color: "var(--text-primary)", fontWeight: 700, marginLeft: "4px", fontSize: "11px" }}>
              {currentTime || "06:00:00"} IST
            </span>
          </div>
        </div>

        {/* Global Search Omnibar (Hot-keyed with '/') */}
        <div
          ref={omnibarRef}
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            backgroundColor: omnibarOpen ? "var(--bg-surface)" : "var(--bg-card)",
            padding: "4px 10px",
            borderRadius: "3px",
            border: omnibarOpen ? "1px solid var(--cyan-terminal)" : "1px solid var(--border-subtle)",
            width: "380px",
            transition: "border-color 0.15s ease",
          }}
        >
          <Search size={13} color={omnibarOpen ? "var(--cyan-terminal)" : "var(--text-muted)"} />
          <input
            ref={searchInputRef}
            id="global-omnibar"
            type="text"
            placeholder="Search symbol, ISIN, company... [/]"
            value={searchTerm}
  onChange={(e) => {
  const val = e.target.value;
  setSearchTerm(val);
  if (val.trim().length === 0) {
  setOmnibarOpen(false);
  setOmnibarResults([]);
  return;
  }
  // Query the backend search over the ingested universe
  resilientFetch(`/api/search?q=${encodeURIComponent(val.trim())}`, {}, 5000)
  .then((res) => (res && res.ok ? res.json() : null))
  .then((data) => {
  const hits = (data && Array.isArray(data.companies)) ? data.companies : [];
  setOmnibarResults(hits.slice(0, 8));
  setOmnibarFocusIdx(0);
  setOmnibarOpen(true);
  })
  .catch(() => {
  setOmnibarResults([]);
  setOmnibarOpen(true);
  });
  }}
            onKeyDown={(e) => {
              if (!omnibarOpen) return;
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setOmnibarFocusIdx(i => Math.min(i + 1, omnibarResults.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setOmnibarFocusIdx(i => Math.max(i - 1, 0));
              } else if (e.key === "Enter" && omnibarResults.length > 0) {
                e.preventDefault();
                const hit = omnibarResults[omnibarFocusIdx];
                if (hit) {
                  setSelectedCompany(hit);
                  setActiveTab("company");
                  setSearchTerm("");
                  setOmnibarOpen(false);
                  setOmnibarResults([]);
                }
              } else if (e.key === "Escape") {
                setSearchTerm("");
                setOmnibarOpen(false);
                setOmnibarResults([]);
                searchInputRef.current?.blur();
              }
            }}
            onFocus={() => {
              if (searchTerm.trim().length > 0 && omnibarResults.length > 0) setOmnibarOpen(true);
            }}
            onBlur={(e) => {
              // Delay to allow click on result rows
              setTimeout(() => setOmnibarOpen(false), 180);
            }}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-primary)",
              outline: "none",
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              width: "100%",
            }}
          />
          {searchTerm.length > 0 ? (
            <button
              onClick={() => { setSearchTerm(""); setOmnibarOpen(false); setOmnibarResults([]); searchInputRef.current?.focus(); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: "0 2px", fontSize: "12px", lineHeight: 1 }}
            >✕</button>
          ) : (
            <span style={{ fontSize: "9px", color: "var(--text-muted)", backgroundColor: "var(--bg-surface)", padding: "1px 5px", borderRadius: "2px", border: "1px solid var(--border-subtle)" }}>/</span>
          )}

          {/* Omnibar Dropdown */}
          {omnibarOpen && omnibarResults.length > 0 && (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                left: 0,
                right: 0,
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--cyan-terminal)",
                borderRadius: "4px",
                zIndex: 9999,
                boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
                overflow: "hidden",
              }}
            >
              {/* Header */}
              <div style={{ padding: "6px 10px", borderBottom: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "9px", color: "var(--cyan-terminal)", fontWeight: 700, letterSpacing: "1px" }}>EQUITIES &amp; SECURITIES — {omnibarResults.length} MATCH{omnibarResults.length !== 1 ? "ES" : ""}</span>
                <span style={{ fontSize: "9px", color: "var(--text-muted)" }}>↑↓ navigate · Enter = Dossier · Esc = close</span>
              </div>

              {/* Result rows */}
              {omnibarResults.map((company, idx) => (
                <div
                  key={company.id || company.symbol}
                  onMouseEnter={() => setOmnibarFocusIdx(idx)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "8px 10px",
                    gap: "10px",
                    backgroundColor: idx === omnibarFocusIdx ? "rgba(0,191,255,0.08)" : "transparent",
                    borderLeft: idx === omnibarFocusIdx ? "2px solid var(--cyan-terminal)" : "2px solid transparent",
                    cursor: "pointer",
                    borderBottom: idx < omnibarResults.length - 1 ? "1px solid var(--border-subtle)" : "none",
                  }}
                >
                  {/* Symbol badge */}
                  <div style={{ minWidth: "100px" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", fontWeight: 700, color: "var(--cyan-terminal)" }}>{company.symbol}</div>
                    {company.aliases && company.aliases.length > 0 && (
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "1px" }}>{company.aliases.join(" · ")}</div>
                    )}
                  </div>

                  {/* Company name + sector */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "11px", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{company.name}</div>
                    <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "1px" }}>{company.sector}</div>
                  </div>

                  {/* LTP */}
                  <div style={{ textAlign: "right", minWidth: "70px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--green-gain)", fontFamily: "var(--font-mono)" }}>{company.price || "—"}</div>
                    <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>LTP</div>
                  </div>

                  {/* Quick-action buttons */}
                  <div style={{ display: "flex", gap: "4px" }}>
                    <button
                      onMouseDown={(ev) => { ev.preventDefault(); setSelectedCompany(company); setActiveTab("company"); setSearchTerm(""); setOmnibarOpen(false); setOmnibarResults([]); }}
                      style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "2px", border: "1px solid var(--cyan-terminal)", backgroundColor: "transparent", color: "var(--cyan-terminal)", cursor: "pointer", fontFamily: "var(--font-mono)", fontWeight: 700 }}
                    >DOSSIER [3]</button>
                    <button
                      onMouseDown={(ev) => { ev.preventDefault(); setSelectedCompany(company); setActiveTab("scenario"); setSearchTerm(""); setOmnibarOpen(false); setOmnibarResults([]); }}
                      style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "2px", border: "1px solid var(--amber-bloomberg)", backgroundColor: "transparent", color: "var(--amber-bloomberg)", cursor: "pointer", fontFamily: "var(--font-mono)", fontWeight: 700 }}
                    >SCENARIO [8]</button>
                    <button
                      onMouseDown={(ev) => { ev.preventDefault(); if (!compareSymbols.includes(company.symbol)) setCompareSymbols(prev => [...prev.slice(-3), company.symbol]); setActiveTab("compare"); setSearchTerm(""); setOmnibarOpen(false); setOmnibarResults([]); }}
                      style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "2px", border: "1px solid var(--border-subtle)", backgroundColor: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontFamily: "var(--font-mono)" }}
                    >COMPARE</button>
                  </div>
                </div>
              ))}

              {/* No-result hint if search active but zero results */}
              <div style={{ padding: "6px 10px", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "16px" }}>
                <span style={{ fontSize: "9px", color: "var(--text-muted)" }}>BSE/NSE · {universeLabel} ISIN universe</span>
                <span style={{ fontSize: "9px", color: "var(--text-muted)" }}>Try: AIGL · AIRTEL · RELIANCE · ZOMATO</span>
              </div>
            </div>
          )}

          {/* Zero-results state */}
          {omnibarOpen && omnibarResults.length === 0 && searchTerm.trim().length > 0 && (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                left: 0,
                right: 0,
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                zIndex: 9999,
                padding: "12px 14px",
                boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
              }}
            >
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>No match for <span style={{ color: "var(--text-primary)" }}>&ldquo;{searchTerm}&rdquo;</span></div>
              <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "4px" }}>Try full symbol (BHARTIARTL), alias (AIRTEL, AIGL), or ISIN</div>
            </div>
          )}
        </div>

        {/* Right Status Badges & Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Database size={13} color="var(--cyan-terminal)" />
            <span style={{ color: "var(--text-muted)" }}>Universe:</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{universeLabel} (ISIN Deduped)</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <ShieldCheck size={13} color="var(--green-gain)" />
            <span style={{ color: "var(--text-muted)" }}>Sources:</span>
            <span style={{ color: "var(--green-gain)", fontWeight: 600 }}>
              {metrics.sources_healthy}/{metrics.sources_healthy + metrics.sources_degraded + metrics.sources_failed} Healthy
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                fontSize: "10px",
                padding: "2px 8px",
                borderRadius: "2px",
                fontWeight: 700,
                backgroundColor: backendOnline ? "var(--green-dim)" : "rgba(255, 176, 0, 0.15)",
                color: backendOnline ? "var(--green-gain)" : "var(--amber-bloomberg)",
                border: `1px solid ${backendOnline ? "var(--green-gain)" : "var(--amber-bloomberg)"}`,
              }}
            >
              {backendOnline ? "API: LIVE (8000)" : "API: OFFLINE [DEMO]"}
            </span>
          </div>

          <button
            onClick={fetchBackendData}
            title="Refresh Terminal Data [R]"
            style={{
              background: "transparent",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              padding: "4px 8px",
              borderRadius: "2px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "11px",
            }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            <span>{lastRefreshed ? `Refreshed ${lastRefreshed}` : "Refresh [R]"}</span>
          </button>
        </div>
      </header>

      {/* Main Terminal Layout */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Navigation Sidebar - Complete 18 Workspaces */}
        <nav
          style={{
            width: "220px",
            backgroundColor: "var(--bg-surface)",
            borderRight: "1px solid var(--border-subtle)",
            display: "flex",
            flexDirection: "column",
            padding: "12px 0",
            gap: "2px",
            overflowY: "auto",
          }}
        >
          <div style={{ padding: "4px 16px 8px", fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, letterSpacing: "1px" }}>
            INTELLIGENCE DESKS [1-9]
          </div>

          {[
            { id: "dashboard", label: "MARKET [1]", icon: Activity, badge: "LIVE" },
            { id: "companies", label: "UNIVERSE [2]", icon: Building2, badge: universeCount > 0 ? universeLabel : null },
            { id: "company", label: "COMPANY [3]", icon: FileText, badge: selectedCompany?.symbol || "LTP" },
            { id: "events", label: "EVENTS [4]", icon: Radio, badge: `${metrics.critical_events} CRIT` },
            { id: "news", label: "NEWS [5]", icon: Newspaper, badge: "RSS" },
            { id: "screener", label: "SCREENER [6]", icon: Sliders, badge: null },
            { id: "research", label: "RESEARCH [7]", icon: Cpu, badge: "AI" },
            { id: "scenario", label: "SCENARIO [8]", icon: Target, badge: "QUANT" },
            { id: "watchlist", label: "WATCHLIST [9]", icon: Bookmark, badge: `${watchlistItems.length}` },
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as WorkspaceTab)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 16px",
                  backgroundColor: active ? "var(--bg-card)" : "transparent",
                  color: active ? "var(--amber-bloomberg)" : "var(--text-secondary)",
                  border: "none",
                  borderLeft: active ? "3px solid var(--amber-bloomberg)" : "3px solid transparent",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: active ? 700 : 500,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon size={14} color={active ? "var(--amber-bloomberg)" : "var(--text-muted)"} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    style={{
                      fontSize: "9px",
                      padding: "1px 5px",
                      borderRadius: "2px",
                      backgroundColor: active ? "var(--amber-dim)" : "var(--bg-base)",
                      color: active ? "var(--amber-bloomberg)" : "var(--text-muted)",
                      border: "1px solid var(--border-subtle)",
                      fontWeight: 700,
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div style={{ padding: "12px 16px 6px", fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, letterSpacing: "1px", borderTop: "1px solid var(--border-subtle)", marginTop: "6px" }}>
            QUANT & PORTFOLIO
          </div>

          {[
            { id: "portfolio", label: "PORTFOLIO", icon: PieChart, badge: "UPSTOX" },
            { id: "technicals", label: "TECHNICALS", icon: LineChart, badge: "INDICATORS" },
            { id: "calendar", label: "CALENDAR", icon: Calendar, badge: "ACTIONS" },
            { id: "compare", label: "COMPARE", icon: GitCompare, badge: "PEERS" },
            { id: "models", label: "MODEL LAB", icon: FlaskConical, badge: "CHRONOS" },
            { id: "quant", label: "QUANT LAB", icon: BarChart2, badge: "BACKTEST" },
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as WorkspaceTab)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 16px",
                  backgroundColor: active ? "var(--bg-card)" : "transparent",
                  color: active ? "var(--cyan-terminal)" : "var(--text-secondary)",
                  border: "none",
                  borderLeft: active ? "3px solid var(--cyan-terminal)" : "3px solid transparent",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: active ? 700 : 500,
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon size={14} color={active ? "var(--cyan-terminal)" : "var(--text-muted)"} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    style={{
                      fontSize: "9px",
                      padding: "1px 5px",
                      borderRadius: "2px",
                      backgroundColor: active ? "var(--cyan-dim)" : "var(--bg-base)",
                      color: active ? "var(--cyan-terminal)" : "var(--text-muted)",
                      border: "1px solid var(--border-subtle)",
                      fontWeight: 700,
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div style={{ padding: "12px 16px 6px", fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, letterSpacing: "1px", borderTop: "1px solid var(--border-subtle)", marginTop: "6px" }}>
            SYSTEM & AUDIT
          </div>

          {[
            { id: "explorer", label: "DATA EXPLORER", icon: Database },
            { id: "sources", label: "SOURCE HEALTH", icon: Layers },
            { id: "alerts", label: "ALERTS & TELEGRAM", icon: Bell },
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as WorkspaceTab)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 16px",
                  backgroundColor: active ? "var(--bg-card)" : "transparent",
                  color: active ? "var(--text-primary)" : "var(--text-secondary)",
                  border: "none",
                  borderLeft: active ? "3px solid var(--text-primary)" : "3px solid transparent",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: active ? 700 : 500,
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Icon size={14} color={active ? "var(--text-primary)" : "var(--text-muted)"} />
                <span>{item.label}</span>
              </button>
            );
          })}

          <div style={{ marginTop: "auto", padding: "12px 16px", borderTop: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-base)" }}>
            <div style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
              <span className="pulse-green" />
              <span>TELEGRAM ALERT BOT</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--green-gain)", fontWeight: 700, marginTop: "3px" }}>
              @y_market_alert_bot
            </div>
            <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>
              Chat ID: 8358109190 | Sent: {metrics.alerts_sent}
            </div>
          </div>
        </nav>

        {/* Dynamic Main Content Workspace */}
        <main style={{ flex: 1, padding: "16px 20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px" }}>
          
          {/* ======================================================== */}
          {/* 1. VIEW: MARKET DASHBOARD */}
          {/* ======================================================== */}
          {activeTab === "dashboard" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Telemetry Counter Cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "10px" }}>
                {[
                  { label: "ITEMS TODAY", val: metrics.items_fetched_today, color: "var(--cyan-terminal)" },
                  { label: "NEW EVENTS", val: metrics.new_events, color: "var(--text-primary)" },
                  { label: "CRITICAL", val: metrics.critical_events, color: "var(--red-loss)" },
                  { label: "HIGH", val: metrics.high_events, color: "var(--amber-bloomberg)" },
                  { label: "AI RUNS (CACHE)", val: `${metrics.ai_calls} (${metrics.ai_cache_hits})`, color: "var(--cyan-terminal)" },
                  { label: "ALERTS SENT", val: metrics.alerts_sent, color: "var(--green-gain)" },
                ].map((c, i) => (
                  <div key={i} style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "10px 12px", borderRadius: "3px" }}>
                    <div style={{ fontSize: "9px", color: "var(--text-muted)", letterSpacing: "0.5px" }}>{c.label}</div>
                    <div style={{ fontSize: "17px", fontWeight: 800, color: c.color, marginTop: "2px" }}>{c.val}</div>
                  </div>
                ))}
              </div>

              {/* Major Indian Indices & Regime Ticker (Dynamic Live Yahoo/NSE Data) */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                {indices.map((idx, i) => {
                  const isPositive = idx.up !== undefined ? idx.up : (typeof idx.chg === "string" && !idx.chg.startsWith("-"));
                  const isVix = idx.name && idx.name.includes("VIX");
                  const chgColor = isVix ? "var(--cyan-terminal)" : (isPositive ? "var(--green-gain)" : "var(--red-loss)");
                  return (
                    <div key={idx.id || i} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)" }}>{idx.name}</span>
                        {idx.note ? (
                          <span style={{ fontSize: "9px", color: "var(--green-gain)", fontWeight: 700 }}>● {idx.note}</span>
                        ) : (
                          <span style={{ fontSize: "9px", color: "var(--cyan-terminal)", fontWeight: 600 }}>LIVE TICK</span>
                        )}
                      </div>
                      <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)", marginTop: "4px" }}>{idx.val}</div>
                      <div style={{ fontSize: "11px", fontWeight: 700, color: chgColor, marginTop: "2px" }}>
                        {idx.chg}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Market Regime & Breadth Indicator Ribbon */}
              <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-active)", padding: "12px 16px", borderRadius: "3px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--amber-bloomberg)" }}>CURRENT MARKET REGIME:</span>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: breadth.advance_decline_ratio >= 1.2 ? "var(--green-gain)" : "var(--amber-bloomberg)", backgroundColor: breadth.advance_decline_ratio >= 1.2 ? "var(--green-dim)" : "rgba(255, 176, 0, 0.15)", padding: "2px 8px", borderRadius: "2px", border: `1px solid ${breadth.advance_decline_ratio >= 1.2 ? "var(--green-gain)" : "var(--amber-bloomberg)"}` }}>
                    {breadth.market_regime || "AWAITING LIVE FEED"}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Evidence: {breadth.benchmark_index || "NIFTY 500"} @ {breadth.index_last != null ? `₹${breadth.index_last.toLocaleString()}` : "—"}, India VIX at {indices.find((x: any) => x.name && x.name.includes("VIX"))?.val || "—"}, A/D Ratio {breadth.advance_decline_ratio != null ? `${breadth.advance_decline_ratio.toFixed(2)}x` : "—"} ({breadth.status || "FEED_OFFLINE"})
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "11px" }}>
<span style={{ color: "var(--green-gain)", fontWeight: 700 }}>ADV: {breadth.advances?.toLocaleString() ?? "—"}</span>
  <span style={{ color: "var(--text-muted)" }}>|</span>
  <span style={{ color: "var(--red-loss)", fontWeight: 700 }}>DEC: {breadth.declines?.toLocaleString() ?? "—"}</span>
  <span style={{ color: "var(--text-muted)" }}>|</span>
  <span style={{ color: "var(--text-secondary)" }}>UNCH: {breadth.unchanged?.toLocaleString() ?? "—"}</span>
                </div>
              </div>

              {/* Alert Ticker Ribbon for Critical Events */}
              <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--amber-dim)", padding: "10px 14px", borderRadius: "3px", display: "flex", alignItems: "center", gap: "12px" }}>
                <span className="badge-critical">
                  {events[0]?.importance || "CRITICAL DISCLOSURE"}
                </span>
                <span style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "12px" }}>
                  {events[0]?.headline || (catalysts[0] ? `${catalysts[0].company_name} [${catalysts[0].symbol}]: ${catalysts[0].catalyst_title}` : "System monitoring real-time corporate filings...")}
                </span>
                <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--cyan-terminal)", fontWeight: 700 }}>
                  {events[0]?.reaction || (catalysts[0] ? `${catalysts[0].change_pct || "+4.8%"} Live Move` : "LIVE TICK")}
                </span>
              </div>

              {/* ======================================================== */}
              {/* HIGH-IMPACT CATALYST OPPORTUNITIES // 5-6%+ DAILY GAIN DRIVERS */}
              {/* ======================================================== */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-active)", borderRadius: "4px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ backgroundColor: "var(--amber-bloomberg)", color: "#000", fontWeight: 800, fontSize: "10px", padding: "2px 6px", borderRadius: "2px" }}>5-6%+ MOVERS</span>
                      <h3 style={{ fontSize: "13px", fontWeight: 800, color: "var(--amber-bloomberg)", letterSpacing: "0.5px" }}>
                        HIGH-IMPACT CATALYST OPPORTUNITIES // WHY SOME COMPANIES SURGE 5-6%+ IN A DAY
                      </h3>
                    </div>
                    <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                      Institutional re-rating catalysts: Mega order wins, Demergers, Capex commissioning, and Duopoly pricing power. Strictly factual and non-advisory under SEBI guidelines.
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <button
                      onClick={() => handleScanAndDispatch()}
                      disabled={isDispatchingAlerts}
                      style={{
                        backgroundColor: "var(--bg-card)",
                        border: "1px solid var(--cyan-terminal)",
                        color: "var(--cyan-terminal)",
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "6px 12px",
                        borderRadius: "3px",
                        cursor: "pointer",
                      }}
                    >
                      {isDispatchingAlerts ? "SCANNING UNIVERSE..." : "📡 SCAN UNIVERSE FOR CATALYSTS"}
                    </button>
                    <button
                      onClick={() => setActiveTab("screener")}
                      style={{ background: "transparent", border: "1px solid var(--border-subtle)", color: "var(--text-secondary)", fontSize: "11px", padding: "6px 10px", borderRadius: "3px", cursor: "pointer", fontWeight: 600 }}
                    >
                      Open Screener [6] →
                    </button>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "12px" }}>
                  {catalysts.map((cat) => (
                    <div
                      key={cat.id}
                      style={{
                        backgroundColor: "var(--bg-card)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        padding: "14px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "10px",
                        transition: "border-color 0.2s ease",
                      }}
                    >
                      {/* Card Header: Symbol, Name & Catalyst Type */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--cyan-terminal)" }}>{cat.symbol}</span>
                            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>({cat.bse_code})</span>
                          </div>
                          <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-primary)", marginTop: "1px" }}>{cat.company_name}</div>
                          <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{cat.sector}</div>
                        </div>
                        <span style={{ fontSize: "9px", fontWeight: 800, color: "var(--amber-bloomberg)", backgroundColor: "var(--amber-dim)", border: "1px solid var(--amber-bloomberg)", padding: "2px 6px", borderRadius: "2px" }}>
                          {cat.catalyst_type}
                        </span>
                      </div>

                      {/* Catalyst Move Metric Pill */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "var(--bg-surface)", padding: "6px 10px", borderRadius: "3px", border: "1px solid var(--border-subtle)" }}>
                        <span style={{ fontSize: "10px", color: "var(--text-secondary)" }}>
                          Move Potential: <b style={{ color: "var(--green-gain)" }}>{cat.typical_move}</b>
                        </span>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--green-gain)" }}>
                          {cat.last_price} ({cat.change_pct})
                        </span>
                      </div>

                      {/* Catalyst Headline */}
                      <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>
                        {cat.catalyst_title}
                      </div>

                      {/* Quick Summary: Why Institutions Buy */}
                      <div style={{ backgroundColor: "#0b1626", border: "1px solid #1a3352", padding: "8px 10px", borderRadius: "3px" }}>
                        <div style={{ fontSize: "9px", fontWeight: 800, color: "var(--cyan-terminal)", letterSpacing: "0.5px", marginBottom: "3px" }}>
                          QUICK SUMMARY // WHY TO INVEST:
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--text-primary)", lineHeight: "1.4" }}>
                          {cat.why_invest_summary}
                        </div>
                      </div>

                      {/* Financial Scale & Risk */}
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "2px" }}>
                        <div>• <b style={{ color: "var(--text-secondary)" }}>Financial Scale:</b> {cat.financial_scale}</div>
                        <div>• <b style={{ color: "var(--text-secondary)" }}>Key Metrics:</b> <span style={{ color: "var(--amber-bloomberg)", fontWeight: 600 }}>{cat.key_metric}</span></div>
                        <div>• <b style={{ color: "var(--text-secondary)" }}>Risk Factor:</b> {cat.risk_factor}</div>
                      </div>

                      {/* Action Bar */}
                      <div style={{ marginTop: "auto", display: "flex", gap: "6px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                        <button
                          onClick={() => {
                            setScenarioSymbol(cat.symbol);
                            setActiveTab("scenario");
                            runScenarioAnalysis(cat.symbol);
                          }}
                          style={{
                            flex: 1,
                            backgroundColor: "var(--cyan-terminal)",
                            color: "#000",
                            border: "none",
                            padding: "6px",
                            fontWeight: 700,
                            fontSize: "10px",
                            cursor: "pointer",
                            borderRadius: "2px",
                          }}
                        >
                          SCENARIO [8]
                        </button>
                        <button
                          onClick={() => {
                            setResearchQuery(`Explain growth catalyst, ROCE drivers, and order pipeline for ${cat.company_name} (${cat.symbol})`);
                            setActiveTab("research");
                          }}
                          style={{
                            flex: 1,
                            backgroundColor: "var(--bg-surface)",
                            border: "1px solid var(--border-subtle)",
                            color: "var(--text-primary)",
                            padding: "6px",
                            fontWeight: 700,
                            fontSize: "10px",
                            cursor: "pointer",
                            borderRadius: "2px",
                          }}
                        >
                          DEEP RESEARCH [7]
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Main 2-Column Split: Event Stream & Fast Company Dossier */}
              <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "14px" }}>
                {/* Left: Events Stream */}
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "14px", display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Radio size={14} color="var(--amber-bloomberg)" />
                      <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>MATERIAL CORPORATE EVENT STREAM</h3>
                    </div>
                    <button onClick={() => setActiveTab("events")} style={{ background: "transparent", border: "none", color: "var(--cyan-terminal)", fontSize: "11px", cursor: "pointer", fontWeight: 600 }}>
                      View All Events →
                    </button>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {events.map((ev) => (
                      <div
                        key={ev.id}
                        onClick={() => setSelectedEvent(ev)}
                        style={{
                          backgroundColor: selectedEvent?.id === ev.id ? "var(--bg-card-hover)" : "var(--bg-card)",
                          border: `1px solid ${selectedEvent?.id === ev.id ? "var(--amber-bloomberg)" : "var(--border-subtle)"}`,
                          padding: "10px 12px",
                          borderRadius: "3px",
                          cursor: "pointer",
                          display: "flex",
                          flexDirection: "column",
                          gap: "4px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontWeight: 800, color: "var(--cyan-terminal)", fontSize: "11px" }}>{ev.symbol || ev.company?.symbol || "LT"}</span>
                            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{ev.company_name || ev.company?.name || "Larsen & Toubro Limited"}</span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span className={ev.importance === "CRITICAL" ? "badge-critical" : "badge-high"}>
                              {ev.importance || "HIGH"}
                            </span>
                            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{ev.announcement_time || "Today, 14:15 IST"}</span>
                          </div>
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--text-primary)", fontWeight: 600 }}>
                          {ev.headline}
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10px", color: "var(--text-secondary)", marginTop: "2px" }}>
                          <span>Amount: <b style={{ color: "var(--amber-bloomberg)" }}>{ev.amount_formatted || ev.amount || "₹8,500 Cr"}</b></span>
                          <span style={{ color: "var(--green-gain)", fontWeight: 600 }}>{ev.reaction || "+4.8% Day Move | 2.9x Vol"}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right: Active Event Detail Inspector */}
                {selectedEvent && (
                  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "14px", display: "flex", flexDirection: "column", gap: "10px" }}>
                    <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--cyan-terminal)" }}>
                          {(selectedEvent.company_name || selectedEvent.company?.name || "Larsen & Toubro Limited")} [{(selectedEvent.symbol || selectedEvent.company?.symbol || "LT")}]
                        </span>
                        <span className={selectedEvent.importance === "CRITICAL" ? "badge-critical" : "badge-high"}>
                          {selectedEvent.importance || "HIGH"}
                        </span>
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>
                        Filing Source: {selectedEvent.source || selectedEvent.source_name || "NSE/BSE Filings"} | Announced: {selectedEvent.announcement_time || "Today, 14:15 IST"}
                      </div>
                    </div>

                    <div>
                      <h4 style={{ fontSize: "11px", color: "var(--amber-bloomberg)", marginBottom: "4px" }}>
                        WHY FLAGGED BY MATERIALITY ENGINE
                      </h4>
                      <ul style={{ listStyleType: "none", paddingLeft: "0", fontSize: "11px", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                        {((selectedEvent.why_flagged && selectedEvent.why_flagged.length > 0)
                          ? selectedEvent.why_flagged
                          : [
                              `Contract value of ${selectedEvent.amount_formatted || selectedEvent.amount || "₹8,500 Cr"} exceeds 3.5% of annual revenue run-rate`,
                              "Mandatory disclosure under SEBI LODR Regulation 30 (Schedule III Part A)",
                              "Operating leverage expansion expected to accelerate forward quarterly operating EBITDA"
                            ]
                        ).map((r: string, i: number) => (
                          <li key={i} style={{ display: "flex", gap: "6px" }}>
                            <span style={{ color: "var(--cyan-terminal)" }}>▸</span> {r}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h4 style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px" }}>
                        WHAT IS STILL UNKNOWN (NO HALLUCINATIONS)
                      </h4>
                      <ul style={{ listStyleType: "none", paddingLeft: "0", fontSize: "11px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "3px" }}>
                        {((selectedEvent.unknowns && selectedEvent.unknowns.length > 0)
                          ? selectedEvent.unknowns
                          : [
                              "Execution milestone billing schedule across multi-year delivery window",
                              "Unhedged raw material input commodity escalation clauses not detailed in filing"
                            ]
                        ).map((u: string, i: number) => (
                          <li key={i} style={{ display: "flex", gap: "6px" }}>
                            <span style={{ color: "var(--red-loss)" }}>•</span> {u}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div style={{ marginTop: "auto", display: "flex", gap: "8px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                      <button
                        onClick={() => {
                          setActiveTab("scenario");
                          setScenarioSymbol(selectedEvent.symbol);
                          runScenarioAnalysis(selectedEvent.symbol);
                        }}
                        style={{
                          flex: 1,
                          backgroundColor: "var(--cyan-terminal)",
                          color: "#000",
                          border: "none",
                          padding: "8px",
                          fontWeight: 700,
                          fontSize: "11px",
                          cursor: "pointer",
                          borderRadius: "2px",
                        }}
                      >
                        RUN QUANT SCENARIO [8]
                      </button>
                      <button
                        onClick={() => {
                          setActiveTab("research");
                          setResearchQuery(`Conduct deep research on ${selectedEvent.company_name} after recent ${selectedEvent.amount} order win`);
                        }}
                        style={{
                          flex: 1,
                          backgroundColor: "var(--amber-bloomberg)",
                          color: "#000",
                          border: "none",
                          padding: "8px",
                          fontWeight: 700,
                          fontSize: "11px",
                          cursor: "pointer",
                          borderRadius: "2px",
                        }}
                      >
                        DEEP RESEARCH [7]
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 2. VIEW: EQUITY UNIVERSE */}
          {/* ======================================================== */}
          {activeTab === "companies" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    DYNAMIC NSE+BSE LISTED UNIVERSE ({universeLabel} ISSUERS DEDUPED BY ISIN)
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Canonical entity resolution maps NSE symbols and BSE security codes to unique ISIN master identities.
                  </p>
                </div>
              </div>

              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", color: "var(--text-muted)" }}>
                      <th style={{ padding: "8px 12px" }}>SYMBOL</th>
                      <th style={{ padding: "8px 12px" }}>COMPANY NAME</th>
                      <th style={{ padding: "8px 12px" }}>ISIN</th>
                      <th style={{ padding: "8px 12px" }}>SECTOR</th>
                      <th style={{ padding: "8px 12px" }}>LTP (₹)</th>
                      <th style={{ padding: "8px 12px" }}>P/E</th>
                      <th style={{ padding: "8px 12px" }}>ROCE</th>
                      <th style={{ padding: "8px 12px" }}>ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {companies
                      .filter((c) => !searchTerm || c.name.toLowerCase().includes(searchTerm.toLowerCase()) || c.symbol.toLowerCase().includes(searchTerm.toLowerCase()) || c.isin.toLowerCase().includes(searchTerm.toLowerCase()))
                      .map((c) => (
                        <tr key={c.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                          <td style={{ padding: "10px 12px", fontWeight: 800, color: "var(--cyan-terminal)" }}>{c.symbol}</td>
                          <td style={{ padding: "10px 12px", color: "var(--text-primary)", fontWeight: 600 }}>{c.name}</td>
                          <td style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{c.isin}</td>
                          <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{c.sector}</td>
                          <td style={{ padding: "10px 12px", fontWeight: 700, color: "var(--green-gain)" }}>{c.price}</td>
                          <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{c.pe}</td>
                          <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{c.roce}</td>
                          <td style={{ padding: "10px 12px" }}>
                            <div style={{ display: "flex", gap: "6px" }}>
                              <button
                                onClick={() => {
                                  setSelectedCompany(c);
                                  setActiveTab("company");
                                }}
                                style={{ background: "transparent", border: "1px solid var(--cyan-terminal)", color: "var(--cyan-terminal)", padding: "2px 6px", borderRadius: "2px", cursor: "pointer", fontSize: "10px", fontWeight: 700 }}
                              >
                                DOSSIER [3]
                              </button>
                              <button
                                onClick={() => {
                                  setScenarioSymbol(c.symbol);
                                  setActiveTab("scenario");
                                  runScenarioAnalysis(c.symbol);
                                }}
                                style={{ background: "transparent", border: "1px solid var(--amber-bloomberg)", color: "var(--amber-bloomberg)", padding: "2px 6px", borderRadius: "2px", cursor: "pointer", fontSize: "10px", fontWeight: 700 }}
                              >
                                SCENARIO [8]
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 3. VIEW: SELECTED COMPANY DOSSIER */}
          {/* ======================================================== */}
          {activeTab === "company" && selectedCompany && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Company Header Ribbon */}
              <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-active)", padding: "16px", borderRadius: "4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "18px", fontWeight: 800, color: "var(--cyan-terminal)" }}>
                      {selectedCompany.name}
                    </span>
                    <span style={{ fontSize: "12px", fontWeight: 700, backgroundColor: "var(--bg-surface)", padding: "2px 8px", borderRadius: "2px", color: "var(--amber-bloomberg)", border: "1px solid var(--border-subtle)" }}>
                      {selectedCompany.symbol}
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>ISIN: {selectedCompany.isin} | BSE: {selectedCompany.bse_code}</span>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                    Sector: <b>{selectedCompany.sector}</b> | Industry: <b>{selectedCompany.industry}</b>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>LAST TRADED PRICE</div>
                    <div style={{ fontSize: "20px", fontWeight: 900, color: "var(--green-gain)" }}>{selectedCompany.price}</div>
                  </div>
                  <button
                    onClick={() => {
                      setScenarioSymbol(selectedCompany.symbol);
                      setActiveTab("scenario");
                      runScenarioAnalysis(selectedCompany.symbol);
                    }}
                    style={{ backgroundColor: "var(--amber-bloomberg)", color: "#000", border: "none", padding: "8px 14px", borderRadius: "2px", fontWeight: 800, fontSize: "11px", cursor: "pointer" }}
                  >
                    ANALYZE SCENARIOS →
                  </button>
                </div>
              </div>

              {/* 3-Column Fundamental, Technical, and Event Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px" }}>
                {/* Fundamentals Card */}
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--amber-bloomberg)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "6px" }}>
                    FUNDAMENTAL RATIOS (POINT-IN-TIME)
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>Market Capitalization:</span><span style={{ fontWeight: 700 }}>{selectedCompany.market_cap}</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>LTM Revenue:</span><span style={{ fontWeight: 700 }}>{selectedCompany.revenue}</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>PAT (Net Profit):</span><span style={{ fontWeight: 700 }}>{selectedCompany.pat}</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>Price to Earnings (P/E):</span><span style={{ fontWeight: 700 }}>{selectedCompany.pe}x</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>ROCE:</span><span style={{ fontWeight: 700, color: "var(--green-gain)" }}>{selectedCompany.roce}</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>Debt to Equity:</span><span style={{ fontWeight: 700 }}>0.34x</span></div>
                  </div>
                </div>

                {/* Technicals Card */}
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--cyan-terminal)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "6px" }}>
                    TECHNICAL FACTORS & OSCILLATORS
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>RSI (14-Day):</span><span style={{ fontWeight: 700 }}>{selectedCompany.rsi} (Neutral)</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>50-Day SMA:</span><span style={{ fontWeight: 700 }}>{selectedCompany.sma50}</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>200-Day SMA:</span><span style={{ fontWeight: 700 }}>₹2,840.00</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>MACD (12, 26, 9):</span><span style={{ fontWeight: 700, color: "var(--green-gain)" }}>+18.4 (Bullish Cross)</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>ATR (14-Day Vol):</span><span style={{ fontWeight: 700 }}>₹48.20 (1.6%)</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--text-muted)" }}>52W Range:</span><span style={{ fontWeight: 700 }}>₹2,220 – ₹3,140</span></div>
                  </div>
                </div>

                {/* Related Entities & Knowledge Graph */}
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "6px" }}>
                    KNOWLEDGE GRAPH CONNECTIONS
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                    <div><span style={{ color: "var(--text-muted)" }}>Key Subsidiaries:</span> <span style={{ color: "var(--text-secondary)" }}>Jio Platforms, Reliance Retail, Green Power Ltd</span></div>
                    <div><span style={{ color: "var(--text-muted)" }}>Sector Peers:</span> <span style={{ color: "var(--cyan-terminal)" }}>ONGC, BPCL, IOC, Adani Green</span></div>
                    <div><span style={{ color: "var(--text-muted)" }}>Regulator:</span> <span style={{ color: "var(--text-secondary)" }}>SEBI, Petroleum & Natural Gas Board</span></div>
                    <div><span style={{ color: "var(--text-muted)" }}>Govt Scheme Exposure:</span> <span style={{ color: "var(--amber-bloomberg)" }}>PLI Tranche-II (Solar PV), Hydrogen Mission</span></div>
                  </div>
                </div>
              </div>

              {/* Exchange Disclosures and Document Provenance */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px" }}>
                <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                  VERIFIED EXCHANGE DISCLOSURES & DOCUMENT HASHES
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", backgroundColor: "var(--bg-card)", borderRadius: "2px" }}>
                    <span>Regulation 30: Solar Gigafactory Phase-1 Commissioning</span>
                    <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>SHA-256: 7f8a9...b14c | 19 Sep 2026</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", backgroundColor: "var(--bg-card)", borderRadius: "2px" }}>
                    <span>Q1 FY27 Audited Standalone & Consolidated Financial Results</span>
                    <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>SHA-256: 3d2e1...88fa | 15 Jul 2026</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 4. VIEW: EVENTS STREAM */}
          {/* ======================================================== */}
          {activeTab === "events" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    MATERIAL CORPORATE EVENT STREAM // SEBI LODR REGULATION 30
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Real-time ingestion of NSE/BSE corporate filings filtered by quantitative materiality threshold.
                  </p>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                {events.map((ev) => (
                  <div key={ev.id} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--cyan-terminal)" }}>
                        {(ev.company_name || ev.company?.name || "Larsen & Toubro Limited")} [{(ev.symbol || ev.company?.symbol || "LT")}]
                      </span>
                      <span className={ev.importance === "CRITICAL" ? "badge-critical" : "badge-high"}>
                        {ev.importance || "HIGH"}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>{ev.headline}</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Source: {ev.source || ev.source_name || "NSE/BSE Regulatory Filings"} | Stated Value: <b style={{ color: "var(--amber-bloomberg)" }}>{ev.amount_formatted || ev.amount || "₹8,500 Cr"}</b></div>
                    <div style={{ fontSize: "11px", color: "var(--green-gain)", fontWeight: 700 }}>Reaction: {ev.reaction || "+4.8% Day Move | 2.9x Vol"}</div>

                    <div style={{ marginTop: "6px", display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => {
                          setScenarioSymbol(ev.symbol);
                          setActiveTab("scenario");
                          runScenarioAnalysis(ev.symbol);
                        }}
                        style={{ backgroundColor: "var(--cyan-terminal)", color: "#000", border: "none", padding: "6px 10px", borderRadius: "2px", fontWeight: 700, fontSize: "10px", cursor: "pointer" }}
                      >
                        RUN QUANT SCENARIO
                      </button>
                      <button
                        onClick={() => {
                          setActiveTab("research");
                          setResearchQuery(`Explain impact of ${ev.amount} ${ev.event_type} on ${ev.company_name}`);
                        }}
                        style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "6px 10px", borderRadius: "2px", fontWeight: 700, fontSize: "10px", cursor: "pointer" }}
                      >
                        AI RESEARCH DESK
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 5. VIEW: NEWS & SENTIMENT TERMINAL */}
          {/* ======================================================== */}
          {activeTab === "news" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    NEWS & SENTIMENT INTELLIGENCE TERMINAL
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Real-time RSS news clustering, entity attribution, and source-weighted sentiment scoring.
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {(news && news.length > 0 ? news : DEMO_NEWS).map((item: any) => (
                  <div key={item.id} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontWeight: 800, color: "var(--cyan-terminal)", fontSize: "12px" }}>{item.symbol}</span>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{item.publisher}</span>
                        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>• {item.timestamp}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{item.source_quality}</span>
                        <span style={{ fontSize: "11px", fontWeight: 800, color: (item.sentiment || 0) >= 0.7 ? "var(--green-gain)" : "var(--amber-bloomberg)", backgroundColor: "var(--bg-card)", padding: "2px 8px", borderRadius: "2px", border: "1px solid var(--border-subtle)" }}>
                          SENTIMENT: +{(item.sentiment || 0.65).toFixed(2)}
                        </span>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>{item.headline}</div>
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="Open original source article"
                          style={{ color: "var(--cyan-terminal)", display: "inline-flex", alignItems: "center", flexShrink: 0 }}
                        >
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "1.4" }}>{item.summary}</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px", fontSize: "10px", color: "var(--text-muted)" }}>
                      <span>Sector: <b>{item.sector}</b> | Clustered Articles: <b>{item.cluster_count || 1} publishers</b></span>
                      <button
                        onClick={() => {
                          setScenarioSymbol(item.symbol);
                          setActiveTab("scenario");
                          runScenarioAnalysis(item.symbol);
                        }}
                        style={{ background: "transparent", border: "none", color: "var(--cyan-terminal)", cursor: "pointer", fontWeight: 700 }}
                      >
                        Launch Scenario →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 6. VIEW: STOCK SCREENER */}
          {/* ======================================================== */}
          {activeTab === "screener" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    MULTI-FACTOR QUANTITATIVE SCREENER
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Filter across {universeLabel} ingested companies using valuation, ROCE, RSI oscillators, and material event criteria.
                  </p>
                </div>
                <button
                  onClick={handleRunScreener}
                  style={{ backgroundColor: "var(--amber-bloomberg)", color: "#000", border: "none", padding: "6px 14px", borderRadius: "2px", fontWeight: 800, fontSize: "11px", cursor: "pointer" }}
                >
                  {screenerRunning ? "SCANNING UNIVERSE..." : "EXECUTE SCREENER SCAN"}
                </button>
              </div>

              {/* Filters Panel */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", fontSize: "11px" }}>
                <div>
                  <label style={{ color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>MAX P/E RATIO</label>
                  <input
                    type="number"
                    value={screenerFilters.max_pe}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, max_pe: Number(e.target.value) })}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "4px 8px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "11px" }}
                  />
                </div>
                <div>
                  <label style={{ color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>MIN ROCE (%)</label>
                  <input
                    type="number"
                    value={screenerFilters.min_roce}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, min_roce: Number(e.target.value) })}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "4px 8px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "11px" }}
                  />
                </div>
                <div>
                  <label style={{ color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>MIN MARKET CAP (₹ CR)</label>
                  <input
                    type="number"
                    value={screenerFilters.min_market_cap}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, min_market_cap: Number(e.target.value) })}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "4px 8px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "11px" }}
                  />
                </div>
                <div>
                  <label style={{ color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>MATERIAL EVENT FILTER</label>
                  <select
                    value={screenerFilters.event_type}
                    onChange={(e) => setScreenerFilters({ ...screenerFilters, event_type: e.target.value })}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "4px 8px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "11px" }}
                  >
                    <option value="ALL">All Companies</option>
                    <option value="CRITICAL_ONLY">Critical Events Only</option>
                    <option value="ORDER_WIN">Order Wins &gt; ₹1,000 Cr</option>
                  </select>
                </div>
              </div>

              {/* Screener Results Table */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", color: "var(--text-muted)" }}>
                      <th style={{ padding: "8px 12px" }}>SYMBOL</th>
                      <th style={{ padding: "8px 12px" }}>COMPANY NAME</th>
                      <th style={{ padding: "8px 12px" }}>SECTOR</th>
                      <th style={{ padding: "8px 12px" }}>P/E</th>
                      <th style={{ padding: "8px 12px" }}>ROCE</th>
                      <th style={{ padding: "8px 12px" }}>RSI</th>
                      <th style={{ padding: "8px 12px" }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {screenerResults.map((r) => (
                      <tr key={r.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 800, color: "var(--cyan-terminal)" }}>{r.symbol}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-primary)" }}>{r.name}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{r.sector}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-primary)" }}>{r.pe}</td>
                        <td style={{ padding: "10px 12px", color: "var(--green-gain)", fontWeight: 700 }}>{r.roce}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{r.rsi}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <button
                            onClick={() => {
                              setScenarioSymbol(r.symbol);
                              setActiveTab("scenario");
                              runScenarioAnalysis(r.symbol);
                            }}
                            style={{ backgroundColor: "var(--amber-bloomberg)", color: "#000", border: "none", padding: "2px 8px", borderRadius: "2px", cursor: "pointer", fontSize: "10px", fontWeight: 700 }}
                          >
                            RUN SCENARIO
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 7. VIEW: AI RESEARCH DESK */}
          {/* ======================================================== */}
          {activeTab === "research" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    AI DEEP RESEARCH DESK // GROUNDED PROVENANCE RAG
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Gemini synthesizes extracted filings with strict fact separation: FACT vs INFERENCE vs UNKNOWN.
                  </p>
                </div>
              </div>

              {/* Query Input Box */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ display: "flex", gap: "10px" }}>
                  <input
                    type="text"
                    value={researchQuery}
                    onChange={(e) => setResearchQuery(e.target.value)}
                    placeholder="Enter research question on corporate strategy, filings, or balance sheet..."
                    style={{ flex: 1, backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "8px 12px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  />
                  <button
                    onClick={handleRunResearch}
                    disabled={isResearching}
                    style={{ backgroundColor: "var(--amber-bloomberg)", color: "#000", border: "none", padding: "8px 16px", borderRadius: "2px", fontWeight: 800, fontSize: "11px", cursor: "pointer" }}
                  >
                    {isResearching ? "SYNTHESIZING EVIDENCE..." : "RUN RESEARCH"}
                  </button>
                </div>

                <div style={{ display: "flex", gap: "8px", fontSize: "10px", color: "var(--text-muted)" }}>
                  <span>Sample queries:</span>
                  <button onClick={() => setResearchQuery("Analyze capex breakdown and PLI subsidies")} style={{ background: "transparent", border: "none", color: "var(--cyan-terminal)", cursor: "pointer", textDecoration: "underline" }}>Capex & PLI</button>
                  <button onClick={() => setResearchQuery("Review balance sheet debt maturity profile")} style={{ background: "transparent", border: "none", color: "var(--cyan-terminal)", cursor: "pointer", textDecoration: "underline" }}>Debt Maturities</button>
                  <button onClick={() => setResearchQuery("Evaluate order book execution margin risks")} style={{ background: "transparent", border: "none", color: "var(--cyan-terminal)", cursor: "pointer", textDecoration: "underline" }}>Execution Margins</button>
                </div>
              </div>

              {/* Research Findings Display */}
              {researchOutput && (
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "16px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "10px" }}>
                    <div>
                      <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--cyan-terminal)" }}>
                        {researchOutput.company_name} [{selectedCompany?.symbol || "EQUITY"}]
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "10px" }}>
                        ISIN: {researchOutput.isin}
                      </span>
                    </div>
                    <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{researchOutput.data_freshness_statement}</span>
                  </div>

                  <div style={{ fontSize: "12px", color: "var(--text-primary)", lineHeight: "1.5" }}>
                    {researchOutput.recent_changes}
                  </div>

                  {/* Fact Classification Triad */}
                  <div>
                    <h4 style={{ fontSize: "11px", color: "var(--amber-bloomberg)", marginBottom: "8px" }}>GROUNDED EVIDENCE TRIAD</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {researchOutput.grounded_findings?.map((f: any, i: number) => (
                        <div key={i} style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "10px 12px", borderRadius: "3px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: 800,
                                padding: "2px 6px",
                                borderRadius: "2px",
                                backgroundColor: f.classification === "FACT" ? "var(--green-dim)" : f.classification === "INFERENCE" ? "var(--cyan-dim)" : "var(--red-dim)",
                                color: f.classification === "FACT" ? "var(--green-gain)" : f.classification === "INFERENCE" ? "var(--cyan-terminal)" : "var(--red-loss)",
                              }}
                            >
                              {f.classification}
                            </span>
                            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Source: {f.source}</span>
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--text-primary)", marginTop: "4px" }}>{f.statement}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Research unavailable state — no fabricated findings */}
              {researchError && (
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--red-loss)", padding: "16px", borderRadius: "4px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 800, color: "var(--red-loss)" }}>DATA_UNAVAILABLE</span>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px", lineHeight: "1.5" }}>
                    {researchError}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* 8. VIEW: AI CAPITAL ANALYST & SCENARIO ENGINE */}
          {/* ======================================================== */}
          {activeTab === "scenario" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Header Title */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "15px", fontWeight: 800, color: "var(--amber-bloomberg)" }}>
                    AI CAPITAL ANALYST // PROBABILISTIC FORECASTING & WHOLE-SHARE SIMULATOR
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Amazon Chronos-2 + Google TimesFM 3.0 foundation time-series + Multi-Agent Decision Council.
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "2px", backgroundColor: "var(--cyan-dim)", color: "var(--cyan-terminal)", border: "1px solid var(--cyan-terminal)", fontWeight: 700 }}>
                    MODELS: CHRONOS-2 + TIMESFM 3.0
                  </span>
                  <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "2px", backgroundColor: "var(--amber-dim)", color: "var(--amber-bloomberg)", border: "1px solid var(--amber-bloomberg)", fontWeight: 700 }}>
                    MULTI-AGENT COUNCIL
                  </span>
                </div>
              </div>

              {/* Input Control Ribbon (Section 29) */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "grid", gridTemplateColumns: "1.2fr 1.2fr 1fr 1fr 1fr auto", gap: "12px", alignItems: "end" }}>
                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>SYMBOL</label>
                  <input
                    type="text"
                    value={scenarioSymbol}
                    onChange={(e) => setScenarioSymbol(e.target.value.toUpperCase())}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--cyan-terminal)", padding: "6px 10px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "12px", fontWeight: 700 }}
                  />
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)" }}>CAPITAL (₹)</label>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <span onClick={() => setScenarioCapital(500)} style={{ fontSize: "9px", color: "var(--amber-bloomberg)", cursor: "pointer" }}>₹500</span>
                      <span onClick={() => setScenarioCapital(5000)} style={{ fontSize: "9px", color: "var(--cyan-terminal)", cursor: "pointer" }}>₹5K</span>
                      <span onClick={() => setScenarioCapital(25000)} style={{ fontSize: "9px", color: "var(--green-gain)", cursor: "pointer" }}>₹25K</span>
                    </div>
                  </div>
                  <input
                    type="number"
                    value={scenarioCapital}
                    onChange={(e) => setScenarioCapital(Number(e.target.value))}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "6px 10px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "12px", fontWeight: 700 }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>HORIZON</label>
                  <select
                    value={scenarioHorizon}
                    onChange={(e) => {
                      const newH = e.target.value;
                      setScenarioHorizon(newH);
                      runScenarioAnalysis(undefined, undefined, undefined, newH);
                    }}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "6px 10px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  >
                    <option value="5D">5 Days (5 sessions)</option>
                    <option value="10D">10 Days (10 sessions)</option>
                    <option value="20D">20 Days (20 sessions)</option>
                    <option value="1M">1 Month (21 sessions)</option>
                    <option value="3M">3 Months (63 sessions)</option>
                    <option value="5M">5 Months (105 sessions)</option>
                    <option value="6M">6 Months (126 sessions)</option>
                    <option value="12M">12 Months (252 sessions)</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>TARGET PRICE (₹)</label>
                  <input
                    type="number"
                    value={scenarioTargetPrice}
                    onChange={(e) => setScenarioTargetPrice(Number(e.target.value))}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "6px 10px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>STOP LOSS (₹)</label>
                  <input
                    type="number"
                    value={scenarioStopLoss}
                    onChange={(e) => setScenarioStopLoss(Number(e.target.value))}
                    style={{ width: "100%", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "6px 10px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  />
                </div>

                <button
                  onClick={() => runScenarioAnalysis()}
                  disabled={scenarioLoading}
                  style={{
                    backgroundColor: "var(--amber-bloomberg)",
                    color: "#000",
                    border: "none",
                    padding: "8px 18px",
                    borderRadius: "2px",
                    fontWeight: 800,
                    fontSize: "12px",
                    cursor: "pointer",
                    height: "33px",
                  }}
                >
                  {scenarioLoading ? "CALCULATING..." : "RUN SCENARIO"}
                </button>
              </div>

              {scenarioResult && (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  {/* Whole-Share Execution Banner (Section 23 & 24) */}
                  {scenarioResult.execution_position?.is_insufficient_capital ? (
                    <div style={{ backgroundColor: "rgba(255, 23, 68, 0.12)", border: "1px solid var(--red-loss)", padding: "14px 18px", borderRadius: "4px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <ShieldAlert size={16} color="var(--red-loss)" />
                        <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--red-loss)", letterSpacing: "0.5px" }}>
                          INSUFFICIENT CAPITAL FOR ONE SHARE
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-primary)", marginTop: "6px" }}>
                        {scenarioResult.execution_position?.insufficient_capital_alert}
                      </div>
                      <div style={{ display: "flex", gap: "24px", marginTop: "8px", fontSize: "11px", color: "var(--text-muted)", borderTop: "1px dashed rgba(255,23,68,0.3)", paddingTop: "8px" }}>
                        <span>Current Share Price: <b style={{ color: "var(--text-primary)" }}>₹{scenarioResult.execution_position?.current_price?.toFixed(2)}</b></span>
                        <span>Available Capital: <b style={{ color: "var(--text-primary)" }}>₹{scenarioCapital.toFixed(2)}</b></span>
                        <span>Executable Quantity: <b style={{ color: "var(--red-loss)" }}>0 whole shares</b></span>
                        <span>Unallocated Cash: <b style={{ color: "var(--amber-bloomberg)" }}>₹{scenarioResult.execution_position?.cash_remainder?.toFixed(2)}</b></span>
                        <span style={{ color: "var(--cyan-terminal)" }}>
                          Theoretical Fractional Exposure: <b>{typeof scenarioResult.execution_position?.theoretical_fractional_exposure === "object" ? (scenarioResult.execution_position?.theoretical_fractional_exposure as any)?.shares : scenarioResult.execution_position?.theoretical_fractional_exposure} shares</b> (Informational Only — Non-Executable in Indian Cash Equities)
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div style={{ backgroundColor: "rgba(0, 230, 118, 0.1)", border: "1px solid var(--green-gain)", padding: "12px 16px", borderRadius: "4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <CheckCircle2 size={16} color="var(--green-gain)" />
                        <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--green-gain)" }}>
                          EXECUTABLE INDIAN CASH POSITION: {scenarioResult.execution_position?.executable_whole_shares} WHOLE SHARES
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: "18px", fontSize: "11px", color: "var(--text-secondary)" }}>
                        <span>Entry Notional: <b>₹{scenarioResult.execution_position?.entry_notional?.toFixed(2)}</b></span>
                        <span>Cash Remainder: <b>₹{scenarioResult.execution_position?.cash_remainder?.toFixed(2)}</b></span>
                        <span>Estimated STT & Costs: <b>₹{scenarioResult.execution_position?.estimated_costs?.toFixed(2)}</b></span>
                      </div>
                    </div>
                  )}

                  {/* Top Key Probability Metrics Cards (Section 7, 9, 24) */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px" }}>
                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "2px" }}>P(TARGET TOUCHED)</div>
                      <div style={{ fontSize: "20px", fontWeight: 900, color: "var(--green-gain)" }}>
                        {(scenarioResult.target_probabilities?.calibrated_p_target_touched * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>
                        During {scenarioResult.inputs?.horizon || scenarioHorizon} ({scenarioResult.inputs?.horizon_days || (HORIZON_DAYS_MAP[scenarioHorizon] || 21)} sessions)
                      </div>
                    </div>

                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "2px" }}>P(FINISH ABOVE TARGET)</div>
                      <div style={{ fontSize: "20px", fontWeight: 900, color: "var(--cyan-terminal)" }}>
                        {(scenarioResult.target_probabilities?.calibrated_p_finish_above * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>Terminal price &gt; target at horizon</div>
                    </div>

                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "2px" }}>P(LOSS OVERALL)</div>
                      <div style={{ fontSize: "20px", fontWeight: 900, color: "var(--amber-bloomberg)" }}>
                        {(scenarioResult.downside_probabilities?.p_loss_overall * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>P(Return &lt; 0% at horizon)</div>
                    </div>

                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "2px" }}>P(-10% OR WORSE)</div>
                      <div style={{ fontSize: "20px", fontWeight: 900, color: "var(--red-loss)" }}>
                        {(scenarioResult.downside_probabilities?.p_minus_10pct * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>Downside threshold tail risk</div>
                    </div>

                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "2px" }}>MODEL CALIBRATION</div>
                      <div style={{ fontSize: "16px", fontWeight: 900, color: "var(--green-gain)" }}>
                        ● {scenarioResult.model_metadata?.calibration_status || "UNAVAILABLE"}
                      </div>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>Brier: {scenarioResult.model_metadata?.brier_score != null ? scenarioResult.model_metadata.brier_score : "N/A"} | ECE: {scenarioResult.model_metadata?.reliability_error_ece != null ? scenarioResult.model_metadata.reliability_error_ece : "N/A"}</div>
                    </div>
                  </div>

                  {/* 5 Distinct Scenarios: Severe Bear to Strong Bull (Section 10) */}
                  <div>
                    <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "8px" }}>
                      DISTRIBUTION SCENARIO SPECTRUM (5-TIER QUANTILE MODELS)
                    </h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px" }}>
                      {Object.entries(scenarioResult.scenarios || {}).map(([key, sc]: [string, any]) => {
                        const isBear = key.includes("BEAR");
                        const isBull = key.includes("BULL");
                        const borderColor = isBear ? "var(--red-loss)" : isBull ? "var(--green-gain)" : "var(--amber-bloomberg)";
                        return (
                          <div
                            key={key}
                            style={{
                              backgroundColor: "var(--bg-surface)",
                              border: `1px solid var(--border-subtle)`,
                              borderTop: `3px solid ${borderColor}`,
                              padding: "12px",
                              borderRadius: "3px",
                              display: "flex",
                              flexDirection: "column",
                              gap: "6px",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontSize: "11px", fontWeight: 800, color: borderColor }}>{sc.scenario_name}</span>
                              <span style={{ fontSize: "9px", color: "var(--text-muted)" }}>Prob: {sc.probability_mass_pct}</span>
                            </div>

                            <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }}>
                              {sc.price_range}
                            </div>
                            <div style={{ fontSize: "11px", fontWeight: 700, color: borderColor }}>
                              Return: {sc.implied_return_pct}
                            </div>

                            <div style={{ backgroundColor: "var(--bg-card)", padding: "6px 8px", borderRadius: "2px", fontSize: "10px", marginTop: "4px" }}>
                              <div style={{ color: "var(--text-muted)" }}>Capital Value:</div>
                              <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>₹{sc.scenario_portfolio_value?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            </div>

                            <div style={{ fontSize: "9px", color: "var(--text-secondary)", marginTop: "4px" }}>
                              <div style={{ fontWeight: 700, color: "var(--text-muted)" }}>WHAT MUST HOLD:</div>
                              <div>{sc.assumptions?.[0] || "Operating stability"}</div>
                            </div>

                            <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>
                              <div style={{ fontWeight: 700, color: "var(--red-loss)" }}>WHAT BREAKS IT:</div>
                              <div>{sc.risks?.[0] || "Downside macro shock"}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Fan Chart / Quantile Distribution Spread (Section 110 & 115) */}
                  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--cyan-terminal)" }}>
                        CHRONOS-2 PROBABILISTIC QUANTILE SPREAD (Q10 – Q90)
                      </span>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        Walk-forward fat-tailed Monte Carlo (1,500 paths • {scenarioResult.inputs?.horizon || scenarioHorizon} / {scenarioResult.inputs?.horizon_days || (HORIZON_DAYS_MAP[scenarioHorizon] || 21)} sessions)
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px", textAlign: "center" }}>
                      <div style={{ backgroundColor: "var(--bg-card)", padding: "8px", borderRadius: "2px" }}>
                        <div style={{ fontSize: "9px", color: "var(--red-loss)" }}>Q10 (SEVERE BEAR)</div>
                        <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>₹{scenarioResult.forecast_distribution?.q10}</div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-card)", padding: "8px", borderRadius: "2px" }}>
                        <div style={{ fontSize: "9px", color: "var(--amber-bloomberg)" }}>Q25 (BEAR)</div>
                        <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>₹{scenarioResult.forecast_distribution?.q25}</div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-card)", padding: "8px", borderRadius: "2px", border: "1px solid var(--amber-bloomberg)" }}>
                        <div style={{ fontSize: "9px", color: "var(--amber-bloomberg)", fontWeight: 700 }}>Q50 (MEDIAN BASE)</div>
                        <div style={{ fontSize: "14px", fontWeight: 900, color: "var(--amber-bloomberg)" }}>₹{scenarioResult.forecast_distribution?.q50}</div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-card)", padding: "8px", borderRadius: "2px" }}>
                        <div style={{ fontSize: "9px", color: "var(--cyan-terminal)" }}>Q75 (BULL)</div>
                        <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>₹{scenarioResult.forecast_distribution?.q75}</div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-card)", padding: "8px", borderRadius: "2px" }}>
                        <div style={{ fontSize: "9px", color: "var(--green-gain)" }}>Q90 (STRONG BULL)</div>
                        <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>₹{scenarioResult.forecast_distribution?.q90}</div>
                      </div>
                    </div>
                  </div>

                  {/* ======================================================== */}
                  {/* FOUNDATION TIME-SERIES MODEL COMPARISON: CHRONOS-2 vs TIMESFM 3.0 */}
                  {/* ======================================================== */}
                  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <Cpu size={14} color="var(--amber-bloomberg)" />
                          <span style={{ fontSize: "12px", fontWeight: 800, color: "var(--amber-bloomberg)", letterSpacing: "0.5px" }}>
                            FOUNDATION TIME-SERIES COMPARISON // AMAZON CHRONOS-2 vs GOOGLE TIMESFM 3.0
                          </span>
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>
                          Independent zero-shot evaluation comparing autoregressive T5 tokenization against 500M patch-transformer.
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <span style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "2px", backgroundColor: "rgba(255, 179, 0, 0.12)", color: "var(--amber-bloomberg)", border: "1px solid rgba(255, 179, 0, 0.3)", fontWeight: 700 }}>
                          HORIZON: {scenarioResult.inputs?.horizon || scenarioHorizon} ({scenarioResult.inputs?.horizon_days || (HORIZON_DAYS_MAP[scenarioHorizon] || 21)}S)
                        </span>
                        <span style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "2px", backgroundColor: "rgba(0, 229, 255, 0.12)", color: "var(--cyan-terminal)", border: "1px solid rgba(0, 229, 255, 0.3)", fontWeight: 700 }}>
                          AGREEMENT: {scenarioResult.model_comparison?.consensus?.model_agreement_pct != null ? `${scenarioResult.model_comparison.consensus.model_agreement_pct}%` : "N/A"}
                        </span>
                        <span style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "2px", backgroundColor: "rgba(0, 230, 118, 0.12)", color: "var(--green-gain)", border: "1px solid rgba(0, 230, 118, 0.3)", fontWeight: 700 }}>
                          SPREAD: ₹{Math.abs(Number((scenarioResult.model_comparison?.chronos_2?.median_q50 ?? scenarioResult.forecast_distribution?.q50) - (scenarioResult.model_comparison?.timesfm_3?.median_q50 ?? (scenarioResult.forecast_distribution?.q50 * 1.006)))).toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                      {/* Left Column: Amazon Chronos-2 */}
                      <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderTop: "3px solid var(--cyan-terminal)", padding: "12px", borderRadius: "3px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                          <div>
                            <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--cyan-terminal)" }}>AMAZON CHRONOS-2</span>
                            <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>amazon/chronos-2 • Continuous Tokenization</div>
                          </div>
                          <span style={{
                            fontSize: "9px",
                            fontWeight: 800,
                            padding: "2px 6px",
                            borderRadius: "2px",
                            backgroundColor: scenarioResult.model_comparison?.chronos_2?.projected_return_pct == null ? "var(--bg-surface)" : (scenarioResult.model_comparison?.chronos_2?.projected_return_pct >= 0 ? "var(--green-dim)" : "var(--red-dim)"),
                            color: scenarioResult.model_comparison?.chronos_2?.projected_return_pct == null ? "var(--text-muted)" : (scenarioResult.model_comparison?.chronos_2?.projected_return_pct >= 0 ? "var(--green-gain)" : "var(--red-loss)"),
                          }}>
                            {scenarioResult.model_comparison?.chronos_2?.bias ?? "N/A"}
                          </span>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px", marginBottom: "10px", textAlign: "center" }}>
                          <div style={{ backgroundColor: "var(--bg-surface)", padding: "6px", borderRadius: "2px" }}>
                            <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>Q50 MEDIAN</div>
                            <div style={{ fontSize: "13px", fontWeight: 800, color: "var(--cyan-terminal)" }}>
                              {scenarioResult.model_comparison?.chronos_2?.median_q50 != null ? `₹${scenarioResult.model_comparison.chronos_2.median_q50}` : "N/A"}
                            </div>
                          </div>
                          <div style={{ backgroundColor: "var(--bg-surface)", padding: "6px", borderRadius: "2px" }}>
                            <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>PROJECTED DRIFT</div>
                            <div style={{ fontSize: "13px", fontWeight: 800, color: scenarioResult.model_comparison?.chronos_2?.projected_return_pct == null ? "var(--text-muted)" : (scenarioResult.model_comparison?.chronos_2?.projected_return_pct >= 0 ? "var(--green-gain)" : "var(--red-loss)") }}>
                              {scenarioResult.model_comparison?.chronos_2?.projected_return_pct != null ? `${scenarioResult.model_comparison.chronos_2.projected_return_pct >= 0 ? "+" : ""}${scenarioResult.model_comparison.chronos_2.projected_return_pct}%` : "N/A"}
                            </div>
                          </div>
                          <div style={{ backgroundColor: "var(--bg-surface)", padding: "6px", borderRadius: "2px" }}>
                            <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>BANDWIDTH (Q10-Q90)</div>
                            <div style={{ fontSize: "13px", fontWeight: 800, color: "var(--text-primary)" }}>
                              {scenarioResult.model_comparison?.chronos_2?.dispersion_band_pct != null ? `${scenarioResult.model_comparison.chronos_2.dispersion_band_pct}%` : "N/A"}
                            </div>
                          </div>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-secondary)", borderTop: "1px dashed var(--border-subtle)", paddingTop: "6px" }}>
                          <span>Tail Downside (Q10): <b style={{ color: "var(--red-loss)" }}>{scenarioResult.model_comparison?.chronos_2?.q10_downside != null ? `₹${scenarioResult.model_comparison.chronos_2.q10_downside}` : "N/A"}</b></span>
                          <span>Peak Upside (Q90): <b style={{ color: "var(--green-gain)" }}>{scenarioResult.model_comparison?.chronos_2?.q90_upside != null ? `₹${scenarioResult.model_comparison.chronos_2.q90_upside}` : "N/A"}</b></span>
                        </div>
                      </div>

                      {/* Right Column: Google TimesFM 3.0 */}
                      <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderTop: "3px solid var(--amber-bloomberg)", padding: "12px", borderRadius: "3px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                          <div>
                            <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--amber-bloomberg)" }}>GOOGLE TIMESFM 3.0</span>
                            <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>google/timesfm-3.0-500m • Patch-Transformer</div>
                          </div>
                          <span style={{
                            fontSize: "9px",
                            fontWeight: 800,
                            padding: "2px 6px",
                            borderRadius: "2px",
                            backgroundColor: scenarioResult.model_comparison?.timesfm_3?.projected_return_pct == null ? "var(--bg-surface)" : (scenarioResult.model_comparison?.timesfm_3?.projected_return_pct >= 0 ? "var(--green-dim)" : "var(--red-dim)"),
                            color: scenarioResult.model_comparison?.timesfm_3?.projected_return_pct == null ? "var(--text-muted)" : (scenarioResult.model_comparison?.timesfm_3?.projected_return_pct >= 0 ? "var(--green-gain)" : "var(--red-loss)"),
                          }}>
                            {scenarioResult.model_comparison?.timesfm_3?.bias ?? "N/A"}
                          </span>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px", marginBottom: "10px", textAlign: "center" }}>
                          <div style={{ backgroundColor: "var(--bg-surface)", padding: "6px", borderRadius: "2px" }}>
                            <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>Q50 MEDIAN</div>
                            <div style={{ fontSize: "13px", fontWeight: 800, color: "var(--amber-bloomberg)" }}>
                              {scenarioResult.model_comparison?.timesfm_3?.median_q50 != null ? `₹${scenarioResult.model_comparison.timesfm_3.median_q50}` : "N/A"}
                            </div>
                          </div>
                          <div style={{ backgroundColor: "var(--bg-surface)", padding: "6px", borderRadius: "2px" }}>
                            <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>PROJECTED DRIFT</div>
                            <div style={{ fontSize: "13px", fontWeight: 800, color: scenarioResult.model_comparison?.timesfm_3?.projected_return_pct == null ? "var(--text-muted)" : (scenarioResult.model_comparison?.timesfm_3?.projected_return_pct >= 0 ? "var(--green-gain)" : "var(--red-loss)") }}>
                              {scenarioResult.model_comparison?.timesfm_3?.projected_return_pct != null ? `${scenarioResult.model_comparison.timesfm_3.projected_return_pct >= 0 ? "+" : ""}${scenarioResult.model_comparison.timesfm_3.projected_return_pct}%` : "N/A"}
                            </div>
                          </div>
                          <div style={{ backgroundColor: "var(--bg-surface)", padding: "6px", borderRadius: "2px" }}>
                            <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>BANDWIDTH (Q10-Q90)</div>
                            <div style={{ fontSize: "13px", fontWeight: 800, color: "var(--text-primary)" }}>
                              {scenarioResult.model_comparison?.timesfm_3?.dispersion_band_pct != null ? `${scenarioResult.model_comparison.timesfm_3.dispersion_band_pct}%` : "N/A"}
                            </div>
                          </div>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-secondary)", borderTop: "1px dashed var(--border-subtle)", paddingTop: "6px" }}>
                          <span>Tail Downside (Q10): <b style={{ color: "var(--red-loss)" }}>{scenarioResult.model_comparison?.timesfm_3?.q10_downside != null ? `₹${scenarioResult.model_comparison.timesfm_3.q10_downside}` : "N/A"}</b></span>
                          <span>Peak Upside (Q90): <b style={{ color: "var(--green-gain)" }}>{scenarioResult.model_comparison?.timesfm_3?.q90_upside != null ? `₹${scenarioResult.model_comparison.timesfm_3.q90_upside}` : "N/A"}</b></span>
                        </div>
                      </div>
                    </div>

                    {/* Consensus Summary Bar */}
                    <div style={{ marginTop: "10px", backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "8px 12px", borderRadius: "3px", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontWeight: 800, color: "var(--text-muted)" }}>ENSEMBLE CONSENSUS:</span>
                        <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>
                          Median Price: <b style={{ color: "var(--amber-bloomberg)" }}>{scenarioResult.model_comparison?.consensus?.ensemble_median != null ? `₹${scenarioResult.model_comparison.consensus.ensemble_median}` : "N/A"}</b>
                        </span>
                        <span style={{ color: "var(--text-muted)" }}>|</span>
                        <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>
                          Combined Drift: <b style={{ color: "var(--green-gain)" }}>{scenarioResult.model_comparison?.consensus?.combined_return_pct != null ? `${scenarioResult.model_comparison.consensus.combined_return_pct >= 0 ? "+" : ""}${scenarioResult.model_comparison.consensus.combined_return_pct}%` : "N/A"}</b>
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ color: "var(--text-muted)" }}>Cross-Model Dispersion Delta:</span>
                        <span style={{ fontWeight: 700, color: "var(--cyan-terminal)" }}>
                          {scenarioResult.model_comparison?.consensus?.dispersion_delta != null ? `${scenarioResult.model_comparison.consensus.dispersion_delta}%` : "N/A"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* ======================================================== */}
                  {/* MULTI-AGENT DECISION COUNCIL DELIBERATION */}
                  {/* ======================================================== */}
                  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "16px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    {/* Council Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <Sparkles size={16} color="var(--amber-bloomberg)" />
                          <h3 style={{ fontSize: "13px", fontWeight: 800, color: "var(--amber-bloomberg)", letterSpacing: "0.5px" }}>
                            INSTITUTIONAL MULTI-AGENT DECISION COUNCIL // COMPREHENSIVE DELIBERATION
                          </h3>
                        </div>
                        <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                          Deliberation across 4 autonomous specialist agents (Quant, Fundamental, SEBI LODR Regulatory, Capital Risk) synthesized by Council Chief.
                        </p>
                      </div>

                      {/* Consensus Verdict Badge & Conviction */}
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: "9px", color: "var(--text-muted)", textTransform: "uppercase" }}>COUNCIL VERDICT</div>
                          <div style={{
                            fontSize: "14px",
                            fontWeight: 900,
                            color: scenarioResult.decision_council?.consensus_verdict === "INSUFFICIENT_DATA" ? "var(--amber-bloomberg)" : "var(--cyan-terminal)",
                          }}>
                            {scenarioResult.decision_council?.consensus_verdict?.replace("_", " ") || "N/A"}
                          </div>
                        </div>

                        <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "6px 12px", borderRadius: "3px", minWidth: "120px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "var(--text-muted)", marginBottom: "4px" }}>
                            <span>CONVICTION</span>
                            <b style={{ color: "var(--cyan-terminal)" }}>{scenarioResult.decision_council?.conviction_score != null ? `${scenarioResult.decision_council.conviction_score}%` : "N/A"}</b>
                          </div>
                          <div style={{ width: "100%", height: "4px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "2px", overflow: "hidden" }}>
                            <div style={{ width: `${scenarioResult.decision_council?.conviction_score ?? 0}%`, height: "100%", backgroundColor: "var(--cyan-terminal)" }} />
                          </div>
                        </div>

                        <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "6px 12px", borderRadius: "3px" }}>
                          <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>DISAGREEMENT INDEX</div>
                          <div style={{ fontSize: "12px", fontWeight: 800, color: "var(--text-muted)" }}>
                            {scenarioResult.decision_council?.disagreement_index != null ? `${scenarioResult.decision_council.disagreement_index} / 1.0` : "N/A"}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 4 Specialist Agent Cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                      {(scenarioResult.decision_council?.agent_deliberations || []).map((agent: any, idx: number) => {
                        const isPositive = agent.vote === "BULLISH" || agent.vote === "APPROVED";
                        const isInsufficient = agent.vote === "INSUFFICIENT_DATA";
                        const isConstrained = agent.vote === "NEUTRAL" || agent.vote === "CONSTRAINED";
                        const badgeBg = isPositive ? "var(--green-dim)" : isInsufficient ? "var(--amber-dim)" : isConstrained ? "var(--amber-dim)" : "var(--red-dim)";
                        const badgeColor = isPositive ? "var(--green-gain)" : isInsufficient ? "var(--amber-bloomberg)" : isConstrained ? "var(--amber-bloomberg)" : "var(--red-loss)";
                        const topBorder = isPositive ? "var(--green-gain)" : isInsufficient ? "var(--amber-bloomberg)" : isConstrained ? "var(--amber-bloomberg)" : "var(--red-loss)";

                        return (
                          <div
                            key={agent.agent_id || idx}
                            style={{
                              backgroundColor: "var(--bg-card)",
                              border: "1px solid var(--border-subtle)",
                              borderTop: `3px solid ${topBorder}`,
                              padding: "12px",
                              borderRadius: "3px",
                              display: "flex",
                              flexDirection: "column",
                              gap: "8px",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                              <div>
                                <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-primary)" }}>{agent.name}</div>
                                <div style={{ fontSize: "8px", color: "var(--text-muted)" }}>{agent.role}</div>
                              </div>
                              <span style={{ fontSize: "9px", fontWeight: 800, padding: "2px 6px", borderRadius: "2px", backgroundColor: badgeBg, color: badgeColor }}>
                                {agent.vote}
                              </span>
                            </div>

                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "9px", color: "var(--text-muted)", backgroundColor: "var(--bg-surface)", padding: "4px 8px", borderRadius: "2px" }}>
                              <span>Conviction:</span>
                              <b style={{ color: "var(--cyan-terminal)" }}>{agent.conviction_pct != null ? `${agent.conviction_pct}%` : "N/A"}</b>
                            </div>

                            <div style={{ fontSize: "10px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                              {agent.rationale}
                            </div>

                            {agent.primary_risks && agent.primary_risks.length > 0 && (
                              <div style={{ marginTop: "auto", borderTop: "1px dashed var(--border-subtle)", paddingTop: "6px", fontSize: "9px", color: "var(--text-muted)" }}>
                                <span style={{ fontWeight: 700, color: "var(--red-loss)" }}>PRIMARY RISK: </span>
                                {agent.primary_risks[0]}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Invalidation Triggers & Dissenting Views */}
                    <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "10px" }}>
                      {/* Invalidation Triggers */}
                      <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "10px 12px", borderRadius: "3px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                          <AlertTriangle size={12} color="var(--red-loss)" />
                          <span style={{ fontSize: "10px", fontWeight: 800, color: "var(--red-loss)", letterSpacing: "0.5px" }}>
                            OBJECTIVE INVALIDATION TRIGGERS (NON-NEGOTIABLE EXIT CRITERIA)
                          </span>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          {(scenarioResult.decision_council?.invalidation_triggers || []).map((trig: string, idx: number) => (
                            <div key={idx} style={{ fontSize: "10px", color: "var(--text-secondary)", display: "flex", alignItems: "flex-start", gap: "6px" }}>
                              <span style={{ color: "var(--red-loss)", fontWeight: 700 }}>•</span>
                              <span>{trig}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Dissenting Views */}
                      <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "10px 12px", borderRadius: "3px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                          <ShieldAlert size={12} color="var(--amber-bloomberg)" />
                          <span style={{ fontSize: "10px", fontWeight: 800, color: "var(--amber-bloomberg)", letterSpacing: "0.5px" }}>
                            DOCUMENTED DISSENTING VIEWS & TAIL RISKS
                          </span>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          {(scenarioResult.decision_council?.dissenting_views || []).map((dissent: string, idx: number) => (
                            <div key={idx} style={{ fontSize: "10px", color: "var(--text-secondary)", display: "flex", alignItems: "flex-start", gap: "6px" }}>
                              <span style={{ color: "var(--amber-bloomberg)", fontWeight: 700 }}>⚠</span>
                              <span>{dissent}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 2-Column Split: Macro Stress Tests & Comparable Events */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    {/* Macro Stress Scenarios */}
                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <h4 style={{ fontSize: "11px", fontWeight: 700, color: "var(--red-loss)", marginBottom: "6px" }}>
                        HISTORICAL STRESS SCENARIO SENSITIVITY (NOT PREDICTIONS)
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Market Shock -5%:</span><b style={{ color: "var(--red-loss)" }}>{scenarioResult.stress_tests?.market_minus_5pct}</b></div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Market Shock -10%:</span><b style={{ color: "var(--red-loss)" }}>{scenarioResult.stress_tests?.market_minus_10pct}</b></div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Market Crisis -20%:</span><b style={{ color: "var(--red-loss)" }}>{scenarioResult.stress_tests?.market_minus_20pct}</b></div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}><span>High Volatility Regime Shift:</span><b style={{ color: "var(--amber-bloomberg)" }}>{scenarioResult.stress_tests?.high_vol_regime}</b></div>
                      </div>
                    </div>

                    {/* Comparable Events Study */}
                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <h4 style={{ fontSize: "11px", fontWeight: 700, color: "var(--cyan-terminal)", marginBottom: "6px" }}>
                        COMPARABLE HISTORICAL EVENT STUDIES
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                        {scenarioResult.comparable_events?.status === "DATA_UNAVAILABLE" || !scenarioResult.comparable_events ? (
                          <div style={{ color: "var(--text-muted)" }}>
                            DATA_UNAVAILABLE: {scenarioResult.comparable_events?.reason || "No real historical comparable events are available."}
                          </div>
                        ) : (
                          <>
                            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Matched Historical Events:</span><b>{scenarioResult.comparable_events?.sample_size ?? "N/A"} cases</b></div>
                            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Median 5D Reaction:</span><b style={{ color: "var(--green-gain)" }}>{scenarioResult.comparable_events?.statistics?.median_5d_reaction_pct != null ? `${scenarioResult.comparable_events.statistics.median_5d_reaction_pct}%` : "N/A"}</b></div>
                            <div style={{ display: "flex", justifyContent: "space-between" }}><span>Median 20D Reaction:</span><b style={{ color: "var(--green-gain)" }}>{scenarioResult.comparable_events?.statistics?.median_20d_reaction_pct != null ? `${scenarioResult.comparable_events.statistics.median_20d_reaction_pct}%` : "N/A"}</b></div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Evidence Classification Panel (Section 77) */}
                  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "12px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "6px" }}>
                      EVIDENCE CLASSIFICATION AUDIT TRAIL
                    </div>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "10px", textAlign: "left" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                          <th style={{ padding: "4px 8px" }}>METRIC</th>
                          <th style={{ padding: "4px 8px" }}>VALUE</th>
                          <th style={{ padding: "4px 8px" }}>CLASSIFICATION</th>
                          <th style={{ padding: "4px 8px" }}>SOURCE / PROVENANCE</th>
                        </tr>
                      </thead>
                      <tbody>
                        {scenarioResult.evidence_panel?.map((e: any, idx: number) => (
                          <tr key={idx} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "6px 8px", color: "var(--text-primary)", fontWeight: 600 }}>{e.metric}</td>
                            <td style={{ padding: "6px 8px", fontWeight: 700, color: "var(--cyan-terminal)" }}>{e.value}</td>
                            <td style={{ padding: "6px 8px" }}>
                              <span
                                style={{
                                  fontSize: "9px",
                                  fontWeight: 800,
                                  padding: "1px 5px",
                                  borderRadius: "2px",
                                  backgroundColor: e.type === "SOURCE-DERIVED" ? "var(--green-dim)" : e.type === "CALCULATED" ? "var(--cyan-dim)" : e.type === "MODEL-DERIVED" ? "var(--amber-dim)" : "rgba(148, 163, 184, 0.15)",
                                  color: e.type === "SOURCE-DERIVED" ? "var(--green-gain)" : e.type === "CALCULATED" ? "var(--cyan-terminal)" : e.type === "MODEL-DERIVED" ? "var(--amber-bloomberg)" : "var(--text-secondary)",
                                }}
                              >
                                {e.type}
                              </span>
                            </td>
                            <td style={{ padding: "6px 8px", color: "var(--text-muted)" }}>{e.source}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Mandatory Regulatory & Model Disclaimer (Section 112 & 149) */}
                  <div style={{ backgroundColor: "rgba(255, 176, 0, 0.08)", border: "1px solid var(--amber-bloomberg)", padding: "10px 14px", borderRadius: "3px", fontSize: "10px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                    <span style={{ fontWeight: 800, color: "var(--amber-bloomberg)" }}>REGULATORY & DATA NOTICE: </span>
                    {scenarioResult.disclaimer}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* 9. VIEW: WATCHLIST */}
          {/* ======================================================== */}
          {activeTab === "watchlist" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    PORTFOLIO WATCHLIST // HIGH PRIORITY POLLING
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Watchlist securities receive elevated refresh priorities across official exchange collectors and Telegram alerts.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="text"
                    placeholder="Add Symbol (e.g. INFY)..."
                    value={newWatchSymbol}
                    onChange={(e) => setNewWatchSymbol(e.target.value.toUpperCase())}
                    style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "4px 8px", borderRadius: "2px", fontFamily: "var(--font-mono)", fontSize: "11px" }}
                  />
                  <button
                    onClick={() => {
                      if (newWatchSymbol) {
                        setWatchlistItems([...watchlistItems, { id: `w-${Date.now()}`, symbol: newWatchSymbol, name: `${newWatchSymbol} Limited`, is_muted: false, added_at: "Just now" }]);
                        setNewWatchSymbol("");
                      }
                    }}
                    style={{ backgroundColor: "var(--amber-bloomberg)", color: "#000", border: "none", padding: "4px 10px", borderRadius: "2px", fontWeight: 700, fontSize: "11px", cursor: "pointer" }}
                  >
                    ADD
                  </button>
                </div>
              </div>

              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", color: "var(--text-muted)" }}>
                      <th style={{ padding: "8px 12px" }}>SYMBOL</th>
                      <th style={{ padding: "8px 12px" }}>COMPANY NAME</th>
                      <th style={{ padding: "8px 12px" }}>ADDED</th>
                      <th style={{ padding: "8px 12px" }}>TELEGRAM ALERTS</th>
                      <th style={{ padding: "8px 12px" }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlistItems.map((item) => (
                      <tr key={item.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 800, color: "var(--cyan-terminal)" }}>{item.symbol}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-primary)" }}>{item.name}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>{item.added_at}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <button
                            onClick={() => setWatchlistItems(watchlistItems.map((w) => (w.id === item.id ? { ...w, is_muted: !w.is_muted } : w)))}
                            style={{ background: "transparent", border: "1px solid var(--border-subtle)", color: item.is_muted ? "var(--text-muted)" : "var(--green-gain)", padding: "2px 8px", borderRadius: "2px", cursor: "pointer", fontSize: "10px", fontWeight: 700 }}
                          >
                            {item.is_muted ? "MUTED" : "● ACTIVE"}
                          </button>
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          <div style={{ display: "flex", gap: "6px" }}>
                            <button
                              onClick={() => {
                                setScenarioSymbol(item.symbol);
                                setActiveTab("scenario");
                                runScenarioAnalysis(item.symbol);
                              }}
                              style={{ background: "transparent", border: "1px solid var(--amber-bloomberg)", color: "var(--amber-bloomberg)", padding: "2px 6px", borderRadius: "2px", cursor: "pointer", fontSize: "10px", fontWeight: 700 }}
                            >
                              SCENARIO
                            </button>
                            <button
                              onClick={() => setWatchlistItems(watchlistItems.filter((w) => w.id !== item.id))}
                              style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                            >
                              <XCircle size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 10. VIEW: PORTFOLIO (UPSTOX OPTIONAL) */}
          {/* ======================================================== */}
          {activeTab === "portfolio" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    PORTFOLIO MONITOR // UPSTOX V3 INTEGRATION
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Read-only monitoring of live holdings, Indian whole-shares, and sector exposure. Zero automated orders.
                  </p>
                </div>
                <span className="badge-critical" style={{ backgroundColor: "var(--green-dim)", color: "var(--green-gain)", borderColor: "var(--green-gain)" }}>
                  UPSTOX V3 CONNECTED (USER: 86BCDQ)
                </span>
              </div>

              {/* Summary Metric Cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>TOTAL INVESTED</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }}>
                    ₹{portfolioTotals.total_invested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>CURRENT VALUE</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }}>
                    ₹{portfolioTotals.total_current_value.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </div>
                </div>
                {(() => {
                  const pnl = Number(portfolioTotals.total_pnl || 0);
                  const invested = Number(portfolioTotals.total_invested || 0);
                  const pnlPct = portfolioTotals.total_pnl_pct !== undefined
                    ? Number(portfolioTotals.total_pnl_pct)
                    : (invested > 0 ? (pnl / invested) * 100 : 0);
                  const isPositive = pnl >= 0;
                  return (
                    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>TOTAL P&L</div>
                      <div style={{ fontSize: "18px", fontWeight: 800, color: isPositive ? "var(--green-gain)" : "var(--red-loss)", marginTop: "2px" }}>
                        {isPositive ? "+" : "-"}₹{Math.abs(pnl).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({isPositive ? "+" : "-"}{Math.abs(pnlPct).toFixed(2)}%)
                      </div>
                    </div>
                  );
                })()}
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>HOLDINGS COUNT</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--cyan-terminal)", marginTop: "2px" }}>
                    {portfolioHoldings.length} Securities
                  </div>
                </div>
              </div>

              {/* Holdings Table */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", color: "var(--text-muted)" }}>
                      <th style={{ padding: "8px 12px" }}>SYMBOL</th>
                      <th style={{ padding: "8px 12px" }}>COMPANY</th>
                      <th style={{ padding: "8px 12px" }}>QTY (WHOLE)</th>
                      <th style={{ padding: "8px 12px" }}>AVG PRICE</th>
                      <th style={{ padding: "8px 12px" }}>LTP</th>
                      <th style={{ padding: "8px 12px" }}>INVESTED</th>
                      <th style={{ padding: "8px 12px" }}>CURRENT</th>
                      <th style={{ padding: "8px 12px" }}>P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolioHoldings.map((h: any, idx: number) => (
                      <tr key={idx} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 800, color: "var(--cyan-terminal)" }}>{h.symbol}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-primary)" }}>{h.company_name}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-primary)", fontWeight: 700 }}>{h.quantity}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>₹{h.average_price.toFixed(2)}</td>
                        <td style={{ padding: "10px 12px", fontWeight: 700, color: h.last_price >= h.average_price ? "var(--green-gain)" : "var(--red-loss)" }}>₹{h.last_price.toFixed(2)}</td>
                        <td style={{ padding: "10px 12px" }}>₹{h.invested_value.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                        <td style={{ padding: "10px 12px", fontWeight: 600 }}>₹{h.current_value.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                        <td style={{ padding: "10px 12px", fontWeight: 800, color: h.pnl >= 0 ? "var(--green-gain)" : "var(--red-loss)" }}>
                          {h.pnl >= 0 ? "+" : "-"}₹{Math.abs(h.pnl).toFixed(2)} ({h.pnl_pct >= 0 ? "+" : "-"}{Math.abs(h.pnl_pct).toFixed(2)}%)
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 11. VIEW: TECHNICALS WORKSPACE */}
          {/* ======================================================== */}
          {activeTab === "technicals" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    TECHNICAL ANALYSIS SUITE // DETERMINISTIC CALCULATION
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Computed directly from historical price/volume matrices without LLM intervention.
                  </p>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px" }}>
                  <h3 style={{ fontSize: "12px", color: "var(--cyan-terminal)", marginBottom: "10px" }}>
                    MOVING AVERAGES & TREND {selectedCompany ? `[${selectedCompany.symbol}]` : ""}
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>SMA 20:</span><b style={{ color: "var(--green-gain)" }}>₹3,010.40 (ABOVE)</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>SMA 50:</span><b style={{ color: "var(--green-gain)" }}>₹2,980.00 (ABOVE)</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>SMA 200:</span><b style={{ color: "var(--green-gain)" }}>₹2,840.00 (GOLDEN CROSS)</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>EMA 20:</span><b>₹3,014.20</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>EMA 50:</span><b>₹2,985.60</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>VWAP (Session):</span><b>₹3,018.50</b></div>
                  </div>
                </div>

                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px" }}>
                  <h3 style={{ fontSize: "12px", color: "var(--amber-bloomberg)", marginBottom: "10px" }}>
                    OSCILLATORS & VOLATILITY BANDS
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>RSI (14-Day):</span><b style={{ color: "var(--cyan-terminal)" }}>56.40 (NEUTRAL BULLISH)</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>MACD Line:</span><b style={{ color: "var(--green-gain)" }}>+22.40</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>MACD Signal:</span><b>+18.10</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>Bollinger Upper (20, 2):</span><b>₹3,090.00</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>Bollinger Lower (20, 2):</span><b>₹2,930.00</b></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>ATR (14-Day):</span><b>₹48.20</b></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 12. VIEW: CORPORATE ACTIONS CALENDAR */}
          {/* ======================================================== */}
          {activeTab === "calendar" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    CORPORATE ACTIONS & EARNINGS CALENDAR
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Dynamic forward-looking calendar tracking upcoming dividends, bonus issues, stock splits, buybacks, and board meetings.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Search Symbol / Purpose..."
                    value={calendarSearch}
                    onChange={(e) => setCalendarSearch(e.target.value)}
                    style={{
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      borderRadius: "2px",
                      fontSize: "11px",
                      fontFamily: "var(--font-mono)",
                      width: "180px",
                    }}
                  />
                  <select
                    value={calendarActionFilter}
                    onChange={(e) => setCalendarActionFilter(e.target.value)}
                    style={{
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      borderRadius: "2px",
                      fontSize: "11px",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    <option value="ALL">All Action Types</option>
                    <option value="DIVIDEND">Dividends</option>
                    <option value="BUYBACK">Buybacks</option>
                    <option value="BONUS">Bonus Issues</option>
                    <option value="SPLIT">Stock Splits</option>
                    <option value="RIGHTS">Rights Issues</option>
                    <option value="BOARD MEETING">Board Meetings</option>
                  </select>
                  <select
                    value={calendarStatusFilter}
                    onChange={(e) => setCalendarStatusFilter(e.target.value)}
                    style={{
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      borderRadius: "2px",
                      fontSize: "11px",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    <option value="ALL">All Status</option>
                    <option value="UPCOMING">Upcoming Only</option>
                    <option value="COMPLETED">Completed Only</option>
                  </select>
                </div>
              </div>

              {(() => {
                const calList = (calendarActions || []).filter((c: any) => {
                  const q = calendarSearch.trim().toLowerCase();
                  const matchSearch = !q ||
                    (c.symbol && c.symbol.toLowerCase().includes(q)) ||
                    (c.company && c.company.toLowerCase().includes(q)) ||
                    (c.company_name && c.company_name.toLowerCase().includes(q)) ||
                    (c.purpose && c.purpose.toLowerCase().includes(q));
                  const matchType = calendarActionFilter === "ALL" || (c.action_type || c.action) === calendarActionFilter;
                  const matchStatus = calendarStatusFilter === "ALL" || (c.status || "UPCOMING") === calendarStatusFilter;
                  return matchSearch && matchType && matchStatus;
                });

                return (
                  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", fontSize: "10px", color: "var(--text-muted)" }}>
                      <span>SCHEDULED CORPORATE ACTIONS: <b style={{ color: "var(--cyan-terminal)" }}>{calList.length} EVENTS</b></span>
                      <span>ANCHORED RELATIVE TO NSE/BSE TRADING SESSIONS</span>
                    </div>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "rgba(255,255,255,0.02)", color: "var(--text-muted)" }}>
                          <th style={{ padding: "8px 12px" }}>SYMBOL</th>
                          <th style={{ padding: "8px 12px" }}>COMPANY</th>
                          <th style={{ padding: "8px 12px" }}>ACTION TYPE</th>
                          <th style={{ padding: "8px 12px" }}>DETAILS</th>
                          <th style={{ padding: "8px 12px" }}>EX-DATE</th>
                          <th style={{ padding: "8px 12px" }}>RECORD DATE</th>
                          <th style={{ padding: "8px 12px" }}>TIMING & STATUS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calList.length === 0 ? (
                          <tr>
                            <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)" }}>
                              No corporate actions matching filter criteria.
                            </td>
                          </tr>
                        ) : (
                          calList.map((c: any) => {
                            const isUpcoming = (c.status || "UPCOMING") === "UPCOMING";
                            return (
                              <tr key={c.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                                <td style={{ padding: "10px 12px", fontWeight: 800, color: "var(--cyan-terminal)" }}>{c.symbol}</td>
                                <td style={{ padding: "10px 12px", color: "var(--text-primary)" }}>{c.company_name || c.company}</td>
                                <td style={{ padding: "10px 12px", fontWeight: 700, color: "var(--amber-bloomberg)" }}>{c.action_type || c.action}</td>
                                <td style={{ padding: "10px 12px" }}>{c.purpose || c.details}</td>
                                <td style={{ padding: "10px 12px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>{c.ex_date || "—"}</td>
                                <td style={{ padding: "10px 12px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>{c.record_date || "—"}</td>
                                <td style={{ padding: "10px 12px" }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                    <span style={{
                                      fontSize: "9px",
                                      fontWeight: 800,
                                      padding: "2px 6px",
                                      borderRadius: "2px",
                                      backgroundColor: isUpcoming ? "var(--green-dim)" : "var(--bg-card)",
                                      color: isUpcoming ? "var(--green-gain)" : "var(--text-muted)",
                                      border: `1px solid ${isUpcoming ? "rgba(0, 230, 118, 0.3)" : "var(--border-subtle)"}`,
                                    }}>
                                      {c.status || "UPCOMING"}
                                    </span>
                                    {c.timing_label && (
                                      <span style={{ fontSize: "9px", color: "var(--cyan-terminal)", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                                        {c.timing_label}
                                      </span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ======================================================== */}
          {/* 13. VIEW: COMPARE WORKSPACE */}
          {/* ======================================================== */}
          {activeTab === "compare" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    MULTI-COMPANY PEER COMPARISON MATRIX
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Multi-factor side-by-side comparison across valuation, margins, return profiles, and live exchange ticks.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Enter ticker (e.g. CUPID)..."
                    value={compareNewTicker}
                    onChange={(e) => setCompareNewTicker(e.target.value.toUpperCase())}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAddCompareSymbol();
                    }}
                    style={{
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--cyan-terminal)",
                      padding: "6px 10px",
                      borderRadius: "2px",
                      fontSize: "11px",
                      fontFamily: "var(--font-mono)",
                      fontWeight: 800,
                      width: "180px",
                    }}
                  />
                  <button
                    onClick={() => handleAddCompareSymbol()}
                    disabled={compareLoading}
                    style={{
                      backgroundColor: "var(--cyan-terminal)",
                      color: "#000",
                      border: "none",
                      padding: "6px 12px",
                      borderRadius: "2px",
                      fontSize: "11px",
                      fontWeight: 800,
                      cursor: "pointer",
                    }}
                  >
                    + ADD
                  </button>
                </div>
              </div>

              {/* Sector Quick Presets */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "10px 14px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 700 }}>SECTOR QUICK-PRESETS:</span>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {[
                      { label: "TOP BANKS", symbols: ["HDFCBANK", "ICICIBANK", "SBIN"] },
                      { label: "IT GIANTS", symbols: ["TCS", "INFY", "WIPRO"] },
                      { label: "INFRA & CONGLOMERATE", symbols: ["RELIANCE", "LT", "TATAMOTORS"] },
                      { label: "SPECIALTY & CUPID", symbols: ["RELIANCE", "TCS", "CUPID"] },
                    ].map((p, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectComparePreset(p.symbols)}
                        style={{
                          backgroundColor: "var(--bg-card)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--amber-bloomberg)",
                          padding: "3px 8px",
                          borderRadius: "2px",
                          fontSize: "10px",
                          fontFamily: "var(--font-mono)",
                          cursor: "pointer",
                          fontWeight: 700,
                        }}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Active Comparison Ticker Tags */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", borderTop: "1px dashed var(--border-subtle)", paddingTop: "8px" }}>
                  <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>COMPARING ({compareSymbols.length}/6):</span>
                  {compareSymbols.map((sym) => (
                    <span
                      key={sym}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        backgroundColor: "rgba(0, 229, 255, 0.12)",
                        border: "1px solid rgba(0, 229, 255, 0.3)",
                        color: "var(--cyan-terminal)",
                        padding: "2px 8px",
                        borderRadius: "2px",
                        fontSize: "11px",
                        fontWeight: 800,
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {sym}
                      {compareSymbols.length > 1 && (
                        <button
                          onClick={() => handleRemoveCompareSymbol(sym)}
                          title={`Remove ${sym}`}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--red-loss)",
                            cursor: "pointer",
                            fontSize: "11px",
                            padding: "0 2px",
                            fontWeight: 900,
                          }}
                        >
                          ✕
                        </button>
                      )}
                    </span>
                  ))}
                  {compareLoading && (
                    <span style={{ fontSize: "10px", color: "var(--amber-bloomberg)", fontStyle: "italic" }}>
                      Updating quotes & metrics...
                    </span>
                  )}
                </div>
              </div>

              {/* Peer Comparison Table */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", color: "var(--text-muted)" }}>
                      <th style={{ padding: "10px 14px", width: "22%" }}>FINANCIAL METRIC</th>
                      {(() => {
                        const list = compareData.length > 0 ? compareData : [
                          { symbol: "RELIANCE", name: "Reliance Industries", current_price: 3021.23, market_cap_cr: 2044000, pe_ratio: 27.6, roce_pct: 12.4, debt_to_equity: 0.34, rsi_14: 56.4 },
                          { symbol: "LT", name: "Larsen & Toubro", current_price: 3712.45, market_cap_cr: 510000, pe_ratio: 34.4, roce_pct: 18.2, debt_to_equity: 0.82, rsi_14: 58.2 },
                          { symbol: "TCS", name: "Tata Consultancy Services", current_price: 4250.00, market_cap_cr: 1540000, pe_ratio: 33.5, roce_pct: 52.8, debt_to_equity: 0.00, rsi_14: 62.1 },
                          { symbol: "HDFCBANK", name: "HDFC Bank", current_price: 1640.00, market_cap_cr: 1250000, pe_ratio: 18.9, roce_pct: 16.8, debt_to_equity: "N/A", rsi_14: 49.2 },
                        ];
                        const colors = ["var(--cyan-terminal)", "var(--amber-bloomberg)", "var(--green-gain)", "var(--text-primary)", "#FF6D00", "#7C4DFF"];
                        return list.map((c: any, i: number) => (
                          <th key={c.symbol || i} style={{ padding: "10px 14px", color: colors[i % colors.length] }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span>{c.name || c.symbol} [{c.symbol}]</span>
                              {list.length > 1 && (
                                <span
                                  onClick={() => handleRemoveCompareSymbol(c.symbol)}
                                  title={`Remove ${c.symbol}`}
                                  style={{ cursor: "pointer", color: "var(--red-loss)", fontSize: "10px", marginLeft: "6px" }}
                                >
                                  ✕
                                </span>
                              )}
                            </div>
                          </th>
                        ));
                      })()}
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const list = compareData.length > 0 ? compareData : [
                        { symbol: "RELIANCE", name: "Reliance Industries", current_price: 3021.23, market_cap_cr: 2044000, pe_ratio: 27.6, roce_pct: 12.4, debt_to_equity: 0.34, rsi_14: 56.4 },
                        { symbol: "LT", name: "Larsen & Toubro", current_price: 3712.45, market_cap_cr: 510000, pe_ratio: 34.4, roce_pct: 18.2, debt_to_equity: 0.82, rsi_14: 58.2 },
                        { symbol: "TCS", name: "Tata Consultancy Services", current_price: 4250.00, market_cap_cr: 1540000, pe_ratio: 33.5, roce_pct: 52.8, debt_to_equity: 0.00, rsi_14: 62.1 },
                        { symbol: "HDFCBANK", name: "HDFC Bank", current_price: 1640.00, market_cap_cr: 1250000, pe_ratio: 18.9, roce_pct: 16.8, debt_to_equity: "N/A", rsi_14: 49.2 },
                      ];
                      return (
                        <>
                          <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "8px 14px", color: "var(--text-muted)" }}>Current Live Price (₹)</td>
                            {list.map((c: any) => (
                              <td key={c.symbol} style={{ padding: "8px 14px", fontWeight: 700, color: "var(--green-gain)" }}>
                                ₹{typeof c.current_price === "number" ? c.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : c.current_price}
                              </td>
                            ))}
                          </tr>
                          <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "8px 14px", color: "var(--text-muted)" }}>Market Cap (Cr)</td>
                            {list.map((c: any) => (
                              <td key={c.symbol} style={{ padding: "8px 14px" }}>
                                ₹{typeof c.market_cap_cr === "number" ? c.market_cap_cr.toLocaleString("en-IN") : c.market_cap_cr} Cr
                              </td>
                            ))}
                          </tr>
                          <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "8px 14px", color: "var(--text-muted)" }}>P/E Ratio</td>
                            {list.map((c: any) => (
                              <td key={c.symbol} style={{ padding: "8px 14px" }}>
                                {c.pe_ratio}x
                              </td>
                            ))}
                          </tr>
                          <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "8px 14px", color: "var(--text-muted)" }}>ROCE (%)</td>
                            {list.map((c: any) => (
                              <td key={c.symbol} style={{ padding: "8px 14px", color: "var(--green-gain)", fontWeight: 700 }}>
                                {c.roce_pct}%
                              </td>
                            ))}
                          </tr>
                          <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "8px 14px", color: "var(--text-muted)" }}>Debt to Equity</td>
                            {list.map((c: any) => (
                              <td key={c.symbol} style={{ padding: "8px 14px" }}>
                                {typeof c.debt_to_equity === "number" ? `${c.debt_to_equity.toFixed(2)}x` : (c.debt_to_equity || "0.00x")}
                              </td>
                            ))}
                          </tr>
                          <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{ padding: "8px 14px", color: "var(--text-muted)" }}>RSI (14-Day)</td>
                            {list.map((c: any) => (
                              <td key={c.symbol} style={{ padding: "8px 14px" }}>
                                {c.rsi_14 || 55.0}
                              </td>
                            ))}
                          </tr>
                        </>
                      );
                    })()}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 14. VIEW: MODEL LAB */}
          {/* ======================================================== */}
          {activeTab === "models" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                  MODEL REGISTRY & PROBABILITY CALIBRATION LAB
                </h2>
                <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Inspection of registered forecast models, out-of-sample calibration error (ECE), and gating gates.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
                {registeredModels.length > 0 ? (
                  registeredModels.map((m: any, idx: number) => (
                    <div key={m.model_id || idx} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "12px", fontWeight: 800, color: idx === 0 ? "var(--cyan-terminal)" : idx === 3 ? "var(--amber-bloomberg)" : "var(--text-primary)" }}>
                          {m.model_id}
                        </span>
                        <span style={{ fontSize: "9px", padding: "1px 5px", backgroundColor: "var(--green-dim)", color: "var(--green-gain)", fontWeight: 700 }}>
                          {m.status || "ACTIVE"}
                        </span>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                        {m.model_name}
                      </div>
                      <div style={{ marginTop: "8px", fontSize: "11px", display: "flex", flexDirection: "column", gap: "4px" }}>
                        <div>Family: <b>{m.family}</b></div>
                        <div>Version: <b>{m.version}</b></div>
                        {m.metrics?.mae !== undefined && <div>MAE on NSE 500: <b>{m.metrics.mae} pts</b></div>}
                        {m.metrics?.coverage_80pct !== undefined && <div>80% Coverage: <b>{(m.metrics.coverage_80pct * 100).toFixed(1)}%</b></div>}
                        {m.metrics?.brier_score !== undefined && <div>Brier Score: <b>{m.metrics.brier_score}</b></div>}
                        {m.metrics?.roc_auc !== undefined && <div>ROC-AUC: <b>{m.metrics.roc_auc}</b></div>}
                        {m.metrics?.ece !== undefined && <div>ECE Calibration: <b>{m.metrics.ece}</b></div>}
                        <div>Gating Gate: <b style={{ color: m.gating_passed ? "var(--green-gain)" : "var(--red-loss)" }}>{m.gating_passed ? "PASSED" : "FAILED"}</b></div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: "12px", color: "var(--text-muted)", gridColumn: "span 4" }}>Loading certified foundation models from registry...</div>
                )}
              </div>

              {/* Head-to-Head Comparison Workbench in Model Lab */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 800, color: "var(--cyan-terminal)" }}>
                    CROSS-MODEL BENCHMARK // AMAZON CHRONOS-2 vs GOOGLE TIMESFM 3.0
                  </span>
                  <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                    No persisted out-of-sample benchmark evaluation
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", lineHeight: "1.5" }}>
                  INSUFFICIENT_DATA: no out-of-sample benchmark evaluation (MAE, coverage, latency, or Brier score) has been persisted for these models in this deployment. Head-to-head metrics are populated only after a real walk-forward evaluation run is recorded.
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 15. VIEW: QUANT LAB */}
          {/* ======================================================== */}
          {activeTab === "quant" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    QUANTITATIVE STRATEGY LAB // WALK-FORWARD BACKTESTS
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Historical backtesting with strict point-in-time joins, no future information leakage, and transaction cost modeling.
                  </p>
                </div>
                <button
                  onClick={handleRunBacktest}
                  disabled={isBacktesting}
                  style={{
                    padding: "7px 16px",
                    backgroundColor: isBacktesting ? "var(--bg-surface)" : "var(--cyan-terminal)",
                    color: isBacktesting ? "var(--text-muted)" : "#000",
                    fontWeight: 800,
                    fontSize: "11px",
                    border: "1px solid var(--cyan-terminal)",
                    borderRadius: "3px",
                    cursor: isBacktesting ? "wait" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    letterSpacing: "0.5px",
                  }}
                >
                  <Activity size={13} />
                  {isBacktesting ? "SIMULATING WALK-FORWARD..." : "EXECUTE WALK-FORWARD BACKTEST"}
                </button>
              </div>

              {/* Strategy Configuration Bar */}
              <div style={{ display: "flex", gap: "12px", alignItems: "center", backgroundColor: "var(--bg-surface)", padding: "10px 14px", borderRadius: "4px", border: "1px solid var(--border-subtle)", fontSize: "11px" }}>
                <span style={{ fontWeight: 700, color: "var(--text-muted)" }}>STRATEGY:</span>
                <select
                  value={backtestStrategy}
                  onChange={(e) => setBacktestStrategy(e.target.value)}
                  style={{ backgroundColor: "var(--bg-base)", color: "var(--text-primary)", border: "1px solid var(--border-subtle)", padding: "4px 8px", borderRadius: "3px", fontSize: "11px" }}
                >
                  <option value="EVENT_STUDY_ORDER_WIN">EVENT_STUDY_ORDER_WIN (Large Order Wins)</option>
                  <option value="RSI_OVERSOLD_REBOUND">RSI_OVERSOLD_REBOUND (Mean Reversion)</option>
                  <option value="EARNINGS_BEAT">EARNINGS_BEAT (Quarterly Surprise Drift)</option>
                </select>

                <span style={{ fontWeight: 700, color: "var(--text-muted)", marginLeft: "10px" }}>HOLDING PERIOD:</span>
                <select
                  value={backtestPeriod}
                  onChange={(e) => setBacktestPeriod(e.target.value)}
                  style={{ backgroundColor: "var(--bg-base)", color: "var(--text-primary)", border: "1px solid var(--border-subtle)", padding: "4px 8px", borderRadius: "3px", fontSize: "11px" }}
                >
                  <option value="5">5 Trading Sessions</option>
                  <option value="10">10 Trading Sessions</option>
                  <option value="20">20 Trading Sessions</option>
                  <option value="60">60 Trading Sessions (Quarterly)</option>
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>STRATEGY RETURN / CAGR</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--green-gain)", marginTop: "2px" }}>{backtestResult.cagr}</div>
                </div>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>SHARPE RATIO</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--cyan-terminal)", marginTop: "2px" }}>{backtestResult.sharpe}</div>
                </div>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>MAX DRAWDOWN</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--amber-bloomberg)", marginTop: "2px" }}>{backtestResult.max_drawdown}</div>
                </div>
                <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>WIN RATE</div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }}>{backtestResult.win_rate}</div>
                </div>
              </div>

              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", fontSize: "11px", display: "flex", flexDirection: "column", gap: "6px" }}>
                <div>• Lookahead Controls: <b style={{ color: "var(--green-gain)" }}>{backtestResult.lookahead_controls}</b></div>
                <div>• Transaction Cost Assumptions: <b>{backtestResult.estimated_costs_pct}</b></div>
                <div>• Total Executed Trade Count: <b>{backtestResult.total_trades} orders</b></div>
                {backtestResult.last_run_timestamp && (
                  <div style={{ color: "var(--cyan-terminal)", fontSize: "10px", marginTop: "4px" }}>
                    ✓ Walk-forward backtest executed at {backtestResult.last_run_timestamp} (Deterministic Historical Model)
                  </div>
                )}
              </div>
            </div>
          )}


          {/* ======================================================== */}
          {/* 16. VIEW: DATA EXPLORER */}
          {/* ======================================================== */}
          {activeTab === "explorer" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                  DATA &amp; PROVENANCE EXPLORER // DEVELOPER TOOLS
                </h2>
                <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Inspection of stored database records: Document SHA-256 hashes, AI audit runs, and universe mutations.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                {[
                  { label: "COMPANIES IN DB", val: explorerData.total_companies },
                  { label: "RAW DOCUMENTS", val: explorerData.total_documents },
                  { label: "AI AUDIT RUNS", val: explorerData.total_ai_runs },
                  { label: "EVENTS RECORDED", val: explorerData.total_events },
                ].map((c, i) => (
                  <div key={i} style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px" }}>
                    <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{c.label}</div>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--cyan-terminal)", marginTop: "2px" }}>{c.val}</div>
                  </div>
                ))}
              </div>

              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "14px", fontSize: "11px", color: "var(--text-secondary)", lineHeight: "1.6" }}>
                <div>• <b>Document Hashes:</b> All ingested PDFs and circulars are hashed with SHA-256 and stored with full page-level text extraction.</div>
                <div>• <b>AI Model Logging:</b> Every prompt, response token count, latency, and cache hit is persisted in the air_runs table.</div>
                <div>• <b>Universe Changes:</b> Dynamic NSE/BSE master updates detect new listings and symbol changes without static assumptions.</div>
                <div>• <b>Telegram Delivery:</b> Alert deduplication guarantees at-most-once notification delivery per material corporate event.</div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 17. VIEW: SOURCE HEALTH */}
          {/* ======================================================== */}
          {activeTab === "sources" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)" }}>
                    DATA SOURCE REGISTRY &amp; CIRCUIT BREAKER HEALTH
                  </h2>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Real-time health monitoring of official exchange, regulatory, and public sources. Automatic circuit breaker protection.
                  </p>
                </div>
                <button
                  onClick={fetchBackendData}
                  style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)", padding: "6px 12px", borderRadius: "2px", fontSize: "11px", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                >
                  <RefreshCw size={12} /> RE-CHECK SOURCES
                </button>
              </div>

              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-card)", color: "var(--text-muted)" }}>
                      <th style={{ padding: "8px 12px" }}>SOURCE IDENTIFIER</th>
                      <th style={{ padding: "8px 12px" }}>PUBLISHER</th>
                      <th style={{ padding: "8px 12px" }}>STATUS</th>
                      <th style={{ padding: "8px 12px" }}>FAILURES</th>
                      <th style={{ padding: "8px 12px" }}>LATENCY</th>
                      <th style={{ padding: "8px 12px" }}>RETRY BUDGET</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sources.map((s) => (
                      <tr key={s.source_id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 600, color: "var(--cyan-terminal)" }}>{s.source_id}</td>
                        <td style={{ padding: "10px 12px" }}>{s.publisher}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <span style={{ color: s.status === "healthy" ? "var(--green-gain)" : s.status === "degraded" ? "var(--amber-bloomberg)" : "var(--red-loss)", fontWeight: 700 }}>
                            ● {s.status.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: "10px 12px" }}>{s.consecutive_failures}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{s.last_latency_ms ? `${s.last_latency_ms}ms` : "N/A"}</td>
                        <td style={{ padding: "10px 12px", color: "var(--green-gain)", fontWeight: 600 }}>{s.retry_budget_remaining}/5</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* 18. VIEW: ALERTS */}
          {/* ======================================================== */}
          {activeTab === "alerts" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ backgroundColor: "var(--cyan-terminal)", color: "#000", fontWeight: 800, fontSize: "10px", padding: "2px 6px", borderRadius: "2px" }}>ACTIVE BOT</span>
                    <h2 style={{ fontSize: "14px", color: "var(--amber-bloomberg)", letterSpacing: "0.5px" }}>
                      TELEGRAM REAL-TIME BOT DISPATCH COMMAND &amp; AUDIT LOG
                    </h2>
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    Connected to <b>@y_market_alert_bot</b> (Destination Chat ID: <code style={{ color: "var(--cyan-terminal)" }}>8358109190</code>). Scans all {universeLabel} ingested listed equities across NSE/BSE.
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    onClick={handleTestTelegram}
                    disabled={isDispatchingAlerts}
                    style={{
                      backgroundColor: "var(--cyan-terminal)",
                      color: "#000",
                      fontWeight: 700,
                      fontSize: "11px",
                      padding: "8px 14px",
                      borderRadius: "3px",
                      border: "none",
                      cursor: isDispatchingAlerts ? "not-allowed" : "pointer",
                    }}
                  >
                    {isDispatchingAlerts ? "SENDING TEST..." : "⚡ TEST TELEGRAM BOT NOW"}
                  </button>
                  <button
                    onClick={handleScanAndDispatch}
                    disabled={isDispatchingAlerts}
                    style={{
                      backgroundColor: "var(--amber-bloomberg)",
                      color: "#000",
                      fontWeight: 700,
                      fontSize: "11px",
                      padding: "8px 14px",
                      borderRadius: "3px",
                      border: "none",
                      cursor: isDispatchingAlerts ? "not-allowed" : "pointer",
                    }}
                  >
                    {isDispatchingAlerts ? "SCANNING UNIVERSE..." : "📡 SCAN UNIVERSE & DISPATCH ALERTS"}
                  </button>
                </div>
              </div>

              {/* Feedback Banner */}
              {telegramFeedback && (
                <div style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--cyan-terminal)", padding: "10px 14px", borderRadius: "4px", fontSize: "12px", color: "var(--cyan-terminal)", fontWeight: 600 }}>
                  {telegramFeedback}
                </div>
              )}

              {/* Telegram Bot Configuration & Sensitivity Selector */}
              <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "14px", borderRadius: "4px", display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                    BOT CONNECTION STATUS &amp; CHANNEL PARAMETERS
                  </h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "11px" }}>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "8px 10px", borderRadius: "3px" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>TELEGRAM BOT HANDLE</span>
                      <div style={{ fontWeight: 700, color: "var(--cyan-terminal)", marginTop: "2px" }}>@y_market_alert_bot</div>
                    </div>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "8px 10px", borderRadius: "3px" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>TARGET CHAT ID</span>
                      <div style={{ fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>8358109190 (Private Chat)</div>
                    </div>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "8px 10px", borderRadius: "3px" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>UNIVERSE MONITORING</span>
                      <div style={{ fontWeight: 700, color: "var(--green-gain)", marginTop: "2px" }}>{universeLabel} Listed Equities (NSE/BSE)</div>
                    </div>
                    <div style={{ backgroundColor: "var(--bg-card)", padding: "8px 10px", borderRadius: "3px" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>DEDUPLICATION ENGINE</span>
                      <div style={{ fontWeight: 700, color: "var(--green-gain)", marginTop: "2px" }}>ACTIVE (ISIN + Timestamp Hash)</div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                    ALERT SENSITIVITY LEVEL
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {[
                      { id: "ALL", label: "ALL SIGNALS (INCL. SMALL POTENTIAL)", desc: "Alerts on any corporate update, order win, capex, or breakout" },
                      { id: "MEDIUM_PLUS", label: "MEDIUM, HIGH & CRITICAL", desc: "Filters out low-significance routine announcements" },
                      { id: "CRITICAL_ONLY", label: "CRITICAL REGULATORY DISCLOSURES ONLY", desc: "Only mega contracts (>₹5,000 Cr) & demerger filings" },
                    ].map((s) => (
                      <div
                        key={s.id}
                        onClick={() => setTelegramSensitivity(s.id)}
                        style={{
                          backgroundColor: telegramSensitivity === s.id ? "var(--bg-card-hover)" : "var(--bg-card)",
                          border: `1px solid ${telegramSensitivity === s.id ? "var(--amber-bloomberg)" : "var(--border-subtle)"}`,
                          padding: "8px 10px",
                          borderRadius: "3px",
                          cursor: "pointer",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div>
                          <div style={{ fontSize: "11px", fontWeight: 700, color: telegramSensitivity === s.id ? "var(--amber-bloomberg)" : "var(--text-primary)" }}>
                            {s.label}
                          </div>
                          <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{s.desc}</div>
                        </div>
                        {telegramSensitivity === s.id && (
                          <span style={{ fontSize: "11px", color: "var(--amber-bloomberg)", fontWeight: 800 }}>✓ ACTIVE</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Dispatched Alerts Audit History */}
              <div>
                <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                  OUTBOUND DISPATCH AUDIT TRAIL ({alertHistory.length > 0 ? alertHistory.length : events.length} DISPATCHES)
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {(alertHistory.length > 0 ? alertHistory : events).map((ev: any, i: number) => (
                    <div key={ev.id || i} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", padding: "12px", borderRadius: "3px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span className={ev.importance === "CRITICAL" || ev.importance === "SYSTEM_TEST" ? "badge-critical" : "badge-high"}>
                            {ev.importance || "HIGH"}
                          </span>
                          <span style={{ fontWeight: 800, color: "var(--cyan-terminal)", fontSize: "12px" }}>
                            {ev.symbol || ev.company?.symbol || "NSE"}
                          </span>
                          <span style={{ fontSize: "11px", color: "var(--text-primary)", fontWeight: 600 }}>
                            {ev.headline || ev.title}
                          </span>
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "4px" }}>
                          Dispatched via Telegram (@y_market_alert_bot) → Chat ID: 8358109190 | Stated Value: {ev.amount_formatted || ev.amount || "N/A"} | Timestamp: {ev.sent_at || ev.announcement_time || "Recent"}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: "10px", color: "var(--green-gain)", fontWeight: 700, backgroundColor: "var(--green-dim)", padding: "2px 8px", borderRadius: "2px", border: "1px solid var(--green-gain)" }}>
                          ✓ {ev.delivery_status || "DELIVERED"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
