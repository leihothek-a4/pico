"""
pn532_i2c.py
============

Adaptado do módulo oficial adafruit_pn532.i2c para MicroPython.

Este módulo permite comunicar com o PN532 via I2C utilizando machine.I2C.

Autor(es): Adaptado a partir do código oficial do Adafruit PN532.
"""

import time
from micropython import const
from machine import Pin

# Endereço I2C padrão do PN532.
_I2C_ADDRESS = const(0x24)

# Importa a classe base PN532 e a exceção BusyError.
# Certifique-se de que o arquivo base (por exemplo, pn532.py) esteja disponível.
from nfc.pn532 import PN532, BusyError


class PN532_I2C(PN532):
    """
    Driver para o PN532 conectado via I2C (MicroPython).

    Parâmetros:
      - i2c: Objeto machine.I2C já inicializado.
      - address: Endereço I2C do PN532 (padrão: 0x24).
      - irq: (Opcional) Objeto machine.Pin conectado à IRQ (não utilizado nesta implementação).
      - reset: (Opcional) Objeto machine.Pin para resetar o PN532.
      - req: (Opcional) Objeto machine.Pin conectado ao pino "REQ" (para wakeup).
      - debug: (Opcional) Se True, ativa mensagens de debug.
    """

    def __init__(self, i2c, address=_I2C_ADDRESS, *, irq=None, reset=None, req=None, debug=False):
        self.debug = debug
        self._req = req
        self._i2c = i2c            # Objeto machine.I2C
        self._address = address    # Endereço do dispositivo
        super().__init__(debug=debug, irq=irq, reset=reset)

    def _wakeup(self):
        """Envia os comandos necessários para acordar o PN532."""
        if self._reset_pin:
            self._reset_pin.value(1)
            time.sleep(0.01)
        if self._req:
            self._req.value(0)
            time.sleep(0.01)
            self._req.value(1)
            time.sleep(0.01)
        
        # Wakeup bytes sturen
        try:
            self._i2c.writeto(self._address, bytes([0x55, 0x55, 0x00, 0x00, 0x00]))
        except:
            pass
        time.sleep(0.5)
        
        # Wacht tot module klaar is (0x01 = bezig)
        for _ in range(20):
            try:
                data = self._i2c.readfrom(self._address, 1)
                if data[0] != 0x01:
                    break
            except:
                pass
            time.sleep(0.1)
        time.sleep(0.2)
        
        self.low_power = False
        self.SAM_configuration()

    def _wait_ready(self, timeout=1):
        """
        Aguarda até que o PN532 esteja pronto (até 'timeout' segundos).

        Lê um byte de status do PN532 e espera até que seja 0x01.
        """
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout * 1000:
            try:
                status = self._i2c.readfrom(self._address, 1)
            except OSError:
                # Pode ocorrer se o dispositivo não responder; tenta novamente.
                time.sleep(0.01)
                continue
            if status and status[0] == 0x01:
                return True  # Dispositivo pronto.
            time.sleep(0.01)
        # Timeout atingido.
        return False

    def _read_data(self, count):
        """
        Lê 'count' bytes úteis do PN532 via I2C.
        De PN532 stuurt status byte + data in één pakket.
        """
        # Lees status + data in één keer
        frame = self._i2c.readfrom(self._address, count + 1)
        if self.debug:
            print("Reading:", [hex(b) for b in frame])
        if frame[0] != 0x01:
            raise BusyError("PN532 não está pronto (status=%s)" % frame[0])
        # Geef alleen de data terug, zonder de status-byte
        return frame[1:]

    def _write_data(self, framebytes):
        """
        Envia os dados especificados (framebytes) para o PN532 via I2C.
        """
        self._i2c.writeto(self._address, framebytes)



