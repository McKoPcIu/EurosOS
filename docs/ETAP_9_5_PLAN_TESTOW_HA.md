# Euros OS — ETAP 9.5: plan bezpiecznej kontroli na rzeczywistym Home Assistant

**Data planu:** 12 listopada 2026 r.  
**Status:** plan i narzędzie porównawcze gotowe; **12 listopada 2026 r. użytkownik potwierdził pierwszy udany odczyt bazowy rejestrów produkcyjnego HA: 73 encje, 2 urządzenia**. Nie wykonywano nowego wdrożenia, restartu ani porównania po aktualizacji.  
**Gałąź przygotowania:** `feature/stage9-ha-validation`, na podstawie `feature/stage9-tests`.  
**Zasada nadrzędna:** żadnego wgrywania plików, restartowania Home Assistant, wyłączania MQTT, zmieniania parametrów pompy ani modyfikowania rejestrów HA bez odrębnej, świadomej zgody operatora.

## A. Potwierdzony punkt odniesienia i jego ograniczenia

- W **ETAPIE 8 (9 listopada 2026)** użytkownik przeprowadził kontrolowany test działającego Home Assistant Core 2026.11.0, z pompą `GEO_1` oraz licznikiem `EMS – Dom / METER_1`. Udokumentowano **2 urządzenia i 73 encje** (38 pompy + 35 EMS), a porównanie `entity_id`, `unique_id` i `device_id` nie wykazało zmian względem wcześniejszej konfiguracji.
- Kod wcześniej wdrożony w HA wskazano jako commit `12d2502091d2364e7cb1803eef3bd523a31618de` (`feature/stage8-ha-preflight`). **Nie weryfikowaliśmy tego ponownie bezpośrednim odczytem z HA 12 listopada**; sam numer wersji `manifest.json = 0.1.0` nie identyfikuje jednoznacznie commitu.
- W ETAPIE 8 użytkownik wykonał pełną kopię zapasową HA i archiwa integracji/rejestrów. **Te archiwa są historyczne. Przed jakimkolwiek nowym wdrożeniem konieczny jest świeży backup aktualnie działającego środowiska i świeża kopia jego katalogu integracji.** Archiwum sprzed ETAPU 8 nie może być bezpośrednim rollbackiem do obecnego stanu.
- Zielone [testy ETAPU 9.4](ETAP_9_4_TESTY_AUTOMATYCZNE.md) obejmują 154 testy symulacyjne na każdej z wersji 3.12/3.13/3.14, 6 testów z rzeczywistym Core 2026.11.0 i sztucznym MQTT. **Nie są testem fizycznej pompy.**
- Problem bezpieczeństwa TLS `9.2.5` nadal jest **P1** (niedopasowanie IP w SAN i lokalny niezaufany Root CA). Etap 9.3.9 Marketplace pozostaje otwarty. Test na produkcji nie rozwiązuje tych problemów sam z siebie.

## B. Główne bramki przed jakąkolwiek ingerencją

**9.5.1 — Kopie zapasowe / ZAKOŃCZONE NA PODSTAWIE POTWIERDZENIA OPERATORA 12.11.2026**

**Potwierdzenie archiwum integracji:** użytkownik utworzył 12.11.2026 o 18:17 prywatne archiwum `/config/euros_os_stage9_private/euros_os_before_stage9_20261112.tar.gz` o rozmiarze **66,5 KB** (wynik `ls -lh`). Zrzut terminala potwierdza zakończenie bez błędów poleceń `tar -czf`, `tar -tzf` i sprawdzenia katalogu. Archiwum powstało z aktualnego `/config/custom_components/euros_os` z `umask 077`; wynik uprawnień `-rw-------`. To zabezpiecza kod integracji, ale nie dowodzi samodzielnie zawartości ani możliwości przywrócenia pełnego backupu HA. Warto również przechować ten niewielki plik poza HA. **Operator potwierdził posiadanie klucza Emergency Kit oraz że pobrana na komputer pełna kopia HA 1,2 GB obejmuje konfigurację i historię.** Punkt 9.5.1 zamknięty na podstawie tego potwierdzenia; **nie przeprowadzano próby odtworzenia** całego HA. Archiwum katalogu integracji zostało zapisane lokalnie; warto także przechowywać je poza HA.

