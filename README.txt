MCX NATURAL GAS INTELLIGENCE DASHBOARD
Angel One SmartAPI + resilient contract-master loader + free delayed Henry Hub reference quote
Build: v3.2

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
4. Rule-based fundamental/momentum dashboard, breakout checklist, risk sizing and JSON snapshot export.

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
- Yahoo Finance NG=F: delayed quote. Its public endpoint is not a documented exchange feed, may change, throttle or stop working, and must not be used as an execution-grade real-time source. A page refreshing every minute does not remove the underlying delay.
- CME's public delayed futures quotes are delayed by at least 10 minutes. CME says its website market data is for reference and should not validate or replace its licensed real-time feed.
- For genuine real-time Henry Hub prices, obtain a CME/NYMEX-authorised real-time market-data entitlement from CME or an authorised vendor. There is no reliable, exchange-authorised, unlimited free real-time futures feed assumed in this package.
- Angel One's average_traded_price field is used as an indicative VWAP proxy only; it may not match a platform's exact intraday VWAP calculation. Verify on your chart before using it.
- The stream's snapshot mode provides OI, but the dashboard does not automatically classify long build-up/short covering from a single tick. Use prior-session/interval comparisons and set the OI interpretation deliberately.
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
- Henry Hub unavailable: Yahoo's public endpoint may be throttled or changed. Open https://finance.yahoo.com/quote/NG%3DF/ to inspect the delayed quote, or use CME delayed quotes. The signal engine will not use a stale quote.
- Windows launcher errors: verify Python 3.10+, then run run_dashboard.bat again. Keep the terminal window open.

REFERENCES
Angel One SmartAPI documentation: https://smartapi.angelone.in/docs
Angel One official Python SDK: https://github.com/angel-one/smartapi-python
Angel One WebSocket 2.0: https://smartapi.angelone.in/docs/WebSocket2
Angel One market data API: https://smartapi.angelone.in/docs/MarketData
Angel One instrument master (current documented host): https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json
Legacy Angel One instrument master fallback: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
Yahoo Finance NG=F (delayed quote): https://finance.yahoo.com/quote/NG%3DF/
CME delayed quotes: https://www.cmegroup.com/market-data/browse-data/delayed-quotes.html
CME market-data delay and use notice: https://www.cmegroup.com/trading/about-quotes.html
EIA storage: https://www.eia.gov/naturalgas/storage/
EIA release schedule: https://ir.eia.gov/ngs/schedule.html
NOAA Climate Prediction Center: https://www.cpc.ncep.noaa.gov/
Forecast Gas: https://forecastgas.com/
NatGasWeather: https://natgasweather.com/
MCX: https://www.mcxindia.com/
Open-Meteo docs: https://open-meteo.com/en/docs

VERSION 3.3 TESTED PATCH
- Contract parser now recognizes MCX master segment labels MCX, MCX_FO / mcx_fo, and NCO. Angel One's WebSocket subscription still uses exchangeType=5 (MCX_FO).
- If a downloaded master has no matching Natural Gas futures, the backend error now includes the exchange segments and candidate Natural Gas rows to help diagnose schema changes.
- No API credentials are included. This application remains read-only and does not place orders.
