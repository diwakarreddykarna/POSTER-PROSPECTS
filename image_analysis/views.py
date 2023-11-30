# views.py
import os
import re

import cv2
import pytesseract
import webcolors
from django.shortcuts import render
from django.http import JsonResponse
from image_analysis.forms import ImageUploadForm
from image_analysis.models import UploadedImage
from googletrans import Translator

def calculate_color_contrast(color, background_color=[1.0, 1.0, 1.0]):
    contrast_ratio = calculate_contrast_ratio(color, background_color)
    return contrast_ratio


def calculate_overall_score(scores):
    # Customize the weighting of each score based on importance
    weights = {'contrast_ratio': 0.4, 'font_size': 0.3, 'color_ratio': 0.3}

    # Calculate the weighted sum of scores
    weighted_sum = sum(weights[key] * scores.get(key, 0) for key in weights)

    # Scale the weighted sum to a 1-10 range
    overall_score = 1 + (weighted_sum / sum(weights.values())) * 9

    # Ensure the overall score is within the 1-10 range
    overall_score = max(1, min(overall_score, 10))

    return overall_score



def calculate_contrast_ratio(color1, color2):
    # Calculate relative luminance for color1
    luminance1 = 0.2126 * color1[2] + 0.7152 * color1[1] + 0.0722 * color1[0]

    # Calculate relative luminance for color2
    luminance2 = 0.2126 * color2[2] + 0.7152 * color2[1] + 0.0722 * color2[0]

    # Ensure luminance1 is the lighter color
    if luminance1 < luminance2:
        luminance1, luminance2 = luminance2, luminance1

    # Calculate contrast ratio
    contrast_ratio = (luminance1 + 0.05) / (luminance2 + 0.05)

    return contrast_ratio

def evaluate_contrast_level(contrast_ratio):
    if contrast_ratio >= 7.0:
        return "AAA (Large Text)"
    elif contrast_ratio >= 4.5:
        return "AA (Normal Text)"
    else:
        return "Fail"

def closest_color(requested_color):
    min_distance = float('inf')
    closest_name = None
    for key, name in webcolors.CSS3_HEX_TO_NAMES.items():
        color_rgb = webcolors.hex_to_rgb(key)
        r_c, g_c, b_c = color_rgb
        r_d, g_d, b_d = requested_color
        distance = (r_c - r_d) ** 2 + (g_c - g_d) ** 2 + (b_c - b_d) ** 2
        if distance < min_distance:
            min_distance = distance
            closest_name = name
    return closest_name

def calculate_color_contrast(color, background_color=[1.0, 1.0, 1.0]):
    contrast_ratio = calculate_contrast_ratio(color, background_color)
    return contrast_ratio

def detect_font_size(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply thresholding to create a binary image
    _, binary_image = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)

    # Find contours in the binary image
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    font_sizes = []

    for contour in contours:
        # Calculate the bounding box of the contour
        x, y, w, h = cv2.boundingRect(contour)

        # Calculate the font size based on the height of the bounding box
        font_size = h
        font_sizes.append(font_size)

    # Return the font sizes detected in the image
    return font_sizes

def analyze_logo(image_path, target_language):
    # Load the image using OpenCV
    image = cv2.imread(image_path)

    # Calculate the average color of the logo
    average_color = cv2.mean(image)[:3]

    # Convert the average color to CSS color code (e.g., "#RRGGBB")
    css_color = "#{:02X}{:02X}{:02X}".format(int(average_color[2]), int(average_color[1]), int(average_color[0]))

    # Find the closest color name to the average color
    closest_color_name = closest_color(average_color)

    # Calculate contrast ratio with a reference color (e.g., white)
    reference_color = [1.0, 1.0, 1.0]  # White color
    contrast_ratio = calculate_contrast_ratio(average_color, reference_color)
    # Calculate color contrast with white background
    color_contrast_ratio = calculate_color_contrast(average_color)

    # Perform OCR using pytesseract
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    #pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract" in production
    detected_text = pytesseract.image_to_string(gray_image, lang='eng')

    font_sizes = detect_font_size(image)
    average_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else None

    scores = {
        'contrast_ratio': contrast_ratio,
        'font_size': average_font_size,  # Add font size score calculation logic
        'color_ratio': average_font_size,  # Add font size score calculation logic
    }

    overall_score = calculate_overall_score(scores)

    # Translate the detected text to the target language
    try:
        # Translate the detected text to the target language
        translator = Translator()
        translated_text = translator.translate(detected_text, dest=target_language).text
    except Exception as e:
        # Handle the exception
        translated_text = "Translation failed: " + str(e)

    return {
        'average_color': css_color,
        'color_name': closest_color_name,
        'contrast_ratio': contrast_ratio,
        'contrast_level': evaluate_contrast_level(contrast_ratio),
        'detected_text': detected_text,
        'translated_text': translated_text,
        'font_size': average_font_size,
        'color_ratio': color_contrast_ratio,
        'overall_score': overall_score,
    }

def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_images = request.FILES.getlist('images')
            target_language = request.POST.get('target_language')  # Get the selected target language

            analysis_results = []

            for uploaded_image in uploaded_images:
                # Create an instance of UploadedImage
                uploaded_file = UploadedImage(file=uploaded_image)
                uploaded_file.save()

                # Analyze the logo using the analyze_logo function with the selected target language
                analysis_result = analyze_logo(uploaded_file.file.path, target_language)

                analysis_results.append(analysis_result)

                # Remove the uploaded image file after analysis
                os.remove(uploaded_file.file.path)

            return render(request, 'image_analysis/upload_image.html', {'results': analysis_results})
        else:
            return JsonResponse({'error': 'Invalid form data'}, status=400)
    else:
        form = ImageUploadForm()

    return render(request, 'image_analysis/upload_image.html', {'form': form})