Na podstawie zrzutu ekranu Home Assistant użytkownik potwierdził, że na liście automatycznych backupów widoczne są **trzy** kopie, w tym najnowsza „Automatic backup 2026.11.1”, **1,2 GB**, oznaczona jako utworzona „2 minuty temu” w chwili zrzutu; starsze to „Automatic backup 2026.11.1” (1,15 GB, „9 godzin temu”) i „Automatic backup 2026.11.0” (1,13 GB, „wczoraj”). Zrzut potwierdza istnienie *wpisów* i wyświetlane rozmiary. Użytkownik następnie potwierdził pobranie najnowszej kopii na komputer. Operator potwierdził pełny zakres (konfiguracja i historia) oraz posiadanie klucza szyfrowania; osobne archiwum aktualnej integracji zostało zapisane i sprawdzone przez `tar -tzf`. Nie wykonywano technicznej próby pełnego odtworzenia.

**Przesłanki zaliczenia 9.5.1:** pobranie pełnej kopii poza HA (potwierdzone), zakres obejmujący konfigurację i historię (potwierdzony przez operatora), dostępność Emergency Kit (potwierdzona), aktualne archiwum katalogu integracji 66,5 KB z poprawną kontrolą `tar -tzf` (potwierdzone). Nie stanowi to wyniku próbnego odtwarzania kopii ani zgody na instalację, restart lub ingerencję w pompę. Kopie należy odświeżyć, jeśli konfiguracja zmieni się przed wdrożeniem.



1. Na HA przejść do **Ustawienia → System → Kopie zapasowe** i wykonać NOWĄ pełną kopię, obejmującą aktualną konfigurację i historię Recorder (w przypadku zewnętrznej bazy osobny backup danych).
2. Pobrać backup poza urządzenie HA, sprawdzić niezerowy rozmiar i zachować właściwy **emergency kit / klucz szyfrowania** w bezpiecznej lokalizacji. Nie publikować backupu i klucza ani nie załączać ich do GitHub, zgłoszeń czy rozmów.
3. Stworzyć dodatkową prywatną kopię **aktualnego** `/config/custom_components/euros_os/`, z której można cofnąć *wyłącznie integrację*.
4. Upewnić się, że na docelowym HA jest wolne miejsce, znamy sposób dostępu awaryjnego i istnieje metoda przywrócenia kopii.
5. Po wykonaniu przez operatora potwierdzić: datę, lokalizację prywatnej kopii oraz istnienie klucza. **Nie odnotowywać klucza ani ścieżki ujawniającej dane osobowe w publicznym repo.**

Oficjalne źródła: https://www.home-assistant.io/common-tasks/general/backups i https://www.home-assistant.io/more-info/backup-emergency-kit .

**9.5.2 — Decyzja operatora / NIE UZGODNIONO**

- Wybrać okno serwisowe, sprawdzić brak krytycznych automatyzacji grzewczych w tym czasie oraz dostęp do lokalnej obsługi pompy.
- Preferować osobną instancję HA. Gdy to niemożliwe, użytkownik musi zaakceptować ryzyko restartu produkcyjnego Home Assistant.
- Najpierw uzgodnić, czy testujemy wyłącznie odczyty i dostępność. Domyślna odpowiedź: **TAK**, bez komend MQTT zmieniających nastawy.
- Potwierdzić konkretny SHA kodu po zakończeniu etapów oraz wcześniej uzgodnione otwarte problemy. Sam zielony test CI nie zastępuje decyzji operatora.
- **Do zgody:** nie kopiować kodu na HA, nie tworzyć testowego wpisu integracji w produkcji, nie dotykać .storage ani historii, nie restartować.

