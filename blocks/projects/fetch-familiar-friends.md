---
title: "Social matching and community platform"
category: projects
tags: [ai, ci-cd, database, developer-tools, platform, react, testing, typescript]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job]
tier: full
review_status: auto-generated
stats:
  languages: [typescript]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: CRITICAL
---

# Project: Social matching and community platform

## One-Line
Social matching and community platform

## Short (100 words)
Social matching and community platform. A social pet calendar, care tracker, and gamified companion app for dog and cat owners — built on React 18, Supabase, and Stripe. Fetch Familiar Friends (internally branded DogTale Daily) is a consumer-facing B2C progressive web application that transforms everyday pet ownership into an engaging daily ritual. The app delivers personalized dog and cat imagery each day, layered with journaling, health tracking, social networking, a full gamification engine, and a three-tier subscription model. It sits within ORGAN-III (Ergon), the commerce organ of the eight-organ creative-institutional system, and represents a production-ready consumer product with real monetization infrastructure. Part of ORGAN-III (Ergon).

## Full
**Product Overview:** Pet ownership in the digital age lacks a single hub that combines daily delight with practical care management. Fetch Familiar Friends solves this by merging four distinct value propositions into one application: 1. **Daily content ritual.** Each day surfaces a new breed-specific dog or cat image via the Dog CEO and TheCatAPI services, accompanied by breed knowledge, fun facts, and a daily content seed that makes every visit feel fresh. 2. **Care management.** Owners track vaccinations, vet visits, medications, weight history, grooming schedules, and custom reminders — all attached to individual pet profiles with full health timelines. 3. **Social platform.** An activity feed, friend lists, reactions (like, love, paw, wow), comments, and a proximity-based "Nearby Pet Parents" feature create a lightweight social network purpose-built for the pet community. 4. **Gamification layer.** Quests, achievements, XP leveling, virtual pets, gym battles, PvP matchmaking, season passes, and leaderboards borrow proven engagement mechanics from mobile gaming to drive daily retention. The combination positions the product as a *daily companion app* rather than a single-purpose utility, targeting the recurring-engagement model that sustains consumer subscription businesses. ### Target Audience - Dog and cat owners who want a daily touchpoint with their pet's life - Pet parents managing multiple animals and recurring care schedules - Social pet communities seeking a dedicated, non-generic platform - Casual gamers who enjoy collection and progression mechanics ### Business Model The app operates a freemium SaaS model with three subscription tiers managed through Stripe: | Tier | AI Messages/Day | Features | |------|-----------------|----------| | **Free** | 5 | Core calendar, journaling, favorites, basic health tracking | | **Premium** | 50 | Full social hub, advanced gamification, coaching hub, extended AI | | **Luxury** | 500 | Telemedicine, AR camera, unlimited AI, priority support | Stripe checkout sessions, customer portal management, and webhook-driven subscription state synchronization are implemented via Supabase Edge Functions running on Deno Deploy. ---

**Technical Architecture:** The application is built as a single-page progressive web app with a clear separation between the client-side React application and the Supabase backend-as-a-service layer. ### Stack Overview | Layer | Technology | Purpose | |-------|-----------|---------| |

## Links
- GitHub: https://github.com/organvm-iii-ergon/fetch-familiar-friends
- Organ: ORGAN-III (Ergon) — Commerce
