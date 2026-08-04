import machine
from machine import SPI, SoftSPI, Pin
import time
import ili9341

# --- CONFIGURAZIONE HARDWARE ---
TFT_MISO, TFT_MOSI, TFT_CLK = 12, 13, 14
TFT_CS, TFT_DC, TFT_RST, TFT_BCKL = 15, 2, 4, 21

backlight = Pin(TFT_BCKL, Pin.OUT, value=1)

spi = SPI(1, baudrate=40000000, sck=Pin(TFT_CLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
display = ili9341.Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=Pin(TFT_RST), width=240, height=320, rotation=0)

TP_CLK, TP_MISO, TP_MOSI, TP_CS = 25, 39, 32, Pin(33, Pin.OUT, value=1)
spi_touch = SoftSPI(baudrate=1000000, sck=Pin(TP_CLK), mosi=Pin(TP_MOSI), miso=Pin(TP_MISO))

# --- TAVOLOZZA COLORI WINDOWS ---
WIN_SFONDO = 0x03EF     # Blu classico Windows / Celeste
WIN_TASKBAR = 0x10A2    # Grigio scuro / Nero Taskbar
WIN_START = 0x041F      # Blu acceso per il tasto Start
WIN_FINESTRA = 0xFFFF   # Bianco interno finestre
WIN_BARRA_TITOLO = 0x229F # Blu scuro per i titoli finestre
ROSSO_CHIUDI = 0xF000
GRIGIO_CHIARO = 0xCE79
NERO = 0x0000

# --- APPLICAZIONI SUL DESKTOP ---
lista_app = [
    {"nome": "Cestino", "colore": GRIGIO_CHIARO, "x1": 20, "y1": 30, "x2": 70, "y2": 80},
    {"nome": "App Store", "colore": WIN_START, "x1": 100, "y1": 30, "x2": 150, "y2": 80}
]

# Stati possibili: "desktop", "start_open", "Cestino", "App Store"
stato_attuale = "desktop"

def applica_sfondo():
    """Ridisegna lo sfondo del desktop"""
    display.fill_rectangle(0, 0, 240, 280, WIN_SFONDO)

def disegna_taskbar():
    """Disegna la barra delle applicazioni in basso con il tasto Start"""
    # Barra grigia/nera di fondo (altezza 40 pixel in basso)
    display.fill_rectangle(0, 280, 240, 40, WIN_TASKBAR)
    # Pulsante Start (rettangolo azzurro sulla sinistra)
    display.fill_rectangle(5, 285, 45, 30, WIN_START)
    # Linea di separazione superiore
    display.fill_rectangle(0, 280, 240, 1, GRIGIO_CHIARO)

def disegna_desktop():
    """Disegna l'intera interfaccia di Windows Home"""
    applica_sfondo()
    disegna_taskbar()
    
    # Icone sul desktop
    for app in lista_app:
        display.fill_rectangle(app["x1"], app["y1"], app["x2"] - app["x1"], app["y2"] - app["y1"], app["colore"])

def gestisci_menu_start(apri):
    """Mostra o nasconde la finestra del Menu Start sopra il desktop"""
    if apri:
        # Finestra pop-up del menu Start (in basso a sinistra)
        display.fill_rectangle(5, 120, 120, 155, WIN_TASKBAR)
        # Bordo interno o elementi finti nel menu Start
        display.fill_rectangle(15, 135, 100, 25, WIN_START) # Elemento finto 1
        display.fill_rectangle(15, 175, 100, 25, GRIGIO_CHIARO) # Elemento finto 2
    else:
        # Se lo chiudiamo, ripristiniamo la porzione di desktop coperta
        disegna_desktop()

def apri_finestra_windows(nome_app):
    """Disegna una finestra stile Windows centrata nello schermo"""
    applica_sfondo()
    disegna_taskbar() # Mantiene la taskbar visibile sotto
    
    # Corpo principale della finestra
    # Coordinate finestra: X da 15 a 225, Y da 40 a 240
    display.fill_rectangle(15, 40, 210, 200, WIN_FINESTRA)
    
    # Barra del titolo blu
    display.fill_rectangle(15, 40, 210, 25, WIN_BARRA_TITOLO)
    
    # Pulsante di chiusura rosso "X" (in alto a destra della finestra)
    display.fill_rectangle(195, 42, 28, 21, ROSSO_CHIUDI)
    
    # Contenuto interno finto per differenziare le app
    if nome_app == "Cestino":
        display.fill_rectangle(40, 100, 50, 50, GRIGIO_CHIARO)
    elif nome_app == "App Store":
        display.fill_rectangle(40, 90, 160, 40, WIN_SFONDO)
        display.fill_rectangle(40, 150, 160, 40, WIN_START)

def leggi_touch():
    """Legge il touch screen e restituisce X e Y reali"""
    TP_CS.value(0)
    spi_touch.write(b'\x90')
    rx = spi_touch.read(2)
    spi_touch.write(b'\xD0')
    ry = spi_touch.read(2)
    TP_CS.value(1)
    
    gx = int.from_bytes(rx, 'big') >> 4
    gy = int.from_bytes(ry, 'big') >> 4
    
    if gx != 2047 and gx > 100 and gy > 100:
        px = 240 - int((1823 - gy) * 240 / 1658)
        py = int((1812 - gx) * 320 / 1682)
        return max(0, min(px, 240)), max(0, min(py, 320))
    return None

# --- ACCENSIONE ---
disegna_desktop()

# --- CICLO EVENTI OS ---
while True:
    coordinate = leggi_touch()
    
    if coordinate is not None:
        tx, ty = coordinate
        
        # 1. GESTIONE TOCCO SULLA TASKBAR (Sempre attiva tranne quando un'app è aperta)
        if ty >= 280 and stato_attuale != "Cestino" and stato_attuale != "App Store":
            # Se premiamo il tasto START (X: 5-50)
            if 5 <= tx <= 50:
                if stato_attuale == "desktop":
                    stato_attuale = "start_open"
                    gestisci_menu_start(True)
                elif stato_attuale == "start_open":
                    stato_attuale = "desktop"
                    gestisci_menu_start(False)
                time.sleep(0.4)
                continue

        # 2. GESTIONE SE IL MENU START È APERTO
        if stato_attuale == "start_open":
            # Se tocchi fuori dal menu start, chiudilo
            if not (5 <= tx <= 125 and 120 <= ty <= 275):
                stato_attuale = "desktop"
                gestisci_menu_start(False)
                time.sleep(0.4)

        # 3. GESTIONE DESKTOP (Icone principali)
        elif stato_attuale == "desktop":
            for app in lista_app:
                if app["x1"] <= tx <= app["x2"] and app["y1"] <= ty <= app["y2"]:
                    stato_attuale = app["nome"]
                    apri_finestra_windows(stato_attuale)
                    time.sleep(0.4)
                    break

        # 4. GESTIONE DENTRO UNA FINESTRA APP (Pulsante Chiudi)
        elif stato_attuale in ["Cestino", "App Store"]:
            # Il pulsante rosso della finestra si trova a X: 195-223, Y: 42-63
            if 195 <= tx <= 225 and 42 <= ty <= 65:
                stato_attuale = "desktop"
                disegna_desktop()
                time.sleep(0.4)

    time.sleep(0.02)
