import unittest

from check import extraer_precio_producto, formatear_oferta, producto_permitido


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

    def test_permite_zapatillas_y_crocs(self):
        self.assertTrue(producto_permitido("Zapatillas adidas Grand Court Lo De Mujer"))
        self.assertTrue(producto_permitido("Crocs Classic Unisex"))

    def test_rechaza_ojotas_y_productos_de_ninos(self):
        self.assertFalse(producto_permitido("Ojotas Rider R1 De Mujer"))
        self.assertFalse(producto_permitido("Zapatillas Diversao Ale De Niños"))
        self.assertFalse(producto_permitido("Zapatillas Puma Rickie De Bebés"))


if __name__ == "__main__":
    unittest.main()
