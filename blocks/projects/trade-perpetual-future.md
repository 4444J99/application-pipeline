---
title: "Perpetual futures trading system"
category: projects
tags: [ai, blockchain, ci-cd, database, developer-tools, fintech, platform, react, testing, typescript]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job]
tier: full
review_status: auto-generated
---

# Project: Perpetual futures trading system

## One-Line
Perpetual futures trading system

## Short (100 words)
Perpetual futures trading system. A non-custodial perpetual futures trading platform on Solana, powered by Drift Protocol — with AI-driven sentiment, on-chain gaming, and a Cloudflare Worker backend. Users connect browser wallets (Phantom, Solflare) and trade leveraged perpetual contracts (SOL-PERP, BTC-PERP, ETH-PERP) directly against Drift Protocol smart contracts. The platform never touches user funds. Revenue accrues through Drift's on-chain Builder Code referral system — a compliant, zero-custody affiliate model where 10-15% of trading fees are paid automatically to the platform operator. This is an ORGAN-III (Ergon) repository — the commerce organ of the organvm creative-institutional system.

## Full
**Product Overview:** Perpetual futures ("perps") are the dominant trading instrument in crypto markets — contracts that let traders speculate on asset prices with leverage, without expiration dates. The global crypto derivatives market regularly exceeds $100B in daily volume. Most of that volume flows through centralized exchanges (Binance, Bybit), which custody user funds and operate opaque matching engines. `trade-perpetual-future` takes a different approach. It is a **full-stack trading platform** — a React SPA backed by a Cloudflare Worker API — that connects users directly to [Drift Protocol](https://drift.trade), Solana's largest decentralized perpetual futures exchange. The platform: - **Never custodies funds.** Users sign every transaction in their own wallet. Private keys never leave the browser extension. - **Delegates all trading logic to audited smart contracts.** Order matching, liquidation, funding rates, and settlement all happen on-chain via Drift Protocol's program accounts. - **Generates revenue without holding money.** The Drift Builder Code system attributes trades to the referring frontend and pays a percentage of protocol fees directly to the operator's wallet — no invoicing, no payment processing, no custodial risk. - **Enhances trading with AI sentiment.** A Cloudflare Worker API proxies Claude for market sentiment analysis, reality scenario generation, and hashtag trend detection — with PRNG fallbacks for zero-downtime operation. - **Deploys on Cloudflare.** Pages for the SPA, Workers for the API, KV for caching and affiliate state. Infrastructure cost approaches zero. This architecture produces a product that is simultaneously simpler to operate, harder to attack, and more transparent than traditional alternatives. ### Core Capabilities | Capability | Implementation | |-----------|----------------| | **Markets** | SOL-PERP, BTC-PERP, ETH-PERP (expandable via `markets.ts`) | | **Order types** | Market, Limit, Stop Market | | **Leverage** | 1x to 10x, visual slider control | | **Position management** | Real-time open positions, one-click close, P&L tracking | | **Account dashboard** | Total collateral, net USD value, unrealized P&L, current leverage | | **Sentiment analysis** | AI-powered market sentiment with Claude (PRNG fallback) | | **Gaming** | Coin flip, dice roll, prediction games with achievements and leaderboards | | **Affiliate system** | Referral codes, commission tracking, affiliate leaderboard | | **Personalization** | 7

## Links
- GitHub: https://github.com/organvm-iii-ergon/trade-perpetual-future
- Organ: ORGAN-III (Ergon) — Commerce
