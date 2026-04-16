import pytest

from plugins.sync.report_writer import ReportWriter


def test_validate_arg():
    writer = ReportWriter()
    # Should pass
    assert writer._validate_arg("valid-id") == "valid-id"
    
    # Should raise ValueError for starting with '-'
    with pytest.raises(ValueError, match="potential flag injection"):
        writer._validate_arg("--dangerous-flag")
    
    # Should also raise for single dash
    with pytest.raises(ValueError, match="potential flag injection"):
        writer._validate_arg("-f")

if __name__ == "__main__":
    test_validate_arg()
    print("Validation test passed!")
