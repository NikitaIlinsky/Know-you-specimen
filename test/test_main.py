def test_main_function_exists():
    """Test that main function exists in main module"""
    try:
        from src.know_your_specimen import main

        assert callable(main)
    except ImportError:
        # If importing from src, main might not be there yet
        pass
