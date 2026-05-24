from pathlib import Path
import tempfile
import unittest

from check import (
    cargar_historial,
    clave_oferta,
    extraer_precio_producto,
    formatear_oferta,
    guardar_historial,
    producto_permitido,
)


class SportingAlertTests(unittest.TestCase):
    def test_extrae_el_precio_mas_bajo_con_stock(self):
        producto = {
            "items": [
                {
                    "sellers": [
                        {"commertialOffer": {"Price": 49999, "AvailableQuantity": 3}},
                        {"commertialOffer": {"Price": 39999, "AvailableQuantity": 2}},
                    ]
                }
            ]
        }

        self.assertEqual(extraer_precio_producto(producto), 39999)

    def test_ignora_precios_sin_stock(self):
        producto = {
            "items": [
                {
                    "sellers": [
                        {"commertialOffer": {"Price": 9999, "AvailableQuantity": 0}},
                        {"commertialOffer": {"Price": 29999, "AvailableQuantity": 1}},
                    ]
                }
            ]
        }

        self.assertEqual(extraer_precio_producto(producto), 29999)

    def test_devuelve_none_si_no_hay_precio_disponible(self):
        producto = {"items": [{"sellers": [{"commertialOffer": {"Price": 0}}]}]}

        self.assertIsNone(extraer_precio_producto(producto))

    def test_formatea_mensaje_sin_caracteres_corruptos(self):
        mensaje = formatear_oferta("Zapatillas Test", 25000, "https://example.com")

        self.assertIn("OFERTA SPORTING", mensaje)
        self.assertIn("Producto: Zapatillas Test", mensaje)
        self.assertIn("Precio: $25000", mensaje)
        self.assertIn("https://example.com", mensaje)

    def test_permite_productos_que_no_estan_excluidos(self):
        self.assertTrue(producto_permitido("Zapatillas adidas Grand Court Lo De Mujer"))
        self.assertTrue(producto_permitido("Crocs Classic Unisex"))
        self.assertTrue(producto_permitido("Botines Joma Aguila FG De Hombre"))
        self.assertTrue(producto_permitido("Zapatos Mocasines Marcel E7052 De Hombre"))

    def test_rechaza_ojotas_chinelas_y_sandalias(self):
        self.assertFalse(producto_permitido("Ojotas Rider R1 De Mujer"))
        self.assertFalse(producto_permitido("Ojotas y Chinelas adidas Adilette Aqua Unisex"))
        self.assertFalse(producto_permitido("Chinelas Rider Pump II De Hombre"))
        self.assertFalse(producto_permitido("Sandalias Rider Free Style II De Niños"))

    def test_rechaza_productos_de_ninos(self):
        self.assertFalse(producto_permitido("Zapatillas Diversao Ale De Niños"))
        self.assertFalse(producto_permitido("Zapatillas Marcel York De Niñas"))
        self.assertFalse(producto_permitido("Botines Umbro Mutant De Niños"))
        self.assertFalse(producto_permitido("Zapatillas Puma Rickie De Bebés"))

    def test_clave_oferta_cambia_si_cambia_el_precio(self):
        link = "https://www.sporting.com.ar/producto/p"

        self.assertNotEqual(clave_oferta(39000, link), clave_oferta(35000, link))
        self.assertEqual(clave_oferta(39000, link), f"{link}|39000")

    def test_guarda_y_carga_historial_de_alertas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sent_offers.json"
            key = clave_oferta(39000, "https://www.sporting.com.ar/producto/p")
            historial = {
                key: {
                    "name": "Producto Test",
                    "price": 39000,
                    "link": "https://www.sporting.com.ar/producto/p",
                    "sent_at": "2026-05-24T00:00:00Z",
                }
            }

            guardar_historial(historial, path)

            cargado = cargar_historial(path)
            self.assertIn(key, cargado)
            self.assertEqual(cargado[key]["name"], "Producto Test")
            self.assertEqual(cargado[key]["price"], 39000)
            self.assertEqual(cargado[key]["link"], "https://www.sporting.com.ar/producto/p")

    def test_carga_historial_legacy_en_lista(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sent_offers.json"
            path.write_text('{"sent": ["a|1", "b|2"]}', encoding="utf-8")

            cargado = cargar_historial(path)

            self.assertIn("a|1", cargado)
            self.assertIn("b|2", cargado)


if __name__ == "__main__":
    unittest.main()
