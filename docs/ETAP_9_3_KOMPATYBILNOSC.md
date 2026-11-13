# Euros OS — ETAP 9.3: kompatybilność urządzeń, API HA i instalacji

**Data aktualizacji:** 2026-11-12. **Etap:** częściowo zakończony — **8/9** zadań formalnie zaliczonych (9.3.5 w zakresie zgodności metadanych i symulacji; test panelu na prawdziwym HA w 9.5). Brak instalacji nowego kodu w produkcyjnym HA; nie ma PR do autora.

## Repozytorium i wynik testów

- Gałąź prac: `feature/stage9-compatibility`, powstała z `feature/stage9-reliability`.
- Wersja bazowa HA użytkownika w testach z 9 listopada: Core 2026.11.0, GEO_1 oraz EMS Dom / METER_1, łącznie 73 nienaruszone identyfikatory.
- [Przebieg CI](https://github.com/BudrysLP/EurosOS/actions/runs/43212325942): **137/137** testów jednostkowych/symulacyjnych na każdej z wersji Python 3.12/3.13/3.14, dodatkowo **5/5** testów rzeczywistych klas encji HA i **1/1** test setup/unload na pełnym Home Assistant Core 2026.11.0 (Python 3.14.10). MQTT w teście HA jest symulowany, bez połączenia z pompą.
- Home Assistant 2026.11 wymaga **Python >=3.14.2**: https://pypi.org/project/homeassistant/ .
- Podczas pierwszego CI `3.14.2` instalacja na `ubuntu-latest` / Ubuntu 26.04 zakończyła się błędem dostępności dokładnego patcha w `actions/setup-python`, a nie błędem integracji. Ustalono `ubuntu-24.04`, `setup-python@v6` i najnowszy patch 3.14 spełniający >=3.14.2; wynik zielony.
- Oficjalna dokumentacja SensorEntity: https://contributors.home-assistant.io/core/entities/sensor/ .
- Oficjalne reguły klasy IoT (MQTT push): https://contributors.home-assistant.io/core/integrations/manifest/ .
- Marketplace i HACS `zip_release`: https://contributors.home-assistant.io/marketplace/guides/releases/ .

## Zrealizowane punkty

| ID | Wynik | Dowody/ograniczenia |
| --- | --- | --- |
| 9.3.1 | **Wykonane (symulacje)** | `discovery.find_pump()` rozpoznaje FriskoGEO, FriskoATMO i FriskoALLINONE po typie. Nie oznacza to testów fizycznych ATMO i ALLINONE. |
| 9.3.2 | **Wykonane (symulacje)** | Kolejność `Devices` nie zmienia wyboru pompy. Dwie pompy bez jednoznacznej tożsamości są odrzucane; skonfigurowana pompa nie jest podmieniana. |
| 9.3.3 | **Wykonane (analiza + wcześniejsze testy HA)** | Istniejące `unique_id`/identyfikatory urządzeń pozostają niezmienione w kodzie; 73 `entity_id`, `unique_id` i `device_id` zweryfikowano na fizycznym HA w ETAPIE 8. Ponowna kontrola najnowszej gałęzi w HA należy do 9.5. |
| 9.3.4 | **Wykonane (rzeczywiste API HA)** | Przeprowadzono 5 testów klas `SensorEntity`, `RestoreSensor`, `NumberEntity`, `SelectEntity`, `SwitchEntity` i `BinarySensorEntity` z faktycznych bibliotek Home Assistant 2026.11 oraz test platform i rejestru. [Raport](ETAP_9_3_TESTY_HA_CORE.md). |
| 9.3.8 | **Wykonane (testowa instancja HA Core 2026.11.0)** | Python 3.14.10, prawdziwy `hass` i `MockConfigEntry`, 2 urządzenia, 73 poprawne klucze rejestru encji, odczyt 23.5°C, setup/unload bez kasowania wpisów. MQTT symulowany, realny HA do 9.5. [Raport](ETAP_9_3_TESTY_HA_CORE.md). |
| 9.3.5 | **Wykonane (walidacja schematów + testy symulacyjne)** | Naprawiono legacy `ZM_AC_IN_ENERGY` przez wydzielenie `RestoreSensor`, integrację tylko przy nowych pakietach MQTT i bez podwójnego naliczania przy odczycie. Zachowano `unique_id`; istniejący wskaźnik nie jest bezpośrednim pomiarem pompy. Zweryfikowano deklaracje `device_class`, `state_class`, `kWh`, a także `PWM_1` (%) i obroty wentylatorów (RPM). Prawdziwy panel Energia i nowa gałąź wymagają weryfikacji w 9.5. |
| 9.3.6 | **Wykonane (symulacje)** | `METER_1`: 33 sensory + 2 liczniki dzienne, stałe ID i nazwy. `METER_N`: tworzone dopiero po realnym polu MQTT; brak fantomowych liczników. Fizyczny METER_2 nadal nieprzetestowany. |
| 9.3.7 | **Wykonane (symulacje + wcześniejszy HA)** | Testy obrotu dnia, timera północy, restore po restarcie, niepoprawnych odczytów, drobnego spadku i resetu licznika; historia energii na rzeczywistym HA przeżyła restart ETAPU 8. |

## Zmiany w gałęzi 9.3

1. `sensor.py`: starszy EurosOSSensor przeniesiony z override `state` / `unit_of_measurement` / `state_class` na `native_value`, `_attr_native_unit_of_measurement` i `_attr_state_class`. Zasady HA: `None` = unknown, `available=False` = unavailable; nie wysyłać napisu `unknown` jako odczytu temperatury. `unique_id` pozostał bez zmian.
2. Dla wartości liczbowych z `state_class` odrzucane są `NaN`, `inf`, wartości logiczne i nienumeryczne; brak napięcia lub prądu w szacowanej mocy nie jest przedstawiany jako pomiar 0 W. Dodano regresje. **Zrobiono:** algorytm szacowania `ZM_AC_IN_ENERGY` przepisano na `RestoreSensor`, z obliczaniem tylko po nowej próbce MQTT, bez naliczania od czasu odczytu stanu; szczegóły w 9.3.5 poniżej.
3. `manifest.json` oraz `hacs.json`: `iot_class` zmieniono z `local_polling` na `local_push`; faktyczna telemetria dociera z brokera MQTT i powiadamia HA. Nie zmieniano wersji wydania ani sposobu instalacji.
4. CI rozbudowano o Python 3.14 na kompatybilnym runnerze.
5. Testy `test_dynamic_ems.py`, `test_mqtt_to_ha_integration.py`, `test_ha08_compat.py`, `test_manifest_preflight.py` dostosowano/rozszerzono.

## Test pełnego API i rejestracji Core 2026.11

Dodatkowy raport [ETAP_9_3_TESTY_HA_CORE.md](ETAP_9_3_TESTY_HA_CORE.md) dokumentuje konfigurację `pytest-homeassistant`, pięć testów prawdziwych klas oraz jeden test uruchomienia/wyładowania integracji w testowym HA Core. Wszystkie 73 encje rejestrują się prawidłowo w dwóch urządzeniach. Cztery tekstowe `unique_id` są powtarzane pomiędzy różnymi domenami i są rozróżniane przez domenę i platformę — zgodnie z zasadami Home Assistant. [GitHub Actions](https://github.com/BudrysLP/EurosOS/actions/runs/43212325942) przeszedł.

## Pozostałe zadania — nie odhaczać przedwcześnie

| ID | Ryzyko / stan | Następny bezpieczny krok |
| --- | --- | --- |
| 9.3.9 | **W toku:** istniejący upstream ma archiwa `euros_os.zip` w wydaniach `v0.1.0`, `v0.1.1`, `v0.1.1-hotfix`, `v0.1.2`. `hacs.json` ma `zip_release:true`, ale fork nie ma własnych wydań; `homeassistant:2021.12.0` i metadane wersji nie odzwierciedlają zweryfikowanego zakresu. | Uzgodnić minimalną wersję HA i wymagania Marketplace, nie zmieniać `zip_release` i nie oznaczać starszych HA jako wspieranych bez testów. Test instalacji/upgrade w 9.5/9.6. |

## Szczegółowy wynik zadania 9.3.5 (12 listopada 2026)

### Problem potwierdzony w starszej implementacji

Poprzednia gałąź implementowała `ZM_AC_IN_ENERGY` we właściwości `EurosOSSensor.native_value`. Każde odczytanie stanu wywoływało `dt_util.utcnow()`, obliczało czas od poprzedniego odczytu i dopisywało kolejne kWh na podstawie `prąd × napięcie`. Było to zależne od liczby/czasu odczytów w HA, nie od nowych próbek urządzenia. Ponadto po resecie instancji licznik zaczynał od 0. Wersja mogła pokazywać fałszywe przyrosty i niepoprawne statystyki.

### Zaimplementowana korekta

- Nowa klasa `EurosOSLegacyEstimatedEnergySensor(RestoreSensor)` obsługuje **wyłącznie** klucz `ZM_AC_IN_ENERGY` u modeli, gdzie ten klucz jest dozwolony; FriskoGEO nadal go wyklucza, bo sterownik nie dostarcza wymaganych odczytów.
- Odczyt `native_value` jest bez skutków ubocznych; obliczenia wykonywane tylko przy zmianie `coordinator._last_update` dla pakietów pompy. Pakiety METER-only i timeout-watchdog nie zwiększają wyniku.
- Szacowanie metodą trapezów: uśredniona moc kolejnych próbek (A × V) × odstęp sekund / 3 600 000 = kWh. Pomija przedziały `> MQTT_TIMEOUT` i próbki nienumeryczne lub ujemne; brak dopisywania zużycia przez okres niedostępności HA.
- Wartość `kWh` przywracana z natywnych danych `RestoreSensor.async_get_last_sensor_data()`. Jeżeli poprzednia integracja nie zapisywała natywnego stanu, odtwarzanie historycznej wartości nie jest możliwe — pierwszy poprawny pomiar stanowi nowy punkt bazowy. Nie ma obietnicy odtworzenia całej historii przed tą zmianą.
- Identyfikator `{unique_prefix}_zm_ac_in_energy`, nazwa i jednostka pozostają bez zmian, więc istniejąca encja może zachować identyfikację w rejestrze HA. Wymaga to jednak ponownej kontroli rzeczywistego rejestru przed wdrożeniem.
- Dopasowano metadane starszych sensorów: `PWM_1` z jednostką `%` nie jest już klasyfikowany jako `power`; odczyty wentylatorów w `RPM` nie są klasyfikowane jako liniowa `speed`. Nie zmieniono nazw, jednostek i `unique_id`.
- Zachowano metadane EMS Dom: chwilowa moc `power`/`measurement` w `kW`; rzeczywiste liczniki `energy`/`total_increasing` w `kWh`; dwa dzienne liczniki również z `energy`/`total_increasing` w `kWh`.
- `ZM_AC_IN_ENERGY` pozostaje **oszacowaniem**, gdyż `U × I` nie musi odpowiadać mocy czynnej; nie należy wykorzystywać go jako wiarygodnego źródła rozliczeń. Nie mieszać go z `METER_1`, który mierzy **przyłącze całego domu**, a nie tylko pompę.

### Testy i zakres potwierdzenia

- Dodano 5 testów interpolacji, przerw MQTT, powtarzanych odczytów, przywracania i błędnych próbek, 1 test zachowania klasy i `unique_id` przy konfiguracji platformy oraz 3 testy metadanych i zgodności z EMS.
- [CI GitHub Actions](https://github.com/BudrysLP/EurosOS/actions/runs/43204946143): **134/134** na każdej z wersji 3.12, 3.13 i 3.14; konfiguracja nie wymaga produkcyjnego MQTT ani instalacji HA.
- Oficjalne kryteria Energy Dashboard: `device_class=energy`, `state_class=total|total_increasing`, jednostka energii np. `kWh`. Źródło: https://www.home-assistant.io/docs/energy/faq/ . Wymagania sensorów i restore: https://contributors.home-assistant.io/core/entities/sensor/ .
- Test rzeczywistego interfejsu panelu Energia i potencjalnej migracji istniejącej historii **nie został przeprowadzony**. Pozostaje w ETAPIE 9.5.

## Otwarte blokady poza ETAPEM 9.3

**9.2.5 TLS (P1)** nadal otwarte: lokalny broker posiada samopodpisany Root CA oraz certyfikat niedopasowany do bieżącego IP pompy. Nie wprowadzać niezweryfikowanej zmiany uwierzytelniania, która odetnie urządzenie. Szczegóły: [ETAP_9_2_TLS_DIAGNOSTYKA.md](ETAP_9_2_TLS_DIAGNOSTYKA.md).

## Zasady publikacji

- Nie wdrażano najnowszej gałęzi na HA produkcyjnym.
- Nie zmieniano upstream `main` ani PR #3.
- Nie otwieramy końcowego PR przed zamknięciem bramki 9.8.
