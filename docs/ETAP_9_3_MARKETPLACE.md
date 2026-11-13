# Euros OS — ETAP 9.3.9: HACS / Marketplace i bezpieczna aktualizacja

**Stan na 2026-11-12: test archiwum i metadanych zaliczony; zadanie 9.3.9 NADAL OTWARTE.**

## Potwierdzone fakty

- Integracja ma katalog `custom_components/euros_os/` i plik `hacs.json` w korzeniu repozytorium.
- `hacs.json` deklaruje `domain: euros_os`, `zip_release: true`, `filename: euros_os.zip` i `iot_class: local_push`. To oznacza, że każda wydana wersja musi mieć dołączony zasób o dokładnej nazwie `euros_os.zip`; Marketplace rozpakowuje ZIP bezpośrednio do folderu integracji.
- Archiwum wydania musi więc mieć pliki takie jak `manifest.json` i `__init__.py` **w korzeniu ZIP**, a katalog `translations/` wewnątrz archiwum; NIE może mieć dodatkowego prefiksu `custom_components/euros_os/`.
- Upstream `McKoPcIu/EurosOS` ma co najmniej wydania `v0.1.0`, `v0.1.1`, `v0.1.1-hotfix`, `v0.1.2` z zasobami `euros_os.zip`. Ostatni sprawdzony asset `v0.1.2` ma rozmiar 14712 bajtów. Fork BudrysLP nie miał własnych wydań w chwili audytu.
- **Niespójność do rozstrzygnięcia z autorem:** `manifest.json` w gałęzi rozwojowej ma `version: 0.1.0`, podczas gdy ostatni tag upstream to `v0.1.2`. Zmiana numeru jest decyzją autora na etapie wydania; nie publikujemy wersji pod przypadkowym numerem.
- **Niespójne minimalne HA:** `hacs.json` wskazuje `2021.12.0`, a istniejący `README.md` mówi `HA >= 2023.3`. Testy automatyczne odbyły się na Pythonie 3.12/3.13/3.14, ale NIE potwierdzają zgodności ze starymi wydaniami HA. Nie zmieniono deklaracji minimalnego HA przed testami lub uzgodnieniem wsparcia. Home Assistant 2026.11 ma wbudowany Marketplace, a stary HACS jest migrowany.
- Nie wykonano aktualizacji działającej instalacji HA, pełnej aktualizacji przez Marketplace ani wydania w upstream.

## Wprowadzone zmiany w gałęzi development

- `scripts/build_release_zip.py`: bezpieczny generator płaskiego archiwum z plików `custom_components/euros_os`. Przed zapisem kontroluje domenę, obecność najważniejszych plików i lokalizacji, usuwa pliki robocze (`__pycache__`, `.pyc`), nie czyta plików HA i nie publikuje GitHub Release.
- `tests/test_release_packaging.py`: testy struktury archiwum, zgodności bajtów ze źródłami, deklaracji `hacs.json` i braku plików produkcyjnych.
- `.github/workflows/euros-os-stage4-tests.yml`: po testach regresyjnych wykonuje `python scripts/build_release_zip.py --output /tmp/euros_os.zip`. ZIP zostaje wyłącznie w środowisku runnera; nie ma automatycznej publikacji.
- W CI [run 43209612693](https://github.com/BudrysLP/EurosOS/actions/runs/43209612693) testy automatyczne **137/137** oraz testowe archiwum zawierające **15 plików integracji** zaliczyły się na Pythonie 3.12.16, 3.13.18 i 3.14.10.

## Procedura końcowej aktualizacji (PROJEKT — bez wykonywania teraz)

1. Uzgodnić z autorem numer wersji release i zakres wspieranych wersji HA, zsynchronizować `hacs.json`, `README.md` i `manifest.json`. Nie usuwać historycznych wydań.
2. Przygotować odpowiednio nazwany asset `euros_os.zip` z **tego samego commitu**, który przeszedł wszystkie testy. Przed dołączeniem release sprawdzić manifest/ZIP oraz zgodność lokalizacji plików.
3. Przed aktualizacją istniejącej instalacji HA: pełna kopia zapasowa, lokalna kopia `/config/custom_components/euros_os`, zapis `entity_id`, `unique_id`, `device_id` i stanów licznika energii.
4. W kontrolowanym środowisku testowym sprawdzić instalację/aktualizację przez Marketplace, czy wersja jest oferowana prawidłowo, czy w przypadku zmiany wersji HA jest zgodny komunikat oraz czy integracja uruchamia się bez błędów.
5. Po aktualizacji w rzeczywistym HA sprawdzić dotychczasowe 73 identyfikatory i wartości, historię energii, zgodność urządzeń GEO_1 i EMS Dom, poprawność rollbacku i zachowanie sterowania.
6. Dopiero po zatwierdzeniu przez użytkownika oraz autorze release udostępnić wydanie w jego repozytorium. **Nie wolno instalować na działającym HA ani otwierać PR bez odrębnego polecenia.**

## Pozostałe blokady

- Brak testu Marketplace z *rzeczywistym* Home Assistant Core 2026.11 i archiwum końcowej wersji (9.5/9.3.9).
- Brak decyzji o minimalnej wersji HA; obecne deklaracje są niespójne.
- Otwarty punkt bezpieczeństwa 9.2.5 — broker TLS z lokalnym samopodpisanym CA i SAN niedopasowanym do bieżącego IP.
- Zgodność API `SensorEntity`, `NumberEntity`, `SelectEntity`, `RestoreSensor` z prawdziwym HA nadal wymaga testów 9.3.4/9.3.8.
- Decyzja o dalszym losie otwartego PR #3 przed złożeniem jednego nowego końcowego PR.

## Dokumentacja producenta

- Marketplace ZIP release: https://contributors.home-assistant.io/marketplace/guides/releases/
- Metadane hacs.json: https://contributors.home-assistant.io/marketplace/reference/hacs-json/
- Format repozytorium: https://contributors.home-assistant.io/marketplace/guides/integrations/
- Migracja HACS: https://www.home-assistant.io/integrations/marketplace
