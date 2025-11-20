## MQTT Setup

Aby umożliwić połączenie Home Assistant z urządzeniem przez MQTT, należy wprowadzić małą zmianę w pliku konfiguracyjnym firewalla na urządzeniu.

1. Otwórz plik `/etc/iptables/rules.v4` w edytorze tekstu na karcie SD pompy.
2. Dodaj pod linijką:

```-A INPUT -i wlan0 -p tcp -m tcp --dport 80 -j ACCEPT```

Następującą linijkę:

```-A INPUT -i eth0 -p tcp --dport 8883 -j ACCEPT```

3. Zapisz plik i uruchom ponownie urządzenie, aby zmiany zaczęły obowiązywać.

> Instrukcja pomocnicza dotycząca kopii zapasowej i edycji plików znajduje się pod linkiem, wykonaj instrukcję do kroku "**Modyfikacja plików na karcie SD**", a następnie edytuj plik **rules.v4** nie zapominając o kliknięciu **Unmount** w programie **Linux File Systems for Windows**:
> [Pomocniczy przewodnik](https://docs.google.com/document/d/1tLcjQqh286_qxEosPKLCwNL_i6CWfQHAWCTxhtnMaNo/edit?tab=t.0)

> ⚠️ Uwaga: Edycja plików systemowych może wpłynąć na działanie pompy. Zachowaj ostrożność i wykonaj kopię zapasową.
