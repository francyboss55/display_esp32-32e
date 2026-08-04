# =============================================================================
# [PARTE 1 DI 7] - SMARTPHONE OS: CONFIGURAZIONE PIN HARDWARE E TOUCH SCREEN
# =============================================================================
import machine
from machine import SPI, SoftSPI, Pin
import time
import ili9341
import random
import json  
import gc    

# 1.1 ASSEGNAZIONE PIN SCHEDA ESP32
TFT_MISO, TFT_MOSI, TFT_CLK = 12, 13, 14
TFT_CS, TFT_DC, TFT_RST, TFT_BCKL = 15, 2, 4, 21

# Accensione retroilluminazione pannello LCD
backlight = Pin(TFT_BCKL, Pin.OUT)
backlight.value(1)

# Inizializzazione Display ILI9341 (Risoluzione Verticale standard 240x320)
spi = SPI(1, baudrate=40000000, sck=Pin(TFT_CLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
display = ili9341.Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=Pin(TFT_RST), width=240, height=320, rotation=0)

# Inizializzazione Linea di comunicazione SoftSPI per il Touch Screen
TP_CLK, TP_MISO, TP_MOSI, TP_CS = 25, 39, 32, Pin(33, Pin.OUT)
TP_CS.value(1)
spi_touch = SoftSPI(baudrate=1000000, sck=Pin(TP_CLK), mosi=Pin(TP_MOSI), miso=Pin(TP_MISO))

# Configurazione LED RGB (Anodo Comune: 1 = Spento, 0 = Acceso)
led_r = Pin(22, Pin.OUT, value=1)
led_g = Pin(16, Pin.OUT, value=1)
led_b = Pin(17, Pin.OUT, value=1)

# --- 1.2 LETTURA HARDWARE DEL TOUCH SCREEN ---
def leggi_touch():
    """Legge i dati grezzi SPI del touch e restituisce le coordinate X, Y reali (0-240, 0-320)"""
    TP_CS.value(0)
    spi_touch.write(b'\x90')
    rx = spi_touch.read(2)
    spi_touch.write(b'\xD0')
    ry = spi_touch.read(2)
    TP_CS.value(1)
    
    gx = int.from_bytes(rx, 'big') >> 4
    gy = int.from_bytes(ry, 'big') >> 4
    
    if gx != 2047 and gx > 100 and gy > 100:
        px_grezzo = int((1823 - gy) * 240 / 1658)
        px = 240 - px_grezzo
        py = int((1812 - gx) * 320 / 1682)
        return max(0, min(px, 240)), max(0, min(py, 320))
    return None

print("--- PARTE 1 RIGENERATA: HARDWARE E INTERFACCIA TOUCH PRONTI ---")


# =============================================================================
# [PARTE 2 DI 6] - SMARTPHONE OS: COLORI, STATO COMPLETO E RUBRICA
# =============================================================================

# --- 2.1 TAVOLOZZA COLORI DI SISTEMA ---
NERO_AMOLED    = 0x0000
C_BIANCO       = 0xFFFF
C_GRIGIO_ICONA = 0x31A6
C_BLU_LINK     = 0x03EF
C_VERDE_CALL   = 0x2E44
C_ARANCIO_PREF = 0xFD20
C_VIOLA_CTRL   = 0x780F
C_ROSSO_DROP   = 0xF800 
C_GLOW_CIANO   = ili9341.color565(0, 240, 255)   
C_BIO_VERDE    = ili9341.color565(0, 255, 130)   

# --- 2.2 CONFIGURAZIONE STATO DI BASE OS ---
PIN_CORRETTO = "2514"      
pin_inserito = ""          
stato_telefono = "BLOCCATO" 
app_corrente   = None
# Modifica il limite delle pagine e aggiungi la memoria per il notebook
pagina_home = 1  
testo_nota = ""  
indice_cursore = 0
percentuale_batteria = 88
wifi_connesso = False

# Variabili dinamiche interne delle vecchie applicazioni
numero_digitato = ""
messaggio_inviato = False
dati_mondi = {
    "M2": {"problemi": "NO", "pericolo": 0},
    "M3": {"problemi": "NO", "pericolo": 0}
}

# Variabili dinamiche interne della pagina 2 (Nuove App)
calc_espressione = ""
calc_risultato = ""
crono_avviato = False
crono_inizio = 0
crono_trascorso = 0
lavagna_punti = []
love_percentuale = 0
love_calcolato = False

# --- 2.3 STRUTTURA RUBRICA COMPLETA ---
RUBRICA = [
    {"nome": "bianca 2M",   "numero": "3334561234"},
    {"nome": "camilla 2M",  "numero": "3357894561"},
    {"nome": "pietro 2M",   "numero": "3471236547"},
    {"nome": "michele 2M",  "numero": "3499871230"},
    {"nome": "minus 2M",    "numero": "3204567891"},
    {"nome": "elisa 2M",    "numero": "3281122334"},
    {"nome": "thiago 2M",   "numero": "3885566778"},
    {"nome": "alfredo 2M",  "numero": "3319988776"},
    {"nome": "sbriser 2M",  "numero": "3405544332"},
    {"nome": "dolcetta 2M", "numero": "3451122998"},
    {"nome": "sbriser 3M",  "numero": "3405544333"}, 
    {"nome": "dolcetta 3M", "numero": "3451122999"}, 
    {"nome": "ivie 3M",     "numero": "3347788990"},
    {"nome": "violet 3M",   "numero": "3662233445"},
    {"nome": "crucco 3M",   "numero": "3278899001"},
    {"nome": "elox 3M",     "numero": "3294455667"},
    {"nome": "sense 3M",    "numero": "3294455668"},
    {"nome": "mag 3M",      "numero": "3421133557"}
]
indice_contatto_corrente = 0

print("--- PARTE 2 CARICATA: VARIABILI E DATABASE PRONTI ---")

# =============================================================================
# [PARTE 3 DI 6] - SMARTPHONE OS: SCHERMATE DI SISTEMA (10 AGOSTO 2001)
# =============================================================================

def spegni_led_totale():
    led_r.value(1); led_g.value(1); led_b.value(1)

def lampeggio_conferma(led_selezionato):
    led_selezionato.value(0)
    time.sleep_ms(100)
    led_selezionato.value(1)

def applica_sfondo():
    if hasattr(display, 'clear'): display.clear(NERO_AMOLED)
    else: display.fill_rectangle(0, 0, 240, 320, NERO_AMOLED)

def disegna_barra_stato():
    # Ora fissa bloccata alle 18:00 (Nessun indicatore Wi-Fi)
    display.draw_text8x8(10, 4, "18:00", C_BIANCO)
    display.draw_rectangle(200, 4, 22, 12, C_BIANCO)
    display.fill_rectangle(222, 7, 2, 6, C_BIANCO)
    display.fill_rectangle(202, 6, int(18 * (percentuale_batteria / 100)), 8, C_VERDE_CALL)

def disegna_barra_navigazione():
    display.fill_rectangle(0, 300, 240, 20, NERO_AMOLED)
    display.draw_rectangle(0, 300, 240, 1, C_GRIGIO_ICONA)
    display.fill_rectangle(45, 308, 12, 4, C_BIANCO)
    display.draw_circle(120, 310, 6, C_BIANCO)
    display.draw_rectangle(185, 304, 12, 12, C_BIANCO)

def mostra_schermata_blocco():
    spegni_led_totale()
    backlight.value(1) 
    applica_sfondo()
    disegna_barra_stato()
    # Data storica e orario impostati in modo fisso
    display.draw_text8x8(100, 80, "18:00", C_BIANCO)
    display.draw_text8x8(30, 130, "Venerdi, 10 Agosto 2001", C_BIANCO)
    display.fill_rectangle(20, 240, 200, 30, C_GRIGIO_ICONA)
    display.draw_text8x8(28, 251, "CLICCA QUI PER SBLOCCARE", C_BIANCO)

def mostra_schermata_pin():
    applica_sfondo()
    disegna_barra_stato()
    display.draw_text8x8(45, 35, "INSERISCI IL PIN", C_BIANCO)
    display.draw_rectangle(40, 55, 160, 25, C_BIANCO)
    
    testo_pin = "_ _ _ _" if len(pin_inserito) == 0 else "*" * len(pin_inserito)
    display.draw_text8x8(55, 64, testo_pin, C_GLOW_CIANO)
    
    tasti = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    contatore = 0
    for riga in range(3):
        for colonna in range(3):
            x = 50 + (colonna * 70)
            y = 115 + (riga * 45)
            display.draw_circle(x, y, 16, C_BIANCO)
            display.draw_text8x8(x - 3, y - 4, tasti[contatore], C_BIANCO)
            contatore += 1
    display.draw_text8x8(35, 255, "CANC", C_ROSSO_DROP)

print("--- PARTE 3 CARICATA: SCHERMATE DI SISTEMA CONFIGURED ---")

# =============================================================================
# [PARTE 4 DI 6] - SMARTPHONE OS: HOME SCREEN E INTERFACCE APPLICAZIONI (P1)
# =============================================================================

def attiva_spegnimento_schermo():
    global stato_telefono, app_corrente
    stato_telefono = "SLEEP_NERO"
    app_corrente = None
    spegni_led_totale()
    if hasattr(display, 'clear'): display.clear(NERO_AMOLED)
    else: display.fill_rectangle(0, 0, 240, 320, NERO_AMOLED)
    backlight.value(0)
    print("-> Schermo spento. Tocca lo schermo per riattivarlo.")

def mostra_home_screen():
    global pagina_home
    spegni_led_totale()
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    
    if pagina_home == 1:
        # --- PAGINA 1 ---
        icone_app = [
            ("Chiamate", 65, 75, C_VERDE_CALL),
            ("Messaggi", 175, 75, C_BLU_LINK),
            ("Controllo", 65, 165, C_VIOLA_CTRL),
            ("Spegni", 175, 165, C_ROSSO_DROP)
        ]
        for nome, x, y, colore in icone_app:
            display.fill_circle(x, y, 16, colore)
            display.draw_circle(x, y, 16, C_BIANCO)
            if nome == "Chiamate": display.fill_rectangle(x-4, y-7, 8, 14, C_BIANCO)
            elif nome == "Messaggi": display.fill_rectangle(x-7, y-4, 14, 8, C_BIANCO)
            elif nome == "Controllo": display.draw_rectangle(x-6, y-6, 12, 12, C_BIANCO)
            elif nome == "Spegni": display.fill_rectangle(x-2, y-8, 4, 10, C_BIANCO)
            display.draw_text8x8(x - 30, y + 22, nome, C_BIANCO)
            
        # Indicatori di pagina (Pagina 1 attiva)
        display.fill_circle(100, 275, 3, C_BIANCO)
        display.draw_circle(120, 275, 3, C_BIANCO)
        display.draw_circle(140, 275, 3, C_BIANCO)
        display.draw_text8x8(210, 271, ">>", C_GRIGIO_ICONA)
        
    elif pagina_home == 2:
        # --- PAGINA 2 ---
        icone_app = [
            ("Calcola", 65, 75, C_ARANCIO_PREF),
            ("Crono", 175, 75, C_GLOW_CIANO),
            ("Lavagna", 65, 165, C_BIO_VERDE),
            ("Love", 175, 165, 0xF81F)
        ]
        for nome, x, y, colore in icone_app:
            display.fill_circle(x, y, 16, colore)
            display.draw_circle(x, y, 16, C_BIANCO)
            if nome == "Calcola": display.draw_text8x8(x-4, y-4, "=", C_BIANCO)
            elif nome == "Crono": display.draw_text8x8(x-4, y-4, "T", NERO_AMOLED)
            elif nome == "Lavagna": display.draw_text8x8(x-4, y-4, "L", NERO_AMOLED)
            elif nome == "Love": display.draw_text8x8(x-4, y-4, "L", C_BIANCO)
            display.draw_text8x8(x - 30, y + 22, nome, C_BIANCO)
            
        # Indicatori di pagina (Pagina 2 attiva)
        display.draw_circle(100, 275, 3, C_BIANCO)
        display.fill_circle(120, 275, 3, C_BIANCO)
        display.draw_circle(140, 275, 3, C_BIANCO)
        display.draw_text8x8(15, 271, "<<", C_GRIGIO_ICONA)
        display.draw_text8x8(210, 271, ">>", C_GRIGIO_ICONA)

    elif pagina_home == 3:
        # --- PAGINA 3 (NUOVA) ---
        icone_app = [
            ("Notebook", 65, 75, C_ARANCIO_PREF)
        ]
        for nome, x, y, colore in icone_app:
            display.fill_circle(x, y, 16, colore)
            display.draw_circle(x, y, 16, C_BIANCO)
            # Icona blocco note stilizzata (Linee orizzontali)
            display.fill_rectangle(x-6, y-6, 12, 2, C_BIANCO)
            display.fill_rectangle(x-6, y-2, 12, 2, C_BIANCO)
            display.fill_rectangle(x-6, y+2, 12, 2, C_BIANCO)
            display.draw_text8x8(x - 32, y + 22, nome, C_BIANCO)
            
        # Indicatori di pagina (Pagina 3 attiva)
        display.draw_circle(100, 275, 3, C_BIANCO)
        display.draw_circle(120, 275, 3, C_BIANCO)
        display.fill_circle(140, 275, 3, C_BIANCO)
        display.draw_text8x8(15, 271, "<<", C_GRIGIO_ICONA)


def attendi_tasto_qwerty():
    """Disegna la tastiera con frecce direzionali, attende il tocco e restituisce l'azione"""
    # Spazio inferiore (Y=160 a Y=295)
    display.fill_rectangle(0, 160, 240, 135, NERO_AMOLED)
    display.draw_rectangle(0, 160, 240, 1, C_GRIGIO_ICONA)
    
    riga1 = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]
    riga2 = ["A", "S", "D", "F", "G", "H", "J", "K", "L"]
    riga3 = ["Z", "X", "C", "V", "B", "N", "M"]
    
    for i, let in enumerate(riga1):
        x = 2 + (i * 24)
        display.fill_rectangle(x, 165, 22, 26, C_GRIGIO_ICONA)
        display.draw_text8x8(x + 7, 174, let, C_BIANCO)
        
    for i, let in enumerate(riga2):
        x = 14 + (i * 24)
        display.fill_rectangle(x, 196, 22, 26, C_GRIGIO_ICONA)
        display.draw_text8x8(x + 7, 205, let, C_BIANCO)
        
    # Riga 3: CANC, Lettere, OK
    display.fill_rectangle(2, 227, 34, 26, C_ROSSO_DROP)
    display.draw_text8x8(6, 236, "DEL", C_BIANCO)
    
    for i, let in enumerate(riga3):
        x = 40 + (i * 24)
        display.fill_rectangle(x, 227, 22, 26, C_GRIGIO_ICONA)
        display.draw_text8x8(x + 7, 236, let, C_BIANCO)
        
    display.fill_rectangle(208, 227, 30, 26, C_VERDE_CALL)
    display.draw_text8x8(212, 236, "OK", C_BIANCO)
    
    # RIGA 4 MODIFICATA: Freccia SX, Spazio, Freccia DX
    display.fill_rectangle(2, 258, 34, 24, C_GRIGIO_ICONA) # Freccia SX
    display.draw_text8x8(15, 266, "<", C_BIANCO)
    
    display.fill_rectangle(40, 258, 160, 24, C_GRIGIO_ICONA) # Spazio
    display.draw_text8x8(104, 266, "SPAZIO", C_BIANCO)
    
    display.fill_rectangle(204, 258, 34, 24, C_GRIGIO_ICONA) # Freccia DX
    display.draw_text8x8(217, 266, ">", C_BIANCO)

    # LOOP ATTESA TOCCO
    while True:
        coordinate = leggi_touch()
        if coordinate is not None:
            x, y = coordinate
            if 160 <= y <= 285:
                tasto_rilevato = None
                
                if 165 <= y <= 191:
                    idx = int((x - 2) / 24)
                    if 0 <= idx < len(riga1) and (2 + idx*24) <= x <= (2 + idx*24 + 22):
                        tasto_rilevato = riga1[idx]
                        
                elif 196 <= y <= 222:
                    idx = int((x - 14) / 24)
                    if 0 <= idx < len(riga2) and (14 + idx*24) <= x <= (14 + idx*24 + 22):
                        tasto_rilevato = riga2[idx]
                        
                elif 227 <= y <= 253:
                    if 2 <= x <= 36: tasto_rilevato = "CANC"
                    elif 208 <= x <= 238: tasto_rilevato = "OK"
                    else:
                        idx = int((x - 40) / 24)
                        if 0 <= idx < len(riga3) and (40 + idx*24) <= x <= (40 + idx*24 + 22):
                            tasto_rilevato = riga3[idx]
                            
                elif 258 <= y <= 282:
                    if 2 <= x <= 36: tasto_rilevato = "MOVE_SX"
                    elif 40 <= x <= 200: tasto_rilevato = " "
                    elif 204 <= x <= 238: tasto_rilevato = "MOVE_DX"
                
                if tasto_rilevato is not None:
                    while leggi_touch() is not None:
                        time.sleep_ms(10)
                    return tasto_rilevato
        time.sleep_ms(20)

