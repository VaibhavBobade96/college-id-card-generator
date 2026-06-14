from io import BytesIO
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from config import CARD_OUTPUT_FOLDER
from database import Student, Card
from services.id_card_generator import generate_card_images


# ----------------- A4 + Card Layout -----------------

A4_W, A4_H = A4

CARD_W = 260
CARD_H = 150

COLS = 2
ROWS = 5

MARGIN_X = 30
MARGIN_Y = 30
GAP_X = 10
GAP_Y = 10


# ----------------- Draw 10 cards on A4 -----------------

def draw_cards_on_page(c, images):
    x0 = MARGIN_X
    y0 = A4_H - MARGIN_Y - CARD_H

    i = 0
    for r in range(ROWS):
        for col in range(COLS):
            if i >= len(images):
                return

            img = ImageReader(images[i])

            x = x0 + col * (CARD_W + GAP_X)
            y = y0 - r * (CARD_H + GAP_Y)

            c.drawImage(img, x, y, CARD_W, CARD_H)
            i += 1


# ----------------- Duplex back re-order -----------------

def duplex_reorder(page):
    """
    Converts:
    [1,2,3,4,5,6,7,8,9,10]
    to
    [2,1,4,3,6,5,8,7,10,9]
    so duplex printing + cutting matches perfectly.
    """
    fixed = []
    for i in range(0, len(page), 2):
        if i + 1 < len(page):
            fixed.append(page[i + 1])
            fixed.append(page[i])
        else:
            fixed.append(page[i])
    return fixed


# ----------------- Build Final Batch PDF -----------------

def build_batch_pdf(students: Iterable[Student], cards: Iterable[Card]):
    Path(CARD_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    pdf_path = Path(CARD_OUTPUT_FOLDER) / "batch_cards.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)

    card_map = {c.student_id: c for c in cards}

    fronts = []
    backs = []

    # Generate all front & back images
    for student in students:
        card = card_map.get(student.id)
        if not card:
            continue

        f, b = generate_card_images(student, card)
        fronts.append(f)
        backs.append(b)

    # -------- FRONT PAGES (1–10, 11–20...) --------
    for i in range(0, len(fronts), 10):
        draw_cards_on_page(c, fronts[i:i + 10])
        c.showPage()

    # -------- BACK PAGES (Duplex Corrected) --------
    for i in range(0, len(backs), 10):
        page = backs[i:i + 10]
        page = duplex_reorder(page)
        draw_cards_on_page(c, page)
        c.showPage()

    c.save()

    # Load into memory for download
    buffer = BytesIO()
    with open(pdf_path, "rb") as f:
        buffer.write(f.read())
    buffer.seek(0)

    return buffer, str(pdf_path)