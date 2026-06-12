"""
================================================================
  LibLine.py — Sistem Penyimpanan & Pencarian Buku
================================================================
  Struktur data & algoritma yang digunakan:

  1. HASH TABLE (struktur data utama)
     - Menyimpan buku dengan kunci = kode buku
     - Hash function: polynomial rolling hash
     - Collision resolution: open addressing (linear probing)
     - Operasi: insert O(1) avg, search O(1) avg, delete O(1) avg

  2. QUEUE (antrian peminjaman)
     - Implementasi: circular array queue
     - Operasi: enqueue O(1), dequeue O(1), peek O(1)
     - Digunakan untuk antrian peminjaman buku

  3. MERGE SORT (pengurutan tampilan)
     - Mengurutkan daftar buku by kode/judul/pengarang/tahun
     - Kompleksitas: O(n log n)

  4. BINARY SEARCH (pencarian alternatif)
     - Mencari buku pada data yang sudah terurut
     - Digunakan sebagai alternatif saat hash table tidak optimal
     - Kompleksitas: O(log n)

  5. TRIE (autocomplete judul buku)
     - Menyimpan judul buku karakter demi karakter
     - Mencari semua judul yang cocok dengan awalan
     - Digunakan untuk fitur pencarian judul cepat

  6. HASH FUNCTION
     - Polynomial rolling hash: sum(ord(c) * BASE^i) % TABLE_SIZE
     - Menghasilkan indeks dari kode buku sebagai kunci
================================================================
"""

import os
from collections import deque
from datetime import date
from typing import Optional


# ================================================================
#  KONSTANTA KONFIGURASI
# ================================================================

TABLE_SIZE = 53

HASH_BASE = 31

QUEUE_CAPACITY = 20

DELETED = "__DELETED__"




# ================================================================
#  STRUKTUR DATA BUKU
# ================================================================

class Book:
    """
    Merepresentasikan satu buku dalam sistem.

    Atribut:
        code   (str)  : Kode unik buku, misal "BK001"
        title  (str)  : Judul buku
        author (str)  : Nama pengarang
        year   (int)  : Tahun terbit
        stock  (int)  : Jumlah stok tersedia
    """

    def __init__(self, code: str, title: str, author: str,
                 year: int, stock: int = 1):
        self.code   = code.upper().strip()
        self.title  = title.strip()
        self.author = author.strip()
        self.year   = year
        self.stock  = stock

    def __str__(self) -> str:
        """Format tampilan satu baris buku."""
        return (f"  [{self.code}] {self.title} — {self.author} "
                f"({self.year}) | Stok: {self.stock}")

    def detail(self) -> str:
        """Format tampilan detail buku (multi-baris)."""
        return (
            f"  Kode      : {self.code}\n"
            f"  Judul     : {self.title}\n"
            f"  Pengarang : {self.author}\n"
            f"  Tahun     : {self.year}\n"
            f"  Stok      : {self.stock}\n"
            f"  {'─'*40}"
        )


class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.title = None


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, title: str) -> None:
        current = self.root
        normalized = title.strip().lower()
        for char in normalized:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_end = True
        current.title = title.strip()

    def autocomplete(self, prefix: str) -> list:
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
    """
    Polynomial Rolling Hash Function.

    Rumus:
        hash = sum( ord(code[i]) * BASE^i ) % TABLE_SIZE

    Cara kerja:
        Setiap karakter dikonversi ke nilai ASCII (ord), lalu
        dikalikan dengan BASE dipangkatkan posisinya (i).
        Hasilnya dijumlahkan dan dimodulo TABLE_SIZE untuk
        menghasilkan indeks dalam rentang [0, TABLE_SIZE-1].

    Kenapa polynomial rolling hash?
        - Mempertimbangkan POSISI karakter, bukan hanya nilainya
        - "AB" dan "BA" menghasilkan hash berbeda
        - Distribusi lebih merata → lebih sedikit collision

    Contoh: hash("BK001")
        = (ord('B')*31^0 + ord('K')*31^1 + ord('0')*31^2 +
           ord('0')*31^3 + ord('1')*31^4) % 53

    Args:
        code: Kode buku yang akan di-hash

    Returns:
        Indeks integer dalam rentang [0, TABLE_SIZE-1]
    """
    h = 0
    for i, char in enumerate(code.upper()):
        h = (h + ord(char) * (HASH_BASE ** i)) % TABLE_SIZE
    return h


