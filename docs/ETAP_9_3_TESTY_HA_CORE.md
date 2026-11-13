# Euros OS — ETAP 9.3.4 i 9.3.8: testy na prawdziwym Home Assistant Core

**Data:** 12 listopada 2026. **Wynik:** zaliczone dla Home Assistant Core 2026.11.0 (Python 3.14.10), bez połączenia z prawdziwą pompą.

## Zasady i środowisko

- Gałąź: `feature/stage9-compatibility`; nie zmieniono `main`, upstream ani konfiguracji Home Assistant użytkownika.
- Testy działają wyłącznie na hostowanym runnerze GitHub Actions `ubuntu-24.04` z Pythonem 3.14.10.
- Instalujemy **rzeczywiste paczki** `homeassistant==2026.11.0`, `pytest-homeassistant==2026.11.0` i `paho-mqtt>=1.6,<3`, a nie imitacje modułów HA.
- MQTT jest w scenariuszu rejestracji wyłącznie atrapą `EurosOSMQTTCoordinator.connect`/`disconnect`; nie dochodzi do połączenia TCP ani do wysłania komendy na pompę.
- [Zielony przebieg GitHub Actions](https://github.com/BudrysLP/EurosOS/actions/runs/43212325942): **137/137** testów jednostkowych i MQTT na każdej z wersji Python 3.12, 3.13 i 3.14; **5/5** testów prawdziwych klas HA oraz **1/1** test pełnego setup/unload w testowej instancji Core 2026.11.0.

## Co sprawdzono

### 9.3.4 — API encji

`tests_ha/test_real_ha_api.py` importuje prawdziwe klasy:
- `SensorEntity` oraz `RestoreSensor` — zwykłe sensory GEO, szacowana energia legacy i liczniki EMS;
- `NumberEntity`/`NumberMode`, `SelectEntity`, `SwitchEntity`, `BinarySensorEntity` — istniejące kontrolki.
Testy sprawdzają `native_value`, `native_unit_of_measurement`, `state_class`, `device_class`, `available`, granice NumberEntity i niezmienne wzorce `unique_id`.

### 9.3.8 — uruchomienie integracji w prawdziwej instancji HA

`tests_ha/test_real_ha_registration.py` wykorzystuje fixture `hass` z `pytest-homeassistant` i `MockConfigEntry`. Po wstrzyknięciu lokalnych przykładowych danych `GEO_1` + `METER_1` sprawdzono:
1. `hass.config_entries.async_setup()` uruchamia wszystkie platformy bez otwierania połączenia MQTT;
2. Rejestr urządzeń zawiera **2** urządzenia (pompa i licznik EMS); licznik jest prawidłowo połączony z urządzeniem nadrzędnym;
3. Rejestr encji zawiera **73** encje i 73 unikalne **klucze rejestru** (domena + platforma + unique_id).
4. `unique_id` traktowany jako sam tekst nie musi być globalnie unikalny: w tym scenariuszu jest **69 różnych ciągów**. Cztery są ponownie użyte w innych domenach, co jest zgodne z regułami HA i nie oznacza duplikacji encji.
5. Sensor temperatury GEO ma dostępny stan **23.5 °C** (dane testowe).
6. `hass.config_entries.async_unload()` usuwa uruchomioną instancję integracji, nie kasując 73 wpisów rejestru encji.

Dokumentacja reguł `unique_id`: https://contributors.home-assistant.io/core/entities/registry/ .

## Uwagi z procesu testowego

- Początkowa konfiguracja `pytest` nie aktywowała asynchronicznych fixture'ów. Dodano `pyproject.toml` z `asyncio_mode="auto"` i zakresem testów `tests_ha`, zgodnie z dokumentacją pakietu `pytest-homeassistant`.
- Home Assistant 2026.11 deprecjonuje używanie map `device_registry.devices`/`entity_registry.entities` i stare wyszukiwanie `async_get_device`. Testy korzystają teraz z `async_entries_for_config_entry` i `async_get_device_by_identifier`.
- Nie poprawiano na siłę poprawnego zachowania: Home Assistant pozwala używać tego samego tekstowego `unique_id` w różnych domenach, o ile para (domena, integracja, ID) jest unikalna.
- Ostrzeżenia `DeprecationWarning` w niektórych zależnościach Home Assistant nie zablokowały testów. Wynik nie stanowi gwarancji zgodności z HA 2027.

## Świadome ograniczenia

- **Nie wykonywano aktualizacji fizycznego Home Assistant ani komunikacji z pompą.** Weryfikacja rzeczywistej instalacji GEO_1/EMS Dom, 73 istniejących `entity_id`, zapisów historii i zachowania sterowania należy do ETAPU 9.5.
- Nie przetestowano fizycznych modeli ATMO/ALLINONE ani dodatkowego licznika METER_2.
- Nie testowano przejścia przez instalator Marketplace ani odtwarzania archiwum release na realnym HA — punkt 9.3.9 pozostaje otwarty.
- Problem TLS 9.2.5 z niezaufanym CA i niedopasowanym SAN nadal jest P1 i blokuje końcowy PR.
- Liczba encji i przebieg prób dotyczą sztucznego fixture'a; nie zastępują porównania identyfikatorów z prawdziwą instalacją.

## Decyzja

**9.3.4 i 9.3.8 zaliczone w zakresie zgodności z prawdziwym API Core 2026.11.0 i symulowanego przebiegu setup/unload.** Utrzymujemy odrębny obowiązkowy test na fizycznym HA w 9.5 i procedurę aktualizacji w 9.3.9/9.6.
