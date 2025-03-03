from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Create a new image with a white background
    size = (256, 256)
    image = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    # Draw a shield shape
    margin = 20
    shield_points = [
        (margin, size[1]//3),  # Top left
        (size[0]//2, margin),  # Top middle
        (size[0]-margin, size[1]//3),  # Top right
        (size[0]-margin, size[1]*2//3),  # Bottom right
        (size[0]//2, size[1]-margin),  # Bottom middle
        (margin, size[1]*2//3),  # Bottom left
    ]
    
    # Draw shield with gradient
    for i in range(margin):
        # Create a slightly different shade of blue for gradient effect
        blue_shade = (30, 100 + i, 200 + i//2, 255)
        modified_points = [(x + (i if j < 3 else -i), y + (i if j < 3 else -i)) 
                         for j, (x, y) in enumerate(shield_points)]
        draw.polygon(modified_points, fill=blue_shade)

    # Draw "EF" text
    try:
        # Try to use Arial font if available
        font = ImageFont.truetype("arial.ttf", size[0]//3)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    text = "EF"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    text_position = (
        (size[0] - text_width) // 2,
        (size[1] - text_height) // 2
    )
    
    # Draw text with white color
    draw.text(text_position, text, fill=(255, 255, 255), font=font)

    # Save in different sizes for the .ico file
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
        
    icon_path = os.path.join(icons_dir, 'edufilter.ico')
    resized_images = [image.resize(size, Image.Resampling.LANCZOS) for size in sizes]
    resized_images[0].save(
        icon_path,
        format='ICO',
        sizes=sizes,
        append_images=resized_images[1:]
    )
    
    print(f"Icon created successfully at {icon_path}")

if __name__ == '__main__':
    create_icon()
