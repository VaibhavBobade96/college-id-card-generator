from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
import qrcode
import barcode
from barcode.writer import ImageWriter

from config import (
    CARD_OUTPUT_FOLDER,
    LOGO_PATH,
    PRINCIPAL_SIGN_PATH,
    FRONT_BG_PATH,
    BACK_BG_PATH,
    FONT_REGULAR,
    FONT_BOLD,
)
from database import Student, Card

# Card size
CARD_WIDTH = 920
CARD_HEIGHT = 520

WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
PURPLE = (120, 56, 161)
GREY_TEXT = (70, 70, 70)


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if Path(path).is_file():
        return ImageFont.truetype(path, size)
    return ImageFont.truetype("arial.ttf", size)


FONT_TITLE = load_font(FONT_BOLD, 26)
FONT_LABEL_BIG = load_font(FONT_BOLD, 28)   # college name ke liye label
FONT_LABEL = load_font(FONT_BOLD, 23)       # NAME , ADDRESS, CLASS, BLOOD GRP etc  LABEL
FONT_VALUE = load_font(FONT_REGULAR, 22)
FONT_SMALL = load_font(FONT_REGULAR, 16)
FONT_BACK_HEAD = load_font(FONT_BOLD, 24)
FONT_BACK_TEXT = load_font(FONT_REGULAR, 18)


def _load_optional(path: str, size: Tuple[int, int] | None = None) -> Image.Image | None:
    if not path or not Path(path).is_file():
        return None
    img = Image.open(path).convert("RGBA")
    if size:
        img = img.resize(size, Image.LANCZOS)
    return img


# ---------- FRONT SIDE ----------

def generate_front_image(student: Student, card: Card | None = None) -> Image.Image:
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), WHITE)
    d = ImageDraw.Draw(img)

    # Top purple strip
    strip_h = 113
    d.rectangle([0, 0, CARD_WIDTH, strip_h], fill=PURPLE)

    # Logo left
    logo = _load_optional(LOGO_PATH, size=(90, 90))
    if logo:
        img.paste(logo, (40, 15), logo)

    # College name + address
    # College name + address (thoda upar + center)
    college_lines = [
        "Mahatma Gandhi Mission's",
        "COLLEGE OF COMPUTER SCIENCE & IT",
        
    ]

    text_y = 14   # pehle 35 tha, thoda upar
    for line in college_lines:
        bbox = d.textbbox((0, 0), line, font=FONT_LABEL_BIG)
        w = bbox[2] - bbox[0]
        text_x = (CARD_WIDTH - w) // 2   # center in strip
        d.text((text_x, text_y), line, fill=WHITE, font=FONT_LABEL_BIG)
        text_y += 30

    # Strip ke bilkul niche small text (chhota font)
    small_text = "Near Airport, Nanded - 431605, Tel: (02462)-222592   Web: www.mgmccsit.ac.in"
    bbox = d.textbbox((0, 0), small_text, font=FONT_SMALL)
    w = bbox[2] - bbox[0]
    small_x = (CARD_WIDTH - w) // 2
    small_y = strip_h - 25    # strip ke bottom ke thoda upar
    d.text((small_x, small_y), small_text, fill=WHITE, font=FONT_SMALL)

    # Left side data (strip ke niche)
    left_margin = 50
    top_margin = strip_h + 40
    line_gap = 50

    # Name
    d.text((left_margin, top_margin), "Name:", fill=BLACK, font=FONT_LABEL)
    d.text(
        (left_margin + 130, top_margin),
        student.full_name,
        fill=BLACK,
        font=FONT_TITLE,
    )

    # Address block (multi-line)
    addr_lines = [student.address_line1, student.address_line2, student.address_line3]
    addr_y = top_margin + line_gap
    d.text((left_margin, addr_y), "Address:", fill=BLACK, font=FONT_LABEL)
    addr_text_y = addr_y
    for line in addr_lines:
        if line:
            d.text(
                (left_margin + 130, addr_text_y),
                line,
                fill=BLACK,
                font=FONT_VALUE,
            )
            addr_text_y += 26

    # Class
    y = addr_text_y + 10
    d.text((left_margin, y), "Class:", fill=BLACK, font=FONT_LABEL)
    d.text(
        (left_margin + 130, y),
        student.class_name or "",
        fill=BLACK,
        font=FONT_VALUE,
    )

    # DOB + Blood grp same row
    y += line_gap
    d.text((left_margin, y), "DOB:", fill=BLACK, font=FONT_LABEL)
    d.text(
        (left_margin + 130, y),
        student.dob or "",
        fill=BLACK,
        font=FONT_VALUE,
    )
    d.text((left_margin + 360, y), "Blood grp:", fill=BLACK, font=FONT_LABEL)
    d.text(
        (left_margin + 510, y),
        student.blood_group or "",
        fill=BLACK,
        font=FONT_VALUE,
    )

    # Contact + Year same row
    y += line_gap
    d.text((left_margin, y), "Contact:", fill=BLACK, font=FONT_LABEL)
    d.text(
        (left_margin + 130, y),
        student.contact_no or "",
        fill=BLACK,
        font=FONT_VALUE,
    )
    d.text((left_margin + 360, y), "Year:", fill=BLACK, font=FONT_LABEL)
    d.text(
        (left_margin + 480, y),
        student.year_text or "",
        fill=BLACK,
        font=FONT_VALUE,
    )

    # Photo right side
    photo_w, photo_h = 170, 205
    photo_x = CARD_WIDTH - photo_w - 70
    photo_y = strip_h + 40
    d.rectangle(
        [photo_x, photo_y, photo_x + photo_w, photo_y + photo_h],
        outline=BLACK,
        width=2,
    )
    if student.photo_path and Path(student.photo_path).is_file():
        photo = Image.open(student.photo_path).convert("RGB")
        photo = photo.resize((photo_w, photo_h), Image.LANCZOS)
        img.paste(photo, (photo_x, photo_y))

    # Principal sign
    principal_font = load_font(FONT_BOLD, 24)
    sign = _load_optional(PRINCIPAL_SIGN_PATH, size=(250, 90))
    sign_y = photo_y + photo_h + 10
    sign_x = photo_x + 20
    if sign:
        img.paste(sign, (sign_x, sign_y), sign)
    d.text(
        (photo_x + 50, sign_y + 55),
        "Principal",
        fill=BLACK,
        font=FONT_SMALL,
    )

    return img


