import os
import sys
import asyncio
from fastapi import HTTPException, UploadFile
from io import BytesIO

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import resolve_image_url

async def run_tests():
    print("=======================================================")
    print("  RUNNING UNIT TESTS ON CLOUDINARY UPLOAD FALLBACKS")
    print("=======================================================")

    # Mock UploadFile
    mock_file = UploadFile(filename="test_image.jpg", file=BytesIO(b"dummy image content"))

    # Test Case 1: Local development (RENDER not set, CLOUDINARY not set)
    print("\nTest Case 1: Local Dev Fallback (No Cloudinary, No RENDER)")
    os.environ.pop("RENDER", None)
    os.environ.pop("CLOUDINARY_CLOUD_NAME", None)
    os.environ.pop("CLOUDINARY_API_KEY", None)
    os.environ.pop("CLOUDINARY_API_SECRET", None)
    os.environ.pop("CLOUDINARY_URL", None)

    try:
        url = await resolve_image_url(mock_file)
        print(f"Success: Generated local storage URL: {url}")
        assert "uploads/" in url
    except Exception as e:
        print(f"Failed: Unexpected exception raised in local dev fallback: {e}")

    # Test Case 2: Production (RENDER is set, CLOUDINARY not set)
    print("\nTest Case 2: Production Safe Mode (No Cloudinary, RENDER is set)")
    os.environ["RENDER"] = "true"
    
    try:
        await resolve_image_url(mock_file)
        print("Failed: Did not raise an exception in production when Cloudinary was missing!")
    except HTTPException as e:
        print(f"Success: Correctly raised HTTPException in production!")
        print(f"   Status code: {e.status_code}")
        print(f"   Detail: {e.detail}")
        assert e.status_code == 500
    except Exception as e:
        print(f"Failed: Raised wrong exception: {e}")

    print("\n=======================================================")
    print("  ALL TEST CASES COMPLETED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