def mostra_app_chiamate():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_rectangle(15, 22, 210, 24, C_BLU_LINK)
    display.draw_text8x8(22, 30, "<", C_GLOW_CIANO)
    display.draw_text8x8(210, 30, ">", C_GLOW_CIANO)
    if len(RUBRICA) == 0: display.draw_text8x8(55, 30, "Rubrica vuota", C_GRIGIO_ICONA)
    else:
        nome_contatto = RUBRICA[indice_contatto_corrente]["nome"]
        if len(nome_contatto) > 15: nome_contatto = nome_contatto[:12] + "..."
        display.draw_text8x8(45, 30, "RUB: " + nome_contatto, C_BIANCO)
    display.draw_rectangle(20, 52, 200, 22, C_BIANCO)
    if numero_digitato == "": display.draw_text8x8(30, 59, "Inserisci...", C_GRIGIO_ICONA)
    else: display.draw_text8x8(30, 59, numero_digitato, C_BIANCO)
    
    tasti = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    contatore = 0
    for riga in range(3):
        for colonna in range(3):
            x = 50 + (colonna * 70)
            y = 110 + (riga * 45)
            display.draw_circle(x, y, 16, C_BIANCO)
            display.draw_text8x8(x - 3, y - 4, tasti[contatore], C_BIANCO)
            contatore += 1
    display.draw_text8x8(25, 251, "CANC", C_ROSSO_DROP)
    
    # Due pulsanti: Verde (Chiama) e Rosso (Riattacca)
    display.fill_circle(105, 255, 16, C_VERDE_CALL)
    display.fill_rectangle(102, 248, 6, 14, C_BIANCO)
    display.fill_circle(155, 255, 16, C_ROSSO_DROP)
    display.fill_rectangle(147, 253, 16, 4, C_BIANCO)