def probe(code: str, attempt: int) -> int:
    """
    Linear Probing: strategi resolusi collision.

    Ketika slot hash(code) sudah terisi (collision), cari slot
    berikutnya secara linear: (hash + 1), (hash + 2), dst.

    Rumus: index = (hash(code) + attempt) % TABLE_SIZE

    Kenapa linear probing?
        - Sederhana dan cache-friendly (akses memori berurutan)
        - Kekurangan: primary clustering (penumpukan di area tertentu)
        - Alternatif: quadratic probing atau double hashing

    Args:
        code    : Kode buku
        attempt : Percobaan ke-n (0 = posisi awal, 1 = +1, dst.)

    Returns:
        Indeks slot yang dicoba
    """
    return (hash_function(code) + attempt) % TABLE_SIZE


# ================================================================
#  HASH TABLE
# ================================================================

class HashTable:
    """
    Hash Table dengan open addressing (linear probing).

    Struktur internal:
        _table: list berukuran TABLE_SIZE
                - None     : slot kosong (belum pernah diisi)
                - DELETED  : slot bekas hapus (tombstone)
                - Book     : slot berisi buku

    Kenapa open addressing (bukan chaining)?
        - Lebih hemat memori (tidak perlu linked list)
        - Cache-friendly karena data tersimpan dalam satu array
        - Cocok untuk TABLE_SIZE yang cukup besar vs jumlah data
    """

    def __init__(self):
        self._table: list = [None] * TABLE_SIZE
        self._count: int  = 0

    # ---- INSERT ----
    def insert(self, book: Book) -> bool:
        """
        Menyimpan buku ke hash table.

        Cara kerja:
            1. Hitung indeks awal: idx = hash(book.code)
            2. Jika slot idx kosong (None atau DELETED) → simpan di sini
            3. Jika slot idx berisi buku dengan kode sama → update stok
            4. Jika slot idx berisi buku lain (collision) → probe +1
            5. Ulangi langkah 2-4 sampai slot kosong ditemukan

        Load factor check: jika > 70% penuh, tabel mulai lambat.

        Args:
            book: Objek Book yang akan disimpan

        Returns:
            True jika berhasil, False jika tabel penuh
        """
        if self._count >= int(TABLE_SIZE * 0.7):
            print("  [!] Hash table hampir penuh (>70%). Pertimbangkan resize.")

        for attempt in range(TABLE_SIZE):
            idx = probe(book.code, attempt)

            if self._table[idx] is None or self._table[idx] == DELETED:
                self._table[idx] = book
                self._count += 1
                return True

            if self._table[idx].code == book.code:
                self._table[idx] = book
                return True

        return False

    # ---- SEARCH ----
    def search(self, code: str) -> Optional["Book"]:
        """
        Mencari buku berdasarkan kode menggunakan hash table.

        Cara kerja:
            1. Hitung indeks: idx = hash(code)
            2. Jika slot[idx] berisi buku dengan kode yang dicari → ditemukan
            3. Jika slot[idx] == None → buku tidak ada (berhenti)
            4. Jika slot[idx] == DELETED atau kode berbeda → probe +1
            5. Ulangi sampai ditemukan, None, atau semua slot diperiksa

        Kenapa berhenti di None tapi tidak di DELETED?
            DELETED (tombstone) menandakan slot pernah berisi data.
            Buku yang dicari mungkin di-probe melewati slot ini,
            jadi pencarian harus terus berlanjut.

        Args:
            code: Kode buku yang dicari

        Returns:
            Objek Book jika ditemukan, None jika tidak ada
        """
        code = code.upper().strip()

        for attempt in range(TABLE_SIZE):
            idx = probe(code, attempt)

            if self._table[idx] is None:
                return None

            if self._table[idx] != DELETED and self._table[idx].code == code:
                return self._table[idx]


        return None

    # ---- DELETE ----
    def delete(self, code: str) -> bool:
        """
        Menghapus buku dari hash table menggunakan teknik tombstone.

        Kenapa tombstone (DELETED) bukan langsung None?
            Jika slot langsung dikosongkan (None), pencarian buku lain
            yang di-probe melewati slot ini akan berhenti prematur
            dan mengira buku tidak ada, padahal ada di slot berikutnya.
            Tombstone memastikan probe chain tidak terputus.

        Args:
            code: Kode buku yang akan dihapus

        Returns:
            True jika berhasil dihapus, False jika tidak ditemukan
        """
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

    # ---- GET ALL ----
    def get_all(self) -> list:
        """
        Mengambil semua buku yang tersimpan dalam hash table.

        Returns:
            List objek Book (urutan tidak dijamin — sesuai posisi hash)
        """
        return [slot for slot in self._table
                if slot is not None and slot != DELETED]

    def __len__(self) -> int:
        return self._count


