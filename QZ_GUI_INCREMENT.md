# Incremento 4 · Esportazione QZ dalla GUI

La Fase A ha verificato il commit locale 08bec8db8886fe76833ae4b769c898889ed02f70 contro main sul repository privato. La suite iniziale ha superato 53 test. L'esportatore XML, il profilo Commercial LE e i dati per il riepilogo erano già disponibili.

Il pulsante **Export to QZ XML** genera l'XML con l'esportatore esistente. Mostra gli errori bloccanti prima della scelta del file. L'anteprima distingue il tempo delle righe temporali dalle stime delle righe a distanza e mostra gli avvisi del profilo. Dopo la conferma apre il dialogo per la destinazione.

Il salvataggio accetta percorsi XML e chiede conferma per una destinazione esistente. Scrive e sincronizza un temporaneo nella directory di destinazione. Usa la sostituzione atomica per le sovrascritture confermate e un hard link per pubblicare un file nuovo senza sovrascrivere un file creato nel frattempo. Un file system privo di supporto agli hard link può rifiutare la creazione e la GUI mostra l'errore I/O.

| File | Modifica |
|---|---|
| app.py | Pulsante, callback, anteprima e scrittura sicura |
| test_qz_gui.py | Otto test su callback e scrittura |
| QZ_GUI_INCREMENT.md | Resoconto dell'incremento |

Tutti i 61 test sono passati con Python 3.15 e il comando python -B -m unittest. I mock coprono l'annullamento, il rifiuto della discesa, la conferma di sostituzione e gli errori di accesso. Le prove su file temporanei controllano contenuto XML, integrità del JSON, ripetute a distanza e conflitto con una creazione concorrente. Le prove sul tapis restano aperte.

Verifica manuale su Windows eseguita dall'utente con il campione 3×3000 m. L'anteprima era corretta. L'annullamento ha funzionato sia nell'anteprima sia nella finestra di scelta della destinazione. Il file XML salvato conteneva le 8 righe attese.

Il commit di implementazione è `f573d88`. L'integrazione è stata unita in `main` con la [pull request #7](https://github.com/daniel91universe/treadcraft/pull/7).

L'utente ha aperto in QZ Android l'XML del 3×3000 m esportato da TreadCraft e ha confermato che l'anteprima era corretta. La prova si è svolta senza un tapis roulant collegato.

Nella prova finale su Windows con il 3×3000 m, l'utente ha confermato che un segmento trascinato fuori dal blocco può essere collocato sia sopra sia sotto e che l'XML QZ del 3×3000 m originale contiene ancora le 8 righe attese. Sullo stesso commit di merge, `0cb20ad`, sono passati tutti i 71 test automatici. [Pull request #9](https://github.com/daniel91universe/treadcraft/pull/9)

## Prove QZ con il tapis roulant collegato

- Verificare che QZ Android si connetta al Commercial LE e legga la velocità effettiva.
- Avviare il 3×3000 m esportato e verificare le transizioni. Controllare che le ripetute terminino al raggiungimento dei 3 km e che il riscaldamento, i recuperi e il defaticamento terminino allo scadere delle rispettive durate.
- Alle transizioni, confrontare la velocità richiesta da QZ con quella effettiva del tapis. Verificare il passaggio da 10 a 14 km/h all'inizio delle ripetute e il ritorno a 10 km/h per i recuperi.
