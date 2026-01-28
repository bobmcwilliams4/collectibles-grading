# PRICING RESEARCH PROMPTS - STANDARDIZED QUERY TEMPLATES

## Authority Level 11.0 | Collectibles Grading System Skill

---

## PERPLEXITY SONAR PROMPTS

### PRIMARY PRICE SEARCH

```
Search for recent sold prices for [TITLE] #[ISSUE] comic book.

Find:
1. eBay sold listings in the last 90 days for grades [GRADE-1] to [GRADE+1]
2. Heritage Auctions sales for this issue
3. GoCollect fair market value at grade [GRADE]
4. CGC census population for this grade
5. Current eBay listings (asking prices for reference only)

Format response as JSON:
{
  "ebay_sold": [{"price": X, "grade": Y, "date": "YYYY-MM-DD"}],
  "heritage_sales": [{"price": X, "grade": Y, "date": "YYYY-MM-DD"}],
  "gocollect_fmv": X,
  "cgc_census": {"total_graded": X, "at_grade": Y, "higher_grades": Z},
  "market_trend": "rising|stable|declining"
}
```

### KEY ISSUE VERIFICATION

```
Is [TITLE] #[ISSUE] a key issue comic book?

Check for:
1. First appearances of any characters
2. Origin stories
3. Deaths of major characters
4. First work by notable creators
5. Crossover significance
6. Historical significance

Format response as JSON:
{
  "is_key": true|false,
  "key_reasons": ["reason1", "reason2"],
  "first_appearances": ["character1", "character2"],
  "notable_events": ["event1"],
  "significance_tier": "mega-key|major-key|minor-key|not-key"
}
```

### CGC CENSUS LOOKUP

```
What is the CGC census population for [TITLE] #[ISSUE]?

Provide:
1. Total copies graded by CGC
2. Breakdown by grade (9.8, 9.6, 9.4, etc.)
3. Universal (blue label) count
4. Signature Series count
5. Qualified/Restored counts

Format as JSON:
{
  "total_graded": X,
  "grade_distribution": {
    "9.8": X, "9.6": X, "9.4": X, "9.2": X, "9.0": X,
    "8.5": X, "8.0": X, "7.5": X, "7.0": X, "lower": X
  },
  "label_breakdown": {
    "universal": X,
    "signature_series": X,
    "qualified": X,
    "restored": X
  }
}
```

---

## EBAY SEARCH SYNTAX

### SOLD LISTINGS QUERY

```
[TITLE] [ISSUE] CGC [GRADE] -lot -reprint -facsimile

Filters:
- Sold Items: Yes
- Condition: Used (graded comics)
- Sort: Recently Ended
- Time: Last 90 days
```

### RAW COMIC SEARCH

```
[TITLE] [ISSUE] raw -CGC -CBCS -graded -lot -reprint

Filters:
- Condition: Used
- Sort: Price + Shipping: lowest first (for raw baseline)
```

### ADVANCED OPERATORS

| Operator | Usage | Example |
|----------|-------|---------|
| -term | Exclude | -lot (excludes lots) |
| (term1,term2) | OR | (CGC,CBCS) |
| "exact phrase" | Exact match | "Amazing Spider-Man" |
| term* | Wildcard | Spider* |

---

## GOCOLLECT API QUERIES

### FAIR MARKET VALUE

```
GET /api/comic/{publisher}/{title}/{issue}/fmv?grade={grade}

Response:
{
  "fmv": 1250.00,
  "grade": 9.4,
  "last_updated": "2024-01-15",
  "trend_30d": "+5.2%",
  "trend_90d": "+12.1%"
}
```

### SALES HISTORY

```
GET /api/comic/{publisher}/{title}/{issue}/sales?grade={grade}&days=90

Response:
{
  "sales": [
    {"price": 1300, "grade": 9.4, "date": "2024-01-10", "source": "eBay"},
    {"price": 1200, "grade": 9.4, "date": "2024-01-05", "source": "Heritage"}
  ],
  "average": 1250,
  "median": 1250,
  "high": 1300,
  "low": 1200
}
```

---

## HERITAGE AUCTIONS LOOKUP

### SEARCH TEMPLATE

```
Search Heritage Auctions comics archive for:
[TITLE] #[ISSUE] [PUBLISHER]

Filter by:
- Grade range: [GRADE-1] to [GRADE+1]
- Date range: Last 2 years
- Sort: Most recent first

Return:
- Hammer price (not including buyer's premium)
- Grade
- Sale date
- Lot number
- Any notable pedigree
```

### PEDIGREE IDENTIFICATION

