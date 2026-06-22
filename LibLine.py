import os
import re
import json
from collections import deque
from datetime import date, datetime
from typing import Optional

# ================================================================
#  KONSTANTA KONFIGURASI
# ================================================================
TABLE_SIZE = 53
HASH_BASE = 31
QUEUE_CAPACITY = 20
DELETED = "__DELETED__"  # Penanda tombstone untuk data yang dihapus

# ================================================================
#  STRUKTUR DATA BUKU
# ================================================================
class Book:
    def __init__(self, code: str, title: str, author: str, year: int, rack: str, stock: int = 1):
        self.code   = code.upper().strip()
        self.title  = title.strip()
        self.author = author.strip()
        self.year   = year
        self.stock  = stock
        self.rack   = rack

    def __str__(self) -> str:
        # Format tampilan ringkas satu baris
        return (f"  [{self.code}] {self.title} — {self.author} "
                f"({self.year}) | Stok: {self.stock} | Rak: {self.rack}") 

    def detail(self) -> str:
        # Format tampilan detail multi-baris
        return (
            f"  Kode      : {self.code}\n"
            f"  Judul     : {self.title}\n"
            f"  Pengarang : {self.author}\n"
            f"  Tahun     : {self.year}\n"
            f"  Stok      : {self.stock}\n"
            f"  Rak       : {self.rack}\n"
            f"  {'─'*40}"
        )

# Node untuk struktur data Trie
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.title = None

# Struktur data Trie untuk pencarian autocomplete judul
class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, title: str) -> None:
        # Menyisipkan judul buku ke dalam Trie
        current = self.root
        normalized = title.strip().lower()
        for char in normalized:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_end = True
        current.title = title.strip()

    def autocomplete(self, prefix: str) -> list:
        # Mengembalikan daftar judul yang berawalan dari prefix
        current = self.root
        normalized = prefix.strip().lower()
        for char in normalized:
            if char not in current.children:
                return []
            current = current.children[char]

        results = []
        self._collect_words(current, results)
        return sorted(results, key=lambda x: x.lower())

    def _collect_words(self, node: TrieNode, results: list) -> None:
        if node.is_end and node.title:
            results.append(node.title)
        for child in node.children.values():
            self._collect_words(child, results)

# ================================================================
#  ALGORITMA HASHING
# ================================================================
def hash_function(code: str) -> int:
    # Polynomial Rolling Hash Function
    h = 0
    for i, char in enumerate(code.upper()):
        h = (h + ord(char) * (HASH_BASE ** i)) % TABLE_SIZE
    return h

def probe(code: str, attempt: int) -> int:
    # Linear Probing untuk resolusi konflik
    return (hash_function(code) + attempt) % TABLE_SIZE

# ================================================================
#  HASH TABLE (DATABASE UTAMA)
# ================================================================
class HashTable:
    def __init__(self):
        self._table: list = [None] * TABLE_SIZE
        self._count: int  = 0

    def insert(self, book: Book) -> bool:
        # Memasukkan atau memperbarui data buku di Hash Table
        for attempt in range(TABLE_SIZE):
            idx = probe(book.code, attempt)

            if self._table[idx] is None or self._table[idx] == DELETED:
                self._table[idx] = book
                self._count += 1
                return True

            if self._table[idx].code == book.code:
                # Jika kodenya sama, perbarui datanya
                self._table[idx] = book
                return True

        return False

    def search(self, code: str) -> Optional[Book]:
        # Mencari buku berdasarkan kode unik
        code = code.upper().strip()

        for attempt in range(TABLE_SIZE):
            idx = probe(code, attempt)

            if self._table[idx] is None:
                return None

            if self._table[idx] != DELETED and self._table[idx].code == code:
                return self._table[idx]

        return None

    def delete(self, code: str) -> bool:
        # Menghapus buku menggunakan mekanisme soft delete (Tombstone)
        code = code.upper().strip()

        for attempt in range(TABLE_SIZE):
            idx = probe(code, attempt)

            if self._table[idx] is None:
                return False

            if self._table[idx] != DELETED and self._table[idx].code == code:
                self._table[idx] = DELETED
                self._count -= 1
                return True

        return False

    def get_all(self) -> list:
        # Mengambil semua objek buku aktif dari tabel
        return [slot for slot in self._table if slot is not None and slot != DELETED]