# ================================================================
#  QUEUE (ANTRIAN PEMINJAMAN)
# ================================================================

class BorrowRequest:
    """
    Merepresentasikan satu permintaan peminjaman buku.

    Atribut:
        member_name (str)  : Nama anggota yang meminjam
        book_code   (str)  : Kode buku yang dipinjam
        request_date(str)  : Tanggal permintaan (otomatis diisi)
    """

    def __init__(self, member_name: str, book_code: str):
        self.member_name  = member_name.strip()
        self.book_code    = book_code.upper().strip()
        self.request_date = date.today().strftime("%d/%m/%Y")

    def __str__(self) -> str:
        return (f"  {self.member_name} → [{self.book_code}] "
                f"(masuk: {self.request_date})")


class BorrowQueue:
    """
    Antrian peminjaman buku menggunakan Circular Array Queue.

    Konsep Queue (FIFO — First In First Out):
        - Anggota yang pertama mendaftar, pertama dilayani
        - enqueue: tambah ke belakang antrian
        - dequeue: ambil dari depan antrian
        - peek   : lihat depan antrian tanpa mengambil

    Implementasi Circular Array:
        Menggunakan array tetap dengan dua pointer (front & rear).
        Saat rear mencapai ujung array, ia "melingkar" kembali ke 0.
        Ini menghindari pemborosan memori yang terjadi pada array biasa.

        Visualisasi (kapasitas 5):
            [ _ | A | B | C | _ ]
                  ^           ^
                front        rear

        Setelah dequeue A:
            [ _ | _ | B | C | _ ]
                       ^       ^
                     front    rear

    Atribut:
        _queue   : Array penyimpan antrian
        _front   : Indeks elemen terdepan
        _rear    : Indeks slot kosong berikutnya (setelah elemen terakhir)
        _size    : Jumlah elemen saat ini
        _capacity: Kapasitas maksimal
    """

    def __init__(self, capacity: int = QUEUE_CAPACITY):
        self._capacity = capacity
        self._queue: list = [None] * capacity
        self._front: int  = 0
        self._rear:  int  = 0
        self._size:  int  = 0

    def is_empty(self) -> bool:
        """Cek apakah antrian kosong."""
        return self._size == 0

    def is_full(self) -> bool:
        """Cek apakah antrian sudah penuh."""
        return self._size == self._capacity

    def enqueue(self, request: BorrowRequest) -> bool:
        """
        Menambahkan permintaan ke belakang antrian.

        Cara kerja:
            1. Cek apakah antrian penuh
            2. Simpan request di posisi _rear
            3. Geser _rear ke depan secara circular: (_rear + 1) % capacity
            4. Tambah _size

        Kompleksitas: O(1)

        Args:
            request: Objek BorrowRequest yang akan ditambahkan

        Returns:
            True jika berhasil, False jika antrian penuh
        """
        if self.is_full():
            return False

        self._queue[self._rear] = request
        self._rear = (self._rear + 1) % self._capacity
        self._size += 1
        return True

    def dequeue(self) -> Optional[BorrowRequest]:
        """
        Mengambil dan menghapus permintaan dari depan antrian.

        Cara kerja:
            1. Cek apakah antrian kosong
            2. Ambil elemen di posisi _front
            3. Kosongkan slot _front (set None)
            4. Geser _front ke depan secara circular
            5. Kurangi _size

        Kompleksitas: O(1)

        Returns:
            Objek BorrowRequest terdepan, atau None jika kosong
        """
        if self.is_empty():
            return None

        request = self._queue[self._front]
        self._queue[self._front] = None
        self._front = (self._front + 1) % self._capacity
        self._size -= 1
        return request

    def peek(self) -> Optional[BorrowRequest]:
        """
        Melihat permintaan terdepan tanpa menghapusnya.

        Returns:
            Objek BorrowRequest terdepan, atau None jika kosong
        """
        if self.is_empty():
            return None
        return self._queue[self._front]

    def display(self) -> None:
        """Menampilkan seluruh isi antrian dari depan ke belakang."""
        if self.is_empty():
            print("  Antrian kosong.")
            return

        print(f"  Antrian peminjaman ({self._size} orang):")
        for i in range(self._size):
            idx = (self._front + i) % self._capacity
            pos = "→ [DEPAN]" if i == 0 else f"  [{i+1}]   "
            print(f"  {pos} {self._queue[idx]}")

    def __len__(self) -> int:
        return self._size


