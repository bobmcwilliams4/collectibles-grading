# COMIC IDENTIFICATION PATTERNS - METADATA EXTRACTION REFERENCE

## Authority Level 11.0 | Collectibles Grading System Skill

---

## PUBLISHER LOGO IDENTIFICATION

### DC COMICS EVOLUTION

| Era | Years | Logo Style | Location |
|-----|-------|------------|----------|
| Golden Age | 1938-1949 | "A Superman DC Publication" | Top left |
| 1950s | 1950-1969 | "DC" in circle (bullet) | Top left |
| 1970s | 1970-1976 | "DC" bullet with stars | Top left |
| DC Explosion | 1976-1977 | "DC" bullet, "The Line of DC Super-Stars" | Top left |
| DC Implosion | 1978 | "DC Bullet" simplified | Top left |
| 1980s | 1977-2005 | "DC Bullet" (blue circle) | Top left |
| 2005-2012 | 2005-2012 | "DC" swoosh/spin | Top left |
| New 52 | 2012-2016 | "DC" peel-back | Top left |
| Rebirth+ | 2016-present | "DC" simple letters | Top left |

### MARVEL COMICS EVOLUTION

| Era | Years | Logo Style | Location |
|-----|-------|------------|----------|
| Timely | 1939-1951 | "Timely Comics" | Varies |
| Atlas | 1951-1957 | "Atlas" globe | Top right |
| Early Marvel | 1957-1963 | "MC" or "Marvel Comics" | Top left |
| Corner Box | 1963-2000 | Character head in box | Top left corner |
| 2000s | 2000-2012 | "MARVEL" banner | Top |
| Marvel NOW | 2012-present | "MARVEL" text variations | Top/varies |

### OTHER MAJOR PUBLISHERS

| Publisher | Logo Style | Typical Location |
|-----------|------------|------------------|
| Image | "i" logo | Bottom left/varies |
| Dark Horse | Horse head | Top left |
| Vertigo | "V" stylized | Top left |
| IDW | "IDW" letters | Top/bottom |
| Valiant | "V" chevron | Top left |
| Archie | "Archie" banner | Top |
| Harvey | "Harvey" text | Top |
| Dell | "Dell" in diamond | Top left |
| Gold Key | Key logo | Top left |
| Charlton | "Charlton" text | Top/varies |

---

## ISSUE NUMBER LOCATION PATTERNS

### DC COMICS ISSUE NUMBER FORMATS

**CRITICAL: DC uses "Month + NO." format**

| Format | Example | Era | Notes |
|--------|---------|-----|-------|
| "OCT NO. 12" | Cover shows "OCT NO. 12" | 1960s-1970s | Issue is #12, NOT October |
| "NO. 45" | "NO. 45" near logo | 1940s-1960s | Standard format |
| "#123" | "#123" | 1980s+ | Modern format |
| "JUNE-JULY NO. 8" | Bimonthly issue | 1960s | Issue #8 |

**EXTRACTION RULE:**
```
If format = "[MONTH] NO. [X]" → Issue number = X
If format = "[MONTH]-[MONTH] NO. [X]" → Issue number = X
The month is COVER DATE, not issue number!
```

### MARVEL ISSUE NUMBER FORMATS

| Format | Example | Era |
|--------|---------|-----|
| "#X" | "#129" | Standard |
| "Vol. X No. Y" | "Vol. 1 No. 129" | With volume |
| Small box number | Number in corner box | 1960s-1990s |

### INDIE/OTHER FORMATS

| Publisher | Format | Example |
|-----------|--------|---------|
| Image | "#X" | "#1" |
| Dark Horse | "#X of Y" | "#3 of 4" (mini) |
| IDW | "#X" | "#12" |

---

## COVER DATE FORMAT PATTERNS BY ERA

### GOLDEN AGE (1938-1956)

| Format | Example | Notes |
|--------|---------|-------|
| Season + Year | "SPRING 1940" | Quarterly |
| Month + Year | "MARCH 1945" | Monthly |
| Month-Month | "MAR.-APR." | Bimonthly |
| No date | N/A | Some early issues |

### SILVER AGE (1956-1970)

| Format | Example | Notes |
|--------|---------|-------|
| "MONTH YEAR" | "MARCH 1963" | Standard |
| "MON.-MON." | "MAR.-APR." | Bimonthly |
| "MONTH" only | "OCTOBER" | Year in indicia |

### BRONZE AGE (1970-1985)

| Format | Example | Notes |
|--------|---------|-------|
| "MONTH YEAR" | "JUNE 1974" | Standard |
| "NO. X MONTH" | "NO. 129 FEB" | Combined |

### COPPER/MODERN AGE (1985+)

| Format | Example | Notes |
|--------|---------|-------|
| "MONTH YEAR" | "DECEMBER 1988" | Standard |
| Month number | "12/88" | Numeric |
| No cover date | N/A | Check indicia |

---

## COVER PRICE PATTERNS BY DECADE

