# Euros OS — ETAP 9.4: rozszerzone testy automatyczne

**Data:** 12 listopada 2026 r.  
**Status:** 8/8 zadań ukończonych w zakresie kodu i automatycznych testów.  
**Gałąź:** `feature/stage9-tests`, utworzona na bazie `feature/stage9-compatibility`.  
**Ostatni test bazowy przed dokumentacją:** [GitHub Actions 43215284763](https://github.com/BudrysLP/EurosOS/actions/runs/43215284763).

Nie modyfikowano produkcyjnego Home Assistant ani ustawień pompy, nie scalono `main`, nie otwarto PR do autora. Wszystkie połączenia z pompą w testach są zastąpione atrapami.

## Wynik automatyczny

| Środowisko | Testy | Wynik |
| --- | --- | --- |
| Python 3.12.16, symulacje i jednostkowe | 154/154 | PASS, 0 skipped |
| Python 3.13.18, symulacje i jednostkowe | 154/154 | PASS, 0 skipped |
| Python 3.14.10, symulacje i jednostkowe | 154/154 | PASS, 0 skipped |
| **Rzeczywiste biblioteki** Home Assistant Core 2026.11.0 / Python 3.14.10 | 5/5 testów `unittest` klas encji | PASS |
| Testowa instancja `hass` (Home Assistant Core 2026.11.0), konfiguracja GEO_1 + METER_1, atrapowy MQTT | 1/1 testu `pytest` | PASS, 0 skipped |
| Pakowanie integracji do `euros_os.zip` | 15 plików integracji, powtórzone w macierzy | PASS |

**Łącznie w ramach jednej macierzy:** 154 testy offline na każdej z trzech wersji Pythona, plus sześć niezależnych testów rzeczywistego HA Core na Pythonie 3.14. Zestawy nie są sumowane jako 154+154+154 jednolitych scenariuszy; to ten sam pakiet wykonywany w trzech środowiskach.

## Zamknięte podzadania

| ID | Co zrobiono i co potwierdziły testy |
| --- | --- |
| **9.4.1** | Nazwa workflow zmieniona na `Euros OS - CI (regression and HA Core)`; wyzwalacze `push` dla `main`, `feature/**`, `fix/**`, `pull_request` i ręczny `workflow_dispatch`. Token wyłącznie `contents: read`. Wykonania `push` potwierdzone w CI. **Nie tworzyliśmy PR tylko po to, by wyzwolić `pull_request`** — zdarzenie jest skonfigurowane i testowane statycznie, a praktyczne zachowanie na PR sprawdzimy przy rzeczywistym PR w 9.9. Zachowano historyczną nazwę pliku YAML, aby nie zmieniać historii workflow; nazwa wyświetlana w Actions jest aktualna. |
| **9.4.2** | Zestaw offline uruchamia się na Pythonie 3.12/3.13/3.14. Testy prawdziwego Core 2026.11.0 wykonują się tylko na 3.14 (Home Assistant wymaga Python >=3.14.2). Sprawdzana jest dostępność `paho-mqtt>=1.6,<3` oraz wydrukowana wersja Pythona. |
| **9.4.3** | Test `tests_ha/test_real_ha_registration.py` rozszerzono o **dwa cykle setup/unload** tego samego `MockConfigEntry`. Przy obu konfiguracjach powstają te same 2 urządzenia i 73 encje rejestru; 73 identyfikatory encji i identyfikatory urządzeń pozostają identyczne po ponownym załadowaniu. |
| **9.4.4** | Dodano test dwóch niezależnych koordynatorów (GEO i ATMO), odrzucania obcych pomp i izolacji liczników; testy wykrywania METER_1/METER_2/METER_3 w pakietach o różnej kolejności, w tym z duplikatami. Nie symulowano faktycznego sprzętowego METER_2. |
| **9.4.5** | Dodano test granicy timeoutu MQTT `60.0` versus `60.001` sekundy, koalescencji powiadomień, odzyskania danych licznika bez fałszywego odświeżania pompy oraz zrzucania kolejki callbacków po unload. Z wcześniejszych etapów nadal wykonywane są testy błędów connect/CONNACK, ponownego połączenia, zamknięcia pętli i błędnych pakietów MQTT. |
| **9.4.6** | Dodano test 100 identycznych odczytów bez podwójnego naliczania kWh, przywrócenia licznika po przerwie obejmującej północ, ignorowania `NaN`/`inf`/ujemnych i nieprawidłowych danych oraz zachowania całodziennego wyniku po resecie fizycznego licznika. |
| **9.4.7** | Rozszerzono testy dozwolonych i zakazanych zmian trybu GEO AUTO/EMS oraz CWU Turbo: brak wysyłki przy nieznanych opcjach, złych flagach i niezweryfikowanych przełączeniach; sprawdzono dotychczasowe flagi AUTO, kontrolkę CWU i brak optymistycznej zmiany stanu po odrzuceniu polecenia. Sprawdzono strukturę MQTT `/App` i `retain=False`. Każde polecenie jest przechwycone przez klienta testowego. |
| **9.4.8** | Wprowadzono `scripts/run_unit_tests_strict.py`, który zwraca błąd przy braku testów, błędach, `skipped`, `expectedFailures` lub `unexpectedSuccesses`. Dla suite HA dodano `tests_ha/conftest.py` z analogicznym wymogiem braku pominięć. Dodano 3 testy własnej bramki CI. Ostatni wynik: wszystkie wymagane joby zielone, **0 skipped**. |

## Pliki prac

- `.github/workflows/euros-os-stage4-tests.yml` — workflow z `pull_request`, macierzą 3.12–3.14 i osobnym zadaniem Home Assistant 2026.11.
- `scripts/run_unit_tests_strict.py`, `tests_ha/conftest.py` — wymóg pełnego wykonania testów.
- `tests/test_stage9_ci_gate.py` — test wyzwalaczy, macierzy oraz faktycznego wykrywania `skipped` przez runner.
- `tests_ha/test_real_ha_registration.py` — dwukrotny setup/unload i tożsamość 73 encji.
- `tests/test_coordinator_discovery.py` — równoległe pompy, METER_N, stale, cleanup i MQTT publish.
- `tests/test_ems.py` — dobowe sumowanie, uszkodzone próbki, północ, reset.
- `tests/test_stage9_mode_safety.py` — dodatkowe scenariusze blokad GEO i CWU Turbo.

## Bramka jakości — co NIE jest jeszcze potwierdzone

1. Nie wykonano żadnego testu na fizycznych ATMO, ALLINONE ani dodatkowym METER_2.
2. Nie instalowano nowej gałęzi ani testowego `euros_os.zip` na produkcyjnym HA; test aktualizacji przez Marketplace (9.3.9) pozostaje otwarty.
3. Problem TLS: 9.2.5 (P1) — samopodpisane CA i niezgodny SAN/IP. Nie aktywowano pełnej weryfikacji TLS, która mogłaby odciąć pompę.
4. Wszystkie testy HA Core używały sztucznych odczytów GEO_1/METER_1. Nie są testem rzeczywistej pompy ani dowodem fizycznej zgodności wszystkich modeli.
5. Nie uruchamiano testów na prawdziwym zdarzeniu `pull_request`, ponieważ nadal obowiązuje decyzja, by nie otwierać PR do autora przed zakończeniem prac.

## Następny krok

Przed ETAPEM 9.5 utrzymać pełne kopie bezpieczeństwa i przygotować bezpieczny scenariusz porównania dotychczasowych 73 wpisów rejestru oraz historii energii; nie wykonywać wdrożenia bez osobnego polecenia. Równolegle pozyskać niezależne potwierdzenie Root CA od producenta dla 9.2.5. Dopiero po wyjaśnieniu blokad i zatwierdzeniu dalszych testów przejść do końcowego PR.
