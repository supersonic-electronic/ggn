# GGn Verification Results Summary

## Overview
Verified 583 video game eBooks from MyAnonamouse (MAM) against GazelleGames (GGn) API.

## Final Results

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| **No Match** | 444 | 76.2% | **Upload candidates for GGn** |
| **Match** | 136 | 23.3% | Already on both MAM and GGn |
| **Ambiguous** | 3 | 0.5% | Multiple possible matches (need manual review) |
| **Total** | 583 | 100% | |

## Ambiguous Cases (Require Manual Review)

These books matched multiple groups on GGn - need to verify which is the correct match:

1. **Art of Atari** - Matched GGn groups: 54347, 32003
2. **Stay Awhile and Listen** - Matched GGn groups: 104135, 83364
3. **The Art of Computer Game Design** - Matched GGn groups: 186373, 147424

## Output Files

1. **output_books_ggn.csv** - Complete verification results with GGn details
2. **upload_candidates_ggn.csv** - 444 books NOT on GGn (upload candidates only)
3. **verification_run.log** - Full processing log
4. **ggn_checker.log** - Detailed API interaction log

## Upload Candidate Examples

Books from MAM that don't exist on GGn (partial list):
- 1-2 Punch: Stinkfly and Cannonbolt
- A Game of Thrones (George R R Martin)
- A Late-Start Tamer's Laid-Back Life series (13+ volumes)
- Many Minecraft-related books
- Various video game novelizations
- Game design books not yet on GGn

## Matching Examples

Books successfully matched on both trackers:
- 20 Essential Games to Study (Joshua Bycer)
- 2D/3D Game Development with Unity (Franz Lanzinger)
- 50 Years of Text Games (Aaron A Reed)
- A Theory of Fun for Game Design (Raph Koster)
- AI for Games (Ian Millington)

## Technical Details

- **Matching Algorithm**: 
  - Title: First 5 normalized words as prefix
  - Author: Last name only
  - Case-insensitive, alphanumeric normalization
  - Category filter: eBooks only (GGn category ID 3)

- **Rate Limiting**: 5 requests per 10 seconds (GGn compliant)
- **Processing Time**: ~20 minutes for 583 books
- **API Errors**: 8 temporary connection errors (handled gracefully)

## Next Steps

1. **Review ambiguous cases** manually on GGn website
2. **Filter upload candidates** based on:
   - Quality/completeness
   - Relevance to gaming
   - Availability of files from MAM
3. **Upload to GGn** following their rules and guidelines

## Files Location

All files are in: `/home/jin23/Code/eBookGGn/ggn_checker/`
