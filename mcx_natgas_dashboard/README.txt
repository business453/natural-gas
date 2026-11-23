MCX NATURAL GAS INTELLIGENCE DASHBOARD

WHAT IS INCLUDED
- index.html: one-page dashboard
- TradingView ticker tape showing Henry Hub (NYMEX:NG1!), MCX Natural Gas and USD/INR
- Two TradingView chart embeds: NYMEX:NG1! and MCX:NATURALGAS1!
- Automatic 7-day weather snapshot for six US cities using Open-Meteo
- Manual US fundamentals and live quote inputs
- Transparent rules-based fundamental/momentum score and breakout trigger checklist
- Position sizing calculator
- Local browser storage, browser alerts, JSON snapshot export

HOW TO RUN
1. Extract the ZIP to a folder.
2. Double-click index.html to open it in a modern browser.
3. If the TradingView widgets or weather requests do not load from a local file, run a small local web server from this folder:
   - Windows: double-click start_dashboard.bat
   - Then open http://localhost:8765 in your browser.
   - Or run: python -m http.server 8765
4. Keep the page open during the session. Weather refreshes every 30 minutes; use the Refresh weather button to refresh on demand.

IMPORTANT DATA LIMITATIONS
- The TradingView ticker tape displays Henry Hub (NYMEX:NG1!), MCX Natural Gas and USD/INR inside the dashboard. TradingView lists free CME/NYMEX futures data as delayed by 10 minutes; do not treat it as real-time execution data.
- TradingView widgets do not expose their underlying quote stream to this page, so the signal engine cannot automatically ingest the displayed quote. Enter Henry Hub % change and MCX price/volume/VWAP from your broker. For automated real-time triggers, connect a broker API or purchase an exchange-authorised real-time data entitlement.
- Weather comes from Open-Meteo. The six-city HDD/CDD is a simplified demand proxy, not an official population-weighted US national forecast. Compare actual forecast revisions from NOAA / Forecast Gas / NatGasWeather before selecting the weather-bias input.
- EIA storage actual and consensus values are entered manually after the release. Use the official EIA release and a clearly identified consensus source.
- Position sizing defaults to 1,250 MMBtu per lot as a reference. Verify current MCX contract specifications and the active expiry before placing any trade.
- Signals are rule-based decision support only. They do not predict returns and are not investment advice. Always verify data, order-book liquidity, expiry/rollover, margin, slippage and risk.

DATA LINKS
CME Henry Hub: https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.html
CME free delayed quotes (at least 10 minutes): https://www.cmegroup.com/market-data/browse-data/delayed-quotes.html
TradingView CME/NYMEX data coverage and real-time fees: https://www.tradingview.com/data-coverage/
EIA storage: https://www.eia.gov/naturalgas/storage/
EIA release schedule: https://ir.eia.gov/ngs/schedule.html
NOAA CPC: https://www.cpc.ncep.noaa.gov/
Forecast Gas: https://forecastgas.com/
NatGasWeather: https://natgasweather.com/
MCX: https://www.mcxindia.com/
Open-Meteo docs: https://open-meteo.com/en/docs