def mostra_app_messaggi():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_rectangle(15, 22, 210, 24, C_BLU_LINK)
    display.draw_text8x8(22, 30, "<", C_GLOW_CIANO)
    display.draw_text8x8(210, 30, ">", C_GLOW_CIANO)
    target_chat = "Mamma"
    if len(RUBRICA) > 0:
        target_chat = RUBRICA[indice_contatto_corrente]["nome"]
        if len(target_chat) > 12: target_chat = target_chat[:9] + "..."
    display.draw_text8x8(45, 30, "CHAT: " + target_chat, C_BLU_LINK)
    display.draw_rectangle(10, 55, 160, 25, C_GRIGIO_ICONA)
    display.draw_rectangle(70, 87, 160, 25, C_VERDE_CALL)
    display.draw_rectangle(10, 119, 140, 35, C_GRIGIO_ICONA)
    if messaggio_inviato: display.draw_rectangle(50, 162, 180, 28, C_VERDE_CALL)
    else: display.fill_rectangle(30, 210, 180, 30, C_BLU_LINK)

def mostra_app_controllo():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(30, 30, "MONITORAGGIO PLANETARIO", C_BIANCO)
    display.draw_rectangle(10, 45, 220, 1, C_GRIGIO_ICONA)
    display.draw_text8x8(15, 60, "1) Secondo Mondo", C_GLOW_CIANO)
    display.draw_text8x8(25, 75, "Problemi: " + dati_mondi["M2"]["problemi"], C_BIANCO)
    display.draw_text8x8(25, 90, "Pericolo: " + str(dati_mondi["M2"]["pericolo"]) + "%", C_BIANCO)
    colore_m2 = C_ROSSO_DROP if dati_mondi["M2"]["problemi"] == "SI" else C_BIO_VERDE
    display.fill_circle(210, 75, 4, colore_m2)
    display.draw_rectangle(12, 110, 216, 1, C_GRIGIO_ICONA)
    display.draw_text8x8(15, 125, "2) Terzo Mondo", C_ARANCIO_PREF)
    display.draw_text8x8(25, 140, "Problemi: " + dati_mondi["M3"]["problemi"], C_BIANCO)
    display.draw_text8x8(25, 155, "Pericolo: " + str(dati_mondi["M3"]["pericolo"]) + "%", C_BIANCO)
    colore_m3 = C_ROSSO_DROP if dati_mondi["M3"]["problemi"] == "SI" else C_BIO_VERDE
    display.fill_circle(210, 140, 4, colore_m3)
    display.draw_rectangle(12, 175, 216, 1, C_GRIGIO_ICONA)