# ================================================================
#  QUEUE (ANTRIAN PEMINJAMAN)
# ================================================================
class BorrowRequest:
    def __init__(self, member_name: str, book_code: str):
        self.member_name  = member_name.strip()
        self.book_code    = book_code.upper().strip()
        self.request_date = date.today().strftime("%d/%m/%Y")

class BorrowQueue:
    def __init__(self, capacity: int = QUEUE_CAPACITY):
        self._capacity = capacity
        self._queue: list = [None] * capacity
        self._front: int  = 0
        self._rear:  int  = 0
        self._size:  int  = 0

    def is_empty(self) -> bool:
        return self._size == 0

    def is_full(self) -> bool:
        return self._size == self._capacity

    def enqueue(self, request: BorrowRequest) -> bool:
        if self.is_full():
            return False

        self._queue[self._rear] = request
        self._rear = (self._rear + 1) % self._capacity
        self._size += 1
        return True

    def dequeue(self) -> Optional[BorrowRequest]:
        if self.is_empty():
            return None

        request = self._queue[self._front]
        self._queue[self._front] = None
        self._front = (self._front + 1) % self._capacity
        self._size -= 1
        return request

# ================================================================
#  ALGORITMA MERGE SORT
# ================================================================
def merge_sort(books: list, key: str = "code") -> list:
    if len(books) <= 1:
        return books

    mid   = len(books) // 2
    left  = merge_sort(books[:mid], key)
    right = merge_sort(books[mid:], key)

    return _merge(left, right, key)


def _merge(left: list, right: list, key: str) -> list:
    result = []
    i = j  = 0

    def get_key(book: Book):
        if   key == "title":  return book.title.lower()
        elif key == "author": return book.author.lower()
        elif key == "year":   return book.year
        else:                 return book.code.lower()

    while i < len(left) and j < len(right):
        if get_key(left[i]) <= get_key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result

# ================================================================
#  ALGORITMA BINARY SEARCH
# ================================================================
def binary_search(sorted_books: list, target_code: str) -> int:
    target = target_code.upper().strip()
    left   = 0
    right  = len(sorted_books) - 1

    while left <= right:
        mid = (left + right) // 2

        print(f"  [BS] Cek indeks {mid} → kode: {sorted_books[mid].code}")

        if sorted_books[mid].code == target:
            return mid
        elif sorted_books[mid].code < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


