MCX NATURAL GAS INTELLIGENCE DASHBOARD
Angel One SmartAPI + Henry Hub + USD/INR delayed references + draggable dashboard
Build: v3.5

WHAT THIS VERSION CONNECTS
1. MCX Natural Gas: Angel One SmartAPI WebSocket v2 (your authenticated account feed).
   - Loads the current MCX Natural Gas futures list from Angel One's current angelone.in instrument-master host, with the legacy angelbroking.com host as fallback.
   - Retries temporary gateway errors and saves a local copy of the master for offline fallback. If the remote service is down, the UI labels the list as cached and displays its age. Verify cached contract symbol/expiry with Angel One before connecting.
   - Lets you choose any listed upcoming MCX Natural Gas futures expiry in the UI. Use Refresh contract list to fetch the latest instrument master.
   - Clicking Connect selected contract subscribes to that expiry; connecting a different selection replaces the previous stream.
   - Streams last traded price, average traded price, day high/low, volume and open interest.
   - Updates the dashboard price input automatically. Angel One average traded price is shown as a VWAP proxy; verify exact VWAP on your chart.
2. US Henry Hub: Yahoo Finance public NG=F quote endpoint.
   - Automatically refreshes the quoted price and percentage change every 60 seconds.
   - This is a delayed NYMEX reference quote, not a guaranteed real-time exchange feed.
   - A stale Henry Hub quote is excluded from the automatic signal calculation.
3. US weather: Open-Meteo forecast for six selected US cities, refreshed every 30 minutes.
4. USD/INR: Yahoo Finance INR=X delayed reference quote, refreshed every 60 seconds, with rate, percent change, quote age and intraday reference mini-chart.
   - A rising USD/INR (weaker rupee) is marked as a possible MCX currency-translation tailwind; a falling USD/INR (stronger rupee) is marked as a possible headwind.
   - Default signal band is ±0.10%; change the threshold in the UI. The FX signal contributes at most +1 / -1 to the momentum score. Stale or unavailable quotes are excluded.
   - It is not the MCX USDINR futures price and is not a real-time executable FX feed. It must not be treated as a standalone trade signal.
5. Rule-based fundamental/momentum dashboard, breakout checklist, risk sizing and JSON snapshot export.
6. New Open Interest Tracker: plots Angel One MCX price and OI history with a dual-axis chart; automatically classifies long buildup, short covering, short buildup or long unwinding over a selectable lookback (5m, 15m, 30m, 60m or 4h). The widget is collapsible and remembers its open/closed state. When the OI selector is set to Automatic, its score feeds the momentum calculation; manual overrides remain available.

IMPORTANT: This application is read-only. It does NOT place, modify or cancel orders.

ONE-TIME SETUP (WINDOWS)
1. Install Python 3.10 or later. During installation, select "Add Python to PATH".
2. Extract the ZIP to a folder you can keep on your computer.
3. In the folder, open .env.example only as a template. Run run_dashboard.bat once.
   - The launcher creates a local Python virtual environment and installs dependencies.
   - It creates .env and opens it in Notepad when .env does not exist.
