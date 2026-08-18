import io
import os
import logging
import traceback
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from dotenv import load_dotenv

from models.receipt import Item, ReceiptData
from config.logger import get_logger

load_dotenv()

logger = get_logger("zarzadzca.ai")




def analyze_receipt(image_bytes: bytes) -> ReceiptData:
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Brak zmiennej GEMINI_API_KEY w pliku .env!")
        client = genai.Client(api_key=api_key)


        image = Image.open(io.BytesIO(image_bytes))
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        if image.mode != "RGB":
            image = image.convert("RGB")

        prompt = """
        Przeanalizuj dołączone zdjęcie paragonu. 
        Wyodrębnij nazwę sklepu, datę zakupu, pełną listę kupionych produktów wraz z ich cenami i ilością, oraz łączną sumę.
        Zwróć wynik wyłącznie w formacie JSON zgodnym z podanym schematem.
        """

        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        logger.info(f"🚀 Wysyłanie zapytania do modelu: '{model_name}'...")
        
        response = client.models.generate_content(
            model=model_name,
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReceiptData,
            ),
        )

        logger.info(f"✅ Sukces odczytu z modelu '{model_name}'!")
        
        if hasattr(response, 'parsed') and response.parsed:
            return response.parsed
        
        return ReceiptData.model_validate_json(response.text)

    except Exception as e:
        logger.error(f"❌ Wyjątek w analyze_receipt: {e}")
        traceback.print_exc()
        raise RuntimeError(f"Błąd analizy AI: {str(e)}")