import unittest
import os
from unittest.mock import patch
from src.batch import run_batch
from src.cache import CacheDB

class TestBatchResume(unittest.TestCase):
    def setUp(self):
        # Create a mock input file with 5 wallets
        self.input_file = "test_batch_input.txt"
        self.out_file = "test_batch_output.csv"
        self.db_path = "data/test_cache.db"
        
        with open(self.input_file, "w") as f:
            for i in range(1, 6):
                # 40 chars hex + 0x = 42 chars
                addr = f"0x{str(i).zfill(40)}"
                f.write(addr + "\n")
                
        # Clean db if exists
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def tearDown(self):
        if os.path.exists(self.input_file):
            os.remove(self.input_file)
        if os.path.exists(self.out_file):
            os.remove(self.out_file)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @patch('src.batch.analyze_wallet')
    def test_resume_logic(self, mock_analyze):
        
        # We have 5 wallets. We want to fail the 3rd one.
        # So return "done" for 1 and 2, "error" for 3, "done" for 4, "done" for 5
        def side_effect(addr, client, cache_inst, force_refresh):
            if addr == "0x" + "3".zfill(40):
                res = {"status": "error"}
            else:
                res = {"status": "done"}
            
            # Since analyze_wallet is mocked, we need to manually upsert to simulate
            cache_inst.upsert_wallet(addr, {
                "status": res["status"], "nft_count": 0, "collection_count": 0,
                "holding_tier": "Empty", "hand_type": "Empty", "collector_score": 0,
                "confidence": 0, "recent_sales": 0, "verified_collections": 0,
                "truncated": False, "notes": "", "raw_collections_json": "", "raw_sales_json": ""
            })
            return res
            
        mock_analyze.side_effect = side_effect

        # Run 1
        with patch('src.batch.CacheDB', lambda: CacheDB(self.db_path)):
            run_batch(self.input_file, self.out_file, sleep_time=0)
        
        # Analyze should have been called 5 times
        self.assertEqual(mock_analyze.call_count, 5)
        
        # Reset mock
        mock_analyze.reset_mock()
        
        # Run 2
        # Wallets 1, 2, 4, 5 are "done", should be skipped. 3 is "error", should be retried.
        with patch('src.batch.CacheDB', lambda: CacheDB(self.db_path)):
            run_batch(self.input_file, self.out_file, sleep_time=0)
        
        # Analyze should have been called exactly 1 time (for wallet 3)
        self.assertEqual(mock_analyze.call_count, 1)
        
        called_addr = mock_analyze.call_args[0][0]
        self.assertEqual(called_addr, "0x" + "3".zfill(40))

if __name__ == '__main__':
    unittest.main()
