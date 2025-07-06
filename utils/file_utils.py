import os
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)

class FileUtils:
    @staticmethod
    def create_temp_file(content, suffix='.tmp'):
        """Create a temporary file with given content"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                return tmp.name
        except Exception as e:
            logger.error(f"Failed to create temp file: {str(e)}")
            return None

    @staticmethod
    def delete_file(file_path):
        """Safely delete a file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False

    @staticmethod
    def ensure_directory(path):
        """Create directory if it doesn't exist"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory: {str(e)}")
            return False

    @staticmethod
    def clear_directory(path):
        """Remove all files in a directory"""
        try:
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to clear directory: {str(e)}")
            return False