def mostra_secondo_mondo():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(30 , 30 , "-----SECONDO MONDO-----" , C_GLOW_CIANO)
    display.draw_text8x8(25, 65, "Problemi: " + dati_mondi["M2"]["problemi"], C_BIANCO)
    display.draw_text8x8(25, 80, "Pericolo: " + str(dati_mondi["M2"]["pericolo"]) + "%", C_BIANCO)
    colore_m2 = C_ROSSO_DROP if dati_mondi["M2"]["problemi"] == "SI" else C_BIO_VERDE
    display.fill_circle(210, 65, 4, colore_m2)
    t_nomi = ["Bianca", "Camilla", "Pietro", "Michele", "Sbriser", "Dolcetta", "Minus", "Elisa", "Thiago", "Alfredo"]
    for i, n in enumerate(t_nomi): display.draw_text8x8(25, 100 + (i*10), f"{n} = {random.randint(1,100)}", C_BIANCO)
    display.draw_rectangle(25 , 225 , 190 , 40 , C_GLOW_CIANO)
    display.fill_rectangle(25 , 225 , 190 , 40 , C_BIANCO)
    display.draw_text8x8(25 , 241 , "risolvi problemi" , C_GLOW_CIANO)

def mostra_terzo_mondo():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(30 , 30 , "------TERZO MONDO------" , C_ARANCIO_PREF)
    display.draw_text8x8(25, 65, "Problemi: " + dati_mondi["M3"]["problemi"], C_BIANCO)
    display.draw_text8x8(25, 80, "Pericolo: " + str(dati_mondi["M3"]["pericolo"]) + "%", C_BIANCO)
    colore_m3 = C_ROSSO_DROP if dati_mondi["M3"]["problemi"] == "SI" else C_BIO_VERDE
    display.fill_circle(210, 65, 4, colore_m3)
    t_nomi = ["Sbriser", "Dolcetta", "Ivie", "Violet", "Crucco", "Elox", "Sense", "Mag"]
    for i, n in enumerate(t_nomi): display.draw_text8x8(25, 100 + (i*10), f"{n} = {random.randint(1,100)}", C_BIANCO)
    display.draw_rectangle(25 , 225 , 190 , 40 , C_ARANCIO_PREF)
    display.fill_rectangle(25 , 225 , 190 , 40 , C_BIANCO)
    display.draw_text8x8(25 , 241 , "risolvi problemi" , C_ARANCIO_PREF)

