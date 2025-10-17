#!/usr/bin/env python3
"""
UBS to Cresus Batch Import Converter
Converts UBS CSV bank statements to Cresus Comptabilité TXT format
"""

import csv
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from io import StringIO


def clean_amount(amount_str):
    """Clean and convert amount string to float, handling empty values"""
    if not amount_str or amount_str.strip() == '':
        return 0.0
    # Remove any whitespace and convert to float
    return float(amount_str.strip())


def format_date(date_str):
    """Convert date from YYYY-MM-DD to DD.MM.YYYY (Swiss format)"""
    if not date_str or date_str.strip() == '':
        return ''
    try:
        date_obj = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        return date_obj.strftime('%d.%m.%Y')
    except ValueError:
        return date_str


def load_cleaning_rules(rules_file='cleaning_rules.json'):
    """Load cleaning rules from JSON configuration file"""
    rules_path = Path(__file__).parent / rules_file

    # Default rules if file doesn't exist
    default_rules = {
        'enabled': True,
        'rules': {
            'simple_replacements': [],
            'regex_replacements': [],
            'custom_replacements': [],
            'cleanup_options': {
                'trim_whitespace': True,
                'remove_duplicate_spaces': True,
                'remove_trailing_semicolons': True,
                'remove_trailing_colons': True,
                'remove_empty_parentheses': True,
                'max_length': 0
            }
        },
        'output_format': {
            'separator': ' | '
        }
    }

    if not rules_path.exists():
        return default_rules

    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {rules_file}: {e}")
        print("Using default cleaning rules")
        return default_rules


def apply_cleaning_rules(text, rules_config):
    """Apply cleaning rules from configuration to text"""
    if not rules_config.get('enabled', True):
        return text

    rules = rules_config.get('rules', {})

    # Apply simple text replacements
    for rule in rules.get('simple_replacements', []):
        if rule.get('enabled', True):
            if rule.get('full_replacement', False):
                # If text contains search string, replace ENTIRE text with replace value
                if rule['search'] in text:
                    text = rule['replace']
            else:
                # Normal replacement: only replace matching substring
                text = text.replace(rule['search'], rule['replace'])

    # Apply regex replacements
    for rule in rules.get('regex_replacements', []):
        if rule.get('enabled', True):
            if rule.get('full_replacement', False):
                # If pattern matches, replace ENTIRE text with replace value
                if re.search(rule['pattern'], text):
                    text = rule['replace']
            else:
                # Normal replacement: only replace matching pattern
                text = re.sub(rule['pattern'], rule['replace'], text)

    # Apply custom replacements
    for rule in rules.get('custom_replacements', []):
        if rule.get('enabled', True):
            if rule.get('full_replacement', False):
                # If text contains search string, replace ENTIRE text with replace value
                if rule['search'] in text:
                    text = rule['replace']
            else:
                # Normal replacement: only replace matching substring
                text = text.replace(rule['search'], rule['replace'])

    # Apply cleanup options
    cleanup = rules.get('cleanup_options', {})

    if cleanup.get('remove_duplicate_spaces', True):
        text = re.sub(r'\s+', ' ', text)

    if cleanup.get('remove_trailing_semicolons', True):
        text = text.rstrip(';')

    if cleanup.get('remove_trailing_colons', True):
        text = text.rstrip(':')

    if cleanup.get('remove_empty_parentheses', True):
        text = re.sub(r'\(\s*\)', '', text)

    if cleanup.get('trim_whitespace', True):
        text = text.strip()

    max_length = cleanup.get('max_length', 0)
    if max_length > 0 and len(text) > max_length:
        text = text[:max_length].rstrip()

    return text


def clean_description(desc1, desc2, desc3, rules_config=None):
    """Combine and clean description fields using configuration rules"""

    # Combine all description fields
    full_desc = ' '.join([d.strip() for d in [desc1, desc2, desc3] if d and d.strip()])

    if not full_desc:
        return 'Transaction bancaire'

    # Extract key information
    beneficiary = desc1.strip() if desc1 else ''

    # Extract QRR reference if present
    qrr_match = re.search(r'Reference no\. QRR:\s*([0-9 ]+)', full_desc)
    qrr = qrr_match.group(1).strip() if qrr_match else None

    # Extract payment reason/motive
    motif_match = re.search(r'Motif du paiement:\s*([^;]+)', full_desc)
    motif = motif_match.group(1).strip() if motif_match else None

    # Build clean description
    parts = []

    if beneficiary:
        # Clean beneficiary name (remove redundant address info in some cases)
        beneficiary = re.sub(r';[^;]*\d{4}[^;]*;[^;]*$', '', beneficiary)  # Remove address at end
        parts.append(beneficiary)

    if qrr:
        parts.append(f"Réf. QRR: {qrr}")

    if motif:
        # Clean motif - remove technical details
        motif = re.sub(r'Account no\. IBAN:\s*[^;]+;?', '', motif)
        # Remove BIC/SWIFT codes (handles spaces like "BI C/SWIFT")
        motif = re.sub(r'BI\s*C\s*/\s*SWIFT\s+\w+', '', motif)
        motif = re.sub(r'BIC\s*/\s*SWIFT\s+\w+', '', motif)
        motif = re.sub(r':\s*BI\s*C\s*/\s*SWIFT\s+\w+', '', motif)
        motif = re.sub(r'Coûts:\s*[^;]+;?', '', motif)
        motif = re.sub(r'\s*:\s*$', '', motif)  # Remove trailing colons
        motif = re.sub(r'\s*:\s*;', ';', motif)  # Clean up colon before semicolon
        motif = re.sub(r'\s+', ' ', motif).strip()

        # Remove trailing/leading semicolons and extra spaces
        motif = motif.strip('; :')

        if motif and motif != beneficiary:
            parts.append(motif)

    # If we didn't extract structured info, use a simpler approach
    if len(parts) <= 1:
        # Just clean the first two description fields
        simple_parts = []
        for desc in [desc1, desc2]:
            if desc and desc.strip():
                cleaned = desc.strip()
                # Remove technical noise
                cleaned = re.sub(r'No de transaction:[^;]+;?', '', cleaned)
                cleaned = re.sub(r'Coûts:[^;]+;?', '', cleaned)
                cleaned = re.sub(r'\(\*[a-z]\)[^;]*', '', cleaned)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    simple_parts.append(cleaned)

        result = ' | '.join(simple_parts[:2]) if simple_parts else 'Transaction bancaire'
    else:
        # Get separator from config
        separator = ' | '
        if rules_config:
            separator = rules_config.get('output_format', {}).get('separator', ' | ')
        result = separator.join(parts)

    # Apply custom cleaning rules from config
    if rules_config:
        result = apply_cleaning_rules(result, rules_config)

    return result if result else 'Transaction bancaire'