## C. Inwentaryzacja 73 encji — prywatne narzędzie

Narzędzie `scripts/ha_registry_snapshot.py` odczytuje wyłącznie `/config/.storage/core.config_entries`, `core.entity_registry` i `core.device_registry`. **Nie edytuje tych plików.** Tworzy prywatne zestawienie identyfikatorów, bez haseł, IP, pełnych wpisów konfiguracyjnych, stanów pompy ani surowych danych MQTT.

- Dane zapisuje **wyłącznie w prywatnym pliku lokalnym**, utworzonym z uprawnieniami `0600`, bez nadpisywania istniejącego snapshotu.
- Wymaga 73 encji i 2 urządzeń (parametry są jawne) — inne liczby zgłasza jako **STOP** i nie zapisuje snapshotu, do wyjaśnienia przyczyny.
- Klucz identyfikacji encji: **(domena encji, platforma integracji, unique_id)**, ponieważ niektóre ciągi `unique_id` mogą występować poprawnie w różnych domenach.
- Porównuje zbiór encji, niezmienność `entity_id`, `device_id`, liczbę i ID urządzeń oraz powiązanie `via_device_id`.
- Wyświetla *wyłącznie liczby różnic*, nie pełne identyfikatory, hasła, dane adresowe lub surowe rekordy.
- Wykryta różnica oznacza kod wyjścia **2** i blokadę akceptacji; błędny odczyt/rejestr oznacza kod **1**. Brak różnic: **0**.
- Przed i po aktualizacji trzeba osobno stworzyć snapshoty z różnymi nazwami. Nie umieszczać tego katalogu w repozytorium ani nie udostępniać plików na czacie.

**Tylko po odrębnej zgodzie:** skopiować zweryfikowaną wersję skryptu do prywatnego folderu w `/config`, np. `/config/euros_os_stage9_private/`, i uruchomić:

```sh
python3 /config/euros_os_stage9_private/ha_registry_snapshot.py capture \
  --config /config \
  --output /config/euros_os_stage9_private/before.json
```

Po zatwierdzonym wdrożeniu i nowym odczycie:

```sh
python3 /config/euros_os_stage9_private/ha_registry_snapshot.py capture \
  --config /config \
  --output /config/euros_os_stage9_private/after.json

python3 /config/euros_os_stage9_private/ha_registry_snapshot.py compare \
  --before /config/euros_os_stage9_private/before.json \
  --after /config/euros_os_stage9_private/after.json
```

Są to **instrukcje na przyszłość**; niczego teraz nie uruchomiono. Jeśli wewnętrzny format rejestrów zmienił się w HA, narzędzie ma przerwać pracę, a nie modyfikować pliki. Przed właściwym porównaniem HA nie należy tworzyć ani usuwać encji niezwiązanych z testem.

Testy syntetyczne: `tests/test_ha_registry_snapshot.py` oraz zestaw CI gałęzi 9.5.

## C.1. Korekta narzędzia snapshot — 12 listopada 2026

Podczas pierwszego **odczytu bez zmian w HA** operator zgłosił `STOP: ValueError: An Euros OS entity has incomplete registry identity`. Skrypt zatrzymał się w pamięci podczas budowania zestawienia; `before.json` **nie został zapisany**. Nie stwierdzono na tej podstawie awarii ani uszkodzenia encji. Przyczynę ustalono w źródłach Home Assistant Core 2026.11.0: `core.entity_registry` zapisuje `entity_id`, `platform`, `unique_id` i `config_entry_id`, ale **bez osobnego pola `domain`**. Ponadto aktualny `core.device_registry` używa `config_entry_id` w urządzeniu, a nie starego `config_entries`.