def mostra_app_notebook():
    """Interfaccia Notebook con cursore mobile e inserimento/cancellazione dinamica"""
    global testo_nota, indice_cursore
    
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(15, 20, "NOTEBOOK / APPRENTI", C_ARANCIO_PREF)
    display.draw_rectangle(10, 38, 220, 115, C_BIANCO)
    
    # Il cursore viene azzerato o allineato alla fine del testo all'avvio
    indice_cursore = len(testo_nota)
    
    while True:
        # Genera la stringa visiva unendo il testo prima e dopo il cursore con "|"
        testo_visivo = testo_nota[:indice_cursore] + "|" + testo_nota[indice_cursore:]
        
        # Pulisce l'area interna della nota prima di stampare il testo aggiornato
        display.fill_rectangle(11, 39, 218, 113, NERO_AMOLED)
        
        # Stampa su due righe (massimo 48 caratteri + 1 del cursore)
        if len(testo_visivo) <= 25:
            display.draw_text8x8(20, 48, testo_visivo, C_BIANCO)
        else:
            display.draw_text8x8(20, 48, testo_visivo[:25], C_BIANCO)
            display.draw_text8x8(20, 60, testo_visivo[25:50], C_BIANCO)
        # Resta in attesa del tocco della tastiera
        tasto = attendi_tasto_qwerty()
        
        if tasto == "OK":
            global stato_telefono, app_corrente
            stato_telefono = "HOME"
            app_corrente = None
            mostra_home_screen()
            break
            
        elif tasto == "MOVE_SX":
            if indice_cursore > 0:
                indice_cursore -= 1
                
        elif tasto == "MOVE_DX":
            if indice_cursore < len(testo_nota):
                indice_cursore += 1
                
        elif tasto == "CANC":
            if indice_cursore > 0:
                # Rimuove il carattere immediatamente a sinistra del cursore
                testo_nota = testo_nota[:indice_cursore - 1] + testo_nota[indice_cursore:]
                indice_cursore -= 1
                
        else:
            if len(testo_nota) < 100:
                # Inserisce il carattere esattamente nella posizione del cursore
                testo_nota = testo_nota[:indice_cursore] + tasto + testo_nota[indice_cursore:]
                indice_cursore += 1


print("--- PARTE 4 CARICATA: GRAPHICS (P1) OK ---")
# =============================================================================
# [PARTE 5 DI 6] - SMARTPHONE OS: INTERFACCE NUOVE APPLICAZIONI (P2)
# =============================================================================

def mostra_app_calcolatrice():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(15, 20, "CALCOLATRICE", C_ARANCIO_PREF)
    display.draw_rectangle(15, 35, 210, 30, C_BIANCO)
    if calc_risultato: display.draw_text8x8(20, 46, calc_risultato[-24:], C_GLOW_CIANO)
    else: display.draw_text8x8(20, 46, calc_espressione[-24:] if calc_espressione else "0", C_BIANCO)
    tasti = [["7", "8", "9", "/"], ["4", "5", "6", "*"], ["1", "2", "3", "-"], ["C", "0", "=", "+"]]
    for r in range(4):
        for c in range(4):
            x = 20 + (c * 53)
            y = 80 + (r * 48)
            display.draw_rectangle(x, y, 45, 40, C_GRIGIO_ICONA)
            display.draw_text8x8(x + 18, y + 16, tasti[r][c], C_BIANCO)

def mostra_app_cronometro():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(15, 30, "CRONOMETRO", C_GLOW_CIANO)
    secondi = crono_trascorso / 1000.0
    display.draw_text8x8(60, 90, "{:.2f} s".format(secondi), C_BIANCO)
    display.fill_rectangle(20, 160, 90, 40, C_VERDE_CALL)
    display.draw_text8x8(35, 176, "START/STOP", NERO_AMOLED)
    display.fill_rectangle(130, 160, 90, 40, C_ROSSO_DROP)
    display.draw_text8x8(160, 176, "RESET", C_BIANCO)

def muestra_app_lavagna():
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_rectangle(5, 40, 230, 210, C_GRIGIO_ICONA)
    display.draw_text8x8(10, 20, "LAVAGNA TOUCH", C_BIO_VERDE)
    display.fill_rectangle(170, 15, 65, 20, C_ARANCIO_PREF)
    display.draw_text8x8(188, 21, "CANC", NERO_AMOLED)

def mostra_app_love():
    """Interfaccia grafica del Calcolatore d'Affinita'"""
    applica_sfondo()
    disegna_barra_stato()
    disegna_barra_navigazione()
    display.draw_text8x8(55, 20, "TEST AFFINITA'", 0xF81F)
    
    # Cerchio P1 (In Alto)
    display.draw_circle(120, 65, 20, C_GLOW_CIANO)
    display.draw_text8x8(112, 62, "P1", C_GLOW_CIANO)
    
    # Cerchio P2 (In Basso)
    display.draw_circle(120, 245, 20, C_GLOW_CIANO)
    display.draw_text8x8(112, 242, "P2", C_GLOW_CIANO)
    
    # Schermata centrale dei risultati
    display.draw_rectangle(40, 125, 160, 50, C_GRIGIO_ICONA)
    
    if love_calcolato:
        display.draw_text8x8(95, 145, f"{love_percentuale} %", 0xF81F)
        # Rettangolo di reset
        display.fill_rectangle(85, 185, 70, 20, C_GRIGIO_ICONA)
        display.draw_text8x8(98, 191, "RESET", C_BIANCO)
    else:
        display.draw_text8x8(52, 145, "TOCCATE INSIEME", C_BIANCO)

