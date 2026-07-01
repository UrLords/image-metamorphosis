# Image Metamorphosis

<p align="center">
  <strong>Learn, transform, and understand digital images visually.</strong>
</p>

<p align="center">
  <a href="https://imagemeta.site">https://imagemeta.site</a>
</p>

Image Metamorphosis is an interactive image processing platform built for learning and practical experimentation. It helps users see how an image changes, why it changes, and how each parameter affects the final result.

Most image tools only show the output. Image Metamorphosis connects the output with explanations, formulas, histograms, and side-by-side comparison so the processing concept is easier to understand and present.

## Highlights

- Interactive image upload and before-after comparison.
- Educational explanations with formulas and processing steps.
- RGB and luminance histogram visualization.
- Parameter-based controls for common image processing operations.
- Document scanning with perspective correction and enhancement modes.
- Login-protected processing features.
- Responsive interface for desktop and mobile use.

## Learning Areas

### Image Fundamentals

- Image information and resolution.
- Grayscale conversion.
- Pixel matrix visualization.
- Histogram analysis.

### Arithmetic Operations

- Blending.
- Subtraction.
- Multiplication.
- Division.

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

### Spatial Filtering

- Mean filter.
- Median filter.
- Gaussian blur.

### Pattern and Region Analysis

- Morphological operations.
- Zhang-Suen thinning.
- Edge detection.
- Image segmentation.

### Scan Document

- Auto crop and perspective correction.
- Document cleanup and enhancement.
- Black-white, clean text, grayscale, and color outputs.
- Export-ready processed images.

## Product Focus

Image Metamorphosis is designed as both a learning tool and a practical image utility. The goal is not only to process images, but also to make every transformation understandable through visual feedback and concise explanations.

## Security Notes

- Sensitive configuration is kept outside the repository.
- Environment examples use generic names intentionally.
- Authentication is required before protected processing features can be used.
- API requests are validated and rate-limited to reduce abuse.
- Public error responses avoid exposing internal server details.

## Local Development

Install dependencies in each app folder, then run the local API and web app in separate terminals.

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the local web app at:

```text
http://localhost:5173
```

## Build

```bash
cd frontend
npm run build
```

## Configuration

Use the `.env.example` files as a safe reference for required configuration. Do not commit real credentials, service keys, tokens, or local `.env` files.

## License

This project is intended for educational and product development use.
