"""Shared test fixtures for AnonTool tests."""

import pytest


@pytest.fixture
def sample_text_simple():
    """Simple text with a few person names."""
    return "John Smith met with Jane Doe at the conference yesterday."


@pytest.fixture
def sample_text_mixed():
    """Text with mixed PII: names, companies, emails, phone numbers."""
    return (
        "Dear Mr. James Wilson,\n\n"
        "Thank you for contacting Acme Corporation regarding your account. "
        "Your case has been assigned to Sarah Johnson (sarah.johnson@acme.com). "
        "Please call us at (555) 123-4567 if you have questions.\n\n"
        "Best regards,\n"
        "Michael Chen\n"
        "Acme Corporation"
    )


@pytest.fixture
def sample_text_no_pii():
    """Text with no personally identifiable information."""
    return (
        "The weather today is sunny with a high of 75 degrees. "
        "We expect clear skies throughout the afternoon."
    )


@pytest.fixture
def sample_text_business_email():
    """Realistic business email with multiple PII types."""
    return (
        "From: Robert Garcia <robert.garcia@techstart.io>\n"
        "To: Lisa Wang <lisa.wang@globalfinance.com>\n"
        "Subject: Partnership Proposal\n\n"
        "Hi Lisa,\n\n"
        "Following up on our conversation at the TechStart summit. "
        "I'd like to propose a partnership between TechStart and Global Finance Corp. "
        "David Park from our engineering team will lead the integration.\n\n"
        "Please reach out to me at (415) 555-0198 or robert.garcia@techstart.io.\n\n"
        "Best,\n"
        "Robert Garcia\n"
        "CEO, TechStart"
    )


@pytest.fixture
def sample_text_meeting_notes():
    """Meeting notes with repeated names and organizations."""
    return (
        "Meeting Notes — Q4 Planning\n"
        "Attendees: Alice Martinez, Bob Thompson, Carol Davis\n"
        "Organization: Pinnacle Solutions\n\n"
        "Alice Martinez presented the Q4 roadmap. Bob Thompson raised concerns "
        "about the timeline. Carol Davis suggested partnering with Vertex Analytics "
        "to accelerate delivery.\n\n"
        "Action items:\n"
        "- Alice Martinez to finalize the budget by Friday\n"
        "- Bob Thompson to schedule a follow-up with Vertex Analytics\n"
        "- Carol Davis to draft the partnership proposal"
    )


@pytest.fixture
def tmp_anontool_dir(tmp_path):
    """Create a temporary ~/.anontool/ equivalent for testing."""
    mappings_dir = tmp_path / "mappings"
    output_dir = tmp_path / "output"
    mappings_dir.mkdir()
    output_dir.mkdir()
    return tmp_path


@pytest.fixture
def sample_transcript_folder(tmp_path):
    """Create a temporary folder with sample transcript files."""
    import time

    folder = tmp_path / "transcripts"
    folder.mkdir()

    (folder / "transcript_001.txt").write_text(
        "John Smith discussed the project timeline with Jane Doe."
    )
    time.sleep(0.05)
    (folder / "transcript_002.txt").write_text(
        "John Smith met with Robert Garcia from Acme Corporation."
    )
    time.sleep(0.05)
    (folder / "transcript_003.md").write_text(
        "# Meeting Notes\nSarah Johnson presented the Q4 results for Acme Corporation."
    )

    return folder
