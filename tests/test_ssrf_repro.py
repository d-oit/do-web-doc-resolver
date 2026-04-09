
import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.utils import validate_url, fetch_llms_txt, is_safe_url, fetch_url_content

class TestSSRFRepro(unittest.TestCase):
    @patch("scripts.utils.get_session")
    def test_validate_url_redirect_to_private_ip(self, mock_get_session):
        # Mock a session that redirects to a private IP
        mock_session = Mock()

        # history[0].url is the original URL, response.url is the final one
        mock_response_1 = Mock()
        mock_response_1.is_redirect = True
        mock_response_1.status_code = 302
        mock_response_1.headers = {"Location": "http://127.0.0.1/admin"}
        mock_response_1.url = "http://public-site.com/redirect"

        mock_session.request.return_value = mock_response_1
        mock_get_session.return_value = mock_session

        # This SHOULD fail because it tries to redirect to 127.0.0.1
        result = validate_url("http://public-site.com/redirect")

        self.assertFalse(result.is_valid, "Should have blocked redirect to private IP")

    @patch("scripts.utils.get_session")
    def test_fetch_llms_txt_to_private_ip(self, mock_get_session):
        # This SHOULD be blocked by is_safe_url check before even calling session
        result = fetch_llms_txt("http://127.0.0.1/llms.txt")
        self.assertIsNone(result, "Should have blocked fetching from private IP")

    @patch("scripts.utils.get_session")
    def test_fetch_llms_txt_redirect_to_private_ip(self, mock_get_session):
        mock_session = Mock()

        mock_response_1 = Mock()
        mock_response_1.is_redirect = True
        mock_response_1.status_code = 302
        mock_response_1.headers = {"Location": "http://127.0.0.1/llms.txt"}
        mock_response_1.url = "http://public-site.com/llms.txt"

        mock_session.request.return_value = mock_response_1
        mock_get_session.return_value = mock_session

        result = fetch_llms_txt("http://public-site.com/llms.txt")
        self.assertIsNone(result, "Should have blocked redirect to private IP in fetch_llms_txt")

    @patch("scripts.utils.validate_url")
    @patch("scripts.utils.get_session")
    def test_fetch_url_content_redirect_to_private_ip(self, mock_get_session, mock_validate):
        # Mock initial validation to pass (it only checks initial URL)
        mock_validation = Mock()
        mock_validation.is_valid = True
        mock_validate.return_value = mock_validation

        mock_session = Mock()

        mock_response_1 = Mock()
        mock_response_1.is_redirect = True
        mock_response_1.status_code = 302
        mock_response_1.headers = {"Location": "http://127.0.0.1/admin"}
        mock_response_1.url = "http://public-site.com/redirect"

        mock_session.request.return_value = mock_response_1
        mock_get_session.return_value = mock_session

        result = fetch_url_content("http://public-site.com/redirect")
        self.assertIsNone(result, "Should have blocked redirect to private IP in fetch_url_content")

if __name__ == "__main__":
    unittest.main()
