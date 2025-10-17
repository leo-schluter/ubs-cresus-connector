# UBS to Cresus Converter

A Python utility to convert UBS bank CSV statements into Cresus Comptabilité TXT format for easy import into Swiss accounting software.

## Overview

This tool converts UBS bank transaction exports (CSV format) into the tab-separated format required by Cresus Comptabilité, handling:
- Date format conversion (YYYY-MM-DD → DD.MM.YYYY Swiss format)
- Multiple description field consolidation
- Double-entry bookkeeping account assignment
- Proper debit/credit mapping

## Requirements

- Python 3.x
- No external dependencies (uses only standard library)

## Usage

```bash
python ubs_cresus_converter.py <input_ubs.csv> <output_cresus.txt>
```

### Example

```bash
python ubs_cresus_converter.py transactions.csv cresus_import.txt
```

## Input Format

The converter expects UBS CSV exports with the following columns:
- `Date de comptabilisation` - Transaction posting date (YYYY-MM-DD)
- `Débit` - Debit amounts
- `Crédit` - Credit amounts
- `N° de transaction` - Transaction reference number
- `Description1`, `Description2`, `Description3` - Transaction descriptions

## Output Format

Generates a TXT file (tab-separated) compatible with Cresus Comptabilité batch import:
- Tab-separated values
- CR+LF line endings
- Swiss date format (DD.MM.YYYY)
- Columns: Date | Débit | Crédit | N° pièce | Libellé | Montant

## Account Configuration

The converter uses the following account numbers by default:
- **1020** - Bank account (assets)
- **2000** - Temporary/contra account

To modify these accounts, edit the constants in `ubs_cresus_converter.py`:
```python
BANK_ACCOUNT = '1020'      # Bank account
CONTRA_ACCOUNT = '2000'    # Temporary/contra account
```

## Transaction Logic

The converter applies double-entry bookkeeping principles:

- **Credit transactions** (money coming IN):
  - Debit: Bank account (1020)
  - Credit: Contra account (2000)

- **Debit transactions** (money going OUT):
  - Debit: Contra account (2000)
  - Credit: Bank account (1020)

## Features

- Combines multiple description fields into a single label
- Skips transactions with no amounts
- Validates dates before conversion
- Provides detailed conversion summary
- Error handling with row-level reporting

## Output Example

After conversion, you'll see a summary like:
```
============================================================
Conversion Complete!
============================================================
Transactions converted: 45
Transactions skipped: 2

Skipped transactions:
  - Row 15: No amount
  - Row 28: Invalid date

Output file: cresus_import.txt
Ready to import into Cresus Comptabilité!
```

## Import into Cresus

1. Run the converter to create your TXT file
2. Open Cresus Comptabilité
3. Navigate to batch import function
4. Select the generated TXT file
5. Review and confirm the imported transactions
