"""
Tests for the storage helpers of an evaluation's PDFs.
"""

from api.utils.evaluation_pdfs import (
    join_pdf_urls,
    pdf_url_modality,
    select_pdf_url,
    split_pdf_urls,
    stored_pdf_filename,
)

PRESENCIAL_PDF = "uploads/evaluations/2024-2/52/presencial_abc123.pdf"
DISTANCIA_PDF = "uploads/evaluations/2024-2/52/distancia_def456.pdf"
LEGACY_PDF = "uploads/evaluations/2024-2/52/abc123.pdf"


class TestSplitAndJoin:
    """Test suite for reading and writing the pdf_url column."""

    def test_splits_the_paths_of_an_evaluation(self):
        """Test the two documents of an evaluation are read back as a list."""

        assert split_pdf_urls(f"{PRESENCIAL_PDF},{DISTANCIA_PDF}") == [
            PRESENCIAL_PDF,
            DISTANCIA_PDF,
        ]

    def test_reads_an_evaluation_with_a_single_pdf(self):
        """Test a column written before the split still reads as one path."""

        assert split_pdf_urls(LEGACY_PDF) == [LEGACY_PDF]

    def test_reads_an_evaluation_without_pdfs(self):
        """Test an empty column yields no paths."""

        assert split_pdf_urls(None) == []
        assert split_pdf_urls("") == []

    def test_ignores_blank_entries(self):
        """Test stray separators do not turn into empty paths."""

        assert split_pdf_urls(f"{PRESENCIAL_PDF}, ,") == [PRESENCIAL_PDF]

    def test_join_is_the_inverse_of_split(self):
        """Test joining the paths rebuilds the stored column."""

        paths = [PRESENCIAL_PDF, DISTANCIA_PDF]

        assert split_pdf_urls(join_pdf_urls(paths)) == paths


class TestStoredPdfFilename:
    """Test suite for the name an uploaded PDF is stored under."""

    def test_keeps_the_modality_in_the_name(self):
        """Test the modality can be read back from the stored filename."""

        for modality in ("PRESENCIAL", "DISTANCIA"):
            name = stored_pdf_filename(modality)

            assert name.startswith(modality.lower())
            assert pdf_url_modality(name) == modality

    def test_names_are_unique_per_upload(self):
        """Test two uploads of the same modality never collide."""

        assert stored_pdf_filename("PRESENCIAL") != stored_pdf_filename("PRESENCIAL")

    def test_falls_back_when_the_modality_is_unknown(self):
        """Test a file with no modality is still stored under a valid name."""

        name = stored_pdf_filename(None)

        assert name.endswith(".pdf")
        assert pdf_url_modality(name) is None


class TestSelectPdfUrl:
    """Test suite for picking which of an evaluation's PDFs to serve."""

    def test_serves_the_first_pdf_by_default(self):
        """Test a request without modality gets the first document."""

        assert select_pdf_url(f"{PRESENCIAL_PDF},{DISTANCIA_PDF}") == PRESENCIAL_PDF

    def test_serves_the_document_of_the_requested_modality(self):
        """Test each modality resolves to its own document."""

        stored = f"{PRESENCIAL_PDF},{DISTANCIA_PDF}"

        assert select_pdf_url(stored, "DISTANCIA") == DISTANCIA_PDF
        assert select_pdf_url(stored, "presencial") == PRESENCIAL_PDF

    def test_returns_none_when_that_modality_was_not_uploaded(self):
        """Test asking for a document the evaluation does not have finds nothing."""

        assert select_pdf_url(PRESENCIAL_PDF, "DISTANCIA") is None

    def test_serves_a_legacy_pdf_when_no_modality_is_asked_for(self):
        """Test evaluations uploaded before the split keep working."""

        assert select_pdf_url(LEGACY_PDF) == LEGACY_PDF
        assert select_pdf_url(LEGACY_PDF, "PRESENCIAL") is None

    def test_returns_none_when_the_evaluation_has_no_pdf(self):
        """Test an evaluation with an empty column has nothing to serve."""

        assert select_pdf_url(None) is None
