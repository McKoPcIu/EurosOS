# Euros OS — instrukcja aktualizacji i cofnięcia

Status: projekt procedury, 13.11.2026. **Nie jest poleceniem wykonania aktualizacji teraz.** Właściciel instalacji musi osobno zatwierdzić okno serwisowe, zakres i możliwość restartu. Nie wykonywać kroków na fizycznej pompie ani nie zmieniać MQTT bez osobnej zgody.

## 1. Przygotowanie

1. Potwierdź docelowy commit, wersję wydania, `manifest.json` i pochodzenie `euros_os.zip` z oficjalnego repozytorium.
2. Utwórz świeżą, **pełną** kopię Home Assistant obejmującą konfigurację i Recorder. Pobierz ją poza HA. Zachowaj odpowiedni klucz odzyskiwania, ale **nie publikuj go**.
3. Zarchiwizuj bieżący katalog `/config/custom_components/euros_os` i zachowaj go osobno. Kopia starszego ETAPU 8 lub 9 nie jest automatycznie bezpiecznym rollbackiem do aktualnej instalacji.
4. Zapisz prywatny snapshot rejestrów `config_entries`, `entity_registry`, `device_registry` skryptem dostarczonym w `scripts/ha_registry_snapshot.py` albo równoważną metodą. Nie udostępniaj tych plików w GitHub.
5. Zapisz liczby i identyfikatory encji, urządzeń i statystyk Recorder; sprawdź dostęp do lokalnego sterowania pompą i dostępność osoby mogącej odtworzyć system.
6. Zweryfikuj, że żadne krytyczne automatyzacje grzewcze ani rozliczenia energii nie są aktywnie modyfikowane w wybranym oknie.
7. **Warunek STOP:** otwarte P1 TLS / poświadczenia, nieuzgodniona wersja HA lub brak aktualnego backupu oznaczają, że nie należy wgrywać nowego wydania.

## 2. Aktualizacja — wyłącznie po zatwierdzeniu

1. Zainstaluj zatwierdzony, podpisany/pochodzący z zaufanego źródła zasób `euros_os.zip`, zawierający pliki `__init__.py` i `manifest.json` w korzeniu ZIP.
2. Zachowaj istniejący wpis integracji. **Nie usuwaj urządzeń, encji, rejestrów ani bazy Recorder.**
3. Uruchom ponownie HA lub przeładuj wpis tylko jeśli jest to konieczne i zatwierdzone. Nie wyłączaj sterownika pompy.
4. Porównaj snapshot rejestrów: `entity_id`, `unique_id`, `device_id`, `via_device_id` i liczbę urządzeń. Różnice oznaczają STOP.
5. Zweryfikuj dostępność i aktualność GEO oraz EMS Dom; nie polegaj wyłącznie na statusie `available`.
6. Zweryfikuj dane energii i istnienie serii statystycznych przed i po aktualizacji; sprawdź poprawność jednostek i brak nieoczekiwanych skoków.
7. Zwróć uwagę na błędy TLS/SSL, reconnect, watchdog, wielokrotny setup/unload; nie wymuszaj awarii na rzeczywistej pompie.
8. Nie zmieniaj nastaw GEO dla samego testowania, zwłaszcza niezweryfikowanych przełączeń EMS.

## 3. Warunki przerwania / rollback

Natychmiast przerwij aktualizację w razie: utraty komunikacji z fizyczną pompą, nowych `unavailable` w kluczowych pomiarach, zniknięcia encji albo zmiany ich unikalnych identyfikatorów, błędów TLS po aktywacji weryfikacji, niestabilności Core lub nieprawidłowości liczników.

1. Nie usuwaj rejestru HA i nie twórz nowego wpisu z innym kluczem w miejsce poprzedniego.
2. Przywróć **świeżą kopię poprzedniego kodu** w wybranym, zatwierdzonym trybie, potem wykonaj wymagany restart/przeładowanie.
3. Jeżeli doszło do modyfikacji rejestrów lub historii, rozważ pełne odtworzenie kopii Home Assistant, świadomie oceniając utratę danych powstałych od momentu backupu.
4. Zweryfikuj odczyty GEO/EMS, liczbę encji i statystyki po cofnięciu. Udokumentuj zdarzenie i nie powtarzaj wdrożenia bez analizy przyczyny.

## 4. Historyczny punkt odniesienia, nie uniwersalna gwarancja

13.11.2026 w prywatnej instalacji operatora: HA Core 2026.11.1; GEO_1 i METER_1; 73 encje (38+35) i 2 urządzenia; brak różnic rejestru przed/po; 32 serie statystyczne EMS miały zapisy po obu stronach modyfikacji kodu. Są to wyniki **konkretnego środowiska**, a nie gwarancja bezstratnej aktualizacji innych instalacji.

Odnośniki: [ETAP 9.5](ETAP_9_5_PLAN_TESTOW_HA.md), [lista kontrolna RC](RELEASE_CANDIDATE_CHECKLIST.md).
