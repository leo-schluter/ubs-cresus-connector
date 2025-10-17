# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python utility that converts UBS bank CSV statements to Cresus Comptabilité TXT format for Swiss accounting import. The entire converter is contained in a single Python script: `ubs_cresus_converter.py`.

## Running the Converter

```bash
python ubs_cresus_converter.py <input_ubs.csv> <output_cresus.txt>
```

Example:
```bash
python ubs_cresus_converter.py transactions.csv cresus_import.txt
```

## Architecture

### Input Format (UBS CSV)
- Semicolon-delimited CSV with UTF-8 encoding
- Expected columns:
  - `Date de comptabilisation` (YYYY-MM-DD format)
  - `Débit` (debit amounts)
  - `Crédit` (credit amounts)
  - `N° de transaction` (transaction number)
  - `Description1`, `Description2`, `Description3` (transaction descriptions)

### Output Format (Cresus TXT)
- Tab-separated values with CR+LF line endings (saved as .txt file)
- Format: Date | Débit | Crédit | N° pièce | Libellé | Montant
- Date converted to Swiss format (DD.MM.YYYY)
- Multiple description fields combined with ` | ` separator

### Account Configuration
The converter uses hardcoded Swiss accounting chart accounts (ubs_cresus_converter.py:51-52):
- `BANK_ACCOUNT = '1020'` - Bank account (asset)
- `CONTRA_ACCOUNT = '2000'` - Temporary/contra account

When modifying account numbers, update these constants in the `convert_ubs_to_cresus()` function.

### Transaction Logic
Credit transactions (money IN): Bank account is debited, contra account is credited
Debit transactions (money OUT): Contra account is debited, bank account is credited

This follows double-entry bookkeeping where incoming money increases bank assets (debit) and outgoing money decreases bank assets (credit).
