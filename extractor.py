import os
import json
import fitz  # PyMuPDF
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

class PDFOutlineExtractor:
    def __init__(self):
        # Enhanced noise patterns for better filtering
        self.noise_patterns = [
            r'^\d+$',  # Page numbers only
            r'^page\s+\d+',  # "Page 1", "Page 2"
            r'^\d+\s*$',  # Standalone numbers
            r'^©.*',  # Copyright text
            r'^copyright.*',  # Copyright variations
            r'^www\.',  # URLs
            r'^http[s]?://',  # URLs
            r'^\s*[•·‣▪▫○]\s*$',  # Bullet points alone
            r'^\s*[-–—]\s*$',  # Dashes alone
            r'^\s*[.,;:!?]\s*$',  # Punctuation alone
            r'^\s*version\s+\d+',  # Version numbers
            r'^\s*\d+\s*of\s+\d+',  # "Page X of Y"
            r'^\s*\(\s*\)\s*$',  # Empty parentheses
            r'^\s*\[\s*\]\s*$',  # Empty brackets
        ]
        
        # Enhanced heading indicator patterns
        self.heading_patterns = [
            # Numbered headings
            (r'^\d+\.?\s+[A-Z]', 25, 'H1'),  # "1. Introduction" or "1 INTRODUCTION"
            (r'^\d+\.\d+\.?\s+', 20, 'H2'),  # "1.1 Subsection"
            (r'^\d+\.\d+\.\d+\.?\s+', 15, 'H3'),  # "1.1.1 Sub-subsection"
            
            # Chapter/Section patterns
            (r'^Chapter\s+\d+', 30, 'H1'),  # "Chapter 1"
            (r'^Section\s+\d+', 25, 'H1'),  # "Section 1"
            (r'^Part\s+[IVX\d]+', 30, 'H1'),  # "Part I", "Part 1"
            (r'^Appendix\s+[A-Z\d]', 25, 'H1'),  # "Appendix A"
            
            # All caps headings
            (r'^[A-Z][A-Z\s]{4,}[A-Z]$', 20, 'H1'),  # ALL CAPS titles
            
            # Form-style numbered items
            (r'^\d+\.\s*$', 15, 'H2'),  # "1." (form questions)
            
            # Special document sections
            (r'^Summary\s*$', 20, 'H1'),
            (r'^Background\s*$', 20, 'H1'),
            (r'^Introduction\s*$', 20, 'H1'),
            (r'^Conclusion\s*$', 20, 'H1'),
            (r'^References?\s*$', 20, 'H1'),
            (r'^Bibliography\s*$', 20, 'H1'),
            (r'^Acknowledgements?\s*$', 20, 'H1'),
        ]
        
        # Common footer/header patterns to ignore
        self.header_footer_patterns = [
            r'^\d{4}\s+Page\s+\d+',  # "2014 Page 1"
            r'^.*\d{4}$',  # Lines ending with year
            r'^.*Board$',  # "...Board"
            r'^RFP:.*',  # RFP headers
            r'^.*March\s+\d{4}$',  # Date footers
        ]
    
    def is_noise_text(self, text: str) -> bool:
        """Enhanced noise filtering"""
        text = text.strip()
        
        # Length filters
        if len(text) < 2 or len(text) > 300:
            return True
        
        # Check header/footer patterns
        for pattern in self.header_footer_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
                
        # Pattern-based filtering
        for pattern in self.noise_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Filter very short non-meaningful text
        if len(text) < 4 and not any(c.isalpha() for c in text):
            return True
        
        # Filter lines with too many special characters
        special_chars = sum(1 for c in text if c in '•·‣▪▫○-–—*')
        if special_chars > len(text) * 0.5:
            return True
            
        return False
    
    def calculate_text_features(self, candidate: Dict) -> Dict:
        """Enhanced feature calculation with better pattern recognition"""
        text = candidate["text"]
        features = {
            "text": text,
            "font_size": candidate["font_size"],
            "is_bold": bool(candidate["font_flags"] & 2**4),
            "is_italic": bool(candidate["font_flags"] & 2**1),
            "length": len(text),
            "word_count": len(text.split()),
            "has_numbers": bool(re.search(r'\d', text)),
            "starts_with_number": bool(re.match(r'^\d+', text)),
            "is_all_caps": text.isupper() and len(text) > 3,
            "position_top": candidate["top"],
            "page": candidate["page"],
            "bbox": candidate.get("bbox", [0, 0, 0, 0])
        }
        
        # Enhanced pattern matching with scores
        features["pattern_score"] = 0
        features["suggested_level"] = None
        
        for pattern, score, level in self.heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                if score > features["pattern_score"]:
                    features["pattern_score"] = score
                    features["suggested_level"] = level
        
        # Calculate position score (higher for items near top of page)
        page_height = 800
        features["position_score"] = max(0, 1 - (candidate["top"] / page_height))
        
        # Check if it's likely a form question
        features["is_form_question"] = bool(re.match(r'^\d+\.\s*[A-Z]', text))
        
        # Check if it's a mission statement or important declaration
        features["is_mission"] = bool(re.search(r'mission\s+statement', text, re.IGNORECASE))
        
        return features
    
    def extract_title_candidates(self, features_list: List[Dict]) -> Optional[str]:
        """Improved title extraction with better heuristics"""
        if not features_list:
            return None
            
        # Focus on first 3 pages for title
        first_pages_candidates = [f for f in features_list if f["page"] <= 3]
        
        if not first_pages_candidates:
            return None
        
        title_scores = []
        
        for candidate in first_pages_candidates:
            score = 0
            text = candidate["text"]
            
            # Skip very short or very long text
            if len(text) < 5 or len(text) > 150:
                continue
            
            # Font size score (normalized)
            max_font_size = max(f["font_size"] for f in first_pages_candidates)
            if max_font_size > 0:
                score += (candidate["font_size"] / max_font_size) * 40
            
            # Position score (prefer top of page)
            if candidate["position_score"] > 0.8:
                score += 25
            elif candidate["position_score"] > 0.6:
                score += 15
            
            # Bold formatting bonus
            if candidate["is_bold"]:
                score += 15
            
            # Page 1 strong preference
            if candidate["page"] == 1:
                score += 20
            
            # Length preferences (titles are usually moderate length)
            if 10 <= len(text) <= 80:
                score += 15
            elif 5 <= len(text) <= 120:
                score += 10
            
            # Penalty for numbered items (likely not titles)
            if re.match(r'^\d+\.', text):
                score -= 20
            
            # Penalty for very technical patterns
            if re.search(r'RFP:|Version|Page \d+', text):
                score -= 25
            
            # Bonus for mission statements or main headings
            if candidate["is_mission"]:
                score += 20
            
            # All caps moderate bonus (but not if too long)
            if candidate["is_all_caps"] and len(text) <= 50:
                score += 10
            
            title_scores.append((candidate, score))
        
        # Return highest scoring title
        title_scores.sort(key=lambda x: x[1], reverse=True)
        return title_scores[0][0]["text"] if title_scores and title_scores[0][1] > 30 else None
    
    def classify_heading_level(self, feature: Dict, font_size_thresholds: Dict) -> Optional[str]:
        """Enhanced heading classification with multiple criteria"""
        text = feature["text"]
        font_size = feature["font_size"]
        
        # Skip noise
        if self.is_noise_text(text):
            return None
        
        # Use pattern-based suggestion if available and strong
        if feature["pattern_score"] >= 20 and feature["suggested_level"]:
            return feature["suggested_level"]
        
        # Multi-factor scoring for heading levels
        h1_score = h2_score = h3_score = 0
        
        # Font size scoring
        if font_size >= font_size_thresholds["h1"]:
            h1_score += 25
        elif font_size >= font_size_thresholds["h2"]:
            h2_score += 20
            h1_score += 10  # Could still be H1 if other factors support it
        elif font_size >= font_size_thresholds["h3"]:
            h3_score += 15
            h2_score += 10
        else:
            # Too small, but might be heading if other factors are strong
            pass
        
        # Pattern-based scoring with specific rules
        if re.match(r'^\d+\.?\s+[A-Z]', text):  # "1. Introduction"
            h1_score += 25
        elif re.match(r'^\d+\.\d+\.?\s+', text):  # "1.1 Subsection"
            h2_score += 30
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+', text):  # "1.1.1 Sub-subsection"  
            h3_score += 35
        elif re.match(r'^Chapter|^Section|^Part|^Appendix', text, re.IGNORECASE):
            h1_score += 30
        
        # Form questions (numbered items)
        if feature["is_form_question"]:
            h2_score += 20
        
        # Formatting bonuses
        if feature["is_bold"]:
            h1_score += 15
            h2_score += 12
            h3_score += 8
        
        # All caps bonus (prefer higher levels)
        if feature["is_all_caps"]:
            h1_score += 20
            h2_score += 5
        
        # Length-based scoring
        text_len = len(text)
        if 5 <= text_len <= 60:  # Good heading length
            h1_score += 10
            h2_score += 15
            h3_score += 12
        elif text_len <= 100:  # Acceptable length
            h1_score += 5
            h2_score += 8
            h3_score += 10
        
        # Position scoring
        if feature["position_score"] > 0.7:
            h1_score += 8
            h2_score += 10
            h3_score += 12
        
        # Mission statement bonus
        if feature["is_mission"]:
            h1_score += 25
        
        # Determine best level
        scores = [("H1", h1_score), ("H2", h2_score), ("H3", h3_score)]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Only return if confidence is reasonable
        best_level, best_score = scores[0]
        
        # Minimum thresholds for each level
        min_thresholds = {"H1": 25, "H2": 20, "H3": 15}
        
        if best_score >= min_thresholds.get(best_level, 20):
            return best_level
        
        return None
    
    def calculate_font_thresholds(self, candidates: List[Dict]) -> Dict:
        """Improved font size threshold calculation"""
        # Filter out noise and get meaningful font sizes
        meaningful_texts = []
        for c in candidates:
            if not self.is_noise_text(c["text"]) and len(c["text"]) > 5:
                meaningful_texts.append(c)
        
        if not meaningful_texts:
            return {"h1": 16, "h2": 14, "h3": 12}
        
        font_sizes = [c["font_size"] for c in meaningful_texts]
        font_sizes.sort(reverse=True)
        
        n = len(font_sizes)
        
        if n >= 20:
            # Use percentile-based approach for larger documents
            h1_threshold = font_sizes[max(0, int(n * 0.05))]  # Top 5%
            h2_threshold = font_sizes[max(0, int(n * 0.15))]  # Top 15%
            h3_threshold = font_sizes[max(0, int(n * 0.30))]  # Top 30%
        elif n >= 10:
            h1_threshold = font_sizes[max(0, int(n * 0.1))]   # Top 10%
            h2_threshold = font_sizes[max(0, int(n * 0.25))]  # Top 25%
            h3_threshold = font_sizes[max(0, int(n * 0.45))]  # Top 45%
        else:
            # For smaller documents, use simpler approach
            max_size = max(font_sizes)
            median_size = font_sizes[n // 2] if n > 0 else 12
            
            h1_threshold = max_size * 0.95
            h2_threshold = max(median_size, max_size * 0.85)
            h3_threshold = max(median_size * 0.9, max_size * 0.75)
        
        return {
            "h1": max(h1_threshold, 14),  # Minimum reasonable sizes
            "h2": max(h2_threshold, 12),
            "h3": max(h3_threshold, 10)
        }
    
    def post_process_outline(self, outline: List[Dict]) -> List[Dict]:
        """Post-process outline to fix common issues"""
        if not outline:
            return outline
        
        # Remove duplicates while preserving order
        seen = set()
        unique_outline = []
        for item in outline:
            key = (item["text"].lower().strip(), item["page"])
            if key not in seen:
                seen.add(key)
                unique_outline.append(item)
        
        # Sort by page, then by logical order
        unique_outline.sort(key=lambda x: (x["page"], x.get("position", 0)))
        
        return unique_outline
    
    def extract_outline(self, pdf_path: str) -> Dict:
        """Main extraction function with enhanced processing"""
        try:
            doc = fitz.open(pdf_path)
            candidates = []
            
            # Extract all text candidates with enhanced metadata
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" not in block:
                        continue
                        
                    for line_idx, line in enumerate(block["lines"]):
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if not text:
                                continue
                                
                            candidates.append({
                                "text": text,
                                "font_size": span["size"],
                                "font_flags": span["flags"],
                                "page": page_num + 1,
                                "top": span["bbox"][1],
                                "bbox": span["bbox"],
                                "position": line_idx  # Track position within page
                            })
            
            doc.close()
            
            if not candidates:
                return {"title": "Untitled Document", "outline": []}
            
            # Calculate features for all candidates
            features_list = [self.calculate_text_features(c) for c in candidates]
            
            # Remove noise and duplicates
            clean_features = []
            seen_texts = set()
            
            for feature in features_list:
                text_key = feature["text"].lower().strip()
                if (text_key not in seen_texts and 
                    not self.is_noise_text(feature["text"]) and
                    len(feature["text"]) > 2):
                    seen_texts.add(text_key)
                    clean_features.append(feature)
            
            # Extract title
            title = self.extract_title_candidates(clean_features)
            
            # Calculate font size thresholds
            font_thresholds = self.calculate_font_thresholds(clean_features)
            
            # Extract headings
            outline = []
            for feature in clean_features:
                # Skip title text in outline
                if title and feature["text"].strip().lower() == title.strip().lower():
                    continue
                    
                level = self.classify_heading_level(feature, font_thresholds)
                if level:
                    outline.append({
                        "level": level,
                        "text": feature["text"],
                        "page": feature["page"],
                        "position": feature.get("position", 0)
                    })
            
            # Post-process outline
            outline = self.post_process_outline(outline)
            
            return {
                "title": title or "Untitled Document", 
                "outline": outline
            }
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return {"title": "Untitled Document", "outline": []}

def process_all_pdfs(input_dir: str, output_dir: str):
    """Process all PDFs in input directory with enhanced error handling"""
    extractor = PDFOutlineExtractor()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory {input_dir} does not exist")
        return
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Processing {len(pdf_files)} PDF files...")
    
    for filename in pdf_files:
        try:
            pdf_path = os.path.join(input_dir, filename)
            result = extractor.extract_outline(pdf_path)
            
            output_filename = filename.rsplit('.', 1)[0] + ".json"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Processed: {filename} -> {output_filename} "
                  f"(Title: '{result['title']}', Headings: {len(result['outline'])})")
            
        except Exception as e:
            print(f"✗ Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    IN_DIR = "/app/input"
    OUT_DIR = "/app/output"
    process_all_pdfs(IN_DIR, OUT_DIR)
