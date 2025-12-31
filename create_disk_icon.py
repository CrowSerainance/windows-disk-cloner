#!/usr/bin/env python3
"""
Create a simple disk icon for the Windows Disk Cloner application
This creates an ICO file that can be used with PyInstaller
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # Create a 256x256 icon (Windows supports multiple sizes, but 256 is standard)
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw disk (circle with center hole)
    center = size // 2
    outer_radius = size // 2 - 20
    inner_radius = size // 6
    
    # Outer disk (blue gradient effect)
    draw.ellipse(
        [center - outer_radius, center - outer_radius, 
         center + outer_radius, center + outer_radius],
        fill=(0, 120, 215, 255),  # Windows blue
        outline=(0, 90, 180, 255),
        width=3
    )
    
    # Inner hole (center)
    draw.ellipse(
        [center - inner_radius, center - inner_radius,
         center + inner_radius, center + inner_radius],
        fill=(240, 240, 240, 255),
        outline=(200, 200, 200, 255),
        width=2
    )
    
    # Add some detail lines (like a hard disk)
    for i in range(3):
        y_offset = -outer_radius // 3 + (i * outer_radius // 3)
        draw.arc(
            [center - outer_radius + 10, center - outer_radius + 10 + y_offset,
             center + outer_radius - 10, center + outer_radius - 10 + y_offset],
            start=0,
            end=360,
            fill=(255, 255, 255, 180),
            width=2
        )
    
    # Save as ICO file with multiple sizes
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    for s in sizes:
        resized = img.resize(s, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    icons[0].save('disk_icon.ico', format='ICO', sizes=[(s[0], s[1]) for s in sizes])
    print("Icon created: disk_icon.ico")
    
except ImportError:
    print("PIL/Pillow not installed. Creating a simple placeholder...")
    print("Install with: pip install Pillow")
    print("For now, the build will proceed without a custom icon.")
except Exception as e:
    print(f"Error creating icon: {e}")
    print("Build will proceed without a custom icon.")