# ================================================================
#  ALGORITMA MERGE SORT
# ================================================================

def merge_sort(books: list, key: str = "code") -> list:
    """
    Merge Sort untuk mengurutkan daftar buku.

    Algoritma divide & conquer:
        1. Bagi list menjadi dua bagian di titik tengah (divide)
        2. Urutkan bagian kiri secara rekursif
        3. Urutkan bagian kanan secara rekursif
        4. Gabungkan (merge) dua bagian yang sudah terurut

    Kompleksitas waktu : O(n log n) — untuk semua kasus
    Kompleksitas ruang : O(n)       — membutuhkan array sementara

    Key yang didukung:
        "code"   : urut by kode buku (A-Z)
        "title"  : urut by judul (A-Z, case-insensitive)
        "author" : urut by pengarang (A-Z, case-insensitive)
        "year"   : urut by tahun terbit (terlama ke terbaru)

    Args:
        books : List objek Book yang akan diurutkan
        key   : Kunci pengurutan

    Returns:
        List baru yang sudah terurut (list asli tidak berubah)
    """
    if len(books) <= 1:
        return books

    mid   = len(books) // 2
    left  = merge_sort(books[:mid], key)
    right = merge_sort(books[mid:], key)

    return _merge(left, right, key)


def _merge(left: list, right: list, key: str) -> list:
    """
    Fungsi merge: menggabungkan dua list terurut menjadi satu.

    Cara kerja:
        Bandingkan elemen terdepan dari kiri dan kanan.
        Masukkan yang lebih kecil ke result, geser pointer-nya.
        Ulangi sampai salah satu list habis, lalu salin sisanya.

    Args:
        left  : Sub-list kiri (sudah terurut)
        right : Sub-list kanan (sudah terurut)
        key   : Kunci perbandingan

    Returns:
        List gabungan yang terurut
    """
    result = []
    i = j  = 0

    def get_key(book: Book):
        if   key == "title":  return book.title.lower()
        elif key == "author": return book.author.lower()
        elif key == "year":   return book.year
        else:                 return book.code.lower()

    while i < len(left) and j < len(right):
        if get_key(left[i]) <= get_key(right[j]):
            result.append(left[i]);  i += 1
        else:
            result.append(right[j]); j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


# ================================================================
#  ALGORITMA BINARY SEARCH (Pencarian Alternatif)
# ================================================================

