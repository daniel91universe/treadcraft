# Incremento 5 · Anteprima di esportazione QZ

La baseline effettiva è `7282b7b`, verificata contro `main` su GitHub. Rispetto a `0cb20ad` cambiava solo il report dell'incremento 4. La Fase A ha rilevato 15 file locali non tracciati, nessuna modifica ai file tracciati e 71 test superati.

L'anteprima precedente accorpava riepilogo e diagnostica nello stesso messaggio. La ricognizione ha confermato i quattro contesti di inserimento e la deselezione con clic nel vuoto ed Esc. Le prove precedenti su Windows coprivano l'uscita di un segmento sopra e sotto il blocco.

- `app.py` mostra conteggi, durata programmata, stima dei segmenti a distanza e stato dell'export in un dialogo Tkinter. Il pannello scorrevole distingue errori, avvisi e informazioni. La conferma apre il flusso di salvataggio esistente. La logica dell'editor rimane quella della baseline.
- `test_qz_gui.py` verifica il riepilogo, la separazione della diagnostica e le otto righe del campione, oltre ai controlli esistenti sul salvataggio.

La suite completa con Python 3.15 ha superato 72 test. Su Windows, una prova automatizzata con Tkinter e Python 3.12 ha azionato i pulsanti Cancel ed Export del dialogo reale con il 3×3000 m. La scelta del percorso era simulata. Il file temporaneo conteneva otto righe XML e il JSON sorgente è rimasto identico.

Nella prova manuale su Windows con il 3×3000 m, l'utente ha confermato che la nuova anteprima è corretta, che l'annullamento funziona sia nell'anteprima sia nel selettore di file e che l'XML salvato contiene le otto righe attese. Ha verificato anche il riordinamento dei segmenti dentro e fuori dal blocco.

La prova manuale completa i controlli Windows previsti per questo incremento in vista della futura `v0.1.0`. Le prove QZ con il tapis roulant restano aperte e sono documentate nel report dell'incremento 4.

Il commit di implementazione è `7f9c7f8` sul branch `feature/ux-refinement`. [PR #10 in bozza verso main](https://github.com/daniel91universe/treadcraft/pull/10)