4. Create an API app in your Angel One SmartAPI account. Put your own values in .env:

   ANGEL_API_KEY=your SmartAPI application key
   ANGEL_CLIENT_CODE=your Angel One client code
   ANGEL_PIN=your trading PIN
   ANGEL_TOTP_SECRET=the Base32 TOTP secret (or full otpauth:// URI) used by your authenticator

   Save .env. Never share it, upload it, or paste these values into ChatGPT. Do not use the 6-digit rotating OTP in place of the TOTP secret or otpauth URI. The app generates the current TOTP locally when you click Connect.
5. Run run_dashboard.bat again. Your browser opens at http://127.0.0.1:8765.
6. Select the MCX Natural Gas futures expiry you are actually tracking in the dropdown, then click Connect selected contract. To change expiry, select another listed contract and click Connect selected contract again. Use Refresh contract list to reload the current Angel One instrument master.
7. The MCX price panel should change to Connected and display the first incoming tick. Henry Hub is fetched separately from Yahoo Finance.

DAILY USE
- Start with run_dashboard.bat. Keep the terminal window open while using the dashboard.
- Your Angel One session may expire; reconnect if the feed stops or the API session expires.
- Always select the correct MCX expiry. Near expiry, do not assume the nearest contract is the one you intend to trade.
- The local server listens only on 127.0.0.1 (this computer), not on the public network.
- On macOS/Linux, run ./run_dashboard.sh after editing .env.

DATA TIMING AND LIMITATIONS
- Angel One MCX WebSocket: live account-authorised market feed subject to Angel One/SmartAPI availability, exchange trading hours, app permissions and data terms.
- Yahoo Finance NG=F: delayed quote.
- Yahoo Finance INR=X: delayed USD/INR spot/reference quote. It is a secondary currency context indicator only; it is not an exchange-authorised live USDINR futures feed. The 2-hour age check is a stale-data guard, not a guarantee of timeliness. Its public endpoint is not a documented exchange feed, may change, throttle or stop working, and must not be used as an execution-grade real-time source. A page refreshing every minute does not remove the underlying delay.
- CME's public delayed futures quotes are delayed by at least 10 minutes. CME says its website market data is for reference and should not validate or replace its licensed real-time feed.
- For genuine real-time Henry Hub prices, obtain a CME/NYMEX-authorised real-time market-data entitlement from CME or an authorised vendor. There is no reliable, exchange-authorised, unlimited free real-time futures feed assumed in this package.
- Angel One's average_traded_price field is used as an indicative VWAP proxy only; it may not match a platform's exact intraday VWAP calculation. Verify on your chart before using it.
- Open-interest history begins when this dashboard connects to the selected contract; it is held in memory and cleared when another contract is connected or the server restarts. The chart's lookback comparison is an intraday heuristic, not a substitute for prior-session OI analysis. The automatic OI classification feeds the momentum score only when the selector is set to Automatic; manual overrides are available.
- 15-minute candle close, volume-vs-20-bar confirmation and breakout retest remain manual confirmations. A price tick alone does not establish them.
- The six-city HDD/CDD is a simplified proxy, not the official population-weighted US demand forecast. Compare specialist model revisions and NOAA material.
- EIA storage actual/consensus are manual inputs. Use the official EIA report and a clearly identified consensus source.
- Verify active MCX contract lot size, tick size, expiry, margin, order-book liquidity, rollover and applicable charges in your broker terminal before trading.
- Trading indicators are heuristics, not predictions or investment advice. A dashboard BUY/SELL state is not an instruction to place an order. Confirm every input, stop, position size and liquidity condition independently.

TROUBLESHOOTING
- "Missing local .env settings": complete all four ANGEL_ values and save .env.
- "Invalid Auth token / Feed Token / API Key": verify your SmartAPI app key, client code, PIN, system clock and TOTP secret. Generate a fresh session by clicking Connect again.
- "No upcoming MCX Natural Gas futures": retry after the Angel One instrument master updates; check Angel One SmartAPI availability.
- Contract-list HTTP 502/504: this is usually the Angel One instrument-master download service, not your login credentials. v3.2 tries the current angelone.in hostname, then the legacy hostname, retries transient failures and uses a local cached copy if one exists. If it reports cached data, verify the exact contract symbol and expiry in Angel One before connecting. If no cache exists and both hosts fail, retry later or contact SmartAPI support; do not use a guessed token.
- MCX says "subscribing" but no tick arrives: verify the selected expiry is active, market is open and the account has MCX market-data access. Check the terminal window for SDK errors.
- Henry Hub or USD/INR unavailable: Yahoo's public endpoint may be throttled or changed. For USD/INR, inspect https://finance.yahoo.com/quote/INR%3DX/; stale/unavailable data does not contribute to the momentum score. Open https://finance.yahoo.com/quote/NG%3DF/ to inspect the delayed quote, or use CME delayed quotes. The signal engine will not use a stale quote.
- Windows launcher errors: verify Python 3.10+, then run run_dashboard.bat again. Keep the terminal window open.

REFERENCES
Angel One SmartAPI documentation: https://smartapi.angelone.in/docs
Angel One official Python SDK: https://github.com/angel-one/smartapi-python
Angel One WebSocket 2.0: https://smartapi.angelone.in/docs/WebSocket2
Angel One market data API: https://smartapi.angelone.in/docs/MarketData
Angel One instrument master (current documented host): https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json
Legacy Angel One instrument master fallback: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
Yahoo Finance NG=F (delayed quote): https://finance.yahoo.com/quote/NG%3DF/
Yahoo Finance INR=X USD/INR (delayed quote): https://finance.yahoo.com/quote/INR%3DX/
CME delayed quotes: https://www.cmegroup.com/market-data/browse-data/delayed-quotes.html
CME market-data delay and use notice: https://www.cmegroup.com/trading/about-quotes.html
EIA storage: https://www.eia.gov/naturalgas/storage/
EIA release schedule: https://ir.eia.gov/ngs/schedule.html
NOAA Climate Prediction Center: https://www.cpc.ncep.noaa.gov/
Forecast Gas: https://forecastgas.com/
NatGasWeather: https://natgasweather.com/
MCX: https://www.mcxindia.com/
Open-Meteo docs: https://open-meteo.com/en/docs

VERSION 3.3 PATCH (retained)
- Contract parser recognizes MCX master segment labels MCX, MCX_FO / mcx_fo, and NCO. Angel One's WebSocket subscription uses exchangeType=5 (MCX_FO).
- If a downloaded master has no matching Natural Gas futures, the backend error includes exchange segments and candidate Natural Gas rows to help diagnose schema changes.

VERSION 3.4 ADDITIONS
- Added a collapsible Open Interest Tracker with price and OI trend lines, selectable lookback windows (5m / 15m / 30m / 60m / 4h), live percentage changes and observation count.
- Added automatic price/OI positioning labels: long buildup, short covering, short buildup and long unwinding. The signal is a heuristic and not a standalone trade instruction.
- Added in-memory tick history to /api/status, sampled at up to one point per second and downsampled for the browser poll. History resets on contract switch and server restart.
- The OI selector defaults to Automatic and can be manually overridden. The widget open/closed state is remembered in the browser.
- No API credentials are included. This application remains read-only and does not place orders.

VERSION 3.5 ADDITIONS
- Added Yahoo Finance INR=X USD/INR delayed reference endpoint (/api/usd-inr), with timestamp, quote age, change percentage and intraday mini-chart history.
- Added USD/INR tailwind / headwind / neutral signal. The default ±0.10% threshold is configurable; a fresh signal contributes a limited +1 / -1 momentum modifier. It does not independently generate BUY/SELL. Stale quotes are excluded.
- Added browser notification when the FX signal changes into a tailwind/headwind state after the initial quote, subject to browser notification permission.
- Flattened the dashboard into a responsive two-column widget layout. All 15 top-level widgets have collapse controls and draggable dotted handles. Order and collapse state persist in local storage; Reset layout restores the default arrangement.
- Added reset-layout control and included the current USD/INR reading in exported JSON snapshots.
- All 15 dashboard widgets, including the four KPI cards, are collapsible and draggable using the dotted handle. Widget order and open/closed state are saved in browser local storage. Use Reset layout to restore the default layout.

NEXT RECOMMENDED ALERTS / INDICATORS (NOT YET IMPLEMENTED)
1. FX-adjusted MCX fair-value divergence: compare the same maturity of Henry Hub and MCX, adjust for USD/INR, then alert when MCX deviates materially from the implied move. Contract-month alignment is essential before calculating this.
2. Henry Hub calendar spread / term structure: front-month versus next-month price, spread widening/narrowing, and contract-roll proximity. This helps avoid interpreting a front-month move as a signal for a different MCX expiry.
3. Weather model revision alert: compare successive ECMWF/GFS runs and population-weighted HDD/CDD changes, rather than relying only on the dashboard's six-city proxy. NOAA publishes official 6-10 and 8-14 day temperature outlooks.
4. EIA storage event alert: countdown to the release, actual versus a named consensus source, five-year and year-ago deviations, plus regional breakdowns. EIA's weekly report includes regional stocks and historical comparisons.
5. MCX volatility / participation alerts: ATR expansion, unusually high volume versus the 20-bar average, opening gap, VWAP reclaim/loss, and price/OI confirmation.
6. Liquidity and expiry alerts: bid-ask spread widening, thin order book, low volume, expiry-day risk and rollover into the next MCX contract.
7. Event-risk calendar: EIA release, NOAA model updates, US holidays, major LNG terminal outages and significant pipeline maintenance notices.
