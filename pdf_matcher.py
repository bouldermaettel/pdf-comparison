from __future__ import annotations

import argparse
import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz

try:
    import pdfplumber
except ImportError:  # pragma: no cover - handled at runtime
    pdfplumber = None


DEFAULT_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "intersection_tolerance": 3,
}

FALLBACK_TABLE_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "text_x_tolerance": 2,
    "text_y_tolerance": 2,
}


@dataclass(frozen=True)
class SourceValue:
    value: str
    source_page: int | None = None


@dataclass(frozen=True)
class MatchResult:
    search_value: str
    found: bool
    pages: list[int]
    page_count: int
    source_page: int | None = None


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def normalize_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(value).casefold())


def read_pdf_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def extract_page_texts(pdf_bytes: bytes) -> list[str]:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [page.get_text("text") for page in document]
    finally:
        document.close()


def clean_candidate_value(value: str) -> str:
    cleaned = normalize_text(value)
    cleaned = cleaned.strip("|;:,.-")
    return cleaned


def looks_like_value(value: str, value_pattern: str | None) -> bool:
    if not value:
        return False
    if value_pattern:
        return re.fullmatch(value_pattern, value) is not None
    if len(value) < 4:
        return False
    if not any(char.isdigit() for char in value):
        return False
    # Default generic token shape for IDs/SKUs. Use --value-pattern for custom formats.
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None


def _table_settings_variants() -> Iterable[dict[str, object]]:
    yield DEFAULT_TABLE_SETTINGS
    yield FALLBACK_TABLE_SETTINGS


def _normalize_table_rows(table: list[list[str | None]]) -> list[list[str]]:
    return [[normalize_text(cell) for cell in row] for row in table if row and any(normalize_text(cell) for cell in row)]


def _find_column_index(header: list[str], column_identifier: str) -> int | None:
    wanted = normalize_key(column_identifier)
    if not wanted:
        return None

    normalized_header = [normalize_key(cell) for cell in header]

    for index, cell in enumerate(normalized_header):
        if cell == wanted:
            return index
    for index, cell in enumerate(normalized_header):
        if wanted in cell or cell in wanted:
            return index
    return None