Skrypt `scripts/ha_registry_snapshot.py` poprawiono:
- domena wyprowadzana z `entity_id` (część przed pierwszą kropką), z walidacją i odrzucaniem sprzecznych danych;
- urządzenia przypisywane przez `config_entry_id` (HA 2026.11), z bezpiecznym odczytem starszego wariantu `config_entries`;
- nadal wyłącznie czyta `.storage`, zapisuje prywatny snapshot tylko przy spodziewanych **73 encjach i 2 urządzeniach** oraz nie udostępnia prywatnych identyfikatorów.

Przebudowano syntetyczne fixture'y tak, by odwzorowywały rzeczywisty format zapisu HA 2026.11. Dodano 4 testy dla nowego, starszego i błędnego formatu. Testy lokalnych kopii w CI **nie zastępują** ponownego uruchomienia na HA użytkownika.

Po zielonym CI operator powinien ponownie pobrać poprawiony skrypt do tego samego prywatnego folderu, wykonać `python3 -m py_compile`, a następnie ponowić polecenie `capture` **tylko jeśli nie ma już pliku `before.json`**. Nie usuwać i nie nadpisywać istniejących snapshotów bez ustalenia ich pochodzenia. Nie przekazywać pliku `before.json`, haseł, danych pomp i `.storage` do rozmowy ani repozytorium.

Źródło techniczne:
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_registry.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/device_registry.py

## C.2. Udany odczyt bazowy 12 listopada 2026

Po poprawce skryptu operator wykonał w terminalu Home Assistant:

```sh
python3 /config/euros_os_stage9_private/ha_registry_snapshot.py capture --config /config --output /config/euros_os_stage9_private/before.json
```

Potwierdzony komunikat: `Private baseline saved: 73 entities, 2 devices.`

**Wniosek:** prywatny plik `before.json` został utworzony, a narzędzie odczytało 73 encje i 2 urządzenia oraz przeszło swoje podstawowe kontrole tożsamości rejestrowej. Nie odczytano pliku zdalnie i nie należy go kopiować do GitHub ani na czat. Komunikat nie potwierdza jeszcze zachowania tej tożsamości *po aktualizacji*, funkcjonowania wszystkich encji ani bieżącego SHA faktycznie zainstalowanej integracji.

**Nie tworzyć drugiego `before.json` i nie nadpisywać istniejącego pliku.** Archiwum katalogu `euros_os`, klucz odzyskiwania i zakres pełnej kopii zostały potwierdzone. Przed jakimkolwiek wdrożeniem nadal trzeba zidentyfikować obecnie działający kod, uzgodnić zakres testów i uzyskać osobną zgodę operatora. Żaden restart ani wdrożenie nie nastąpił przy tym odczycie.

## C.3. Weryfikacja kodu działającej integracji — 12 listopada 2026

Użytkownik wykonał **read-only porównanie SHA-256** 4 kluczowych plików obecnie zainstalowanych w `/config/custom_components/euros_os/` z ich odpowiednikami w commicie
`12d2502091d2364e7cb1803eef3bd523a31618de` (ETAP 8).

| Plik | Wynik |
| --- | --- |
| `__init__.py` | **SHA-256 zgodny** |
| `coordinator.py` | **SHA-256 zgodny** |
| `sensor.py` | **SHA-256 zgodny** |
| `manifest.json` | **SHA-256 zgodny** |

Wniosek z pierwszej kontroli: wszystkie cztery wskazane pliki były identyczne bajt po bajcie z ETAPEM 8. **Kontrolę rozszerzono na cały katalog**: użytkownik odczytał archiwum commitu `12d2502091d2364e7cb1803eef3bd523a31618de` i porównał każdą z 15 zawartości plików z `/config/custom_components/euros_os`. Wynik: **15/15 zgodnych; brakujące: []; zmienione: []; dodatkowe: []** (z pominięciem generowanych `__pycache__` i plików `.pyc`). To potwierdza zgodność całej *źródłowej zawartości integracji* z commitem ETAPU 8, a nie tylko czterech plików. Nie stanowi jeszcze zezwolenia na aktualizację ani dowodu poprawności wersji rozwojowej. **HA9-01 zaliczono; 9.5.2 (zakres i okno serwisowe) pozostaje otwarty.**