def binary_search(sorted_books: list, target_code: str) -> int:
    """
    Binary Search pada list buku yang sudah terurut by kode.

    Digunakan sebagai PENCARIAN ALTERNATIF dalam skenario:
        - Hash table sedang dalam proses rehashing
        - Verifikasi hasil pencarian hash (double-check)
        - Pencarian pada subset data yang sudah diurutkan
        - Demonstrasi perbandingan efisiensi vs hash table

    Cara kerja:
        1. Tentukan rentang pencarian [left, right]
        2. Hitung titik tengah: mid = (left + right) // 2
        3. Jika sorted_books[mid].code == target → ditemukan (return mid)
        4. Jika target > sorted_books[mid].code  → cari di kanan
        5. Jika target < sorted_books[mid].code  → cari di kiri
        6. Ulangi sampai ditemukan atau left > right

    Kompleksitas waktu : O(log n) — setiap iterasi memangkas setengah data
    Kompleksitas ruang : O(1)     — tidak butuh memori tambahan

    SYARAT: List HARUS sudah terurut by kode sebelum dicari.
            Gunakan merge_sort(books, "code") terlebih dahulu.

    Args:
        sorted_books : List Book yang sudah terurut by kode
        target_code  : Kode buku yang dicari

    Returns:
        Indeks buku dalam list, atau -1 jika tidak ditemukan
    """
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
#  SISTEM LIBLINE
# ================================================================