print("--- PARTE 5 CARICATA: GRAPHICS (P2) OK ---")

# =============================================================================
# [PARTE 6 DI 7] - SMARTPHONE OS: INTERCETTAZIONE EVENTI TOUCH (LOGICA EXTRA)
# =============================================================================

def gestisci_tocco_telefono(x, y):
    global stato_telefono, app_corrente, numero_digitato, messaggio_inviato, indice_contatto_corrente
    global pagina_home, calc_espressione, calc_risultato, crono_avviato, crono_inizio, crono_trascorso, lavagna_punti
    global love_calcolato, love_percentuale
    
    if stato_telefono == "SLEEP_NERO":
        stato_telefono = "BLOCCATO"
        mostra_schermata_blocco()
        return

    # Barra di navigazione inferiore globale (Y >= 295)
    if y >= 295 and stato_telefono not in ["BLOCCATO", "INSERIMENTO_PIN"]:
        if 20 <= x <= 80: # Tasto indietro / Home
            if stato_telefono == "APP_APERTA":
                stato_telefono = "HOME"
                app_corrente = None
                mostra_home_screen()
            elif stato_telefono == "HOME":
                stato_telefono = "BLOCCATO"
                mostra_schermata_blocco()
        elif 90 <= x <= 150: # Tasto Home Centrale
            stato_telefono = "HOME"
            app_corrente = None
            mostra_home_screen()
        elif 170 <= x <= 230: # Spegnimento schermo hardware da barra
            lampeggio_conferma(led_r)
            attiva_spegnimento_schermo()
        return

    if stato_telefono == "BLOCCATO":
        if 20 <= x <= 220 and 230 <= y <= 280:
            stato_telefono = "INSERIMENTO_PIN"
            globals()['pin_inserito'] = ""
            mostra_schermata_pin()
            
    elif stato_telefono == "INSERIMENTO_PIN":
        tasti_mappa = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        contatore = 0
        for riga in range(3):
            for colonna in range(3):
                bx = 50 + (colonna * 70)
                by = 115 + (riga * 45)
                if (bx-16) <= x <= (bx+16) and (by-16) <= y <= (by+16):
                    if len(pin_inserito) < 4:
                        globals()['pin_inserito'] += tasti_mappa[contatore]
                        mostra_schermata_pin()
                        if len(pin_inserito) == 4:
                            time.sleep_ms(200)
                            if pin_inserito == PIN_CORRETTO:
                                stato_telefono = "HOME"
                                pagina_home = 1
                                mostra_home_screen()
                            else:
                                led_r.value(0); time.sleep_ms(200); led_r.value(1)
                                globals()['pin_inserito'] = ""
                                mostra_schermata_pin()
                    return
                contatore += 1
        if 20 <= x <= 65 and 245 <= y <= 270:
            globals()['pin_inserito'] = pin_inserito[:-1]
            mostra_schermata_pin()
            
    elif stato_telefono == "HOME":
        # --- GESTIONE FRECCE CAMBIO PAGINA DI DESTRA (>>) ---
        if pagina_home == 1 and 200 <= x <= 240 and 260 <= y <= 290:
            pagina_home = 2
            mostra_home_screen()
            return
        elif pagina_home == 2 and 200 <= x <= 240 and 260 <= y <= 290:
            pagina_home = 3
            mostra_home_screen()
            return
            
        # --- GESTIONE FRECCE CAMBIO PAGINA DI SINISTRA (<<) ---
        elif pagina_home == 2 and 0 <= x <= 40 and 260 <= y <= 290:
            pagina_home = 1
            mostra_home_screen()
            return
        elif pagina_home == 3 and 0 <= x <= 40 and 260 <= y <= 290:
            pagina_home = 2
            mostra_home_screen()
            return

        # --- LANCIO DELLE APP IN BASE ALLA PAGINA ATTIVA ---
        if pagina_home == 1:
            if 35 <= x <= 95 and 45 <= y <= 105:
                lampeggio_conferma(led_g)
                stato_telefono = "APP_APERTA"
                app_corrente = "CHIAMATE"
                indice_contatto_corrente = 0
                numero_digitato = RUBRICA[indice_contatto_corrente]["numero"] if len(RUBRICA) > 0 else ""
                mostra_app_chiamate()
            elif 145 <= x <= 205 and 45 <= y <= 105:
                lampeggio_conferma(led_b)
                stato_telefono = "APP_APERTA"
                app_corrente = "MESSAGGI"
                indice_contatto_corrente = 0
                messaggio_inviato = False
                mostra_app_messaggi()
            elif 35 <= x <= 95 and 135 <= y <= 195:
                # Logica monitoraggio mondi... (lascia invariato il vecchio codice)
                stato_telefono = "APP_APERTA"
                app_corrente = "CONTROLLO"
                if dati_mondi["M2"]["problemi"] == "SI" and random.randint(1,100) <= 75 :
                    dati_mondi["M2"]["problemi"] = "SI"
                    dati_mondi["M2"]["pericolo"] = random.randint(11,100)
                elif random.randint(1,100) <= 30 :
                    dati_mondi["M2"]["problemi"] = "SI"
                    dati_mondi["M2"]["pericolo"] = random.randint(11,100)
                else :
                    dati_mondi["M2"]["problemi"] = "NO"
                    dati_mondi["M2"]["pericolo"] = random.randint(1,10)
                    
                if dati_mondi["M3"]["problemi"] == "SI" and random.randint(1,100) <= 75 :
                    dati_mondi["M3"]["problemi"] = "SI"
                    dati_mondi["M3"]["pericolo"] = random.randint(11,100)
                elif random.randint(1,100) <= 30 :
                    dati_mondi["M3"]["problemi"] = "SI"
                    dati_mondi["M3"]["pericolo"] = random.randint(11,100)
                else :
                    dati_mondi["M3"]["problemi"] = "NO"
                    dati_mondi["M3"]["pericolo"] = random.randint(1,10)
                mostra_app_controllo()
            elif 145 <= x <= 205 and 135 <= y <= 195:
                lampeggio_conferma(led_r)
                attiva_spegnimento_schermo()
        
        elif pagina_home == 2:
            if 35 <= x <= 95 and 45 <= y <= 105:
                lampeggio_conferma(led_g)
                stato_telefono = "APP_APERTA"
                app_corrente = "CALCOLA"
                calc_espressione = ""
                calc_risultato = ""
                mostra_app_calcolatrice()
            elif 145 <= x <= 205 and 45 <= y <= 105:
                lampeggio_conferma(led_b)
                stato_telefono = "APP_APERTA"
                app_corrente = "CRONO"
                mostra_app_cronometro()
            elif 35 <= x <= 95 and 135 <= y <= 195:
                lampeggio_conferma(led_g)
                stato_telefono = "APP_APERTA"
                app_corrente = "LAVAGNA"
                lavagna_punti = []
                muestra_app_lavagna()
            elif 145 <= x <= 205 and 135 <= y <= 195:
                lampeggio_conferma(led_b)
                stato_telefono = "APP_APERTA"
                app_corrente = "LOVE"
                love_calcolato = False
                love_percentuale = 0
                mostra_app_love()
                
        elif pagina_home == 3:
            # CLIC SULLA NUOVA APP NOTEBOOK (Riga 1, Colonna 1)
            if 35 <= x <= 95 and 45 <= y <= 105:
                lampeggio_conferma(led_g)
                stato_telefono = "APP_APERTA"
                app_corrente = "NOTEBOOK"
                mostra_app_notebook()

            
    elif stato_telefono == "APP_APERTA":
        if app_corrente == "CHIAMATE":
            if 15 <= x <= 40 and 22 <= y <= 46 and len(RUBRICA) > 0:
                indice_contatto_corrente = (indice_contatto_corrente - 1) % len(RUBRICA)
                numero_digitato = RUBRICA[indice_contatto_corrente]["numero"]
                mostra_app_chiamate()
                return
            elif 200 <= x <= 225 and 22 <= y <= 46 and len(RUBRICA) > 0:
                indice_contatto_corrente = (indice_contatto_corrente + 1) % len(RUBRICA)
                numero_digitato = RUBRICA[indice_contatto_corrente]["numero"]
                mostra_app_chiamate()
                return
            tasti_mappa = [["1","2","3"], ["4","5","6"], ["7","8","9"]]
            for riga in range(3):
                for colonna in range(3):
                    bx = 50 + (colonna * 70)
                    by = 110 + (riga * 45)
                    if (bx-16) <= x <= (bx+16) and (by-16) <= y <= (by+16):
                        if len(numero_digitato) < 15:
                            numero_digitato += tasti_mappa[riga][colonna]
                            mostra_app_chiamate()
                        return
            if 15 <= x <= 75 and 240 <= y <= 270:
                numero_digitato = numero_digitato[:-1]
                mostra_app_chiamate()
            elif 85 <= x <= 125 and 240 <= y <= 270:
                lampeggio_conferma(led_g)
                led_r.value(1); led_g.value(0); led_b.value(1) # LED Verde chiamata
            elif 135 <= x <= 175 and 240 <= y <= 270:
                lampeggio_conferma(led_r)
                spegni_led_totale() # Spegne chiamata
                
        elif app_corrente == "MESSAGGI":
            if 15 <= x <= 40 and 22 <= y <= 46 and len(RUBRICA) > 0:
                indice_contatto_corrente = (indice_contatto_corrente - 1) % len(RUBRICA)
                messaggio_inviato = False
                mostra_app_messaggi()
                return
            elif 200 <= x <= 225 and 22 <= y <= 46 and len(RUBRICA) > 0:
                indice_contatto_corrente = (indice_contatto_corrente + 1) % len(RUBRICA)
                messaggio_inviato = False
                mostra_app_messaggi()
                return
            if 30 <= x <= 210 and 175 <= y <= 205:
                messaggio_inviato = True
                mostra_app_messaggi()

        elif app_corrente == "CONTROLLO":
            if 10 <= x <= 230 and 40 <= y <= 99:
                stato_telefono = "APP_APERTA"; app_corrente = "2M"; mostra_secondo_mondo()
            elif 10 <= x <= 230 and 105 <= y <= 180:
                stato_telefono = "APP_APERTA"; app_corrente = "3M"; mostra_terzo_mondo()
        elif app_corrente == "2M":
            if 25 <= x <= 215 and 225 <= y <= 265:
                time.sleep(5)
                dati_mondi["M2"]["problemi"] = "NO"; dati_mondi["M2"]["pericolo"] = random.randint(0, 10)
                time.sleep(0.5); mostra_secondo_mondo()
        elif app_corrente == "3M":
            if 25 <= x <= 215 and 225 <= y <= 265:
                time.sleep(5)
                dati_mondi["M3"]["problemi"] = "NO"; dati_mondi["M3"]["pericolo"] = random.randint(0, 10)
                time.sleep(0.5); mostra_terzo_mondo()

        elif app_corrente == "CALCOLA":
            tasti = [["7", "8", "9", "/"], ["4", "5", "6", "*"], ["1", "2", "3", "-"], ["C", "0", "=", "+"]]
            for r in range(4):
                for c in range(4):
                    bx = 20 + (c * 53)
                    by = 80 + (r * 48)
                    if bx <= x <= (bx+45) and by <= y <= (by+40):
                        valore = tasti[r][c]
                        if valore == "C":
                            calc_espressione = ""
                            calc_risultato = ""
                        elif valore == "=":
                            try: calc_risultato = str(eval(calc_espressione))
                            except: calc_risultato = "Errore"
                            calc_espressione = ""
                        else:
                            if calc_risultato:
                                calc_risultato = ""
                                calc_espressione += valore
                                mostra_app_calcolatrice()
                            return
                        