Nie wprowadzono zmian ani nie restartowano HA, nie zlecając jeszcze aktualizacji.

## D. Scenariusze na rzeczywistym HA — do wykonania po zgodzie

| Kod | Kroki | Kryterium zaliczenia | Status |
| --- | --- | --- | --- |
| HA9-01 | Przed zmianą: snapshot rejestru i wersja HA | 73/73 encje, 2 urządzenia, kopia prywatna, znany SHA aktualnego kodu | **ZALICZONE:** snapshot 73/2, zabezpieczenia 9.5.1 i porównanie 15/15 plików z commitem `12d2502091d2364e7cb1803eef3bd523a31618de`. Nadal wymagana osobna zgoda na wdrożenie |
| HA9-02 | Po instalacji: setup GEO_1 i METER_1 | 2 urządzenia, 38+35 encji, żadnej zmiany ID, brak duplikatów | ⏳ NIE WYKONANO |
| HA9-03 | Po instalacji: odczyty GEO | Temperatury, tryb, stany pomp, CWU i FW prawidłowe i dostępne, bez fikcyjnych zer | ⏳ NIE WYKONANO |
| HA9-04 | Po instalacji: EMS Dom | Moc, import/eksport i 2 liczniki dzienne są aktualne, nie mieszają danych pompy i domu | ⏳ NIE WYKONANO |
| HA9-05 | Ciągłość historii | Recorder i Panel Energia mają ciągłość starych entity_id i naturalne narastanie energii; bez błędnych resetów | ⏳ NIE WYKONANO |
| HA9-06 | Przywrócenie dostępności po przerwie MQTT | Bezpieczna próba na nieprodukcyjnym brokerze/fixture lub pasywna obserwacja; brak wymuszonego odłączenia pracującej pompy | ⏳ NIE WYKONANO |
| HA9-07 | Restart HA Core | Tylko po wyraźnej zgodzie: poprawny restart i brak nowych entity_id, właściwy restore energii | ⏳ NIE WYKONANO |
| HA9-08 | Logi i bezpieczeństwo sterowania | Brak ERROR/traceback integracji, zmiany parametrów wyłącznie świadome; nie wysyłamy testowych komend pompie | ⏳ NIE WYKONANO |
| HA9-09 | Rollback | Gotowy i zweryfikowany plan powrotu do poprzedniej wersji; samego rollbacku NIE wykonujemy, o ile nie wystąpi powód | ⏳ NIE WYKONANO |

## E. STOP / rollback: reakcja na problemy

**Przerwać test** i uruchomić procedurę wycofania, jeżeli:
- GEO_1 lub METER_1 znika, odczyty są nieprawidłowe albo urządzenie nie przyjmuje normalnych aktualizacji,
- zmienił się choć jeden historyczny `entity_id`, `unique_id`, `device_id` lub relacja pompa → licznik bez świadomej migracji,
- system rejestruje zduplikowane encje, błędne/przedwczesne resety energii, utratę historii lub nietypowe wzrosty,
- w logach są trwałe błędy integracji, wątku MQTT, importu lub restartu,
- pojawia się niezamierzona próba sterowania pompą albo brak możliwości bezpiecznego zakończenia testu.

**Rollback minimalny**, wyłącznie przez operatora we wcześniej zatwierdzonym oknie:

