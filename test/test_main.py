def test_main_function_exists():
    """Test that main function exists in main module"""
    from know_your_specimen.main import main

    assert callable(main)