# ---------- BACK SIDE ----------

def _generate_qr(data: str, size: int = 220) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.LANCZOS)


def _generate_barcode(data: str, width: int = 260, height: int = 60) -> Image.Image:
    code128 = barcode.get("code128", data, writer=ImageWriter())

    tmp = Path(CARD_OUTPUT_FOLDER) / f"tmp_bar{data}"
    code128.save(str(tmp))

    tmp_png = tmp.with_suffix(".png")
    img = Image.open(tmp_png).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)

    try:
        tmp_png.unlink()
    except FileNotFoundError:
        pass

    return img


def generate_back_image(student: Student, card: Card) -> Image.Image:
    base = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), WHITE)
    d = ImageDraw.Draw(base)

    top_h = 220  # upper white area

    # Background image bottom part
    bg = _load_optional(BACK_BG_PATH, size=(CARD_WIDTH, CARD_HEIGHT - top_h))
    if bg:
        base.paste(bg, (0, top_h))

    # Heading
    d.text((40, 40), "PLEASE NOTE", fill=BLACK, font=FONT_BACK_HEAD)

    # Rules text
    rules = [
        "1. The student should possess Identity Card and must produce whenever demanded.",
        "2. If it is lost, the card holder must intimate to the Principal",
        "   and apply for a new card within a week.",
        "3. If this card does not belong to you, please return it to :",
        "   The Principal, MGM's College of Comp. Sci. & IT, Nanded.",
    ]
    text_x = 40
    text_y = 80
    for line in rules:
        d.text((text_x, text_y), line, fill=BLACK, font=FONT_BACK_TEXT)
        text_y += 24

    # Barcode top-right
    bar_data = card.barcode_number or student.student_code
    bar_img = _generate_barcode(bar_data, width=260, height=60)
    bar_x = CARD_WIDTH - 260 - 40
    bar_y = 40
    base.paste(bar_img, (bar_x, bar_y))

    # Barcode number
   
    bbox = d.textbbox((0, 0), bar_data, font=FONT_SMALL)
    num_w = bbox[2] - bbox[0]
    d.text(
    (bar_x + (260 - num_w) // 2, bar_y + 65),
    bar_data,
    fill=BLACK,
    font=FONT_SMALL,
    )

    # QR code bottom center
    qr_size = 220
    qr_img = _generate_qr(card.qr_data or f"{student.student_code}", size=qr_size)
    qr_x = (CARD_WIDTH - qr_size) // 2
    qr_y = top_h + ((CARD_HEIGHT - top_h) - qr_size) // 2
    base.paste(qr_img, (qr_x, qr_y))

    return base


# ---------- PUBLIC API ----------

def generate_card_images(student: Student, card: Card) -> Tuple[str, str]:
    Path(CARD_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    front = generate_front_image(student, card)
    back = generate_back_image(student, card)

    front_path = Path(CARD_OUTPUT_FOLDER) / f"{student.student_code}_front.png"
    back_path = Path(CARD_OUTPUT_FOLDER) / f"{student.student_code}_back.png"

    front.save(front_path, format="PNG")
    back.save(back_path, format="PNG")

    card.front_image_path = str(front_path)
    card.back_image_path = str(back_path)

    return str(front_path), str(back_path)

