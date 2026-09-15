import unittest
from unittest.mock import patch, MagicMock
from src.client import OpenSeaClient

class TestOpenSeaClient(unittest.TestCase):
    @patch('src.client.time.sleep')
    @patch('requests.Session.request')
    def test_429_retry_and_json_parse(self, mock_request, mock_sleep):
        # Create a mock response for 429
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "1"}
        
        # Create a mock response for success
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"collections": [{"name": "Mock Collection"}]}
        
        # side_effect returns the first value, then the second value
        mock_request.side_effect = [mock_429, mock_success]
        
        # min_delay_sec=0 to avoid actual sleep time during testing rate limiting limits
        client = OpenSeaClient(api_key="mock_key", min_delay_sec=0)
        
        response = client.get_collections("0x123")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["collections"][0]["name"], "Mock Collection")
        
        # verify it retried (one 429, one 200 = 2 calls)
        self.assertEqual(mock_request.call_count, 2)
        
        # verify it slept for Retry-After which was mock set to "1"
        mock_sleep.assert_called_with(1)

if __name__ == '__main__':
    unittest.main()
