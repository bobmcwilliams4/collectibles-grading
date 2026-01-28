---
name: collectibles-cataloger
description: Comprehensive cataloging system for collectibles including comic books, baseball cards, trading cards, coins, stamps, vinyl records, action figures, and other hobby items. Use this skill when users want to catalog, value, grade, organize, or manage any collectible inventory. Supports image-based identification, condition grading, market valuation, export to CSV/JSON, and integration with major collecting platforms (CLZ, ComicBase, COMC, PSA, CGC, Beckett).
---

# Collectibles Cataloger

Professional-grade cataloging system for all collectible types with standardized fields, grading systems, and valuation support.

## Supported Collectible Types

### Comic Books
**Grading Scale:** CGC/CBCS 0.5-10.0
**Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| title | Series name | Teen Titans |
| issue_number | Issue # | 8 |
| volume | Volume # | 1 |
| publisher | Publisher name | DC Comics |
| cover_date | Month-Year | March-April 1967 |
| cover_price | Original price | $0.12 |
| story_title | Story name | A Killer Called Honey Bun! |
| writer | Writer(s) | Bob Haney |
| penciler | Pencil artist | Nick Cardy |
| inker | Ink artist | Nick Cardy |
| cover_artist | Cover artist | Nick Cardy |
| editor | Editor | George Kashdan |
| colorist | Colorist | - |
| letterer | Letterer | - |
| characters | Featured characters | Robin, Kid Flash, Aqualad, Wonder Girl |
| genre | Genre | Superhero |
| era | Comic era | Silver Age |
| page_count | Total pages | 32 |
| upc | UPC/Barcode | N/A (pre-1970s) |
| cgc_grade | Professional grade | 4.0 |
| raw_grade | Estimated grade | VG/FN |
| condition_notes | Defects | Spine stress, corner wear |
| key_issue | Key status | No |
| first_appearance | 1st appearances | - |
| variant | Variant type | - |
| signed | Signatures | - |
| storage | Storage type | Bagged & Boarded |
| purchase_price | What paid | $25.00 |
| purchase_date | When purchased | 2024-01-15 |
| market_value | Current value | $40.00 |
| location | Storage location | Box 3, Slot 12 |
| notes | Additional notes | - |

### Baseball Cards / Trading Cards
**Grading Scale:** PSA/BGS 1-10
**Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| player_name | Player/Subject | Mickey Mantle |
| year | Card year | 1952 |
| brand | Manufacturer | Topps |
| set_name | Set name | Topps Baseball |
| card_number | Card # | 311 |
| subset | Subset/Insert | Base |
| parallel | Parallel type | - |
| serial_number | If numbered | /500 |
| auto | Autograph | No |
| relic | Memorabilia | No |
| relic_type | Jersey/Bat/etc | - |
| team | Team name | New York Yankees |
| position | Position | CF |
| rookie | Rookie card | Yes |
| sport | Sport type | Baseball |
| psa_grade | PSA grade | 8 |
| bgs_grade | BGS grade | - |
| sgc_grade | SGC grade | - |
| raw_grade | Estimated | NM |
| centering | Centering % | 60/40 |
| corners | Corner condition | Sharp |
| edges | Edge condition | Clean |
| surface | Surface condition | No creases |
| cert_number | Cert # | 12345678 |
| purchase_price | Cost | $150.00 |
| market_value | Current value | $200.00 |
| comp_sales | Recent comps | $180, $210, $195 |
| location | Storage | Binder 2, Page 5 |

### Coins
**Grading Scale:** Sheldon 1-70 (PCGS/NGC)
**Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| country | Country | USA |
| denomination | Face value | Quarter |
| year | Mint year | 1932 |
| mint_mark | Mint location | D |
| variety | Die variety | - |
| composition | Metal | 90% Silver |
| weight | Weight grams | 6.25g |
| diameter | Diameter mm | 24.3mm |
| series | Series name | Washington Quarter |
| pcgs_grade | PCGS grade | MS65 |
| ngc_grade | NGC grade | - |
| raw_grade | Estimated | AU |
| strike | Strike quality | Full Bell Lines |
| luster | Luster quality | Brilliant |
| toning | Toning | Rainbow |
| eye_appeal | Eye appeal | Above Average |
| cert_number | Cert # | 98765432 |
| purchase_price | Cost | $500.00 |
| market_value | Current value | $750.00 |
| pcgs_price_guide | Guide value | $725.00 |
| location | Storage | Safe, Tray 2 |

### Stamps
**Grading Scale:** VG, F, VF, XF, Superb
**Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| country | Country | USA |
| year | Issue year | 1918 |
| denomination | Face value | 24¢ |
| scott_number | Scott catalog # | C3 |
| description | Subject | Inverted Jenny |
| color | Color | Blue/Red |
| condition | Mint/Used | Mint |
| og | Original gum | OG |
| nh | Never hinged | NH |
| centering | Centering | VF |
| perforations | Perf gauge | 11 |
| watermark | Watermark | None |
| plate_number | Plate # | - |
| block | Block type | Single |
| cert | Certification | PSE |
| grade | PSE grade | 90 |
| market_value | Current value | - |
| location | Storage | Album 3, Page 42 |