def convert_ubs_to_cresus(input_file, output_file):
    """
    Convert UBS CSV to Cresus TXT format

    Args:
        input_file: Path to UBS CSV export file
        output_file: Path for Cresus TXT output file
    """

    # Load cleaning rules
    rules_config = load_cleaning_rules()
    if rules_config.get('enabled'):
        print("Using custom cleaning rules from cleaning_rules.json")

    # Account configuration
    BANK_ACCOUNT = '1020'      # Bank account
    CONTRA_ACCOUNT = '2000'    # Temporary/contra account

    transactions = []
    skipped = []

    print(f"Reading UBS file: {input_file}")

    # Read UBS CSV
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        # Skip header rows until we find the transaction header
        lines = f.readlines()
        header_line_idx = None
        for idx, line in enumerate(lines):
            if 'Date de transaction' in line or 'Date de comptabilisation' in line:
                header_line_idx = idx
                break

        if header_line_idx is None:
            raise ValueError("Could not find transaction header in CSV file")

        # Read from the header line onwards
        csv_content = ''.join(lines[header_line_idx:])
        reader = csv.DictReader(StringIO(csv_content), delimiter=';')

        for row_num, row in enumerate(reader, start=header_line_idx + 2):  # Adjust row number
            try:
                # Extract fields
                posting_date = row.get('Date de comptabilisation', '').strip()
                debit_str = row.get('Débit', '').strip()
                credit_str = row.get('Crédit', '').strip()
                transaction_num = row.get('No de transaction', '') or row.get('N° de transaction', '')
                transaction_num = transaction_num.strip()
                desc1 = row.get('Description1', '').strip()
                desc2 = row.get('Description2', '').strip()
                desc3 = row.get('Description3', '').strip()

                # Handle amounts (may have minus sign in debit column)
                debit = 0.0
                credit = 0.0

                if debit_str:
                    amount = clean_amount(debit_str)
                    if amount < 0:
                        debit = abs(amount)
                    else:
                        debit = amount

                if credit_str:
                    credit = clean_amount(credit_str)

                # Skip if no amount
                if debit == 0.0 and credit == 0.0:
                    skipped.append(f"Row {row_num}: No amount")
                    continue
                
                # Format date
                formatted_date = format_date(posting_date)
                if not formatted_date:
                    skipped.append(f"Row {row_num}: Invalid date")
                    continue
                
                # Combine descriptions with cleaning rules
                description = clean_description(desc1, desc2, desc3, rules_config)
                
                # Determine debit/credit accounts and amount based on transaction type
                if credit > 0:
                    # Money coming IN: Bank account receives money
                    debit_account = BANK_ACCOUNT
                    credit_account = CONTRA_ACCOUNT
                    amount = credit
                else:
                    # Money going OUT: Bank account pays out money
                    debit_account = CONTRA_ACCOUNT
                    credit_account = BANK_ACCOUNT
                    amount = abs(debit)
                
                # Create Cresus transaction
                # Format: Date | Débit | Crédit | N° pièce | Libellé | Montant
                transactions.append({
                    'date': formatted_date,
                    'debit_account': debit_account,
                    'credit_account': credit_account,
                    'doc_number': transaction_num,
                    'description': description,
                    'amount': f"{amount:.2f}"
                })
                
            except Exception as e:
                skipped.append(f"Row {row_num}: Error - {str(e)}")
    
    # Write Cresus TXT
    print(f"\nWriting Cresus file: {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        # Write each transaction
        for trans in transactions:
            # Tab-separated values with CR+LF line endings
            line = '\t'.join([
                trans['date'],
                trans['debit_account'],
                trans['credit_account'],
                trans['doc_number'],
                trans['description'],
                trans['amount']
            ])
            f.write(line + '\r\n')
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Conversion Complete!")
    print(f"{'='*60}")
    print(f"Transactions converted: {len(transactions)}")
    if skipped:
        print(f"Transactions skipped: {len(skipped)}")
        print("\nSkipped transactions:")
        for skip in skipped[:10]:  # Show first 10
            print(f"  - {skip}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")
    print(f"\nOutput file: {output_file}")
    print(f"Ready to import into Cresus Comptabilité!")


def main():
    """Main entry point"""
    if len(sys.argv) != 3:
        print("Usage: python ubs_cresus_converter.py <input_ubs.csv> <output_cresus.txt>")
        print("\nExample:")
        print("  python ubs_cresus_converter.py UBS_export.csv cresus_import.txt")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    # Validate input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Convert
    try:
        convert_ubs_to_cresus(input_file, output_file)
    except Exception as e:
        print(f"\nError during conversion: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
