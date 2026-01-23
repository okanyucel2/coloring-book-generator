# Analytics Dashboard Requirements - Phase 1 Monitoring

## Overview
Post-M3 analytics dashboard for tracking Etsy sales, AI generation performance, and coloring book quality metrics.

---

## 1. Sales & Revenue Metrics (Etsy Integration)

### Daily Dashboard
```
┌─────────────────────────────────────────┐
│ SALES SUMMARY (Today)                   │
├─────────────────────────────────────────┤
│ Orders: 3                                │
│ Revenue: $17.97 (gross)                  │
│ Profit: $15.42 (85.8%)                   │
│ Avg Order Value: $5.99                   │
│ Best Seller: Multi-Animal Collection     │
└─────────────────────────────────────────┘
```

### Weekly Rollup
- Total orders, revenue trend
- Top 3 products by sales
- Customer acquisition cost (via ads, if any)
- Conversion rate (clicks → purchases)

### Monthly Analysis
- Revenue vs target ($300-$400 goal)
- Product mix (% singles vs bundles)
- Seasonal trends
- Customer retention (repeat purchases)

---

## 2. AI Generation Performance Metrics

### Generation Pipeline
```
Generated This Month: 245 images
├─ Gemini (fast): 45 (18%)
├─ Imagen (standard): 180 (73%)
└─ Imagen-Ultra (premium): 20 (8%)

Cache Hit Ratio: 34% (85/245 from cache)
Avg Generation Time: 6.2s (non-cached)
Failed Generations: 0 (100% success rate)
API Cost: ~$2.40 (mostly free tier)
```

### Quality Metrics (Post-Generation)
- **Validation Success Rate**: % passing QA checks
  - Line thickness consistency
  - White space optimization (>60% white for coloring)
  - Image clarity & contrast
  - No rendering artifacts

- **Model Comparison Table**:
  | Metric | Gemini | Imagen | Imagen-Ultra |
  |--------|--------|--------|--------------|
  | Avg Time | 5.2s | 6.8s | 8.1s |
  | Line Quality | Good | Excellent | Premium |
  | Detail Level | 6/10 | 8/10 | 9/10 |
  | User Rating | 3.8★ | 4.4★ | 4.7★ |
  | Cost/1000 | $0 | $0 | $0 |

---

## 3. Popular Animals Tracking

### Trending Animals (Last 30 Days)
```
📊 Top 10 Generated Animals
1. Butterfly: 45 images (18%)
2. Cat: 32 images (13%)
3. Elephant: 28 images (11%)
4. Dolphin: 24 images (10%)
5. Unicorn: 22 images (9%)
6. Lion: 18 images (7%)
7. Giraffe: 16 images (7%)
8. Whale: 14 images (6%)
9. Zebra: 12 images (5%)
10. Penguin: 10 images (4%)
```

### Sales vs Generation Ratio
- Which animals **generate** most ≠ which **sell** most
- Example: Butterfly generates 45x but sells 8x
- Track: Generation popularity vs Sales popularity divergence

### Animal Wish List
- Track customer requests (Etsy messages, comments)
- Queue high-demand animals for next batch

---

## 4. Customer Engagement Metrics

### Review & Rating Analysis
```
Average Rating: 4.6★ (target: 4.5+)
Review Count: 24 reviews (target: 50+ by month 3)
Repeat Customer Rate: 12% (bought 2+ products)

Customer Feedback Tags:
✅ High Quality: 18 mentions
✅ Great for Kids: 15 mentions
✅ Print-Ready: 10 mentions
⚠️ More Animals Needed: 3 mentions
⚠️ Want Difficulty Levels: 2 mentions
```

### Engagement Funnel
- Shop Views: Daily tracker
- Product Views: Which listings get clicked?
- Favorites (hearts): Which products are wishlisted?
- Reviews: NPS-style sentiment analysis

---

## 5. Print Quality & Delivery Metrics

### File Delivery Success
```
PDF Generated: 247 files
├─ Successfully Delivered: 246 (99.6%)
├─ Download Retries: 3 (file corruption cases)
└─ Failed: 1 (customer browser issue)

Avg File Size: 2.1 MB
Avg Download Time: 8 seconds
Print Quality Issues Reported: 0
```

### A/B Testing (Post-M3)
- **Variable 1**: Difficulty level label effect
  - "Easy" listings vs "Medium" vs "Hard"
  - Track which sells best

- **Variable 2**: Bundle size effect
  - 2-animal bundles vs 5-animal vs 10-animal
  - Track conversion rate per bundle size

---

## 6. Backend Performance Metrics

### API Usage
```
Daily API Calls: 45-60 (generation requests)
Cache Hit Rate: 34% (saves API quota)
Peak Time: 6-9 PM (customer browsing hours)
Downtime: 0 minutes (99.99% uptime)
```

