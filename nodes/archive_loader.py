import os
import zipfile
import py7zr
import torch
import numpy as np
from PIL import Image
import folder_paths

class ArchiveImageLoader:
    """
    A node that accepts a compressed file (ZIP, 7z), extracts it to a
    directory within the ComfyUI input folder, and loads the images from
    that directory as a batch.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # This input is hidden and is used to receive the path from the JS frontend
                "archive_file": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "sort_method": (["None", "alphabetical", "reverse_alphabetical"],),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "directory_path")
    FUNCTION = "load_from_archive"
    CATEGORY = "only/Image"

    def load_from_archive(self, archive_file, sort_method="None"):
        if not archive_file or archive_file.strip() == "":
            # Return an empty tensor if no file is provided to avoid errors
            return (torch.empty(0), "")

        # --- 1. Get File Path and Define Extraction Path ---
        # The file is uploaded to the temp directory by the frontend
        temp_dir = folder_paths.get_temp_directory()
        archive_path = os.path.join(temp_dir, archive_file)

        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Archive file not found: {archive_path}")

        # Define the extraction directory inside the main ComfyUI 'input' folder
        input_dir = folder_paths.get_input_directory()
        filename_without_ext = os.path.splitext(os.path.basename(archive_path))[0]
        extract_to_dir = os.path.join(input_dir, filename_without_ext)

        # Create the directory if it doesn't exist
        os.makedirs(extract_to_dir, exist_ok=True)

        # --- 2. Decompress the Archive ---
        print(f"Extracting '{archive_path}' to '{extract_to_dir}'...")
        try:
            if archive_path.lower().endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to_dir)
            elif archive_path.lower().endswith('.7z'):
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    z.extractall(path=extract_to_dir)
            # RAR support is complex due to external binary dependencies (unrar).
            # For now, we are skipping it to keep the node easy to install.
            elif archive_path.lower().endswith('.rar'):
                 raise NotImplementedError("RAR decompression is not supported due to external dependencies. Please use ZIP or 7z.")
            else:
                raise ValueError(f"Unsupported archive format for file: {archive_file}")
            print("Extraction complete.")
        except Exception as e:
            raise RuntimeError(f"Failed to extract archive: {e}")

        # --- 3. Load Images from the Directory ---
        image_files = sorted([f for f in os.listdir(extract_to_dir)
                              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))])

        if sort_method == "alphabetical":
            image_files.sort()
        elif sort_method == "reverse_alphabetical":
            image_files.sort(reverse=True)

        if not image_files:
            return (torch.empty(0), extract_to_dir)

        images = []
        for filename in image_files:
            try:
                img_path = os.path.join(extract_to_dir, filename)
                with Image.open(img_path) as img:
                    # Convert to RGB and normalize
                    img_array = np.array(img.convert("RGB")).astype(np.float32) / 255.0
                    img_tensor = torch.from_numpy(img_array).unsqueeze(0)
                    images.append(img_tensor)
            except Exception as e:
                print(f"Warning: Could not load image '{filename}'. Skipping. Error: {e}")

        if not images:
             return (torch.empty(0), extract_to_dir)

        # Stack all image tensors into a single batch tensor
        batch_tensor = torch.cat(images, 0)
        return (batch_tensor, extract_to_dir)

# --- Add this to the end of the file ---
NODE_CLASS_MAPPINGS = {
    "ArchiveImageLoader": ArchiveImageLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ArchiveImageLoader": "Load Images from Archive",
}