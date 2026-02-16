#!/usr/bin/env python
"""
Test script for Cloudinary file upload functionality.

This script tests uploading files to Cloudinary using credentials from .env file.
Run with: python test_cloudinary_upload.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO

# Try to import PIL (optional)
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Get Cloudinary credentials
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")


def check_credentials():
    """Check if Cloudinary credentials are set."""
    if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
        print("❌ Error: Cloudinary credentials not found in .env file")
        print("\nPlease add the following to your .env file:")
        print("CLOUDINARY_CLOUD_NAME=your-cloud-name")
        print("CLOUDINARY_API_KEY=your-api-key")
        print("CLOUDINARY_API_SECRET=your-api-secret")
        return False
    
    print("✅ Cloudinary credentials found")
    print(f"   Cloud Name: {CLOUDINARY_CLOUD_NAME}")
    print(f"   API Key: {CLOUDINARY_API_KEY[:8]}...")
    print(f"   API Secret: {CLOUDINARY_API_SECRET[:8]}...")
    return True


def create_test_image():
    """Create a simple test image in memory."""
    print("\n📸 Creating test image...")
    
    try:
        # Create a simple 200x200 colored image
        img = Image.new('RGB', (200, 200), color='lightblue')
        
        # Add some text (requires PIL with text support)
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            # Try to use a default font
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            draw.text((50, 85), "Test Upload", fill='darkblue', font=font)
        except Exception:
            pass  # If text fails, just use the colored image
        
        # Save to BytesIO buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        print("✅ Test image created (200x200 PNG)")
        return buffer
    except ImportError:
        print("⚠️  PIL/Pillow not installed. Creating a simple test file instead...")
        # Create a simple text file as fallback
        buffer = BytesIO()
        buffer.write(b"Test file for Cloudinary upload")
        buffer.seek(0)
        print("✅ Test file created")
        return buffer


def test_cloudinary_upload():
    """Test uploading a file to Cloudinary."""
    print("\n" + "="*60)
    print("Cloudinary Upload Test")
    print("="*60)
    
    # Check credentials
    if not check_credentials():
        sys.exit(1)
    
    # Try to import cloudinary
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
    except ImportError:
        print("\n❌ Error: cloudinary package not installed")
        print("Install it with: pip install cloudinary")
        sys.exit(1)
    
    # Configure Cloudinary
    print("\n⚙️  Configuring Cloudinary...")
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )
    print("✅ Cloudinary configured")
    
    # Create test image
    test_image = create_test_image()
    
    # Upload to Cloudinary
    print("\n📤 Uploading test file to Cloudinary...")
    try:
        # Determine resource type based on whether we have PIL
        resource_type = "image" if HAS_PIL else "raw"
        
        result = cloudinary.uploader.upload(
            test_image,
            folder="test_uploads",  # Organize test uploads in a folder
            public_id="test_file_" + str(int(os.path.getmtime(__file__))),  # Unique ID
            resource_type=resource_type,
        )
        
        print("✅ Upload successful!")
        print("\n📋 Upload Details:")
        print(f"   Public ID: {result.get('public_id')}")
        print(f"   URL: {result.get('url')}")
        print(f"   Secure URL: {result.get('secure_url')}")
        print(f"   Format: {result.get('format')}")
        print(f"   Width: {result.get('width')}px")
        print(f"   Height: {result.get('height')}px")
        print(f"   Size: {result.get('bytes', 0)} bytes")
        
        # Test retrieving the image
        print("\n🔍 Testing image retrieval...")
        retrieved = cloudinary.api.resource(result['public_id'])
        if retrieved:
            print(f"✅ Successfully retrieved image: {retrieved.get('url')}")
        
        # Cleanup: Delete the test image
        print("\n🧹 Cleaning up test image...")
        delete_result = cloudinary.uploader.destroy(result['public_id'])
        if delete_result.get('result') == 'ok':
            print("✅ Test image deleted successfully")
        else:
            print(f"⚠️  Could not delete test image: {delete_result.get('result')}")
        
        print("\n" + "="*60)
        print("✅ All tests passed! Cloudinary is working correctly.")
        print("="*60)
        return True
        
    except cloudinary.exceptions.Error as e:
        print(f"\n❌ Cloudinary Error: {e}")
        print("\nPossible issues:")
        print("  - Invalid credentials (check your .env file)")
        print("  - Network connectivity issues")
        print("  - Cloudinary account limits exceeded")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_upload(file_path=None):
    """Test uploading an actual file from disk."""
    if not file_path:
        print("\n💡 Tip: You can test with a real file by running:")
        print("   python test_cloudinary_upload.py path/to/your/image.jpg")
        return
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"\n❌ Error: File not found: {file_path}")
        return
    
    print(f"\n📁 Uploading file: {file_path.name}")
    
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
        )
        
        with open(file_path, 'rb') as f:
            result = cloudinary.uploader.upload(
                f,
                folder="test_uploads",
                resource_type="image",
            )
        
        print("✅ File uploaded successfully!")
        print(f"   URL: {result.get('secure_url')}")
        print(f"   Public ID: {result.get('public_id')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error uploading file: {e}")
        return None


if __name__ == "__main__":
    # Check if a file path was provided as argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        test_file_upload(file_path)
    else:
        # Run the standard test with generated image
        success = test_cloudinary_upload()
        sys.exit(0 if success else 1)
