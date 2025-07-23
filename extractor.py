import os
import fitz  # PyMuPDF
import json

def extract_outline(pdf_path):
    doc = fitz.open(pdf_path)
    title, outline = None, []
    heading_candidates = []

    for page_num, page in enumerate(doc, 1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text: continue
                    if len(text) < 3 or len(text) > 100: continue
                    entry = {
                        "text": text,
                        "font_size": span["size"],
                        "flags": span["flags"],
                        "font": span["font"],
                        "page": page_num,
                        "top": span["bbox"][1]
                    }
                    heading_candidates.append(entry)

    if not heading_candidates:
        return {"title": None, "outline": []}
    font_sizes = sorted({hc["font_size"] for hc in heading_candidates}, reverse=True)

    def heading_level(size):
        if size == font_sizes[0]: return "TITLE"
        elif size == font_sizes[1]: return "H1" if len(font_sizes)>1 else "H1"
        elif len(font_sizes)>2 and size == font_sizes[2]: return "H2"
        else: return "H3"

    seen = set()
    for hc in heading_candidates:
        lvl = heading_level(hc["font_size"])
        if hc["text"] in seen: continue
        seen.add(hc["text"])
        if lvl == "TITLE" and not title:
            title = hc["text"]
        elif lvl in ("H1", "H2", "H3"):
            outline.append({
                "level": lvl,
                "text": hc["text"],
                "page": hc["page"]
            })
    return {"title": title, "outline": outline}

def process_all(input_dir, output_dir):
    for fname in os.listdir(input_dir):
        if not fname.lower().endswith(".pdf"):
            continue
        in_path = os.path.join(input_dir, fname)
        result = extract_outline(in_path)
        out_path = os.path.join(output_dir, fname.rsplit('.',1)[0]+'.json')
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    process_all("/app/input", "/app/output")