# =============================================================================
# [PARTE 7 DI 7] - SMARTPHONE OS: ANIMAZIONE LOVE, APP EXTRA E LOOP FINALE
# =============================================================================

def avvia_animazione_love(cheat):
    """Genera l'animazione dei pallini azzurri che convergono al centro alimentando la percentuale"""
    global love_calcolato, love_percentuale
    
    # Svuota l'area centrale per l'animazione
    display.fill_rectangle(41, 126, 158, 48, NERO_AMOLED)
    if cheat == False :
        target_love = random.randint(0 , 100)# Numero casuale finale dell'affinità
    else :
        target_love = random.randint(90 , 100)
    # Ciclo di animazione dei pallini azzurri (15 passaggi cinetici)
    for passo in range(1, 16):
        # Calcolo posizioni dei pallini azzurri che vanno dai cerchi verso il centro (Y=150)
        y_cima = 65 + int((150 - 65) * (passo / 15))
        y_fondo = 245 - int((245 - 150) * (passo / 15))
        
        # Accende il LED blu a intermittenza per l'effetto di caricamento energetico
        led_b.value(0) if passo % 2 == 0 else led_b.value(1)
        
        # Disegna i pallini azzurri (C_GLOW_CIANO)
        display.fill_circle(120, y_cima, 3, C_GLOW_CIANO)
        display.fill_circle(120, y_fondo, 3, C_GLOW_CIANO)
        
        # Calcolo percentuale parziale che cresce in tempo reale
        percentuale_parziale = int(target_love * (passo / 15))
        display.fill_rectangle(80, 140, 80, 20, NERO_AMOLED)
        display.draw_text8x8(100, 145, str(percentuale_parziale) + " %", C_BIANCO)
        
        time.sleep_ms(120) # Velocità dello scorrimento dei pallini
        
        # Cancella i pallini vecchi lasciando lo schermo pulito per il passo successivo
        display.fill_circle(120, y_cima, 3, NERO_AMOLED)
        display.fill_circle(120, y_fondo, 3, NERO_AMOLED)
        
    spegni_led_totale()
    globals()['love_percentuale'] = target_love
    globals()['love_calcolato'] = True
    mostra_app_love()

