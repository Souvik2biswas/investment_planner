import os
import unittest
from datetime import date
from backend.app.parsing import scrub_pii
from backend.app.categorizer import local_heuristic_categorizer
from backend.app.sql_agent import execute_read_query, fallback_heuristics_nl_to_sql
from backend.app.database import init_db, DBTransaction, SessionLocal

class TestFinanceAgentBackend(unittest.TestCase):
    
    def setUp(self):
        # Set up database file for tests
        os.environ["DATABASE_URL"] = "sqlite:///./test_finance.db"
        init_db()
        self.db = SessionLocal()
        
    def tearDown(self):
        self.db.close()
        # Clean up database files
        if os.path.exists("./test_finance.db"):
            try:
                os.remove("./test_finance.db")
            except Exception:
                pass
                
    def test_pii_scrubbing(self):
        """
        Verify PII scrubbing successfully masks sensitive customer information.
        """
        sample_text = """
        Customer Name: Souvik Biswas
        Account Number: 123456789012
        Email: souvik@example.com
        Phone: +91 98765 43210
        PAN: ABCDE1234F
        AADHAR: 1234-5678-9012
        Paid to John Doe
        """
        
        scrubbed = scrub_pii(sample_text)
        
        # Verify masks are applied
        self.assertIn("[CUSTOMER_NAME]", scrubbed)
        self.assertIn("[ACCOUNT_NUMBER]", scrubbed)
        self.assertIn("[EMAIL]", scrubbed)
        self.assertIn("[PAN_NUMBER]", scrubbed)
        self.assertIn("[AADHAR_NUMBER]", scrubbed)
        # Sensitive details should not be in cleartext
        self.assertNotIn("Souvik Biswas", scrubbed)
        self.assertNotIn("souvik@example.com", scrubbed)
        self.assertNotIn("123456789012", scrubbed)
        
    def test_heuristic_categorization(self):
        """
        Verify the local heuristic classifier extracts and categorizes statements.
        """
        mock_statement_text = """
        05-06-2026 UBER INDIA DEBIT 350.00
        06-06-2026 ZOMATO FOOD DEBIT 620.00
        07-06-2026 LIC LIFE INSURANCE DEBIT 15000.00
        08-06-2026 AWS CLOUD SERVICE DEBIT 2400.00
        09-06-2026 MONTHLY SALARY CREDIT 85000.00
        """
        
        transactions = local_heuristic_categorizer(mock_statement_text)
        
        self.assertEqual(len(transactions), 5)
        
        # Verify dates and categories
        self.assertEqual(transactions[0].category, "TRAVEL") # Uber
        self.assertEqual(transactions[1].category, "FOOD")   # Zomato
        self.assertEqual(transactions[2].category, "POTENTIAL_DEDUCTION") # LIC Insurance
        self.assertIn("Section 80C", transactions[2].notes)
        self.assertEqual(transactions[3].category, "BUSINESS_EXPENSE") # AWS
        self.assertEqual(transactions[4].category, "SALARY") # Salary
        self.assertEqual(transactions[4].transaction_type, "CREDIT")

    def test_sql_agent_safety(self):
        """
        Verify SQL Agent execution block safeguards against destructive queries.
        """
        # Valid read-only query
        valid_query = "SELECT * FROM transactions WHERE user_id = :user_id"
        # Destructive queries
        drop_query = "DROP TABLE transactions"
        delete_query = "DELETE FROM transactions WHERE user_id = :user_id"
        update_query = "UPDATE transactions SET amount = 0"
        
        # Should raise ValueError for destructive statements
        with self.assertRaises(ValueError):
            execute_read_query(drop_query, "user1")
            
        with self.assertRaises(ValueError):
            execute_read_query(delete_query, "user1")
            
        with self.assertRaises(ValueError):
            execute_read_query(update_query, "user1")
            
        # Should run successfully for valid query (even if table is empty, returns empty list)
        results = execute_read_query(valid_query, "user1")
        self.assertEqual(results, [])

    def test_fallback_nl_to_sql(self):
        """
        Verify natural language to SQL translation heuristic templates.
        """
        query_1 = fallback_heuristics_nl_to_sql("What is my average monthly spend on utilities?")
        self.assertIn("AVG(amount)", query_1)
        self.assertIn("UTILITIES", query_1)
        self.assertIn("DEBIT", query_1)
        
        query_2 = fallback_heuristics_nl_to_sql("How much did I spend on food?")
        self.assertIn("SUM(amount)", query_2)
        self.assertIn("FOOD", query_2)

    def test_date_parsing_robustness(self):
        """
        Verify that parse_date_safely correctly handles word-based months and other formats.
        """
        from backend.app.categorizer import parse_date_safely
        
        # Test numeric formats
        self.assertEqual(parse_date_safely("05-06-2026"), date(2026, 6, 5))
        self.assertEqual(parse_date_safely("2026-06-05"), date(2026, 6, 5))
        self.assertEqual(parse_date_safely("05/06/2026"), date(2026, 6, 5))
        
        # Test alphabetic months
        self.assertEqual(parse_date_safely("05-Jun-2026"), date(2026, 6, 5))
        self.assertEqual(parse_date_safely("05/Jun/2026"), date(2026, 6, 5))
        self.assertEqual(parse_date_safely("Jun 05, 2026"), date(2026, 6, 5))
        self.assertEqual(parse_date_safely("5 Jun 2026"), date(2026, 6, 5))
        self.assertEqual(parse_date_safely("June 5, 2026"), date(2026, 6, 5))

if __name__ == '__main__':
    unittest.main()