class LibLine:
    """
    Sistem utama LibLine yang mengintegrasikan semua komponen:
        - HashTable  : penyimpanan & pencarian buku
        - BorrowQueue: antrian peminjaman
        - MergeSort  : pengurutan tampilan
        - BinarySearch: pencarian alternatif

    Semua operasi publik ada di kelas ini sebagai antarmuka tunggal.
    """

    def __init__(self):
        self._ht          = HashTable()
        self._queue       = BorrowQueue()
        self._title_trie  = Trie()

    def _rebuild_title_trie(self) -> None:
        self._title_trie = Trie()
        for book in self._ht.get_all():
            self._title_trie.insert(book.title)

    # ---- TAMBAH BUKU ----
    def add_book(self, code: str, title: str, author: str,
                 year: int, stock: int = 1) -> bool:
        """
        Menambahkan buku baru ke hash table.

        Proses:
            1. Buat objek Book
            2. Cek apakah kode sudah ada (update vs insert baru)
            3. Simpan ke hash table via insert()

        Args:
            code   : Kode unik buku
            title  : Judul buku
            author : Nama pengarang
            year   : Tahun terbit
            stock  : Jumlah stok (default 1)

        Returns:
            True jika berhasil
        """
        book = Book(code, title, author, year, stock)
        ok = self._ht.insert(book)
        if ok:
            self._rebuild_title_trie()
        return ok

    # ---- CARI BUKU (HASH TABLE) ----
    def find_book(self, code: str) -> Optional[Book]:
        """
        Mencari buku berdasarkan kode menggunakan hash table.
        Kompleksitas rata-rata: O(1).

        Args:
            code: Kode buku yang dicari

        Returns:
            Objek Book jika ditemukan, None jika tidak ada
        """
        return self._ht.search(code)

    # ---- CARI BUKU (BINARY SEARCH — alternatif) ----
    def find_book_binary(self, code: str) -> Optional[Book]:
        """
        Mencari buku menggunakan Binary Search sebagai metode alternatif.

        Skenario penggunaan:
            - Verifikasi hasil pencarian hash table
            - Pencarian pada subset data terurut
            - Perbandingan performa dengan hash table

        Proses:
            1. Ambil semua buku dari hash table
            2. Urutkan by kode dengan Merge Sort
            3. Jalankan Binary Search pada list terurut

        Kompleksitas: O(n log n) untuk sort + O(log n) untuk search

        Args:
            code: Kode buku yang dicari

        Returns:
            Objek Book jika ditemukan, None jika tidak ada
        """
        all_books   = self._ht.get_all()
        sorted_books = merge_sort(all_books, "code")

        print(f"\n  [Binary Search] Mencari '{code.upper()}' "
              f"dari {len(sorted_books)} buku terurut:")
        idx = binary_search(sorted_books, code)

        if idx == -1:
            return None
        return sorted_books[idx]

    # ---- CARI JUDUL (TRIE) ----
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

    # ---- HAPUS BUKU ----
    def remove_book(self, code: str) -> bool:
        """
        Menghapus buku dari hash table.

        Args:
            code: Kode buku yang akan dihapus

        Returns:
            True jika berhasil, False jika tidak ditemukan
        """
        ok = self._ht.delete(code)
        if ok:
            self._rebuild_title_trie()
        return ok

    # ---- TAMPILKAN SEMUA BUKU (SORTED) ----
    def display_all(self, key: str = "code") -> None:
        """
        Menampilkan semua buku yang diurutkan dengan Merge Sort.

        Args:
            key: Kunci pengurutan — "code", "title", "author", "year"
        """
        books = self._ht.get_all()
        if not books:
            print_error("Belum ada buku dalam sistem.")
            return

        sorted_books = merge_sort(books, key)
        label = {"code": "Kode", "title": "Judul",
                 "author": "Pengarang", "year": "Tahun Terbit"}

        print(f"\n  --- Daftar Buku (Urut: {label.get(key, key)}) ---\n")

        print("  +-----+-------+------------------------+---------------------+------+-------+")
        print("  | No. | Kode  | Judul                  | Pengarang           | Thn  | Stok  |")
        print("  +-----+-------+------------------------+---------------------+------+-------+")

        for i, book in enumerate(sorted_books, 1):
            title_short = (book.title[:22] if len(book.title) > 22 else book.title).ljust(22)
            author_short = (book.author[:19] if len(book.author) > 19 else book.author).ljust(19)
            print(f"  | {i:>3} | {book.code} | {title_short} | {author_short} | {book.year} | {book.stock:>5} |")

        print("  +-----+-------+------------------------+---------------------+------+-------+")
        print(f"\n  Total: {len(sorted_books)} buku")

    # ---- TAMPILKAN INFO HASH TABLE ----
    def display_hash_info(self, code: str) -> None:
        """
        Menampilkan informasi teknis hash function untuk kode tertentu.
        Berguna untuk memahami cara kerja hashing.

        Args:
            code: Kode buku yang ingin dilihat nilai hash-nya
        """
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

    # ---- ANTRIAN: DAFTAR PINJAM ----
    def enqueue_borrow(self, member: str, code: str) -> bool:
        """
        Mendaftarkan permintaan peminjaman ke antrian.

        Validasi:
            - Buku harus ada di sistem
            - Stok buku harus > 0
            - Antrian tidak boleh penuh

        Args:
            member: Nama anggota
            code  : Kode buku yang ingin dipinjam

        Returns:
            True jika berhasil masuk antrian
        """
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

    # ---- ANTRIAN: PROSES PEMINJAMAN ----
    def process_borrow(self) -> bool:
        """
        Memproses permintaan peminjaman terdepan dari antrian.

        Proses:
            1. Dequeue permintaan terdepan
            2. Cari buku di hash table
            3. Kurangi stok buku sebesar 1
            4. Tampilkan konfirmasi

        Returns:
            True jika berhasil diproses, False jika antrian kosong
        """
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

        print()
        print_success("Peminjaman diproses!")
        print(f"  Anggota   : {req.member_name}")
        print(f"  Buku      : [{book.code}] {book.title}")
        print(f"  Stok sisa : {book.stock} unit")
        return True

    # ---- ANTRIAN: TAMPILKAN ----
    def display_queue(self) -> None:
        """Menampilkan seluruh isi antrian peminjaman."""
        if self._queue.is_empty():
            print()
            print_info("Antrian peminjaman kosong.")
            return

        print(f"\n  --- Antrian Peminjaman ---\n")
        print("  +-----+------------------------+------+")
        print("  | No. | Nama Anggota           | Buku |")
        print("  +-----+------------------------+------+")

        self._queue.display()

        print("  +-----+------------------------+------+")
        print(f"\n  Total: {len(self._queue)} peminjam dalam antrian")

    # ---- UPDATE STOK ----
    def update_stock(self, code: str, delta: int) -> bool:
        """
        Menambah atau mengurangi stok buku.

        Args:
            code  : Kode buku
            delta : Perubahan stok (positif = tambah, negatif = kurangi)

        Returns:
            True jika berhasil
        """
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
    """Mencetak header aplikasi."""
    clear_screen()
    print("  +----------------------------------------------+")
    print("  |        LibLine — Sistem Perpustakaan         |")
    print("  |          Digital Management System           |")
    print("  +----------------------------------------------+\n")