### Cost Tracking
```
Monthly Cost Breakdown:
├─ Imagen API: $0 (free tier + cached)
├─ PDF Processing: $0 (local)
├─ Hosting: ~$10 (shared allocation)
├─ Etsy Fees: ~$30 (6.5% of $450 revenue)
└─ Total Cost: ~$40 (91% margin)
```

---

## 7. Inventory & Listing Metrics

### Active Listings (Etsy Shop)
```
Total Listings: 12 (as of Month 1)
├─ Single Animal (5-10 pages): 5 listings
├─ Collections (15-25 pages): 4 listings
├─ Mega Packs (40+ pages): 2 listings
└─ Custom (made-to-order): 1 listing

Listing Quality Score: 92/100 (Etsy metric)
Banned/Flagged Listings: 0
Renewal Cost: $0.20 × 12 = $2.40/month
```

### Seasonal Planning
- Q4 (Oct-Dec): Holiday-themed listings (15+ new)
- Q1 (Jan-Mar): New Year activity bundles (10+ new)
- Q2 (Apr-Jun): Back-to-school prep (20+ new)

---

## 8. Dashboard Technical Spec

### Tool: Google Sheets (MVP) → Tableau/Metabase (Later)

**Quick MVP Approach** (Weeks 1-4):
```
Google Sheet with 5 tabs:
1. Daily Summary (auto-pull Etsy data via API)
2. Animal Analytics (generation & sales)
3. Customer Feedback (copy from Etsy reviews)
4. Financial Tracking (revenue & costs)
5. A/B Tests (manual tracking during Month 1)
```

**Advanced Dashboard** (Month 2+):
- Etsy API integration (real-time sales data)
- Image analytics (Imagen API usage tracking)
- Custom Python script to aggregate data
- Weekly email report automation

---

## 9. Key Performance Indicators (KPIs)

### Tier 1: Business Health (Check Daily)
| KPI | Target | Current | Status |
|-----|--------|---------|--------|
| Daily Revenue | $15+ | $17.97 | ✅ |
| Avg Rating | 4.5★ | 4.6★ | ✅ |
| Review Count | 1+/day | 0.8/day | ⚠️ |
| Conversion Rate | 2% | 1.8% | ⚠️ |

### Tier 2: Generation Performance (Weekly)
| KPI | Target | Current | Status |
|-----|--------|---------|--------|
| Cache Hit % | 30% | 34% | ✅ |
| Generation Success | 99%+ | 100% | ✅ |
| Model Quality Score | 8.5/10 | 8.3/10 | ⚠️ |
| Cost per Image | <$0.01 | $0.001 | ✅ |

### Tier 3: Growth (Monthly)
| KPI | Target | Current | Status |
|-----|--------|---------|--------|
| MoM Revenue Growth | 20% | TBD | - |
| New Customers | 50+ | 28 | ⚠️ |
| Repeat Rate | 10% | 12% | ✅ |
| Shop Favorites | 100+ | 34 | ⚠️ |

---

## 10. Reporting & Action Items

### Weekly Report (Every Monday)
- Top 3 best-selling products
- Any customer complaints/feedback
- Cache hit rate trend
- Recommend 1-2 actions (new listings, price adjustments)

### Monthly Review (End of Month)
- Revenue vs $300-$400 target
- Product mix analysis (singles vs bundles)
- A/B test results
- Plan next month's releases (new animals, themes)

### Action Triggers (Immediate Response)
- Rating drops below 4.3★ → Quality review
- 3+ complaints about same animal → Regenerate
- Cache hit drops below 20% → Optimize generation
- Revenue 30% below target → Promotional discount

---

## 11. Tools & Integration

### Currently Available
✅ Etsy API (for sales data)
✅ Google Sheets (for manual tracking)
✅ Imagen API (usage tracking built-in)

### Future Additions (Month 2+)
- Tableau/Metabase (visual dashboard)
- Custom Python analytics script
- Email automation (weekly reports)
- Slack notifications (high-value orders, issues)

---

## 12. Metrics Snapshot (Template for Daily Use)

```
DATE: 2026-01-23

📊 SALES
Revenue (Today): $17.97
Orders: 3
Profit: $15.42 (85.8%)
Top Seller: Multi-Animal Collection

🎨 GENERATION
Images Created: 8
Cache Hit: 4/8 (50%)
Model Used: imagen (7), gemini (1)
API Cost: ~$0.01

⭐ REVIEWS
New Reviews: 1
Avg Rating: 4.6★ (24 total)
Latest Feedback: "Perfect for my daughter!"

📈 TRENDING
Most Generated: Butterfly (45 total)
Most Sold: Cat Collection (5 sales)
Wish List: Monkey, Sloth, Parrot (customer requests)

⚠️ ALERTS
None today ✅
```

---

## Conclusion

Start with **Google Sheets MVP** (Weeks 1-4), track daily metrics manually, then graduate to automated dashboard by Month 2. Focus on 3 KPIs: Revenue, Rating, and Customer Feedback.

