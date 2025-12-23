def test_conftest():
    # Check if conftest setup worked
    import sys
    src_path = '/home/nolood/general/review-bot/src' in sys.path
    print(f'src in sys.path: {src_path}')
    assert src_path, 'conftest.py should have added src to path'
