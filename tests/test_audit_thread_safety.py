import threading
import time
import sqlite3
import os
from gateway.audit import AuditLogger, ScanRecord
from config import Config

# Mock Config for testing purposes, assuming database setup is minimal for thread test
class MockConfig(Config):
    DATABASE_PATH = "test_scan.db"

def worker_task(logger: AuditLogger, scan_id: str, thread_id: int):
    """Task executed by each thread to log a record."""
    try:
        # Simulate work delay to increase concurrency chance
        time.sleep(0.01) 
        logger.log(
            scan_id=f"{scan_id}_{thread_id}",
            input_type="text",
            decision="ALLOW",
            risk_score=10,
            finding_codes=[],
            duration_ms=5.0,
            llm_invoked=False,
            file_extension=None,
            error=None
        )
    except sqlite3.ProgrammingError as e:
        print(f"Thread {thread_id} encountered SQLite Programming Error: {e}")
    except Exception as e:
        print(f"Thread {thread_id} encountered general error: {e}")

def test_thread_safe_logging():
    """Tests that multiple threads can safely write to the SQLite audit log."""
    print("--- Starting Thread Safety Test ---")
    
    # Setup
    mock_config = MockConfig()
    # Ensure test DB is clean before starting
    logger = AuditLogger(mock_config)
    logger.clear_all()

    NUM_THREADS = 10
    threads = []
    
    # Create and start threads
    for i in range(NUM_THREADS):
        thread = threading.Thread(target=worker_task, args=(logger, "THREAD_TEST_SCAN", i))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("--- All threads finished. Verifying database integrity. ---")
    
    # Verification
    scans = logger.get_recent_scans(NUM_THREADS)
    
    # Cleanup connections explicitly in case __del__ isn't called immediately
    # This is crucial for test stability
    try:
        # Since _get_connection returns a fresh connection, we must explicitly close the connection
        # retrieved by the last thread for this test to be clean, but we rely on the DB commit inside log().
        # For test cleanup, we just ensure the logger object is finished.
        pass 
    except Exception:
        pass # Ignore if connection setup failed in test
    
    # Assertions
    assert len(scans) == NUM_THREADS, f"Expected {NUM_THREADS} scans, but found {len(scans)}"
    print(f"SUCCESS: Found {len(scans)} records, matching thread count. No SQLite errors reported.")

if __name__ == '__main__':
    test_thread_safe_logging()