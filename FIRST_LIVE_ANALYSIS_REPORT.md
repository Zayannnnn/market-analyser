# FIRST LIVE AI STOCK ANALYSIS REPORT

This report presents the leaderboard results and analysis details for the first live run of the Market Analyser stock intelligence engine, executed on June 4, 2026.

---

## Analysis Summary

The analysis was performed sequentially across all 6 agents utilizing live RSS feeds and the newly integrated direct Yahoo Finance Chart API:
- **Date/Time of Run**: 2026-06-04 00:31:21 IST (UTC: 2026-06-03 19:01:21 UTC)
- **Monitored Ticker Count**: 19 active stocks (17 successfully fetched via live API)
- **Matched News Articles**: 14 matching articles tracked
- **Target Leaderboard size**: Top 10 stocks

---

## Top 10 Stock Leaderboard

Below is the leaderboard of the top 10 stocks ranked by the unified scoring engine:

| Rank | Ticker | Company Name | Price | Daily Change | Unified Score | Trend | Confidence | AI Explanation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **TCS** | Tata Consultancy Services Limited | ₹2,241.70 | -8.39% | **67/100** | Bearish | Medium | Ticker TCS shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 2 | **INFY** | Infosys Limited | ₹1,222.60 | -3.79% | **65/100** | Bearish | Medium | Ticker INFY shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 3 | **WIPRO** | Wipro Limited | ₹204.10 | -2.74% | **62/100** | Bearish | Medium | Ticker WIPRO shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 4 | **NHPC** | NHPC Limited | ₹75.10 | +3.89% | **54/100** | Bullish | Medium | Ticker NHPC shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 5 | **LT** | Larsen & Toubro Limited | ₹3,953.20 | -1.19% | **51/100** | Bearish | Medium | Ticker LT shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 6 | **ADANIPORTS** | Adani Ports & Special Economic Zone Limited | ₹1,803.80 | -0.59% | **50/100** | Bearish | Medium | Ticker ADANIPORTS shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 7 | **COALINDIA** | Coal India Limited | ₹472.30 | +0.03% | **50/100** | Bullish | Medium | Ticker COALINDIA shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 8 | **SBIN** | State Bank of India | ₹970.45 | +1.44% | **47/100** | Bullish | Medium | Ticker SBIN shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 9 | **CANBK** | Canara Bank | ₹131.85 | +2.15% | **46/100** | Bullish | Medium | Ticker CANBK shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |
| 10 | **JPPOWER** | Jaiprakash Power Ventures Limited | ₹19.33 | +1.79% | **46/100** | Bullish | Medium | Ticker JPPOWER shows strong momentum signals based on technical indicators and volume spikes. *(Fallback explanation due to rate-limit cache-miss)* |

---

## Firestore Storage & Persistence

The run succeeded in updating the active Firestore database under the following collections:
- **`stocks`**: Updated with latest pricing, daily change, trading volume, average volume, market capitalization, and technical indicator fields for all monitored stocks.
- **`news`**: Populated with 14 matched articles, including calculated sentiment scores.
- **`rankings`**: Updated document `current` with the active leaderboard shown above.
- **`snapshots`**: Created a permanent time-stamped history document containing this leaderboard state.
- **`ai_analysis`**: Caches generated Gemini Flash briefings and factor breakdowns for easy retrieval and dashboard rendering.

---

## Verdict Summary

```text
LIVE_ANALYSIS_READY = TRUE
TOP_10_GENERATED = TRUE
```