def _looks_like_continuation(rows: list[list[str]], column_index: int, value_pattern: str | None) -> bool:
    values = [clean_candidate_value(row[column_index]) for row in rows if column_index < len(row)]
    if not values:
        return False
    valid_count = sum(1 for value in values if looks_like_value(value, value_pattern))
    threshold = max(2, len(values) // 2)
    return valid_count >= threshold


def extract_source_values(
    pdf_bytes: bytes,
    column_identifier: str,
    value_pattern: str | None = None,
    unique_only: bool = True,
) -> list[SourceValue]:
    if pdfplumber is None:
        raise RuntimeError(
            "pdfplumber is required for column-based extraction from the source PDF. "
            "Install dependencies from requirements.txt first."
        )

    candidates: list[SourceValue] = []
    seen: set[str] = set()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for settings in _table_settings_variants():
            previous_column_index: int | None = None
            for page_number, page in enumerate(pdf.pages, start=1):
                for table in page.extract_tables(table_settings=settings) or []:
                    rows = _normalize_table_rows(table)
                    if not rows:
                        continue
                    header = rows[0]
                    column_index = _find_column_index(header, column_identifier)
                    if column_index is not None:
                        previous_column_index = column_index
                        data_rows = rows[1:]
                    elif previous_column_index is not None and _looks_like_continuation(rows, previous_column_index, value_pattern):
                        column_index = previous_column_index
                        data_rows = rows
                    else:
                        continue

                    for row in data_rows:
                        if column_index >= len(row):
                            continue
                        raw_value = clean_candidate_value(row[column_index])
                        if not looks_like_value(raw_value, value_pattern):
                            continue
                        if unique_only and raw_value in seen:
                            continue
                        seen.add(raw_value)
                        candidates.append(SourceValue(value=raw_value, source_page=page_number))
    if candidates:
        return candidates

    raise ValueError(
        f"Could not find a table column matching '{column_identifier}'. "
        "Try a different column identifier or supply a stricter value regex."
    )


def build_value_regex(value: str, exact_match: bool) -> re.Pattern[str]:
    escaped = re.escape(value)
    if not exact_match:
        return re.compile(escaped, flags=re.IGNORECASE)

    starts_alnum = value[:1].isalnum()
    ends_alnum = value[-1:].isalnum()
    prefix = r"(?<![A-Za-z0-9])" if starts_alnum else ""
    suffix = r"(?![A-Za-z0-9])" if ends_alnum else ""
    return re.compile(f"{prefix}{escaped}{suffix}", flags=re.IGNORECASE)


def search_values_in_pdf(
    values: Iterable[SourceValue],
    target_pdf_bytes: bytes,
    exact_match: bool = True,
) -> list[MatchResult]:
    page_texts = extract_page_texts(target_pdf_bytes)
    results: list[MatchResult] = []

    for source_value in values:
        pattern = build_value_regex(source_value.value, exact_match=exact_match)
        pages = [page_number for page_number, page_text in enumerate(page_texts, start=1) if pattern.search(page_text)]
        results.append(
            MatchResult(
                search_value=source_value.value,
                found=bool(pages),
                pages=pages,
                page_count=len(pages),
                source_page=source_value.source_page,
            )
        )

    return results


def results_to_rows(results: Iterable[MatchResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        rows.append(
            {
                "search_value": result.search_value,
                "found": "yes" if result.found else "no",
                "pages": ",".join(str(page) for page in result.pages),
                "page_count": result.page_count,
                "source_page": result.source_page or "",
            }
        )
    return rows


def results_to_csv_text(results: Iterable[MatchResult]) -> str:
    rows = results_to_rows(results)
    fieldnames = ["search_value", "found", "pages", "page_count", "source_page"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write_results_csv(results: Iterable[MatchResult], output_path: str | Path) -> None:
    with Path(output_path).open("w", newline="", encoding="utf-8") as file_handle:
        file_handle.write(results_to_csv_text(results))


def run_match(
    source_pdf: str | Path,
    target_pdf: str | Path,
    column_identifier: str,
    output_csv: str | Path,
    value_pattern: str | None = None,
    exact_match: bool = True,
) -> list[MatchResult]:
    source_values = extract_source_values(
        pdf_bytes=read_pdf_bytes(source_pdf),
        column_identifier=column_identifier,
        value_pattern=value_pattern,
    )
    results = search_values_in_pdf(
        values=source_values,
        target_pdf_bytes=read_pdf_bytes(target_pdf),
        exact_match=exact_match,
    )
    write_results_csv(results, output_csv)
    return results


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract values from a named source column in one PDF and search them in another PDF."
    )
    parser.add_argument("source_pdf", help="PDF containing the table or list with the values to extract.")
    parser.add_argument("target_pdf", help="PDF in which the extracted values should be searched.")
    parser.add_argument("--column", required=True, help="Header or column identifier to extract from the source PDF.")
    parser.add_argument("--output", required=True, help="Path to the CSV output file.")
    parser.add_argument(
        "--value-pattern",
        default=None,
        help="Optional regex that extracted values must fully match, for example '[A-Z0-9]+'",
    )
    parser.add_argument(
        "--contains",
        action="store_true",
        help="Use substring matching in the target PDF instead of boundary-aware exact matching.",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    results = run_match(
        source_pdf=args.source_pdf,
        target_pdf=args.target_pdf,
        column_identifier=args.column,
        output_csv=args.output,
        value_pattern=args.value_pattern,
        exact_match=not args.contains,
    )
    total_found = sum(1 for result in results if result.found)
    print(f"Processed {len(results)} values; found {total_found} in the target PDF.")
    print(f"CSV written to {args.output}")


if __name__ == "__main__":
    main()