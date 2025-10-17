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
- **Customizable cleaning rules** via `cleaning_rules.json` configuration file
- Skips transactions with no amounts
- Validates dates before conversion
- Provides detailed conversion summary
- Error handling with row-level reporting

## Customizing Label Cleaning

The converter uses a `cleaning_rules.json` file to customize how transaction labels are cleaned. This allows you to:

- Remove unwanted text (e.g., "Réf. QRR:", "Motif du paiement:")
- Use regex patterns to clean technical details (IBAN, BIC/SWIFT codes)
- Add custom replacements for specific text (e.g., rename "VILLE DE GENEVE" → "Ville de Genève")
- Control output format (separator, max length, etc.)

### Configuration File Structure

The `cleaning_rules.json` file contains:

1. **simple_replacements**: Basic text search and replace
2. **regex_replacements**: Regular expression patterns for complex cleaning
3. **custom_replacements**: Your specific custom rules
4. **cleanup_options**: General cleanup settings (trim spaces, max length, etc.)
5. **output_format**: Separator between label parts

### Example Configuration

```json
{
  "enabled": true,
  "rules": {
    "simple_replacements": [
      {
        "description": "Remove 'Réf. QRR:' prefix",
        "search": "Réf. QRR: ",
        "replace": "",
        "full_replacement": false,
        "enabled": true
      }
    ],
    "custom_replacements": [
      {
        "description": "Truncate any label containing Swisscom to just 'Swisscom'",
        "search": "SWISSCOM",
        "replace": "Swisscom",
        "full_replacement": true,
        "enabled": true,
        "comment": "Full replacement: entire label becomes 'Swisscom' if it contains 'SWISSCOM'"
      }
    ],
    "cleanup_options": {
      "trim_whitespace": true,
      "remove_duplicate_spaces": true,
      "max_length": 100
    }
  }
}
```

### Full Replacement Mode

The `full_replacement` parameter allows you to truncate labels intelligently:

- **`full_replacement: false`** (default): Only replaces the matching text
  - Example: `"VILLE DE GENEVE | Invoice 123"` → `"Ville de Genève | Invoice 123"`

- **`full_replacement: true`**: If search text is found, replaces the **entire label**
  - Example: `"SWISSCOM SA | Ref: 12345 | Telecom bill"` → `"Swisscom"`

This is perfect for:
- Truncating long recurring supplier names
- Simplifying utility bills (SIG, Swisscom, etc.)
- Standardizing salary payments, rent, etc.

### How to Use

1. Edit `cleaning_rules.json` to add your custom rules
2. Set `"enabled": true` for rules you want to apply
3. Set `"enabled": false` to temporarily disable a rule
4. Run the converter normally - it will automatically use your rules

The configuration file includes detailed instructions and examples in French.

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
