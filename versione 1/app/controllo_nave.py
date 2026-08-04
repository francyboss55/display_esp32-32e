import machine
from machine import Pin, SPI, SoftSPI
import ili9341
import time
import random

# =========================================================================
# 1. CONFIGURAZIONE HARDWARE (DISPLAY E TOUCH CON VALORI CALIBRATI)
# =========================================================================
TFT_MISO, TFT_MOSI, TFT_CLK = 12, 13, 14
TFT_CS, TFT_DC, TFT_RST, TFT_BCKL = 15, 2, 4, 21

Pin(TFT_BCKL, Pin.OUT).value(1) 

spi = SPI(1, baudrate=40000000, sck=Pin(TFT_CLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
display = ili9341.Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=Pin(TFT_RST), width=320, height=240, rotation=90)

TP_CLK, TP_MISO, TP_MOSI, TP_CS = 25, 39, 32, Pin(33, Pin.OUT)
TP_CS.value(1)
spi_touch = SoftSPI(baudrate=1000000, sck=Pin(TP_CLK), mosi=Pin(TP_MOSI), miso=Pin(TP_MISO))

# Inizializzazione Pin LED RGB
led_r = Pin(22, Pin.OUT, value=1)
led_g = Pin(16, Pin.OUT, value=1)
led_b = Pin(17, Pin.OUT, value=1)

def controlla_led_fisico(stato):
    if stato == "SPARO":
        led_r.value(0); led_g.value(1); led_b.value(1)
    elif stato is True or stato == "ACCESO":
        led_r.value(0); led_g.value(0); led_b.value(0)
    else:
        led_r.value(1); led_g.value(1); led_b.value(1)

def leggi_touch():
    TP_CS.value(0)
    spi_touch.write(b'\x90')
    rx = spi_touch.read(2)
    spi_touch.write(b'\xD0')
    ry = spi_touch.read(2)
    TP_CS.value(1)
    
    gx = int.from_bytes(rx, 'big') >> 4
    gy = int.from_bytes(ry, 'big') >> 4
    
    if gx != 2047 and gx > 100 and gy > 100:
        px = int((1800 - gx) * 320 / 1650)
        py = int((1800 - gy) * 240 / 1550)
        return max(0, min(px, 320)), max(0, min(py, 240))
    return None

# =========================================================================
# 2. PALETTE COLORI INTERFACCIA
# =========================================================================
S_DEEP_SPACE  = ili9341.color565(5, 5, 12)       
C_GLOW_CIANO  = ili9341.color565(0, 240, 255)   
C_NEON_ROSA   = ili9341.color565(255, 0, 127)   
C_AMBRA_ALER  = ili9341.color565(255, 170, 0)   
C_BIO_VERDE   = ili9341.color565(0, 255, 130)   
C_QUANT_VIOLA = ili9341.color565(170, 0, 255)   
C_GRIGIO_COR  = ili9341.color565(40, 45, 60)    
C_BIANCO      = ili9341.color565(255, 255, 255)
C_ROSSO_FIRE  = ili9341.color565(255, 0, 0)     

# =========================================================================
# 3. MEMORIZZAZIONE PARAMETRI INTERATTIVI (DATI DI BORDO)
# =========================================================================
ultimo_tocco_rilasciato = True
lampadina_accesa = False          
schermata_attuale = "PRINCIPALE"

laser_carica = 50          
laser_tipo_munizione = 0   
munizioni_nomi = ["PLASMA", "LASER", "FLUX"]

# Modulo Globo con calcolo dinamico della distanza (30 secondi per ogni salto)
mondo_attuale = 0          # Il pianeta di partenza/dove si trova la nave
mondo_selezionato = 0      
nomi_mondi = ["1 mondo", "2 mondo", "3 mondo", "invasione zombie"]
tempi_secondi = [0, 0, 0, 0]  # Inizializzati a 0, verranno calcolati al momento del tocco


cuore_ossigeno = 98       
cuore_battiti = 72        

scudo_livello = 3         
borsa_selezionata = -1

def disegna_sfondo_immagine():
    display.clear(S_DEEP_SPACE)

# =========================================================================
# 4. FUNZIONI GRAFICHE BASE E PLANCIA PRINCIPALE
# =========================================================================

def formatta_tempo(secondi):
    """Converte i secondi in stringhe leggibili basate sulla tua lista"""
    if secondi <= 0:
        return "0 sec"
    elif secondi < 60:
        return str(secondi) + " sec"
    else:
        minuti = secondi // 60
        restanti_sec = secondi % 60
        if restanti_sec == 0:
            return str(minuti) + " m"
        else:
            return str(minuti) + "m," + str(restanti_sec) + "sec"

def aggiorna_tacche_modulo(modulo, attivi):
    config = {
        "TORRETTA": (8, 46, C_AMBRA_ALER), "GLOBO": (144, 46, C_GLOW_CIANO),
        "CUORE": (280, 46, C_NEON_ROSA), "SCUDO": (8, 188, C_QUANT_VIOLA),
        "BORSA": (280, 188, C_BIO_VERDE)
    }
    if modulo in config:
        x_start, y, colore = config[modulo]
        c = C_BIANCO if attivi else colore
        for i in range(3):
            display.fill_rectangle(x_start + (i * 12), y, 8, 4, c)
            display.draw_rectangle(x_start + (i * 12), y, 8, 4, C_GRIGIO_COR)

def disegna_lampadina(colore):
    display.fill_circle(160, 75, 10, colore) 
    if colore != C_BIANCO: display.fill_circle(160, 75, 8, S_DEEP_SPACE)
    display.fill_rectangle(159, 71, 2, 8, C_BIANCO)       
    display.fill_rectangle(154, 85, 12, 8, C_GRIGIO_COR)

def disegna_interruttore(colore):
    display.draw_circle(160, 204, 32, C_GRIGIO_COR)
    display.draw_circle(160, 204, 31, colore)
    display.fill_circle(160, 206, 15, colore)
    display.fill_circle(160, 206, 11, S_DEEP_SPACE)      
    display.fill_rectangle(158, 188, 5, 20, C_BIANCO)    

def disegna_pulsante_indietro():
    display.fill_rectangle(10, 195, 100, 35, C_GRIGIO_COR)
    display.draw_rectangle(10, 195, 100, 35, C_AMBRA_ALER)
    display.fill_rectangle(25, 212, 25, 2, C_BIANCO)
    display.fill_rectangle(25, 208, 2, 10, C_BIANCO)

def disegna_plancia_principale():
    disegna_sfondo_immagine()
    display.draw_rectangle(0, 0, 320, 240, C_GRIGIO_COR)
    display.draw_rectangle(1, 1, 318, 238, C_GLOW_CIANO)
    for mod in ["TORRETTA", "GLOBO", "CUORE", "SCUDO", "BORSA"]:
        aggiorna_tacche_modulo(mod, False)
    display.fill_rectangle(12, 10, 14, 20, C_AMBRA_ALER)
    display.fill_rectangle(26, 17, 10, 6, C_BIANCO)      
    display.draw_rectangle(12, 10, 14, 20, C_GRIGIO_COR)
    display.draw_circle(160, 20, 13, C_GLOW_CIANO)
    display.fill_rectangle(146, 19, 28, 2, C_GLOW_CIANO) 
    display.fill_rectangle(159, 6, 2, 28, C_GLOW_CIANO)  
    display.fill_circle(288, 16, 5, C_NEON_ROSA)
    display.fill_circle(300, 16, 5, C_NEON_ROSA)
    display.fill_rectangle(284, 18, 21, 6, C_NEON_ROSA)
    for i in range(12): display.fill_rectangle(283 + i, 24 + i, 23 - (i * 2), 1, C_NEON_ROSA)
    display.fill_rectangle(10, 202, 26, 4, C_QUANT_VIOLA)
    display.fill_rectangle(10, 206, 4, 12, C_QUANT_VIOLA)
    display.fill_rectangle(32, 206, 4, 12, C_QUANT_VIOLA)
    for i in range(11): display.fill_rectangle(13 + i, 218 + i, 20 - (i * 2), 1, C_QUANT_VIOLA)
    display.draw_rectangle(286, 202, 22, 6, C_GRIGIO_COR) 
    display.fill_rectangle(282, 208, 30, 22, C_BIO_VERDE) 
    display.fill_rectangle(294, 214, 6, 8, C_GRIGIO_COR)  
    
    if lampadina_accesa: disegna_lampadina(C_BIANCO)
    else: disegna_lampadina(C_BIO_VERDE)
    
    # Stampa dinamica della destinazione e del tempo formattato
    dest_attuale = nomi_mondi[mondo_selezionato]
    tempo_attuale = formatta_tempo(tempi_secondi[mondo_selezionato])
    
    x_dest = 160 - (len("DEST: " + dest_attuale) * 4)
    x_time = 160 - (len("ETA: " + tempo_attuale) * 4)
    
    # Rettangolo nero di pulizia per evitare sovrapposizioni di testo durante il countdown
    display.fill_rectangle(40, 112, 240, 35, S_DEEP_SPACE)
    display.draw_text8x8(x_dest, 115, "DEST: " + dest_attuale, C_GLOW_CIANO)
    display.draw_text8x8(x_time, 135, "TEM: " + tempo_attuale, C_BIANCO)
    
    disegna_interruttore(C_GLOW_CIANO)

# =========================================================================
# 5. SCHERMATE GEOMETRICHE INTERATTIVE SECONDARIE
# =========================================================================
def disegna_struttura_schermata(colore_bordo):
    disegna_sfondo_immagine()
    display.draw_rectangle(0, 0, 320, 240, C_GRIGIO_COR)
    display.draw_rectangle(2, 2, 316, 236, colore_bordo)
    disegna_pulsante_indietro()

def mostra_schermata_torretta(lampo_sparo=False):
    bordo = C_ROSSO_FIRE if lampo_sparo else C_AMBRA_ALER
    disegna_struttura_schermata(bordo)
    display.fill_rectangle(25, 40, 110, 50, C_GRIGIO_COR)
    display.draw_rectangle(25, 40, 110, 50, C_AMBRA_ALER)
    display.fill_rectangle(75, 50, 10, 30, C_BIANCO)
    display.fill_rectangle(185, 40, 110, 50, C_GRIGIO_COR)
    display.draw_rectangle(185, 40, 110, 50, C_GLOW_CIANO)
    for m in range(3):
        col = C_BIANCO if m == laser_tipo_munizione else C_GRIGIO_COR
        display.fill_circle(215 + (m * 30), 65, 6, col)
    colore_grilletto = C_ROSSO_FIRE if laser_carica >= 25 else C_GRIGIO_COR
    display.fill_rectangle(80, 110, 160, 60, colore_grilletto)
    display.draw_rectangle(80, 110, 160, 60, C_BIANCO)
    display.draw_circle(160, 140, 15, C_BIANCO)
    display.draw_rectangle(130, 195, 150, 15, C_GRIGIO_COR)
    if laser_carica > 0:
        larghezza_barra = int(laser_carica * 146 / 100)
        display.fill_rectangle(132, 197, larghezza_barra, 11, C_AMBRA_ALER)

def mostra_schermata_globo():
    disegna_struttura_schermata(C_GLOW_CIANO)
    for i in range(4):
        y_pulsante = 25 + (i * 42)
        colore_sfondo = C_GRIGIO_COR
        colore_bordo = C_GLOW_CIANO if i == mondo_selezionato else C_GRIGIO_COR
        colore_blocchi = C_BIANCO if i == mondo_selezionato else C_GLOW_CIANO
        colore_blocchi_zombie = C_BIANCO if i == mondo_selezionato else C_BIO_VERDE
        
        display.fill_rectangle(40, y_pulsante, 260, 34, colore_sfondo)
        display.draw_rectangle(40, y_pulsante, 260, 34, colore_bordo)
        
        colore_pallino = C_GLOW_CIANO if i == mondo_selezionato else S_DEEP_SPACE
        display.fill_circle(55, y_pulsante + 17, 5, colore_pallino)
        display.draw_circle(55, y_pulsante + 17, 5, C_GLOW_CIANO)
        
        display.draw_text8x8(70, y_pulsante + 13, nomi_mondi[i], C_BIANCO if i == mondo_selezionato else C_GLOW_CIANO)
        
        for t in range(i + 1):
            if i == 3:
                display.fill_rectangle(210 + (t * 20), y_pulsante + 12, 12, 10, colore_blocchi_zombie)
            else:
                display.fill_rectangle(210 + (t * 20), y_pulsante + 12, 12, 10, colore_blocchi)

def mostra_schermata_cuore():
    disegna_struttura_schermata(C_NEON_ROSA)
    display.draw_rectangle(40, 35, 240, 22, C_GRIGIO_COR)
    larghezza_o2 = int(cuore_ossigeno * 236 / 100)
    display.fill_rectangle(42, 37, larghezza_o2, 18, C_GLOW_CIANO)
    
    display.draw_rectangle(100, 100, 120, 40, C_GRIGIO_COR)
    if cuore_battiti > 50:
        larghezza_bpm = int((cuore_battiti - 50) * 116 / 110)
        display.fill_rectangle(102, 102, max(1, larghezza_bpm), 36, C_NEON_ROSA)
        
    display.fill_rectangle(40, 100, 50, 40, C_GRIGIO_COR)
    display.draw_rectangle(40, 100, 50, 40, C_NEON_ROSA)
    display.fill_rectangle(50, 119, 30, 2, C_BIANCO)
    
    display.fill_rectangle(230, 100, 50, 40, C_GRIGIO_COR)
    display.draw_rectangle(230, 100, 50, 40, C_NEON_ROSA)
    display.fill_rectangle(240, 119, 30, 2, C_BIANCO)
    display.fill_rectangle(254, 105, 2, 30, C_BIANCO)
    
    display.fill_rectangle(230, 170, 50, 40, C_GRIGIO_COR)
    display.draw_rectangle(230, 170, 50, 40, C_NEON_ROSA)

def mostra_schermata_scudo():
    disegna_struttura_schermata(C_QUANT_VIOLA)
    for i in range(4):
        x_cella = 40 + (i * 62)
        display.draw_rectangle(x_cella, 80, 55, 40, C_GRIGIO_COR)
        if i < scudo_livello:
            display.fill_rectangle(x_cella + 3, 83, 49, 34, C_QUANT_VIOLA)

def mostra_schermata_borsa():
    disegna_struttura_schermata(C_BIO_VERDE)
    for riga in range(3):
        for colonna in range(4):
            idx = colonna + (riga * 4)
            x_slot = 45 + (colonna * 60)
            y_slot = 35 + (riga * 45)
            if idx == borsa_selezionata:
                colore_bordo = C_BIANCO
            else:
                colore_bordo = C_BIO_VERDE
            display.draw_rectangle(x_slot, y_slot, 50, 35, colore_bordo)
            display.fill_rectangle(x_slot + 3, y_slot + 3, 10, 10, C_GLOW_CIANO)

disegna_plancia_principale()
controlla_led_fisico(lampadina_accesa)
print("=== MOTORE GRAFICO GEOMETRICO COMPILATO CON SUCCESSO ===")

# =========================================================================
# 6. CICLO LOGICO DI RILEVAMENTO EVENTI E COUNTDOWN DELLA NAVE
# =========================================================================
ultimo_controllo_tempo = time.ticks_ms()

while True :
    # --- BLOCCO TIMER ASINCRONO: SCADENZA DEL TEMPO OGNI SECONDO (1000ms) ---
    tempo_corrente = time.ticks_ms()
    if time.ticks_diff(tempo_corrente, ultimo_controllo_tempo) >= 1000:
        ultimo_controllo_tempo = tempo_corrente
        
        # Se la destinazione selezionata ha ancora tempo rimanente, diminuisci di 1 secondo
        if tempi_secondi[mondo_selezionato] > 0:
            tempi_secondi[mondo_selezionato] -= 1
            
            # Se il countdown raggiunge lo zero, la nave è arrivata nel nuovo mondo
            if tempi_secondi[mondo_selezionato] == 0:
                mondo_attuale = mondo_selezionato
            
            # Se l'utente si trova sulla plancia principale, aggiorna i testi a schermo in tempo reale
            if schermata_attuale == "PRINCIPALE":
                dest_attuale = nomi_mondi[mondo_selezionato]
                tempo_attuale = formatta_tempo(tempi_secondi[mondo_selezionato])
                
                x_dest = 160 - (len("DEST: " + dest_attuale) * 4)
                x_time = 160 - (len("ETA: " + tempo_attuale) * 4)
                
                display.fill_rectangle(40, 112, 240, 35, S_DEEP_SPACE)
                display.draw_text8x8(x_dest, 115, "DEST: " + dest_attuale, C_GLOW_CIANO)
                display.draw_text8x8(x_time, 135, "TEM: " + tempo_attuale, C_BIANCO)


    tocco = leggi_touch()
    
    if tocco and ultimo_tocco_rilasciato:
        x, y = tocco
        ultimo_tocco_rilasciato = False  
        
        # --- FILTRO TOCCHI: PLANCIA PRINCIPALE ---
        if schermata_attuale == "PRINCIPALE":
            if 130 <= x <= 190 and y <= 45:
                aggiorna_tacche_modulo("GLOBO", True); time.sleep_ms(200)
                schermata_attuale = "GLOBO"; mostra_schermata_globo()
            elif 130 <= x <= 190 and 65 <= y <= 115:
                lampadina_accesa = not lampadina_accesa
                disegna_lampadina(C_BIANCO if lampadina_accesa else C_BIO_VERDE)
                controlla_led_fisico(lampadina_accesa)
            elif 120 <= x <= 200 and y >= 160:
                disegna_interruttore(C_NEON_ROSA); time.sleep_ms(250); disegna_interruttore(C_GLOW_CIANO)
            else:
                is_alto = (y <= 120)  
                is_destra = (x >= 160) 
                if is_alto and not is_destra:
                    schermata_attuale = "TORRETTA"; mostra_schermata_torretta()
                elif is_alto and is_destra:
                    schermata_attuale = "CUORE"; mostra_schermata_cuore()
                elif not is_alto and not is_destra:
                    schermata_attuale = "SCUDO"; mostra_schermata_scudo()
                elif not is_alto and is_destra:
                    schermata_attuale = "BORSA"; mostra_schermata_borsa()
            time.sleep_ms(150)

        # --- FILTRO TOCCHI: SOTTO-SCHERMATE INTERATTIVE ---
        else:
            if 10 <= x <= 110 and 195 <= y <= 230:
                schermata_attuale = "PRINCIPALE"
                display.clear(S_DEEP_SPACE)
                disegna_plancia_principale()
                time.sleep_ms(200)
            
            elif schermata_attuale == "TORRETTA":
                if 25 <= x <= 135 and 40 <= y <= 90:
                    if laser_carica < 100: laser_carica = min(100, laser_carica + 25); mostra_schermata_torretta()
                elif 185 <= x <= 295 and 40 <= y <= 90:
                    laser_tipo_munizione = (laser_tipo_munizione + 1) % 3; mostra_schermata_torretta()
                elif 80 <= x <= 240 and 110 <= y <= 170:
                    if laser_carica >= 25:
                        laser_carica -= 25
                        controlla_led_fisico("SPARO")
                        mostra_schermata_torretta(lampo_sparo=True)
                        time.sleep_ms(100)
                        mostra_schermata_torretta(lampo_sparo=False)
                        controlla_led_fisico(lampadina_accesa)

            elif schermata_attuale == "GLOBO":
                if 40 <= x <= 300 and 25 <= y <= 193:
                    pianeta_premuto = int((y - 25) / 42)
                    if 0 <= pianeta_premuto <= 3: 
                        mondo_selezionato = pianeta_premuto
                        
                        # Calcola la distanza in passaggi tra i due mondi
                        distanza = abs(mondo_selezionato - mondo_attuale)
                        
                        # Ogni mondo di distanza aggiunge 30 secondi di viaggio
                        tempi_secondi[mondo_selezionato] = distanza * 30
                        
                        mostra_schermata_globo()

            
            elif schermata_attuale == "CUORE":
                if 40 <= x <= 280 and 35 <= y <= 57:
                    cuore_ossigeno = 95 if cuore_ossigeno == 98 else 98; mostra_schermata_cuore()
                elif 40 <= x <= 90 and 100 <= y <= 140:
                    if cuore_battiti > 50: cuore_battiti -= 4; mostra_schermata_cuore()
                elif 230 <= x <= 280 and 100 <= y <= 140:
                    if cuore_battiti < 160: cuore_battiti += 4; mostra_schermata_cuore()
                elif 230 <= x <= 280 and 170 <= y <= 220:
                    cuore_ossigeno = 98       
                    cuore_battiti = 72
                    mostra_schermata_cuore()
            
            elif schermata_attuale == "SCUDO":
                if 40 <= x <= 280 and 80 <= y <= 120:
                    cella_premuta = int((x - 40) / 62)
                    scudo_livello = max(0, min(cella_premuta + 1, 4)); mostra_schermata_scudo()
            
            elif schermata_attuale == "BORSA":
                if 45 <= x <= 285 and 35 <= y <= 170:
                    colonna_sel = int((x - 45) / 60)
                    riga_sel = int((y - 35) / 45)
                    borsa_selezionata = colonna_sel + (riga_sel * 4); mostra_schermata_borsa()
                    
    elif not tocco:
        ultimo_tocco_rilasciato = True 
                
    time.sleep_ms(25)