def gestisci_tocco_applicazioni_extra(x, y):
    """Sotto-gestore touch dedicato esclusivamente alle funzioni di Cronometro, Lavagna e Love"""
    global stato_telefono, app_corrente, crono_avviato, crono_inizio, crono_trascorso, lavagna_punti
    global love_calcolato, love_percentuale
    
    if stato_telefono == "APP_APERTA":
        if app_corrente == "CRONO":
            if 20 <= x <= 110 and 160 <= y <= 200:
                if not crono_avviato:
                    crono_inizio = time.ticks_ms() - crono_trascorso
                    crono_avviato = True
                else:
                    crono_trascorso = time.ticks_ms() - crono_inizio
                    crono_avviato = False
                mostra_app_cronometro()
            elif 130 <= x <= 220 and 160 <= y <= 200:
                crono_avviato = False
                crono_trascorso = 0
                mostra_app_cronometro()

        elif app_corrente == "LAVAGNA":
            if 170 <= x <= 235 and 15 <= y <= 35:
                globals()['lavagna_punti'] = []
                muestra_app_lavagna()
                return
            if 7 <= x <= 230 and 42 <= y <= 248:
                lavagna_punti.append((x, y))
                display.fill_circle(x, y, 2, C_BIANCO)
                
        elif app_corrente == "LOVE":
            # Controllo pressione tasto RESET
            if love_calcolato and 85 <= x <= 155 and 185 <= y <= 205:
                globals()['love_calcolato'] = False
                globals()['love_percentuale'] = 0
                mostra_app_love()
                return
                
            # Rilevamento attivazione: tocco nel cerchio P1 o nel cerchio P2
            if not love_calcolato:
                if (100 <= x <= 140 and 45 <= y <= 85) or (100 <= x <= 140 and 225 <= y <= 265) :
                    cheat = False
                    avvia_animazione_love(cheat)

# --- 2.7 LOOP DI ESECUZIONE CONTINUO E AVVIO INTERFACCIA ---
mostra_schermata_blocco()
ultimo_tocco = 0

print("--- PARTE 7 CARICATA: SMARTPHONE OS IN ESECUZIONE (LAVAGNA + LOVE DIRETTA) ---")

while True:
    coordinate = leggi_touch()
    
    if stato_telefono == "APP_APERTA" and app_corrente == "CRONO" and crono_avviato:
        crono_trascorso = time.ticks_ms() - crono_inizio
        secondi = crono_trascorso / 1000.0
        display.fill_rectangle(50, 85, 140, 20, NERO_AMOLED)
        display.draw_text8x8(60, 90, "{:.2f} s".format(secondi), C_BIANCO)
        time.sleep_ms(30)
        
    if coordinate is not None:
        tempo_attuale = time.ticks_ms()
        if time.ticks_diff(tempo_attuale, ultimo_tocco) > 120:
            tx, ty = coordinate
            
            gestisci_tocco_telefono(tx, ty)
            gestisci_tocco_applicazioni_extra(tx, ty)
            
            ultimo_tocco = tempo_attuale
            if app_corrente != "LAVAGNA" and app_corrente != "LOVE":
                while leggi_touch() is not None:
                    time.sleep_ms(10)
    time.sleep_ms(10)
