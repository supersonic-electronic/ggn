# GGn Matching Issue Diagnosis

## Problem Summary

Many books that exist on both MAM and GGn are being marked as "no_match" incorrectly.

## Root Cause

The matching algorithm requires author last names to appear in the GGn **group name**, but GGn eBook groups typically:
- Store author information in the `Artists` array field
- Do NOT include author names in the group name

### Example: "Encyclopedia of Video Games"

**MAM Data:**
- Title: "Encyclopedia of Video Games: The Culture, Technology, and Art of Gaming, 3 Volumes"
- Author: "Mark J P Wolf"

**GGn Data (Group ID 31980):**
- Name: "Encyclopedia of Video Games: The Culture, Technology, and Art of Gaming"
- Artists: [] (empty)

**Current Behavior:**
- Title matches ✓
- Author "wolf" not in group name ✗
- Result: **no_match** (INCORRECT)

**Expected Behavior:**
- Should match based on strong title match
- OR should check Artists field for author

## Impact

This affects many legitimate matches, inflating the "no_match" count with false negatives.

## Proposed Solutions

### Option 1: Check Artists Field (Recommended)
Modify `is_strong_match()` to check the GGn group's `Artists` array for author matches.

**Pros:**
- More accurate matching
- Uses actual author data from GGn

**Cons:**
- Requires passing full group dict instead of just name
- More complex logic

### Option 2: Make Author Matching Optional for Strong Title Matches
If title prefix matches strongly (e.g., first 7+ words), accept match even without author.

**Pros:**
- Simple fix
- Reduces false negatives

**Cons:**
- May increase false positives
- Less strict matching

### Option 3: Hybrid Approach
- Check Artists field first
- Fall back to group name
- If neither has author data, accept strong title match only

**Pros:**
- Most flexible
- Best accuracy

**Cons:**
- More complex implementation

## Recommendation

Implement **Option 3 (Hybrid)** for best results.

## Files to Modify

1. `matcher.py`:
   - Update `is_strong_match()` to accept full group dict
   - Check Artists field for author matching
   - Fall back to group name matching
   
2. `process_spreadsheet.py`:
   - No changes needed (already passes full group dict)

## Estimated False Negatives

If 136 books matched with current strict logic, potentially 50-150+ more could match with improved author handling.
