class Kasir:
    def __init__(self):
        self.items = []

    def add_item(self, nama, harga, jumlah):
        self.items.append({"nama": nama, "harga": harga, "jumlah": jumlah})

    def hitung_total(self):
        total = 0
        for item in self.items:
            total += item["harga"] * item["jumlah"]
        return total

    def cetak_struk(self):
        print("---- Struk Belanja ----")
        for item in self.items:
            print(f"{item['nama']} - {item['jumlah']} x {item['harga']} = {item['harga'] * item['jumlah']}")
        print(f"Total: {self.hitung_total()}")
        print("-----------------------")

# Contoh penggunaan
kasir = Kasir()
kasir.add_item("Buku", 10000, 2)
kasir.add_item("Pensil", 2000, 5)
kasir.cetak_struk()
