import unittest
from unittest.mock import MagicMock
from src.scoring import analyze_wallet, calculate_score, determine_hand_type, determine_holding_tier

class TestScoring(unittest.TestCase):
    def test_holding_tier(self):
        self.assertEqual(determine_holding_tier(0), "Empty")
        self.assertEqual(determine_holding_tier(5), "Micro")
        self.assertEqual(determine_holding_tier(20), "Small")
        self.assertEqual(determine_holding_tier(75), "Medium")
        self.assertEqual(determine_holding_tier(250), "Large")
        self.assertEqual(determine_holding_tier(600), "Whale")

    def test_hand_type(self):
        self.assertEqual(determine_hand_type(0, 0), "Empty")
        self.assertEqual(determine_hand_type(5, 25), "Flipper")
        self.assertEqual(determine_hand_type(15, 20), "Paper")
        self.assertEqual(determine_hand_type(25, 2), "Diamond")
        self.assertEqual(determine_hand_type(12, 5), "Platinum")
        self.assertEqual(determine_hand_type(8, 2), "Gold")

    def test_calculate_score(self):
        # max score: 200 nfts (35) + 20 collections (25) + 10 verified (20) + Diamond (20) = 100
        score = calculate_score(200, 20, 10, "Diamond")
        self.assertEqual(score, 100)
        
        # paper hands, 15 nfts, 5 collections, 0 verified
        # nft: 15/200*35 = 2. collections: 5/20*25 = 6. verified: 0. paper: 4. Total: 12
        score2 = calculate_score(15, 5, 0, "Paper")
        self.assertEqual(score2, 12)

    def test_analyze_wallet_parsing(self):
        client = MagicMock()
        cache = MagicMock()
        cache.get_wallet.return_value = None
        
        # Mock API responses
        col_mock = MagicMock()
        col_mock.status_code = 200
        col_mock.json.return_value = {
            "collections": [
                {"safelist_request_status": "verified", "owned_asset_count": 5},
                {"safelist_request_status": "not_requested", "owned_asset_count": 2},
            ]
        }
        client.get_collections.return_value = col_mock
        
        sales_mock = MagicMock()
        sales_mock.status_code = 200
        sales_mock.json.return_value = {
            "asset_events": [{}, {}, {}] # 3 sales
        }
        client.get_sales.return_value = sales_mock
        
        res = analyze_wallet("0x123", client, cache)
        
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["nft_count"], 7)
        self.assertEqual(res["collection_count"], 2)
        self.assertEqual(res["verified_collections"], 1)
        self.assertEqual(res["recent_sales"], 3)
        self.assertEqual(res["confidence"], 90)
        self.assertEqual(res["truncated"], False)
        
        # Check cache upsert was called
        cache.upsert_wallet.assert_called_once()
        args = cache.upsert_wallet.call_args[0]
        self.assertEqual(args[0], "0x123")
        self.assertEqual(args[1]["nft_count"], 7)

if __name__ == '__main__':
    unittest.main()