| Decade | Typical Prices | Format |
|--------|---------------|--------|
| 1940s | 10¢ | "10¢" or "TEN CENTS" |
| 1950s | 10¢ | "10¢" |
| Early 1960s | 10¢, 12¢ | "10¢" → "12¢" (1962) |
| Late 1960s | 12¢, 15¢ | "12¢" → "15¢" (1969) |
| Early 1970s | 15¢, 20¢, 25¢ | Price increases frequent |
| Late 1970s | 35¢, 40¢, 50¢ | "35¢" common |
| 1980s | 60¢, 75¢, $1.00 | Dollar barrier broken |
| 1990s | $1.25, $1.50, $1.95, $2.50 | Steady increases |
| 2000s | $2.25, $2.99, $3.99 | $2-4 range |
| 2010s | $3.99, $4.99 | $4-5 standard |
| 2020s | $4.99, $5.99, $6.99 | $5+ standard |

### PRICE BOX LOCATION

| Era | Location |
|-----|----------|
| Pre-1970 | Top left corner, near logo |
| 1970-1980 | Top left corner |
| 1980+ | Top left or UPC area |

---

## BARCODE/UPC PATTERNS

### PRE-BARCODE ERA (Before 1976)
- No UPC code
- Price in top left corner
- Newsstand distribution only

### BARCODE INTRODUCTION (1976-1979)
- UPC appeared on newsstand editions
- Direct market editions: No UPC or "Spider-Man head" placeholder
- Dual distribution began

### NEWSSTAND VS DIRECT EDITION

| Feature | Newsstand | Direct Edition |
|---------|-----------|----------------|
| UPC | Yes, full barcode | No UPC or logo placeholder |
| Distribution | Newsstands, grocery | Comic shops |
| Returns | Returnable | Non-returnable |
| Rarity (modern) | Rarer (less printed) | More common |
| Value premium | Often 2-10x for modern keys | Standard |

### UPC BOX VARIATIONS

| Type | Description | Era |
|------|-------------|-----|
| Full UPC | Standard barcode | 1976+ newsstand |
| Logo box | Publisher logo replacing UPC | 1980s+ direct |
| Spider-head | Spider-Man head in UPC area | Marvel direct 1980s |
| Blank box | Empty UPC area | Some direct |

---

## VARIANT COVER INDICATORS

### VARIANT TYPES

| Type | Identifier | Typical Location |
|------|------------|------------------|
| Newsstand | UPC barcode | UPC area |
| Direct | Logo/blank UPC | UPC area |
| 2nd Print | "2nd Printing" text | Cover/spine |
| Variant | "Variant Cover" | Cover/bottom |
| 1:X Ratio | "1:25 Variant" | Bottom/back |
| Convention | "SDCC Exclusive" | Cover |
| Store Exclusive | Store name | Cover |
| Foil | Foil cover treatment | Physical |
| Glow-in-dark | Special ink | Physical |
| Chromium | Metallic cover | Physical |

### RATIO VARIANT PATTERNS

| Ratio | Rarity Level | Example |
|-------|--------------|---------|
| 1:10 | Uncommon | Order 10, get 1 variant |
| 1:25 | Scarce | Mid-tier incentive |
| 1:50 | Rare | Higher incentive |
| 1:100 | Very Rare | Major incentive |
| 1:200+ | Ultra Rare | Top tier |

---

## ERA CLASSIFICATION

| Era | Years | Characteristics |
|-----|-------|-----------------|
| Platinum Age | 1897-1938 | Pre-Superman, newspaper strips |
| Golden Age | 1938-1956 | Superman debut to Comics Code |
| Silver Age | 1956-1970 | Flash revival to relevant comics |
| Bronze Age | 1970-1985 | Relevance to Crisis |
| Copper Age | 1985-1991 | Dark Knight to Image founding |
| Modern Age | 1991-present | Image founding onward |

### ERA PRICE INDICATORS

| Price | Likely Era |
|-------|------------|
| 10¢ | Golden-early Silver |
| 12¢ | Silver Age |
| 15¢-25¢ | Late Silver-early Bronze |
| 30¢-60¢ | Bronze Age |
| 75¢-$1.50 | Copper Age |
| $1.50+ | Modern Age |

---

## EXTRACTION PRIORITY ORDER

When identifying a comic, extract in this order:

1. **Publisher** - Logo identification
2. **Title** - Main title text (largest text)
3. **Issue Number** - "NO. X" or "#X" format
4. **Cover Date** - Month/Year (NOT part of issue number)
5. **Cover Price** - Price box
6. **Era** - Based on price + date + logo style
7. **Variant Type** - UPC area, cover text
8. **Volume** - If present, typically "Vol. X"

---

## COMMON EXTRACTION ERRORS TO AVOID

| Error | Correct Approach |
|-------|------------------|
| "OCT NO. 12" = October issue | NO. 12 is the issue number |
| Month is issue number | Month = cover date only |
| Missing volume | Check indicia if unclear |
| Wrong publisher | Verify logo matches era |
| Variant as regular | Check UPC area carefully |

---

*Authority Level 11.0 | Comic Identification Patterns Skill*
