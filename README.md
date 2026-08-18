# 🧾 Zarządca Budżetu Domowego & Paragonów

Inteligentna, lekka aplikacja webowa do zarządzania wspólnymi wydatkami i rozliczania paragonów między współlokatorami z wykorzystaniem **Google Gemini AI**.

Działa bezproblemowo na domowym serwerze (np. **Raspberry Pi**) za tunelem **Cloudflare Tunnel**, oferując interfejs zoptymalizowany pod kątem telefonów (Mobile-First) oraz automatyczne wdrażanie zmian przez **GitHub Actions (CI/CD)**.

---

## ✨ Główne Funkcje

* 🤖 **Automatyczny odczyt paragonów (Gemini AI)** – wystarczy zrobić zdjęcie aparatem w telefonie lub wgrać plik, a model AI wyodrębni nazwę sklepu, datę zakupu oraz listę produktów wraz z cenami i ilością.
* ⚖️ **Automatyczny bilans współlokatorów (T / O / K)** – system na bieżąco oblicza łączną sumę wydatków, udział każdego lokatora (1/3) oraz wylicza dokładne kwoty: kto, komu i ile powinien przelać.
* 📱 **Mobile-First UI** – natywny dolny pasek nawigacji (*Bottom Nav*), wygodne karty produktów z dotykowym zaznaczaniem, bezpośrednia integracja z aparatem telefonu oraz wysuwane modale w stylu *Bottom Sheet*.
* 🛡️ **Bezpieczeństwo & Ochrona przed botami**:
  * Logowanie zabezpieczone silnym hasłem i tokenami JWT w ciasteczkach `HttpOnly`.
  * **Rate Limiter (SlowAPI)** z obsługą nagłówków `CF-Connecting-IP` / `X-Forwarded-For` – blokuje ataki brute-force (`429 Too Many Requests`).
  * Wszystkie sekrety i klucze API odseparowane w pliku `.env`.
* ⚡ **Wysokowydajny SQLite (WAL Mode)** – tryb *Write-Ahead Logging* zapewniający brak blokad bazy przy jednoczesnych zapytaniach od wielu osób.

---

## 🏗️ Architektura Projektu

```text
zarzadzca/
├── config/             # Konfiguracja bazy danych, bezpieczeństwa i rate limitera
│   ├── database.py     # Połączenie SQLAlchemy, obsługa SQLite WAL i Foreign Keys
│   ├── limiter.py      # Konfiguracja SlowAPI z wykrywaniem IP Cloudflare
│   └── security.py     # Autoryzacja JWT, haszowanie i weryfikacja sesji
├── controller/         # Warstwa kontrolera FastAPI
│   └── controller.py   # Obsługa endpointów API i serwowanie widoków
├── entity/             # Modele ORM bazy danych (SQLAlchemy)
│   ├── elementy.py     # Tabela pozycji z paragonu
│   └── rachunek.py     # Tabela paragonów
├── models/             # Schematy walidacji danych (Pydantic DTO)
│   ├── auth.py         # Modele logowania
│   └── receipt.py      # Modele zapisu i odczytu paragonów z AI
├── service/            # Logika biznesowa i integracje
│   └── ai.py           # Integracja z Google Gemini API
├── static/             # Frontend aplikacji
│   └── index.html      # Responsywny interfejs SPA (Mobile & Desktop)
├── uploads/            # Zapisane zdjęcia paragonów
├── .env.example        # Szablon zmiennych środowiskowych
├── .gitignore          # Reguły ignorowania plików (sekrety, baza, zdjęcia)
├── bombard.py          # Skrypt testów obciążeniowych Rate Limitera
├── requirements.txt    # Zależności Pythona
└── run.py              # Punkt startowy aplikacji (Uvicorn)
```

---

## 🚀 Szybki Start (Lokalnie / Serwer)

### 1. Klonowanie repozytorium i instalacja zależności
```bash
git clone https://github.com/twoj-user/zarzadzca.git
cd zarzadzca

# Utworzenie wirtualnego środowiska
python -m venv .venv

# Aktywacja środowiska:
# Linux/macOS:
source .venv/bin/activate
# Windows:
.\.venv\Scripts\activate

# Instalacja bibliotek:
pip install -r requirements.txt
```

### 2. Konfiguracja zmiennych środowiskowych
Skopiuj plik `.env.example` do `.env` i uzupełnij klucze:
```bash
cp .env.example .env
```

Przykładowa zawartość `.env`:
```env
# Google Gemini API
GEMINI_API_KEY=twoj_klucz_api_gemini
GEMINI_MODEL=gemini-3.1-flash-lite

# Bezpieczeństwo i autoryzacja
APP_PASSWORD=twoje_bezpieczne_haslo
JWT_SECRET=twoj_losowy_klucz_jwt_secret

# Rate Limiting
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_AI=10/minute

# Baza danych
DATABASE_URL=sqlite:///./zarzadzca.db

# Serwer
HOST=127.0.0.1
PORT=8005
```

### 3. Uruchomienie aplikacji
```bash
python run.py
```
Aplikacja będzie dostępna pod adresem: `http://127.0.0.1:8005`.

---

## 🔄 Automatyzacja Wdrożenia (GitHub Actions CI/CD)

Projekt wspiera w pełni zautomatyzowane wdrażanie na domowy serwer (np. Raspberry Pi) przy każdym `git push` do gałęzi `main`.

### Jak to działa?
1. Programista wykonuje `git push origin main`.
2. **GitHub Actions** uruchamia workflow `.github/workflows/deploy.yml`.
3. GitHub łączy się z serwerem
4. Serwer pobiera najnowszą wersję kodu (`git pull`), instaluje ewentualne nowe pakiety (`pip install -r requirements.txt`) i restartuje usługę systemową