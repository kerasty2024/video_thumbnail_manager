import tkinter as tk
from tkinter import ttk
import webbrowser
from pathlib import Path
from PIL import Image, ImageTk
from loguru import logger
from ..utils import resize_image
from .tooltip import Tooltip

class CryptoManager:
    """Manages cryptocurrency addresses and their corresponding QR codes."""
    def __init__(self, contents_path):
        self.contents_path = Path(contents_path)
        self.crypto_data = {
            "BTC": {
                "address": "bc1qn72yvftnuh7jgjnn9x848pzhhywasxmqt5c7wp",
                "qr_file": "BTC_QR.jpg"
            },
            "ETH": {
                "address": "0x2175Ed9c75C14F113ab9cEaDc1890b2f87f40e78",
                "qr_file": "ETH_QR.jpg"
            },
            "SOL": {
                "address": "6Hc7erZqgreTVwCsTtNvsyzigN2oHJ4EgNGaLWtRWJ69",
                "qr_file": "Solana_QR.jpg"
            }
        }

    def get_address(self, crypto):
        """Get the address for a cryptocurrency."""
        return self.crypto_data.get(crypto, {}).get("address", "")

    def get_qr_path(self, crypto):
        """Get the path to the QR code image for a cryptocurrency."""
        qr_file = self.crypto_data.get(crypto, {}).get("qr_file", "")
        return self.contents_path / "crypto" / qr_file if qr_file else None

def setup_crypto_links(gui, input_frame):
    """Setup cryptocurrency links and QR code display."""
    links_frame = ttk.Frame(input_frame)
    links_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

    # GitHub and Buy Me a Coffee links
    github_label = ttk.Label(links_frame, text="Github: kerasty2024", cursor="hand2", foreground="blue")
    github_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
    github_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/kerasty2024/"))
    Tooltip(github_label, "Visit the author's GitHub profile.")

    coffee_label = ttk.Label(links_frame, text="Buy Me a Coffee: kerasty", cursor="hand2", foreground="blue")
    coffee_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    coffee_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.buymeacoffee.com/kerasty"))
    Tooltip(coffee_label, "Support the author with a coffee via Buy Me a Coffee.")

    # Crypto address labels
    row = 2
    for crypto, data in gui.crypto_manager.crypto_data.items():
        address = data["address"]
        label = ttk.Label(links_frame, text=f"{crypto} Address: {address}", cursor="hand2", foreground="blue")
        label.grid(row=row, column=0, padx=5, pady=5, sticky='w')
        label.bind("<Button-1>", lambda e, c=crypto, a=address: copy_crypto_address(gui, c, a))
        Tooltip(label, f"Click to copy {crypto} address for donations.")
        row += 1

    # Load and display initial QR code (BTC)
    qr_path = gui.crypto_manager.get_qr_path("BTC")
    qr_image = Image.open(qr_path)
    qr_image = resize_image(qr_image, (100, 100))
    gui.qr_photo = ImageTk.PhotoImage(qr_image)
    gui.qr_label = tk.Label(links_frame, image=gui.qr_photo)
    gui.qr_label.image = gui.qr_photo
    gui.qr_label.grid(row=0, column=1, rowspan=row, padx=5, pady=5, sticky='e')
    Tooltip(gui.qr_label, "QR code for the selected cryptocurrency address.")

    links_frame.columnconfigure(0, weight=1)

def copy_crypto_address(gui, crypto, address):
    """Copy the cryptocurrency address to the clipboard and update the QR code."""
    gui.root.clipboard_clear()
    gui.root.clipboard_append(address)
    gui.root.update()
    logger.debug(f"Copied {crypto} address to clipboard: {address}")
    gui.completion_label.config(text=f"{crypto} address copied to clipboard!")

    # Update QR code
    gui.current_crypto = crypto
    qr_path = gui.crypto_manager.get_qr_path(crypto)
    try:
        qr_image = Image.open(qr_path)
        qr_image = resize_image(qr_image, (100, 100))
        gui.qr_photo = ImageTk.PhotoImage(qr_image)
        gui.qr_label.configure(image=gui.qr_photo)
        gui.qr_label.image = gui.qr_photo
    except Exception as e:
        logger.error(f"Failed to load QR code for {crypto}: {e}")
        gui.completion_label.config(text=f"Failed to load {crypto} QR code")