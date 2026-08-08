# Łożyska Klient (Android) - WYGASZONA

Ta appka (lekki natywny klient sieciowy, bez lokalnej bazy) została
zastąpiona przez `../android-offline`, która robi wszystko to samo (i
więcej: działa offline, ma automatyczną synchronizację) i jest jedyną
utrzymywaną appką mobilną w tym projekcie.

**Ta appka nie działa już poprawnie** - serwer (`../server.py`) od wersji z
synchronizacją używa identyfikatorów UUID (tekst) zamiast liczb, a modele
danych w tej appce (`Network.kt`, `Models.kt`) wciąż zakładają liczby
całkowite. Została w repo tylko jako punkt odniesienia / historia projektu.

Jeśli appka jest zainstalowana na którymś telefonie - odinstaluj ją i
zainstaluj `android-offline` zamiast niej.