def clear_screen():
    """
    Membersihkan layar terminal.
    Cross-platform: bekerja di Windows, Linux, dan macOS.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def print_success(text: str) -> None:
    """Mencetak pesan sukses."""
    print(f"  [OK] {text}")


def print_error(text: str) -> None:
    """Mencetak pesan error."""
    print(f"  [!] {text}")


def print_info(text: str) -> None:
    """Mencetak pesan informasi."""
    print(f"  [i] {text}")


def print_title(text: str) -> None:
    """Mencetak judul dengan border."""
    print(f"\n  +----------------------------------------------+")
    padding = (46 - len(text)) // 2
    print(f"  |{' ' * padding}{text}{' ' * (46 - padding - len(text))}|")
    print(f"  +----------------------------------------------+\n")


def print_menu():
    """Mencetak menu utama dengan border ASCII."""
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
    print("  |  7 | -- | Keluar                            |")
    print("  +----+----+----------------------------------+")
    


def get_int(prompt: str, min_val: int = None, max_val: int = None) -> int:
    """
    Meminta input integer dari pengguna dengan validasi.

    Args:
        prompt  : Teks yang ditampilkan
        min_val : Nilai minimum yang diizinkan (opsional)
        max_val : Nilai maksimum yang diizinkan (opsional)

    Returns:
        Integer yang valid
    """
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


def main():
    """
    Fungsi utama — menjalankan loop menu CLI LibLine.

    Alur program:
        1. Inisialisasi sistem LibLine (hash table + queue)
        2. Isi data awal sebagai contoh
        3. Tampilkan menu dan proses pilihan pengguna
        4. Ulangi sampai pengguna memilih keluar
    """
    lib = LibLine()

    # ---- Data awal ----
    initial_books = [
        ("BK001", "Laskar Pelangi",          "Andrea Hirata",    2005, 3),
        ("BK002", "Bumi Manusia",             "Pramoedya A. Toer",1980, 2),
        ("BK003", "Negeri 5 Menara",          "Ahmad Fuadi",      2009, 4),
        ("BK004", "Perahu Kertas",            "Dee Lestari",      2009, 2),
        ("BK005", "Dilan 1990",               "Pidi Baiq",        2014, 5),
        ("BK006", "Filosofi Teras",           "Henry Manampiring",2018, 3),
        ("BK007", "Atomic Habits",            "James Clear",      2018, 2),
        ("BK008", "The Alchemist",            "Paulo Coelho",     1988, 1),
    ]
    for args in initial_books:
        lib.add_book(*args)

    print_header()
    print_success("Data awal berhasil dimuat (8 buku).")

    input("\n  Tekan Enter untuk memulai...")

    # ---- Loop menu utama ----
    while True:
        print_menu()
        pilihan = get_int("\n  Pilih menu [1-7]: ", 1, 7)

        # ---- 1: Tambah Buku ----
        if pilihan == 1:
            clear_screen()
            print_title("Tambah Buku Baru")
            code   = input("  Kode buku   : ").strip()
            title  = input("  Judul       : ").strip()
            author = input("  Pengarang   : ").strip()
            year   = get_int("  Tahun terbit: ", 1000, 9999)
            stock  = get_int("  Stok        : ", 0)

            if not code or not title or not author:
                print_error("Kode, judul, dan pengarang tidak boleh kosong.")
                input("\n  Tekan Enter untuk kembali...")
                continue

            ok = lib.add_book(code, title, author, year, stock)
            if ok:
                h = hash_function(code.upper())
                print()
                print_success(f"Buku ditambahkan ke slot hash #{h}")
                print(f"  Kode  : {code.upper()}")
                print(f"  Judul : {title}")
            else:
                print_error("Gagal menambahkan buku (tabel penuh).")

            input("\n  Tekan Enter untuk kembali...")

        # ---- 2: Hapus Buku ----
        elif pilihan == 2:
            clear_screen()
            print_title("Hapus Buku")
            code = input("  Kode buku yang akan dihapus: ").strip()

            book = lib.find_book(code)
            if book is None:
                print_error(f"Buku '{code.upper()}' tidak ditemukan.")
                input("\n  Tekan Enter untuk kembali...")
                continue

            print(f"\n  Detail Buku:")
            print(book.detail())
            konfirm = input(f"\n  Yakin hapus? (y/n): ").strip().lower()
            if konfirm == 'y':
                lib.remove_book(code)
                print_success("Buku berhasil dihapus dari sistem.")
            else:
                print_info("Penghapusan dibatalkan.")

            input("\n  Tekan Enter untuk kembali...")

        # ---- 3: Update Stok ----
        elif pilihan == 3:
            clear_screen()
            print_title("Update Stok Buku")
            code = input("  Kode buku: ").strip()

            book = lib.find_book(code)
            if book is None:
                print_error(f"Buku '{code.upper()}' tidak ditemukan.")
                input("\n  Tekan Enter untuk kembali...")
                continue

            print("\n  Detail Buku:")
            print(book.detail())
            print(f"\n  Stok saat ini: {book.stock} unit")
            print("  Operasi: 1=Tambah  2=Kurangi")
            op     = get_int("  Pilihan: ", 1, 2)
            jumlah = get_int("  Jumlah : ", 1)

            delta = jumlah if op == 1 else -jumlah
            ok    = lib.update_stock(code, delta)
            if ok:
                updated = lib.find_book(code)
                print()
                print_success(f"Stok diperbarui → {updated.stock} unit")

            input("\n  Tekan Enter untuk kembali...")

        # ---- 4: Tampilkan Semua Buku ----
        elif pilihan == 4:
            clear_screen()
            print_title("Daftar Semua Buku")
            print("  Urutkan berdasarkan:")
            print("    1=Kode  2=Judul  3=Pengarang  4=Tahun Terbit")
            opt = get_int("  Pilihan: ", 1, 4)

            clear_screen()
            key_map = {1: "code", 2: "title", 3: "author", 4: "year"}
            lib.display_all(key_map[opt])

            input("\n  Tekan Enter untuk kembali...")

        # ---- 5: Cari Buku ----
        elif pilihan == 5:
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
                    input("\n  Tekan Enter untuk kembali...")
                    continue

                books = lib.find_books_by_title_prefix(prefix)
                if books:
                    print("\n  Hasil Pencarian:")
                    for i, book in enumerate(books, start=1):
                        print(f"\n  {i}. {book.title}")
                        print(book.detail())
                else:
                    print()
                    print_error("Tidak ditemukan judul buku dengan awalan tersebut.")

            input("\n  Tekan Enter untuk kembali...")

        # ---- 6: Antrian Pinjam ----
        elif pilihan == 6:
            clear_screen()
            print_title("Antrian Pinjam")
            print("  Pilihan:")
            print("    1 = Daftar pinjam buku")
            print("    2 = Proses peminjaman")
            print("    3 = Tampilkan antrian")
            print("    4 = Kembali")
            sub_choice = get_int("  Pilihan: ", 1, 4)

            if sub_choice == 1:
                clear_screen()
                print_title("Daftar Pinjam Buku")
                member = input("  Nama anggota: ").strip()
                code   = input("  Kode buku   : ").strip()

                if not member:
                    print()
                    print_error("Nama anggota tidak boleh kosong.")
                else:
                    ok = lib.enqueue_borrow(member, code)
                    if ok:
                        print()
                        print_success(f"{member} masuk antrian")
                        print(f"  Buku  : {code.upper()}")
                        print(f"  Posisi: #{len(lib._queue)} dalam antrian")

            elif sub_choice == 2:
                clear_screen()
                print_title("Proses Peminjaman")
                if lib._queue.is_empty():
                    print()
                    print_info("Antrian kosong. Tidak ada peminjaman untuk diproses.")
                else:
                    lib.process_borrow()

            elif sub_choice == 3:
                clear_screen()
                print_title("Antrian Peminjaman")
                lib.display_queue()

            input("\n  Tekan Enter untuk kembali...")

        # ---- 7: Keluar ----
        elif pilihan == 7:
            clear_screen()
            print("\n  +----------------------------------------------+")
            print("  |                                              |")
            print("  |  Terima kasih telah menggunakan LibLine!     |")
            print("  |                                              |")
            print("  +----------------------------------------------+\n")
            break


# ================================================================
#  ENTRY POINT
# ================================================================

if __name__ == "__main__":
    main()
