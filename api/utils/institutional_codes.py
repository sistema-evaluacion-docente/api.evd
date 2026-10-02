"""
Matching of institutional codes.

The evaluation PDFs print codes with leading zeros ("00045"), but a code typed
into a spreadsheet loses them as soon as the cell is numeric (45). Both spell
the same person, so codes are compared without leading zeros; the form the PDF
prints stays the stored one, since the PDF report of a teacher is cut by it.
"""


def code_key(code: str) -> str:
    """The comparable form of a code: trimmed, without leading zeros."""

    return code.strip().lstrip("0")
