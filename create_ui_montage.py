#!/usr/bin/env python3
"""Create a 6-panel UI workflow montage for the ApexS IEEE paper."""

from PIL import Image, ImageDraw, ImageFont
import os

# Image filenames in order: upload -> configure -> optimize -> plan -> explain -> approve
image_files = [
    "upload.png",
    "configure.png", 
    "optimize.png",
    "plan.png",
    "explain.png",
    "approve.png"
]

figs_dir = "d:\\SE\\files\\figs"
image_paths = [os.path.join(figs_dir, f) for f in image_files]

# Load all images
images = [Image.open(p) for p in image_paths]

# Get dimensions
widths = [img.width for img in images]
heights = [img.height for img in images]

# Calculate montage dimensions
# We'll scale each image to be the same height (max height), keeping aspect ratio
target_height = min(heights)  # Or set to a specific value like 300
scaled_images = []
scaled_widths = []

for img in images:
    # Scale to target height maintaining aspect ratio
    scale_factor = target_height / img.height
    new_width = int(img.width * scale_factor)
    resized = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
    scaled_images.append(resized)
    scaled_widths.append(new_width)

# Total width with small gaps between images
gap = 5  # pixels between images
total_width = sum(scaled_widths) + (len(scaled_images) - 1) * gap
total_height = target_height

# Create montage image with white background
montage = Image.new('RGB', (total_width, total_height), color='white')

# Paste images side-by-side
current_x = 0
for img in scaled_images:
    montage.paste(img, (current_x, 0))
    current_x += img.width + gap

# Save montage
output_path = os.path.join(figs_dir, "ui_workflow.png")
montage.save(output_path, quality=95)
print("[OK] Montage created: {}".format(output_path))
print("  Dimensions: {}x{} px".format(total_width, total_height))
print("  Panels: {} (upload -> configure -> optimize -> plan -> explain -> approve)".format(len(image_files)))
