# TreadCraft v0.4.0 · Validazione QZ-03D

**Esito positivo per l'invio dal portable.** L'utente ha provato `TreadCraft-QZ-03D-Windows-x64.zip` con QZ Android **2.20.29** sulla rete Wi-Fi locale senza Internet e senza tapis roulant collegato.

QZ ha confermato il salvataggio del **3×3000 m con 8 righe**. Nel file XML salvato da QZ, l'utente ha verificato `distance="3"` alle righe **2, 4 e 6**. Le tre ripetute conservano quindi la distanza di 3 km dopo l'invio via WebSocket.

La copia usata per costruire il portable aveva superato **89 test automatici**. La conferma su Android riguarda il portable e il caso positivo. Le prove negative sul telefono e la ripetizione dalla copia Python non sono documentate. Le transizioni effettive a distanza e il controllo del tapis roulant restano da verificare con l'hardware collegato.