| Pedigree | Premium | Notes |
|----------|---------|-------|
| Mile High | +300-500% | Highest quality Golden Age |
| San Francisco | +100-200% | Exceptional Golden Age |
| Denver | +75-150% | Major collection |
| Allentown | +50-100% | Golden Age collection |
| Bethlehem | +50-100% | Quality Silver Age |
| Pacific Coast | +30-75% | Large collection |
| Curator | +25-50% | Bronze Age quality |
| Don Rosa | +20-40% | Disney specialist |

---

## PRICE AGGREGATION LOGIC

### WEIGHTED AVERAGE FORMULA

```python
def calculate_fair_market_value(sales_data):
    """
    Calculate FMV using weighted average with outlier removal
    """
    weights = {
        'heritage': 1.3,      # Auction house premium
        'ebay': 1.0,          # Market baseline
        'gocollect': 1.2,     # Aggregated data
        'mycomicshop': 0.9,   # Retail markup
        'comiclink': 1.2      # Quality auction
    }
    
    # Remove outliers (beyond 2 standard deviations)
    filtered = remove_outliers(sales_data, std_threshold=2.0)
    
    # Weight by source and recency
    weighted_prices = []
    for sale in filtered:
        recency_weight = calculate_recency_weight(sale['date'])
        source_weight = weights.get(sale['source'], 1.0)
        weighted_prices.append(sale['price'] * recency_weight * source_weight)
    
    return sum(weighted_prices) / len(weighted_prices)

def calculate_recency_weight(sale_date):
    """More recent sales weighted higher"""
    days_ago = (today - sale_date).days
    if days_ago <= 30:
        return 1.2
    elif days_ago <= 60:
        return 1.1
    elif days_ago <= 90:
        return 1.0
    else:
        return 0.8
```

### OUTLIER REMOVAL

```python
def remove_outliers(prices, std_threshold=2.0):
    """Remove prices beyond X standard deviations"""
    mean = statistics.mean(prices)
    std = statistics.stdev(prices)
    
    return [p for p in prices 
            if abs(p - mean) <= std_threshold * std]
```

---

## MARKET TREND INDICATORS

### TREND CLASSIFICATION

| Indicator | Meaning | Action |
|-----------|---------|--------|
| Rising (>10% 90d) | Strong demand | Premium pricing OK |
| Stable (±10% 90d) | Normal market | Use FMV |
| Declining (>10% down) | Weak demand | Conservative pricing |
| Volatile (>25% swings) | Unstable | Use median, not average |

### DEMAND SIGNALS

| Signal | Interpretation |
|--------|----------------|
| Low census, high sales | Strong demand, limited supply |
| High census, low sales | Oversupplied, weak demand |
| Movie/TV announcement | Expect spike (buy before, sell during) |
| Creator death | Temporary spike, then normalize |
| Reprint announced | Raw copies may drop |

---

## GRADE-ADJUSTED PRICING

### PRICE MULTIPLIERS BY GRADE

```python
GRADE_MULTIPLIERS = {
    10.0: 15.0,
    9.9: 10.0,
    9.8: 5.0,
    9.6: 3.0,
    9.4: 2.0,
    9.2: 1.6,
    9.0: 1.4,
    8.5: 1.2,
    8.0: 1.0,   # Baseline
    7.5: 0.85,
    7.0: 0.70,
    6.5: 0.55,
    6.0: 0.45,
    5.5: 0.35,
    5.0: 0.28,
    4.0: 0.20,
    3.0: 0.12,
    2.0: 0.08,
    1.0: 0.04
}

def estimate_price_at_grade(base_price, base_grade, target_grade):
    """Estimate price at different grade"""
    base_mult = GRADE_MULTIPLIERS[base_grade]
    target_mult = GRADE_MULTIPLIERS[target_grade]
    return base_price * (target_mult / base_mult)
```

---

## RESPONSE FORMAT TEMPLATE

### STANDARD PRICING RESPONSE

```json
{
  "comic": {
    "title": "Amazing Spider-Man",
    "issue": 129,
    "publisher": "Marvel",
    "year": 1974
  },
  "grade": 9.4,
  "pricing": {
    "fair_market_value": 15000,
    "price_range": {"low": 13500, "high": 16500},
    "confidence": 0.85,
    "last_updated": "2024-01-15"
  },
  "comparable_sales": [
    {"price": 15200, "grade": 9.4, "date": "2024-01-10", "source": "Heritage"},
    {"price": 14800, "grade": 9.4, "date": "2024-01-05", "source": "eBay"}
  ],
  "census": {
    "total_graded": 3847,
    "at_grade": 412,
    "higher_grades": 1203
  },
  "market_trend": "stable",
  "key_issue_info": {
    "is_key": true,
    "reasons": ["First appearance of Punisher"]
  }
}
```

---

*Authority Level 11.0 | Pricing Research Prompts Skill*