1. Zatrzymać test i zachować komunikaty błędów po usunięciu danych wrażliwych.
2. **Nie usuwać wpisu integracji, wpisów rejestru encji ani historii Recorder.**
3. Przywrócić z prywatnego archiwum najnowszy, wcześniej działający katalog `/config/custom_components/euros_os`. Nie przywracać automatycznie archiwum sprzed ETAPU 8!
4. Zrestartować wyłącznie HA Core, jeśli jest to niezbędne do wczytania przywróconego kodu i operator zatwierdzi ten krok.
5. Po restarcie porównać 73 identyfikatory i podstawowe pomiary, upewnić się, że historia pozostała powiązana.
6. Pełne przywrócenie HA OS/backup rozważać tylko jeśli nie działa rollback katalogu — pełny restore może cofnąć *inne* zmiany i historię powstałe po zrobieniu kopii.

## F. Lista nieprzetestowanych scenariuszy sprzętowych — zadanie 9.5.7

| Scenariusz | Co wiemy | Czego nie potwierdzono |
| --- | --- | --- |
| Fizyczny GEO_1 + EMS Dom | W ETAPIE 8 były testowane 2 urządzenia / 73 encje. Etap 9.4 przetestował analogiczne fixture. | Wdrożenie nowej gałęzi z ETAPU 9 w fizycznym HA. |
| FriskoATMO | Logika jest w testach jednostkowych i symulacjach MQTT. | Rzeczywisty sterownik i komplet jego encji. |
| FriskoALLINONE | Scenariusze bez licznika są w symulacjach. | Rzeczywiste urządzenie, poszczególne warianty i firmware. |
| METER_2 / METER_3 | Symulowana jest niezależna telemetria, unikanie duplikatów i poprawne METER_N. | Fizyczny dodatkowy licznik, nazwy i zakres pól telemetrii. |
| Awaria broker MQTT | Stale, reconnect i wyścigi są przetestowane z atrapami. | Rzeczywista awaria/odbudowa łączności, której nie wolno wywoływać na pompie bez oceny ryzyka. |
| TLS 9.2.5 | Na rzeczywistej pompie potwierdzono CA samopodpisane oraz niezgodne IP w SAN. | Niezależnie zweryfikowany certyfikat CA i bezpieczny model uwierzytelniania/rotacji. |
| Marketplace 9.3.9 | ZIP testowany w CI (15 plików). | Rzeczywista instalacja i aktualizacja tej gałęzi z zachowaniem ID w HA. |
| Sterowanie modelem GEO | W ETAPIE 8 kontrolki były obserwowane i wypróbowane przez użytkownika; w 9.4 działa symulacja. | Całościowe potwierdzenie odpowiedzi pompy dla każdej komendy, zwłaszcza przejść AUTO↔EMS; nie zmieniać ich bez osobnego planu. |

**9.5.7 można uznać za ukończone jako obowiązek dokumentacyjny. Nie oznacza to potwierdzenia tych scenariuszy sprzętowo.**

## G. Kryteria ukończenia 9.5 i dalej

9.5.8 może zostać zaliczone dopiero po:
1. Świeżym i zabezpieczonym backupie, za zgodą operatora na wdrożenie.
2. Rzeczywistym porównaniu rejestrów 73 encji i 2 urządzeń przed/po.
3. Stabilnych odczytach GEO/EMS oraz historii energii po ewentualnym restarcie.
4. Przeglądzie logów i dokumentacji nieprzetestowanych przypadków.
5. Gotowym sprawdzonym planie powrotu do działającego kodu i rozstrzygnięciu blokad wydania (m.in. TLS P1).

**Ograniczenie:** dopóki operator nie potwierdzi okna testowego, bieżących kopii i zgody na instalację, wszystkie rzeczywiste testy pozostają otwarte.

## Źródła

- Oficjalne backupy: https://www.home-assistant.io/common-tasks/general/backups
- Klucz szyfrowania: https://www.home-assistant.io/more-info/backup-emergency-kit
- Logi i troubleshooting: https://www.home-assistant.io/docs/configuration/troubleshooting/
- Poprzedni [plan ETAPU 8](ETAP_8_PLAN_TESTOW_HA.md)
- CI/testy [ETAP 9.4](ETAP_9_4_TESTY_AUTOMATYCZNE.md)
