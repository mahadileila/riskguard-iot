import csv
import io
from datetime import datetime

EXPECTED_HEADERS = ["Instance", "Value", "Captured At"]
MAX_ERRORS = 20  # stops parsing after this many errors to keep the response readable
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


class CsvImportError(Exception):
    def __init__(self, errors):
        super().__init__("CSV validation failed")
        self.errors = errors


def parse_datetime(raw):
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_samples_csv(file_bytes):
    """Validates headers and cells. Returns a list of dicts, or raises CsvImportError."""
    try:
        text = file_bytes.decode("utf-8-sig")  # also strips the BOM added by Excel
    except UnicodeDecodeError:
        raise CsvImportError(["File must be UTF-8 encoded"])

    if not text.strip():
        raise CsvImportError(["The file is empty"])

    # Excel in French exports with ';', others with ','
    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = [h.strip() for h in next(reader)]
    if header != EXPECTED_HEADERS:
        raise CsvImportError([
            f"Invalid headers. Expected: {', '.join(EXPECTED_HEADERS)}. Found: {', '.join(header)}"
        ])

    rows, errors = [], []
    for line_number, row in enumerate(reader, start=2):
        if not row:  # truly blank line (e.g. trailing newline)
            continue
        if len(row) != len(EXPECTED_HEADERS) or any(not cell.strip() for cell in row):
            errors.append(f"Line {line_number}: empty or missing cell")
        else:
            instance, value, captured_at = (cell.strip() for cell in row)
            parsed_date = parse_datetime(captured_at)
            if parsed_date is None:
                errors.append(f"Line {line_number}: invalid 'Captured At' date '{captured_at}'")
            else:
                rows.append({"line": line_number, "instance": instance,
                             "value": value, "captured_at": parsed_date})
        if len(errors) >= MAX_ERRORS:
            errors.append(f"Too many errors, stopped after {MAX_ERRORS}")
            break

    if errors:
        raise CsvImportError(errors)
    if not rows:
        raise CsvImportError(["The file contains no data rows"])
    return rows