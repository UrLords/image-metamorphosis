# Image Metamorphosis

<p align="center">
  <strong>Learn image processing visually, from pixels to patterns.</strong>
</p>

[![Website](https://img.shields.io/badge/Live-imagemeta.site-c9a86c?style=for-the-badge)](https://imagemeta.site)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?style=for-the-badge&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

**Image Metamorphosis** is an interactive digital image processing learning platform. It helps users understand how image operations work by combining real processing results with visual explanations, formulas, histograms, and educational breakdowns.

Live website: [https://imagemeta.site](https://imagemeta.site)

## Overview

Most image tools only show the final output. Image Metamorphosis is built to show the result and the reasoning behind it, so each operation becomes easier to understand, compare, and explain.

The platform is suitable for:

- Digital image processing study.
- Classroom demonstrations.
- Experimenting with OpenCV-based operations.
- Comparing original and processed images.
- Understanding parameters such as threshold, kernel size, sigma, hue shift, saturation, and filtering strength.

## Highlights

| Area | What it provides |
| --- | --- |
| Visual Learning | See the original image, processed result, explanation, and histogram in one place. |
| Practical Processing | Try OpenCV-powered point, color, geometric, spatial, morphology, edge, and segmentation operations. |
| Clear Analysis | Compare RGB and luminance histograms to understand tonal and color distribution. |
| Document Utility | Scan documents with perspective correction, enhancement, and export-ready outputs. |

## Why It Stands Out

- It is built for learning, not only editing.
- Each operation connects output, parameter, formula, and visual feedback.
- The interface keeps image comparison and explanation close together.
- The modules follow common digital image processing topics, making it useful for study and presentation.

## Features

- Google Sign-In authentication.
- Interactive image upload and preview.
- Before-after result comparison.
- RGB and luminance histogram visualization.
- Educational explanations for each operation.
- Parameter controls with real processing results.
- Document scanning with perspective correction and enhancement.
- Image processing history support.
- Clean, responsive interface for desktop and mobile.

## Learning Modules

### Basic Image Processing

- Image information and resolution.
- Grayscale conversion.
- Pixel matrix visualization.
- RGB and luminance histogram analysis.

### Arithmetic Operations

- Image blending.
- Background subtraction.
- Image multiplication.
- Image division.

### Geometric Operations

- Rotation.
- Scaling.
- Translation.
- Flip.

### Point and Color Operations

- Brightness.
- Contrast.
- Negative image.
- Thresholding.
- Saturation.
- Hue shift.
- Opacity.
- Sharpness.

### Spatial Operations

- Mean filter.
- Median filter.
- Gaussian blur.

### Morphology

- Morphological image processing.
- Zhang-Suen thinning.

### Edge Detection

- Sobel edge detection.
- Edge detection concept visualization.

### Segmentation

- Global thresholding.
- Adaptive thresholding.
- Otsu binarization.
- K-Means color segmentation.

### Scan Document

- Automatic document perspective correction.
- Image enhancement for scanned documents.
- Clean black-white, enhanced, and color outputs.
- Export support for processed scan results.

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- Firebase Authentication

### Backend

- Python
- Flask
- OpenCV
- NumPy
- Pillow

### Cloud Services

- Firebase Authentication
- Supabase PostgreSQL
- Cloudinary

## Getting Started

### Requirements

- Node.js 18+
- Python 3.10+
- Git

### Backend

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies and run the API:

```bash
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the local frontend in your browser:

```text
http://localhost:5173
```

## Build

```bash
cd frontend
npm run build
```

## Notes

- This project focuses on educational image processing, not AI-based object segmentation.
- Some operations are designed to explain the concept clearly, so the UI prioritizes learning value and visual comparison.
- Sensitive configuration should be stored locally and should not be committed.

## License

This project is intended for educational use.