# ================================================================
#  SISTEM CORE PERPUSTAKAAN (LIBLINE)
# ================================================================
class LibLine:
    def __init__(self):
        self._ht          = HashTable()
        self._queue       = BorrowQueue()
        self._title_trie  = Trie()

    def _rebuild_title_trie(self) -> None:
        # Membangun ulang struktur data Trie judul buku
        self._title_trie = Trie()
        for book in self._ht.get_all():
            self._title_trie.insert(book.title)

    def save_to_file(self, filename="books.json") -> None:
        """Menyimpan data langsung dari Hash Table ke file JSON tanpa array tambahan."""
        data_to_save = {}
        # Iterasi langsung dari struktur internal hash table
        for slot in self._ht._table:
            if slot is not None and slot != DELETED:
                data_to_save[slot.code] = {
                    "title": slot.title,
                    "author": slot.author,
                    "year": slot.year,
                    "stock": slot.stock,
                    "rack": slot.rack
                }
        
        with open(filename, "w") as f:
            json.dump(data_to_save, f, indent=4)
        print("  [i] Data berhasil dicadangkan ke file.")

    def load_from_file(self, filename="books.json") -> bool:
        """Memuat data dari file JSON langsung dimasukkan kembali ke Hash Table."""
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                for code, info in data.items():
                    # Langsung insert menggunakan data dari berkas penyimpanan
                    book = Book(code, info["title"], info["author"], info["year"], info["rack"], info["stock"])
                    self._ht.insert(book)
                self._rebuild_title_trie()
            return True
        except FileNotFoundError:
            return False 

    def log_history(self, member_name: str, book_code: str, action: str, filename="history.json") -> None:
        """Mencatat aktivitas log peminjaman atau pengembalian langsung ke file JSON."""
        try:
            with open(filename, "r") as f:
                history_data = json.load(f)
        except FileNotFoundError:
            history_data = {}

        # Membuat ID unik berbasis waktu agar riwayat tidak tertimpa
        timestamp_key = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        history_data[timestamp_key] = {
            "name": member_name,
            "book_code": book_code.upper(),
            "action": action,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        with open(filename, "w") as f:
            json.dump(history_data, f, indent=4)

    def check_borrow_history(self, member_name: str, book_code: str, filename="history.json") -> bool:
        """Memeriksa apakah member bersangkutan benar-benar pernah meminjam buku tersebut."""
        try:
            with open(filename, "r") as f:
                history_data = json.load(f)
        except FileNotFoundError:
            return False  # Jika file belum ada, otomatis belum ada riwayat pinjam

        # Normalisasi input agar pencarian akurat (tidak sensitif huruf besar/kecil)
        target_name = member_name.strip().lower()
        target_code = book_code.strip().upper()

        # Telusuri isi riwayat dari JSON
        for log in history_data.values():
            if log["name"].strip().lower() == target_name and log["book_code"] == target_code:
                if log["action"] == "PINJAM":
                    return True  # Ketemu bukti riwayat peminjaman!

        return False  # Tidak ada riwayat pinjam untuk member dan buku ini


    def display_history(self, filter_action: str, filename="history.json") -> None:
        """Menampilkan daftar log riwayat peminjaman buku."""
        try:
            with open(filename, "r") as f:
                history_data = json.load(f)
        except FileNotFoundError:
            print_error("Belum ada data riwayat aktivitas.")
            return
        

        print(f"\n  --- RIWAYAT PEMINJAMAN BUKU ---")
        print("  +---------------------+----------------------+------------+")
        print("  | Tanggal & Waktu     | Nama Anggota         | Kode Buku  |")
        print("  +---------------------+----------------------+------------+")

        count = 0
        for log in history_data.values():
            if log["action"] == filter_action:
                name_short = (log["name"][:20] if len(log["name"]) > 20 else log["name"]).ljust(20)
                print(f"  | {log['date']}    | {name_short} | {log['book_code']:<10} |")
                count += 1

        print("  +---------------------+----------------------+------------+")
        print(f"  Total: {count} aktivitas ditemukan.")

    def add_book(self, code: str, title: str, author: str, year: int, rack: str, stock: int = 1) -> bool:
        # Menambah buku baru dan memperbarui Trie
        if self.find_book(code) is not None:
            print("  Kode buku sudah digunakan")
            return False
            
        book = Book(code, title, author, year, rack, stock)
        ok = self._ht.insert(book)
        if ok:
            self._rebuild_title_trie()
        return ok

    def find_book(self, code: str) -> Optional[Book]:
        # Mencari buku via Hash Table (O(1))
        return self._ht.search(code)

    def find_book_binary(self, code: str) -> Optional[Book]:
        # Mencari buku via Binary Search (Alternatif)
        all_books   = self._ht.get_all()
        sorted_books = merge_sort(all_books, "code")

        print(f"\n  [Binary Search] Mencari '{code.upper()}' "
              f"dari {len(sorted_books)} buku terurut:")
        idx = binary_search(sorted_books, code)

        if idx == -1:
            return None
        return sorted_books[idx]

    def find_titles_by_prefix(self, prefix: str) -> list:
        if not prefix.strip():
            return []
        return self._title_trie.autocomplete(prefix)

    def find_books_by_title_prefix(self, prefix: str) -> list:
        titles = self._title_trie.autocomplete(prefix)
        if not titles:
            return []
        normalized = {title.lower() for title in titles}
        return [book for book in self._ht.get_all()
                if book.title.lower() in normalized]

    def remove_book(self, code: str) -> bool:
        # Menghapus buku dan memperbarui Trie
        ok = self._ht.delete(code)
        if ok:
            self._rebuild_title_trie()
        return ok

    def display_all(self, key: str = "code") -> None:
        # Menampilkan data terurut menggunakan Merge Sort
        books = self._ht.get_all()
        if not books:
            print_error("Belum ada buku dalam sistem.")
            return

        sorted_books = merge_sort(books, key)
        label = {"code": "Kode", "title": "Judul",
                 "author": "Pengarang", "year": "Tahun Terbit"}

        print(f"\n  --- Daftar Buku (Urut: {label.get(key, key)}) ---\n")
        print("  +-----+-------+------------------------+---------------------+------+-------+-----+")
        print("  | No. | Kode  | Judul                  | Pengarang           | Thn  | Stok  | Rak |")
        print("  +-----+-------+------------------------+---------------------+------+-------+-----+")

        for i, book in enumerate(sorted_books, 1):
            title_short = (book.title[:22] if len(book.title) > 22 else book.title).ljust(22)
            author_short = (book.author[:19] if len(book.author) > 19 else book.author).ljust(19)
            rack_short = (book.rack[:3] if len(book.rack) > 3 else book.rack).ljust(3)
            print(f"  | {i:>3} | {book.code} | {title_short} | {author_short} | {book.year} | {book.stock:>5} | {rack_short} |")

        print("  +-----+-------+------------------------+---------------------+------+-------+-----+")
        print(f"\n  Total: {len(sorted_books)} buku")

    def display_hash_info(self, code: str) -> None:
        # Menampilkan simulasi proses hashing dan probing
        code = code.upper().strip()
        h    = hash_function(code)

        print(f"\n  --- INFORMASI HASH FUNCTION ---\n")
        print(f"  Kode Buku    : {code}")
        print(f"  Hash Base    : {HASH_BASE}")
        print(f"  Tabel Size   : {TABLE_SIZE}")

        print(f"\n  Perhitungan Hash:")
        raw = 0
        for i, c in enumerate(code):
            contrib = ord(c) * (HASH_BASE ** i)
            print(f"    ord('{c}') × {HASH_BASE}^{i} = {ord(c)} × {HASH_BASE**i} = {contrib}")
            raw += contrib

        print(f"\n  Total (raw)          : {raw}")
        print(f"  Modulo {TABLE_SIZE}    : {raw} % {TABLE_SIZE} = {h}")
        print(f"  → Indeks Slot Utama  : #{h}")

        print(f"\n  Probe Chain (Linear Probing):")
        for attempt in range(min(5, TABLE_SIZE)):
            idx  = probe(code, attempt)
            slot = self._ht._table[idx]
            if slot is None:
                print(f"    attempt {attempt}: slot[{idx}] = kosong (BERHENTI)")
                break
            elif slot == DELETED:
                print(f"    attempt {attempt}: slot[{idx}] = [DELETED]")
            else:
                marker = " ← COCOK!" if slot.code == code else ""
                print(f"    attempt {attempt}: slot[{idx}] = {slot.code}{marker}")
                if slot.code == code:
                    break

    def enqueue_borrow(self, member: str, code: str) -> bool:
        # Menambahkan data peminjam ke antrean
        book = self.find_book(code)
        if book is None:
            print_error(f"Buku '{code.upper()}' tidak ditemukan.")
            return False
        if book.stock <= 0:
            print_error(f"Stok buku '{code.upper()}' habis.")
            return False

        req = BorrowRequest(member, code)
        ok  = self._queue.enqueue(req)
        if not ok:
            print_error("Antrian penuh. Coba lagi nanti.")
        return ok

    def process_borrow(self) -> bool:
        # Memproses transaksi peminjaman terdepan (FIFO)
        req = self._queue.dequeue()
        if req is None:
            print_info("Antrian kosong. Tidak ada yang diproses.")
            return False

        book = self.find_book(req.book_code)
        if book is None:
            print_error(f"Buku '{req.book_code}' tidak ditemukan saat proses.")
            return False

        book.stock -= 1
        self._ht.insert(book)
        self.save_to_file()
        self.log_history(req.member_name, book.code, "PINJAM")

        print()
        print_success("Peminjaman diproses!")
        print(f"  Anggota   : {req.member_name}")
        print(f"  Buku      : [{book.code}] {book.title}")
        print(f"  Stok sisa : {book.stock} unit")
        return True

    def display_queue(self) -> None:
        # Menampilkan antrean peminjaman aktif
        if self._queue.is_empty():
            print_info("Antrian peminjaman kosong.")
            return

        print(f"\n  --- Antrian Peminjaman ---\n")
        print("  +-----+------------------------+-------+-----+")
        print("  | No. | Nama Anggota           | Buku  | Rak |")
        print("  +-----+------------------------+-------+-----+")

        for i in range(self._queue._size):
            idx = (self._queue._front + i) % self._queue._capacity
            req = self._queue._queue[idx]
            if req is None:
                continue
            book = self.find_book(req.book_code)
            rack_info = book.rack if book else "-"
            pos_label = "→" if i == 0 else f"{i+1:>2}"
            print(f"  | {pos_label:>3} | {req.member_name[:22].ljust(22)} | {req.book_code.ljust(5)} | {rack_info.ljust(3)} |")

        print("  +-----+------------------------+-------+-----+")
        print(f"\n  Total: {self._queue._size} peminjam dalam antrian")

    def update_stock(self, code: str, delta: int) -> bool:
        # Mengubah nilai stok buku di database
        book = self.find_book(code)
        if book is None:
            return False

        new_stock = book.stock + delta
        if new_stock < 0:
            print(f"  [!] Stok tidak cukup. Stok saat ini: {book.stock}")
            return False

        book.stock = new_stock
        self._ht.insert(book)
        return True

# ================================================================
#  ANTARMUKA PENGGUNA (CLI)
# ================================================================
def print_header():
    clear_screen()
    print("  +----------------------------------------------+")
    print("  |        LibLine — Sistem Perpustakaan         |")
    print("  |          Digital Management System           |")
    print("  +----------------------------------------------+\n")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_success(text: str) -> None:
    print(f"  [OK] {text}")

def print_error(text: str) -> None:
    print(f"  [!] {text}")

def print_info(text: str) -> None:
    print(f"  [i] {text}")

def print_title(text: str) -> None:
    print(f"\n  +----------------------------------------------+")
    padding = (46 - len(text)) // 2
    print(f"  |{' ' * padding}{text}{' ' * (46 - padding - len(text))}|")
    print(f"  +----------------------------------------------+\n")

def print_menu():
    clear_screen()
    print_title("MENU UTAMA - LibLine")
    print("  +----+----+-----------------------------------+")
    print("  | No | Kat| Menu                              |")
    print("  +----+----+-----------------------------------+")
    print("  |  1 | MB | Tambah buku baru                  |")
    print("  +----+----+-----------------------------------+")
    print("  |  2 | MB | Hapus buku                        |")
    print("  +----+----+-----------------------------------+")
    print("  |  3 | MB | Update stok buku                  |")
    print("  +----+----+-----------------------------------+")
    print("  |  4 | MB | Tampilkan semua buku (Merge Sort) |")
    print("  +----+----+-----------------------------------+")
    print("  |  5 | PC | Cari buku                         |")
    print("  +----+----+-----------------------------------+")
    print("  |  6 | AP | Antrian pinjam                    |")
    print("  +----+----+-----------------------------------+")
    print("  |  7 | PB | Pengembalian buku                 |")
    print("  +----+----+-----------------------------------+")
    print("  |  8 | -- | Keluar                            |")
    print("  +----+----+-----------------------------------+")


def get_int(prompt: str, min_val: int = None, max_val: int = None) -> int:
    # Memvalidasi input agar hanya menerima angka dalam range tertentu
    while True:
        try:
            val = int(input(prompt))
            if min_val is not None and val < min_val:
                print(f"  [!] Nilai minimal {min_val}.")
                continue
            if max_val is not None and val > max_val:
                print(f"  [!] Nilai maksimal {max_val}.")
                continue
            return val
        except ValueError:
            print("  [!] Masukkan angka yang valid.")


def get_yes_no(prompt: str) -> str:
    """Memaksa pengguna hanya bisa menginput 'y' atau 'n'."""
    while True:
        pilihan = input(prompt).strip().lower()
        if pilihan in ['y', 'n']:
            return pilihan
        print("  [!] Input tidak valid! Harap hanya masukkan 'y' atau 'n'.")


# ================================================================
#  MAIN PROGRAM LOOP
# ================================================================
def main():
    lib = LibLine()

    # Logika pengecekan file agar data awal tidak bentrok / duplikat
    if lib.load_from_file():
        print_header()
        print_success("Data berhasil dimuat dari penyimpanan lokal (books.json).")
    else:
        # Memasukkan database buku awal jika berkas belum pernah ada
        initial_books = [
            ("BK001", "Laskar Pelangi",          "Andrea Hirata",    2005, "A1", 3),
            ("BK002", "Bumi Manusia",             "Pramoedya A. Toer",1980, "C3", 2),
            ("BK003", "Negeri 5 Menara",          "Ahmad Fuadi",      2009, "E8", 4),
            ("BK004", "Perahu Kertas",            "Dee Lestari",      2009, "B1", 2),
            ("BK005", "Dilan 1990",               "Pidi Baiq",        2014, "C2", 5),
            ("BK006", "Filosofi Teras",           "Henry Manampiring",2018, "D3", 3),
            ("BK007", "Atomic Habits",            "James Clear",      2018, "I5", 2),
            ("BK008", "The Alchemist",            "Paulo Coelho",     1988, "D2", 1),
        ]
        for args in initial_books:
            lib.add_book(*args)
        
        lib.save_to_file()
        print_header()
        print_success("File data baru dibuat. Data awal berhasil dimuat (8 buku).")

    input("\n  Tekan Enter untuk memulai...")

    # Main menu loop
    while True:
        print_menu()
        pilihan = get_int("\n  Pilih menu [1-8]: ", 1, 8)

        # ---- 1: Tambah Buku ----
        if pilihan == 1:
            while True:
                clear_screen()
                print_title("Tambah Buku Baru")
                code   = input("  Kode buku   : ").strip()
                title  = input("  Judul       : ").strip()
                author = input("  Pengarang   : ").strip()
                year   = get_int("  Tahun terbit: ", 1000, 9999)
                stock  = get_int("  Stok        : ", 0)
                
                while True:
                    rack = input("  Rak (Contoh: A1) : ").strip().upper() 
                    if re.match(r"^[A-Z][0-9]$", rack):
                        break  
                    print("  [!] Format rak salah! Harus berupa 1 huruf kapital dan 1 angka (Contoh: A1, B5, C2).")

                if not code or not title or not author:
                    print_error("Kode, judul, dan pengarang tidak boleh kosong.")
                else:
                    ok = lib.add_book(code, title, author, year, rack, stock)
                    if ok:
                        h = hash_function(code.upper())
                        print()
                        print_success(f"Buku ditambahkan ke slot hash #{h}")
                        print(f"  Kode  : {code.upper()}")
                        print(f"  Judul : {title}")
                        lib.save_to_file()
                    else:
                        print_error("Gagal menambahkan buku. Kode sudah digunakan atau tabel penuh.")
                
                ulang = get_yes_no("\n  Apakah anda ingin menambahkan buku lagi? (y/n): ")
                if ulang == 'n':
                    break

        # ---- 2: Hapus Buku ----
        elif pilihan == 2:
            while True:
                clear_screen()
                print_title("Hapus Buku")
                code = input("  Kode buku yang akan dihapus: ").strip()

                book = lib.find_book(code)
                if book is None:
                    print_error(f"Buku '{code.upper()}' tidak ditemukan.")
                else:
                    print(f"\n  Detail Buku:")
                    print(book.detail())
                    konfirm = get_yes_no(f"\n  Yakin hapus buku ini? (y/n): ")
                    if konfirm == 'y':
                        lib.remove_book(code)
                        lib.save_to_file()
                        print_success("Buku berhasil dihapus dari sistem.")
                    else:
                        print_info("Penghapusan dibatalkan.")
                
                ulang = get_yes_no("\n  Apakah anda ingin menghapus buku lagi? (y/n): ")
                if ulang == 'n':
                    break

        # ---- 3: Update Stok ----
        elif pilihan == 3:
            while True:
                clear_screen()
                print_title("Update Stok Buku")
                code = input("  Kode buku: ").strip()

                book = lib.find_book(code)
                if book is None:
                    print_error(f"Buku '{code.upper()}' tidak ditemukan.")
                else:
                    print("\n  Detail Buku:")
                    print(book.detail())
                    print(f"\n  Stok saat ini: {book.stock} unit")
                    print("  Operasi: 1=Tambah  2=Kurangi")
                    op     = get_int("  Pilihan: ", 1, 2)
                    jumlah = get_int("  Jumlah : ", 1)

                    delta = jumlah if op == 1 else -jumlah
                    ok    = lib.update_stock(code, delta)
                    if ok:
                        lib.save_to_file()
                        updated = lib.find_book(code)
                        print()
                        print_success(f"Stok diperbarui → {updated.stock} unit.")
                
                ulang = get_yes_no("\n  Apakah anda ingin mengupdate stok buku lagi? (y/n): ")
                if ulang == 'n':
                    break

        # ---- 4: Tampilkan Semua Buku ----
        elif pilihan == 4:
            while True:
                clear_screen()
                print_title("Daftar Semua Buku")
                print("  Urutkan berdasarkan:")
                print("    1=Kode  2=Judul  3=Pengarang  4=Tahun Terbit")
                opt = get_int("  Pilihan: ", 1, 4)

                clear_screen()
                key_map = {1: "code", 2: "title", 3: "author", 4: "year"}
                lib.display_all(key_map[opt])
                
                ulang = get_yes_no("\n  Apakah anda ingin melihat daftar buku dengan urutan lain? (y/n): ")
                if ulang == 'n':
                    break

        # ---- 5: Cari Buku ----
        elif pilihan == 5:
            while True:
                clear_screen()
                print_title("Cari Buku")
                print("  Pilih metode pencarian:")
                print("    1 = Kode buku (Binary Search)")
                print("    2 = Judul buku (Trie Autocomplete)")
                search_type = get_int("  Pilihan: ", 1, 2)

                if search_type == 1:
                    code = input("  Kode buku: ").strip()
                    book = lib.find_book_binary(code)
                    if book:
                        print(f"\n  [OK] Buku Ditemukan:\n")
                        print(book.detail())
                    else:
                        print()
                        print_error(f"Buku '{code.upper()}' tidak ditemukan.")
                else:
                    prefix = input("  Masukkan awalan judul: ").strip()
                    if not prefix:
                        print_error("Awalan judul tidak boleh kosong.")
                    else:
                        books = lib.find_books_by_title_prefix(prefix)
                        if books:
                            print("\n  Hasil Pencarian:")
                            for i, book in enumerate(books, start=1):
                                print(f"\n  {i}. {book.title}")
                                print(book.detail())
                        else:
                            print()
                            print_error("Tidak ditemukan judul buku dengan awalan tersebut.")
                
                ulang = get_yes_no("\n  Apakah anda ingin mencari buku lagi? (y/n): ")
                if ulang == 'n':
                    break

        # ---- 6: Antrian Pinjam ----
        elif pilihan == 6:
            while True:
                clear_screen()
                print_title("Antrian Pinjam")
                print("  Pilihan:")
                print("    1 = Daftar pinjam buku")
                print("    2 = Proses peminjaman")
                print("    3 = Tampilkan antrian")
                print("    4 = Lihat Riwayat Peminjaman")
                print("    5 = Kembali ke Menu Utama")
                sub_choice = get_int("  Pilihan: ", 1, 5)

                # JIKA PILIH 5, BARU KELUAR DARI SUB-MENU
                if sub_choice == 5:
                    break

                # 1. Daftar Pinjam Buku
                if sub_choice == 1:
                    clear_screen()
                    print_title("Daftar Pinjam Buku")
                    member = input("  Nama anggota: ").strip()
                    code   = input("  Kode buku   : ").strip()

                    if not member or not code:
                        print()
                        print_error("Nama anggota dan kode buku tidak boleh kosong.")
                    else:
                        ok = lib.enqueue_borrow(member, code)
                        if ok:
                            print()
                            print_success(f"{member} masuk antrian")
                            print(f"  Buku  : {code.upper()}")
                            print(f"  Posisi: #{lib._queue._size} dalam antrian")

                    input("\n  Tekan Enter untuk kembali ke Sub-Menu Antrian...")
                    continue

                # 2. Proses Peminjaman
                elif sub_choice == 2:
                    clear_screen()
                    print_title("Proses Peminjaman")
                    if lib._queue.is_empty():
                        print()
                        print_info("Antrian kosong. Tidak ada peminjaman untuk diproses.")
                    else:
                        lib.process_borrow()
                    
                    input("\n  Tekan Enter untuk kembali ke Sub-Menu Antrian...")
                    continue

                # 3. Tampilkan Antrian
                elif sub_choice == 3:
                    clear_screen()
                    print_title("Antrian Peminjaman")
                    lib.display_queue()
                    
                    input("\n  Tekan Enter untuk kembali ke Sub-Menu Antrian...")
                    continue

                # 4. Lihat Riwayat Peminjaman
                elif sub_choice == 4:
                    clear_screen()
                    lib.display_history("PINJAM")
                    
                    input("\n  Tekan Enter untuk kembali ke Sub-Menu Antrian...")
                    continue

        # ---- 7: Pengembalian Buku ----
        elif pilihan == 7:
            while True:
                clear_screen()
                print_title("Pengembalian Buku")
                member = input("  Nama anggota yang mengembalikan: ").strip()
                code   = input("  Kode buku yang dikembalikan    : ").strip()
                
                if not member or not code:
                    print_error("Nama dan kode buku tidak boleh kosong.")
                else:
                    book = lib.find_book(code)
                    if book is None:
                        print_error(f"Buku dengan kode '{code.upper()}' tidak terdaftar.")
                    else:
                        # ---- VALIDASI UTAMA: CEK RIWAYAT PINJAM ----
                        if not lib.check_borrow_history(member, code):
                            print()
                            print_error(f"Gagal! Tidak ada data riwayat peminjaman buku [{code.upper()}] atas nama '{member}'.")
                        else:
                            # Jika lolos validasi riwayat, baru stok boleh bertambah
                            book.stock += 1
                            lib._ht.insert(book)
                            lib.save_to_file()  
                            lib.log_history(member, code, "KEMBALI")
                            print()
                            print_success(f"Buku [{book.code}] {book.title} berhasil dikembalikan oleh {member}.")
                            print(f"  Stok saat ini menjadi: {book.stock} unit.")
                
                ulang = get_yes_no("\n  Apakah anda ingin memproses pengembalian buku lagi? (y/n): ")
                if ulang == 'n':
                    break

        # ---- 8: Keluar ----
        elif pilihan == 8:
            clear_screen()
            print("\n  +----------------------------------------------+")
            print("  |                                              |")
            print("  |  Terima kasih telah menggunakan LibLine!     |")
            print("  |                                              |")
            print("  +----------------------------------------------+\n")
            break


if __name__ == "__main__":
    main()
