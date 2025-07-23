# Adobe India Hackathon 2025 — PDF Outline Extractor (Round 1A)

## Challenge Theme: Connecting the Dots Through Docs

This solution extracts a hierarchical **outline** (title, headings H1/H2/H3, and page numbers) from any PDF (up to 50 pages) as required in Round 1A.

## Approach

- **Text & Structure Extraction:**  
  We use [PyMuPDF](https://pymupdf.readthedocs.io/) (fitz) to systematically extract all text elements along with their font size, style, position, and page metadata from each page of the PDF.
- **Title and Heading Detection:**  
  Headings and title are identified using a combination of:
  - Font size and style heuristics,
  - Position on page,
  - Deduplication and line length constraints,
  - Analysis of text properties (e.g., all-caps, boldness) without relying solely on font size.
- **Heading Level Assignment:**
  - The largest, top-most text is treated as the **Title**.
  - Remaining headings are mapped to H1, H2, H3 based on relative font size and position clusters, ensuring no hardcoding and maximum adaptability across varying layouts and languages.
- **Output Format:**  
  The result is output as a JSON file, matching the example shown in the problem statement.

## How to Build and Run

**Requirements:**  
- Works entirely offline (NO network/web calls)
- Model size (if used): ≤ 200MB
- CPU only (AMD64/Linux)

**Docker Build:**  
In your project root directory, run:
```
docker build --platform linux/amd64 -t outline_extractor: .
```

**Docker Execution:**  
To process all PDFs in `/input/` and output JSONs to `/output/`:
```
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  outline_extractor:
```
- On Windows Command Prompt, use `%cd%` instead of `$(pwd)`.

**Expected Output:**  
For every `filename.pdf` in `/app/input`, the code writes a matching `filename.json` with outline information to `/app/output`.

## Dependencies

- Python 3.9
- [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) (`pip install pymupdf`)

**NB:** All dependencies are pre-installed within the Docker container.  
No internet connection is required for execution.

## Constraints & Highlights

- **Execution time:** ≤ 10 seconds for any 50-page PDF
- **Model size:** ≤ 200MB (if used; none required in baseline)
- **No hardcoding** of document-specific logic or headings
- **No external API/web calls**
- **Handles both simple and complex, and some multilingual PDFs**

## Scoring Criteria Alignment

- **Heading Detection Accuracy:** Combines layout, font, and text features for high precision/recall
- **Performance:** Designed for fast, lightweight operation
- **Modularity:** Codebase is modular for future rounds and reuse

## Repository Structure

```
|-- extractor.py     # Main code for outline extraction
|-- Dockerfile       # For reproducible builds and runs
|-- README.md        # THIS file (instructions/approach)
|-- input/           # Empty directory for input PDFs
|-- output/          # Empty directory for output JSONs
```

_Keep `input/` and `output/` directories empty for submission (no sample files included)._

## Notes

- **Keep this repository private** until instructed by the hackathon organizers.
- Please refer to the challenge PDF for any further constraints or expected behavior.

## Contact

If you have any questions or encounter issues with execution, please contact Team Code Reality(Harshvardhan Patidar, harshvardhanvinodpatidar@gmail.com).

**Thank you for reviewing our submission!**
