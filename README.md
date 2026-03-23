# 🌾 YieldHunter

Real-time DeFi yield aggregator for Solana. Pulls live APY data from **Kamino**, **MarginFi**, **Solend**, and **Drift**, ranks every opportunity by risk-adjusted return, and tells you exactly where to put your capital for maximum yield.

**Built by LixerDev**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Solana](https://img.shields.io/badge/network-Solana-9945FF)
![License](https://img.shields.io/badge/license-MIT-purple)

---

## 📊 Dashboard Preview

```
🌾 YieldHunter  |  4 protocols  |  refreshed: 09:41:22 UTC

  #   Token   Protocol    Type          Supply APY   Reward APY   Total APY   TVL          Risk    
  1   USDC    Kamino      Supply        6.82%        1.40%        8.22% 🔥    $412M        LOW     
  2   USDT    MarginFi    Supply        5.91%        0.85%        6.76%        $88M         LOW     
  3   SOL     Kamino      Supply        4.20%        2.10%        6.30%        $234M        LOW     
  4   USDC    Solend      Supply        5.60%        0.50%        6.10%        $61M         MEDIUM  
  5   SOL     MarginFi    Supply        3.80%        1.90%        5.70%        $145M        LOW     
  6   mSOL    Drift       Supply        4.50%        0.80%        5.30%        $29M         MEDIUM  
  7   USDC    Drift       Supply        4.80%        0.40%        5.20%        $41M         MEDIUM  
  8   JUP     Kamino      Supply        8.10%        0.00%        8.10% 🔥    $18M         HIGH    
  ...

  4 protocols active  |  36 opportunities  |  Best: 8.22% (USDC/Kamino)
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/LixerDev/YieldHunter.git
cd YieldHunter
pip install -r requirements.txt
cp .env.example .env

# Show top 10 yields across all protocols
python main.py top

# Compare a specific token across all protocols
python main.py compare USDC

# Optimize allocation for $10,000
python main.py optimize --capital 10000

# Live dashboard (refreshes every 30s)
python main.py watch

# Filter by token + minimum APY
python main.py top --token SOL --min-apy 4.0

# Filter by risk level
python main.py top --risk low
```

---

## 🧮 Yield Model

YieldHunter normalizes data from all protocols into a unified model:

```
Total APY = Supply APY + Reward APY (farming incentives)

Risk-Adjusted APY = Total APY × (1 - risk_penalty)
```

### APY Sources per Protocol

| Protocol | Supply APY | Reward APY | Borrow APY | Notes |
|---|---|---|---|---|
| **Kamino** | ✅ | ✅ (KMNO) | ✅ | Lending + strategies |
| **MarginFi** | ✅ | ✅ (MRGN) | ✅ | Lending markets |
| **Solend** | ✅ | ✅ (SLND) | ✅ | Oldest Solana lender |
| **Drift** | ✅ | ✅ (DRIFT) | ✅ | Spot + perps |

---

## ⚖️ Risk Scoring

Each opportunity gets a **risk score (0–100)**, where lower = safer:

| Factor | Weight | Description |
|---|---|---|
| TVL | 40% | Higher TVL = lower smart contract risk |
| Utilization | 30% | 40–80% = healthy; extremes = risky |
| Protocol age | 20% | Older, more battle-tested protocols |
| Audit score | 10% | Security audit coverage |

Risk labels:
- **LOW** (0–30): Safe for large capital
- **MEDIUM** (31–60): Moderate risk
- **HIGH** (61–100): Higher yield, higher risk

---

## 💡 Capital Optimizer

```bash
python main.py optimize --capital 50000 --max-per-protocol 40
```

```
💡 Optimal Allocation — $50,000

  Protocol    Token   APY      Amount        Weekly Yield   Annual Yield
  Kamino      USDC    8.22%    $20,000 (40%) $31.62         $1,644
  MarginFi    USDT    6.76%    $20,000 (40%) $26.00         $1,352
  Solend      USDC    6.10%    $10,000 (20%) $11.73         $610
  ─────────────────────────────────────────────────────────────────
  TOTAL                6.77%   $50,000       $69.35         $3,606
```

---

## 🔔 Alerts

Set up Discord alerts for:
- APY drops more than X% for your positions
- New high-yield opportunity found (> threshold)
- Protocol utilization warning (>90%)

---

## 🏗️ Architecture

```
main.py (CLI)
    └── Aggregator
            ├── protocols/
            │     ├── kamino.py    → GET api.kamino.finance/strategies
            │     ├── marginfi.py  → GET production.marginfi.com/marginfi_groups
            │     ├── solend.py    → GET api.solend.fi/v1/markets/configs
            │     └── drift.py    → GET dlob.drift.trade (spot markets)
            ├── Ranker            → sort by APY, risk, TVL, token
            ├── Optimizer         → greedy allocation algorithm
            ├── Alerter           → Discord webhook + change detection
            └── Dashboard         → Rich live terminal display
```