### Vinyl Records
**Grading Scale:** Goldmine G, VG, VG+, NM, M
**Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| artist | Artist name | The Beatles |
| album_title | Album name | Abbey Road |
| year | Release year | 1969 |
| label | Record label | Apple |
| catalog_number | Catalog # | SO-383 |
| format | LP/45/78 | LP |
| speed | RPM | 33⅓ |
| pressing | Pressing info | 1st US |
| matrix | Matrix # | - |
| record_grade | Vinyl grade | VG+ |
| sleeve_grade | Cover grade | VG |
| inner_sleeve | Inner condition | Generic |
| inserts | Inserts included | Poster |
| genre | Genre | Rock |
| barcode | UPC | - |
| discogs_id | Discogs release | 123456 |
| purchase_price | Cost | $50.00 |
| market_value | Current value | $75.00 |
| location | Storage | Shelf A, Slot 23 |

### Action Figures / Toys
**Grading Scale:** AFA 0-100
**Fields:**
| Field | Description | Example |
|-------|-------------|---------|
| name | Figure name | Luke Skywalker |
| line | Product line | Star Wars |
| brand | Manufacturer | Kenner |
| year | Release year | 1978 |
| series | Series/Wave | 12-Back |
| scale | Scale | 3.75" |
| condition | MOC/Loose | MOC |
| afa_grade | AFA grade | 85 |
| card_condition | Card grade | C85 |
| bubble_condition | Bubble grade | B85 |
| figure_condition | Figure grade | F85 |
| variant | Variant | Double Telescoping |
| accessories | Included items | Lightsaber |
| completeness | % Complete | 100% |
| country | Country of origin | Hong Kong |
| upc | UPC | - |
| purchase_price | Cost | $2500.00 |
| market_value | Current value | $3500.00 |
| location | Storage | Display Case 2 |

## Condition Grading Quick Reference

### Comics (CGC Scale)
- **10.0 Gem Mint** - Perfect
- **9.8 NM/MT** - Nearly perfect
- **9.6 NM+** - Minor handling
- **9.4 NM** - Minor wear
- **9.2 NM-** - Light wear
- **9.0 VF/NM** - Some wear
- **8.0 VF** - Moderate wear
- **6.0 FN** - Above average
- **4.0 VG** - Average
- **2.0 GD** - Heavy wear
- **1.0 FR** - Very heavy wear
- **0.5 PR** - Barely holding together

### Cards (PSA Scale)
- **10 Gem Mint** - Perfect
- **9 Mint** - One minor flaw
- **8 NM-MT** - Minor flaws
- **7 NM** - Slight wear
- **6 EX-MT** - Visible wear
- **5 EX** - Moderate wear
- **4 VG-EX** - Noticeable wear
- **3 VG** - Heavy wear
- **2 Good** - Major flaws
- **1 Poor** - Severe damage

### Coins (Sheldon Scale)
- **MS70** - Perfect Mint State
- **MS65** - Gem Mint State
- **MS60** - Mint State
- **AU58** - Choice About Uncirculated
- **AU50** - About Uncirculated
- **EF45** - Choice Extremely Fine
- **VF30** - Choice Very Fine
- **F15** - Fine
- **VG8** - Very Good
- **G4** - Good
- **AG3** - About Good

## Export Formats

### CSV Export
```csv
title,issue_number,volume,publisher,cover_date,grade,market_value
Teen Titans,8,1,DC Comics,March-April 1967,4.0,$40.00
```

### JSON Export
```json
{
  "type": "comic_book",
  "title": "Teen Titans",
  "issue_number": 8,
  "volume": 1,
  "publisher": "DC Comics",
  "cover_date": "March-April 1967",
  "grade": 4.0,
  "market_value": 40.00,
  "currency": "USD"
}
```

### Platform-Specific Exports
- **CLZ Comics**: XML format with CLZ field mapping
- **ComicBase**: CBX format
- **League of Comic Geeks**: CSV with LOCG fields
- **COMC**: Standard consignment format
- **Beckett**: Beckett inventory format

## Image-Based Identification

When analyzing collectible images:
1. Identify type (comic, card, coin, etc.)
2. Extract visible text (title, year, numbers)
3. Note condition indicators
4. Estimate grade range
5. Provide market value range
6. List all cataloging fields

## Valuation Sources

### Comics
- GoCollect
- GPAnalysis
- eBay sold listings
- Heritage Auctions
- ComicLink

### Cards
- PSA Price Guide
- eBay sold listings
- PWCC
- Goldin Auctions
- 130point

### Coins
- PCGS Price Guide
- NGC Price Guide
- Heritage Auctions
- eBay sold listings
- GreySheet

## Workflow

1. **Identify** - Type and specific item
2. **Catalog** - Fill all relevant fields
3. **Grade** - Assess condition
4. **Value** - Research market prices
5. **Store** - Assign location
6. **Export** - Generate reports

## Best Practices

- Always photograph front and back
- Note all defects in condition notes
- Track purchase info for ROI
- Update values periodically
- Maintain consistent location system
- Back up catalog regularly
- Use standardized terminology

---
*Authority Level 11.0 | Collectibles Cataloger Skill*
