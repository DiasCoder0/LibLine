/* ================================================================
   LibLine Web — app.js
   Semua algoritma diimplementasikan persis seperti versi Python:
   - Hash Table (Polynomial Rolling Hash + Linear Probing)
   - Trie (Autocomplete judul)
   - Merge Sort (pengurutan buku)
   - Binary Search (pencarian by kode)
   - Circular Queue (antrian peminjaman FIFO, kapasitas 20)
   ================================================================ */

'use strict';

// ================================================================
//  KONSTANTA
// ================================================================
const TABLE_SIZE    = 53;
const HASH_BASE     = 31;
const QUEUE_CAP     = 20;
const DELETED       = '__DELETED__';
const LS_BOOKS      = 'libline_books';
const LS_HISTORY    = 'libline_history';

// ================================================================
//  HASH FUNCTION  (Polynomial Rolling Hash — sama persis Python)
// ================================================================
function hashFunction(code) {
  let h = 0;
  const upper = code.toUpperCase();
  for (let i = 0; i < upper.length; i++) {
    h = (h + upper.charCodeAt(i) * Math.pow(HASH_BASE, i)) % TABLE_SIZE;
  }
  return h;
}

function probe(code, attempt) {
  return (hashFunction(code) + attempt) % TABLE_SIZE;
}

// ================================================================
//  HASH TABLE
// ================================================================
class HashTable {
  constructor() {
    this._table = new Array(TABLE_SIZE).fill(null);
    this._count = 0;
  }

  insert(book) {
    for (let attempt = 0; attempt < TABLE_SIZE; attempt++) {
      const idx = probe(book.code, attempt);
      if (this._table[idx] === null || this._table[idx] === DELETED) {
        this._table[idx] = book;
        this._count++;
        return true;
      }
      if (this._table[idx].code === book.code) {
        this._table[idx] = book; // update
        return true;
      }
    }
    return false;
  }

  search(code) {
    const upper = code.toUpperCase().trim();
    for (let attempt = 0; attempt < TABLE_SIZE; attempt++) {
      const idx = probe(upper, attempt);
      if (this._table[idx] === null) return null;
      if (this._table[idx] !== DELETED && this._table[idx].code === upper) {
        return this._table[idx];
      }
    }
    return null;
  }

  delete(code) {
    const upper = code.toUpperCase().trim();
    for (let attempt = 0; attempt < TABLE_SIZE; attempt++) {
      const idx = probe(upper, attempt);
      if (this._table[idx] === null) return false;
      if (this._table[idx] !== DELETED && this._table[idx].code === upper) {
        this._table[idx] = DELETED;
        this._count--;
        return true;
      }
    }
    return false;
  }

  getAll() {
    return this._table.filter(s => s !== null && s !== DELETED);
  }
}

// ================================================================
//  TRIE  (Autocomplete judul)
// ================================================================
class TrieNode {
  constructor() { this.children = {}; this.isEnd = false; this.title = null; }
}

class Trie {
  constructor() { this.root = new TrieNode(); }

  insert(title) {
    let cur = this.root;
    const norm = title.trim().toLowerCase();
    for (const ch of norm) {
      if (!cur.children[ch]) cur.children[ch] = new TrieNode();
      cur = cur.children[ch];
    }
    cur.isEnd = true;
    cur.title = title.trim();
  }

  autocomplete(prefix) {
    let cur = this.root;
    const norm = prefix.trim().toLowerCase();
    for (const ch of norm) {
      if (!cur.children[ch]) return [];
      cur = cur.children[ch];
    }
    const results = [];
    this._collect(cur, results);
    return results.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
  }

  _collect(node, results) {
    if (node.isEnd && node.title) results.push(node.title);
    for (const child of Object.values(node.children)) this._collect(child, results);
  }
}

// ================================================================
//  MERGE SORT
// ================================================================
function mergeSort(books, key = 'code') {
  if (books.length <= 1) return books;
  const mid = Math.floor(books.length / 2);
  const left  = mergeSort(books.slice(0, mid), key);
  const right = mergeSort(books.slice(mid),    key);
  return merge(left, right, key);
}

function getKey(book, key) {
  if (key === 'title')  return book.title.toLowerCase();
  if (key === 'author') return book.author.toLowerCase();
  if (key === 'year')   return book.year;
  return book.code.toLowerCase();
}

function merge(left, right, key) {
  const result = []; let i = 0, j = 0;
  while (i < left.length && j < right.length) {
    if (getKey(left[i], key) <= getKey(right[j], key)) result.push(left[i++]);
    else result.push(right[j++]);
  }
  return result.concat(left.slice(i)).concat(right.slice(j));
}

// ================================================================
//  BINARY SEARCH  (mengembalikan {index, steps[]})
// ================================================================
function binarySearch(sortedBooks, targetCode) {
  const target = targetCode.toUpperCase().trim();
  let left = 0, right = sortedBooks.length - 1;
  const steps = [];

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const midCode = sortedBooks[mid].code;
    const found = midCode === target;
    steps.push({ mid, code: midCode, found, left, right });
    if (found) return { index: mid, steps };
    if (midCode < target) left = mid + 1;
    else right = mid - 1;
  }
  return { index: -1, steps };
}

// ================================================================
//  CIRCULAR QUEUE  (peminjaman FIFO)
// ================================================================
class BorrowQueue {
  constructor(capacity = QUEUE_CAP) {
    this._cap   = capacity;
    this._queue = new Array(capacity).fill(null);
    this._front = 0;
    this._rear  = 0;
    this._size  = 0;
  }
  isEmpty() { return this._size === 0; }
  isFull()  { return this._size === this._cap; }

  enqueue(req) {
    if (this.isFull()) return false;
    this._queue[this._rear] = req;
    this._rear = (this._rear + 1) % this._cap;
    this._size++;
    return true;
  }

  dequeue() {
    if (this.isEmpty()) return null;
    const req = this._queue[this._front];
    this._queue[this._front] = null;
    this._front = (this._front + 1) % this._cap;
    this._size--;
    return req;
  }

  toArray() {
    const arr = [];
    for (let i = 0; i < this._size; i++) {
      arr.push(this._queue[(this._front + i) % this._cap]);
    }
    return arr;
  }
}

// ================================================================
//  LIBLINE CORE
// ================================================================
class LibLine {
  constructor() {
    this._ht    = new HashTable();
    this._queue = new BorrowQueue();
    this._trie  = new Trie();
  }

  _rebuildTrie() {
    this._trie = new Trie();
    for (const b of this._ht.getAll()) this._trie.insert(b.title);
  }

  // ── Persistence (localStorage) ──
  save() {
    const obj = {};
    for (const b of this._ht.getAll()) {
      obj[b.code] = { title: b.title, author: b.author, year: b.year, stock: b.stock, rack: b.rack };
    }
    localStorage.setItem(LS_BOOKS, JSON.stringify(obj));
  }

  load() {
    const raw = localStorage.getItem(LS_BOOKS);
    if (!raw) return false;
    try {
      const data = JSON.parse(raw);
      for (const [code, info] of Object.entries(data)) {
        this._ht.insert({ code: code.toUpperCase(), title: info.title, author: info.author,
                          year: info.year, stock: info.stock, rack: info.rack });
      }
      this._rebuildTrie();
      return true;
    } catch { return false; }
  }

  // ── Riwayat ──
  logHistory(memberName, bookCode, action) {
    const history = this.getHistory();
    const key = new Date().toISOString();
    history[key] = {
      name: memberName.trim(),
      book_code: bookCode.toUpperCase(),
      action,
      date: new Date().toLocaleString('id-ID', { day:'2-digit', month:'2-digit',
            year:'numeric', hour:'2-digit', minute:'2-digit' })
    };
    localStorage.setItem(LS_HISTORY, JSON.stringify(history));
  }

  getHistory() {
    try { return JSON.parse(localStorage.getItem(LS_HISTORY) || '{}'); } catch { return {}; }
  }

  checkBorrowHistory(memberName, bookCode) {
    const history = this.getHistory();
    const tName = memberName.trim().toLowerCase();
    const tCode = bookCode.trim().toUpperCase();
    for (const log of Object.values(history)) {
      if (log.name.trim().toLowerCase() === tName && log.book_code === tCode && log.action === 'PINJAM') {
        return true;
      }
    }
    return false;
  }

  // ── Operasi Buku ──
  addBook(code, title, author, year, rack, stock = 1) {
    if (this._ht.search(code.toUpperCase())) return { ok: false, msg: 'Kode buku sudah digunakan.' };
    const book = { code: code.toUpperCase().trim(), title: title.trim(),
                   author: author.trim(), year: parseInt(year), stock: parseInt(stock),
                   rack: rack.toUpperCase().trim() };
    const ok = this._ht.insert(book);
    if (ok) { this._rebuildTrie(); this.save(); }
    return ok ? { ok: true, slot: hashFunction(code.toUpperCase()) }
              : { ok: false, msg: 'Hash Table penuh.' };
  }

  findBook(code) { return this._ht.search(code); }

  findBookBinary(code) {
    const all = mergeSort(this._ht.getAll(), 'code');
    const { index, steps } = binarySearch(all, code);
    return { book: index >= 0 ? all[index] : null, steps, total: all.length };
  }

  findByTitlePrefix(prefix) {
    if (!prefix.trim()) return [];
    return this._trie.autocomplete(prefix);
  }

  findBooksByTitlePrefix(prefix) {
    const titles = new Set(this._trie.autocomplete(prefix).map(t => t.toLowerCase()));
    return this._ht.getAll().filter(b => titles.has(b.title.toLowerCase()));
  }

  removeBook(code) {
    const ok = this._ht.delete(code);
    if (ok) { this._rebuildTrie(); this.save(); }
    return ok;
  }

  updateStock(code, delta) {
    const book = this._ht.search(code);
    if (!book) return { ok: false, msg: 'Buku tidak ditemukan.' };
    const newStock = book.stock + delta;
    if (newStock < 0) return { ok: false, msg: `Stok tidak cukup. Stok saat ini: ${book.stock}` };
    book.stock = newStock;
    this._ht.insert(book);
    this.save();
    return { ok: true, stock: newStock };
  }

  getAllSorted(key = 'code') { return mergeSort(this._ht.getAll(), key); }

  // ── Queue Peminjaman ──
  enqueueBorrow(member, code) {
    const book = this._ht.search(code);
    if (!book)          return { ok: false, msg: `Buku '${code.toUpperCase()}' tidak ditemukan.` };
    if (book.stock <= 0) return { ok: false, msg: `Stok buku '${code.toUpperCase()}' habis.` };
    if (this._queue.isFull()) return { ok: false, msg: 'Antrian penuh (20/20). Coba lagi nanti.' };
    const req = { memberName: member.trim(), bookCode: code.toUpperCase(),
                  date: new Date().toLocaleDateString('id-ID') };
    this._queue.enqueue(req);
    return { ok: true, pos: this._queue._size };
  }

  processBorrow() {
    const req = this._queue.dequeue();
    if (!req) return { ok: false, msg: 'Antrian kosong.' };
    const book = this._ht.search(req.bookCode);
    if (!book) return { ok: false, msg: `Buku '${req.bookCode}' tidak ditemukan saat proses.` };
    book.stock--;
    this._ht.insert(book);
    this.save();
    this.logHistory(req.memberName, book.code, 'PINJAM');
    return { ok: true, req, book };
  }

  returnBook(member, code) {
    const book = this._ht.search(code);
    if (!book) return { ok: false, msg: `Buku dengan kode '${code.toUpperCase()}' tidak terdaftar.` };
    if (!this.checkBorrowHistory(member, code)) {
      return { ok: false, msg: `Tidak ada riwayat peminjaman buku [${code.toUpperCase()}] atas nama '${member}'.` };
    }
    book.stock++;
    this._ht.insert(book);
    this.save();
    this.logHistory(member, code, 'KEMBALI');
    return { ok: true, book };
  }
}

// ================================================================
//  INITIAL DATA (sama seperti Python)
// ================================================================
const lib = new LibLine(); // deklarasi di sini agar bisa dipakai oleh semua event listener

const INITIAL_BOOKS = [
  { code:'BK001', title:'Laskar Pelangi',    author:'Andrea Hirata',     year:2005, rack:'A1', stock:3 },
  { code:'BK002', title:'Bumi Manusia',      author:'Pramoedya A. Toer', year:1980, rack:'C3', stock:2 },
  { code:'BK003', title:'Negeri 5 Menara',   author:'Ahmad Fuadi',       year:2009, rack:'E8', stock:4 },
  { code:'BK004', title:'Perahu Kertas',     author:'Dee Lestari',       year:2009, rack:'B1', stock:2 },
  { code:'BK005', title:'Dilan 1990',        author:'Pidi Baiq',         year:2014, rack:'C2', stock:5 },
  { code:'BK006', title:'Filosofi Teras',    author:'Henry Manampiring', year:2018, rack:'D3', stock:3 },
  { code:'BK007', title:'Atomic Habits',     author:'James Clear',       year:2018, rack:'I5', stock:2 },
  { code:'BK008', title:'The Alchemist',     author:'Paulo Coelho',      year:1988, rack:'D2', stock:1 },
];

// ================================================================
//  UI HELPERS
// ================================================================
const $ = (id) => document.getElementById(id);

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  el.textContent = `${icon} ${msg}`;
  $('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function showResult(elId, msg, type) {
  const el = $(elId);
  el.className = `result-box ${type}`;
  el.innerHTML = msg;
  el.classList.remove('hidden');
}

function hideResult(elId) {
  const el = $(elId);
  if (el) { el.classList.add('hidden'); el.innerHTML = ''; }
}

function stockBadge(stock) {
  const cls = stock === 0 ? 'stock-zero' : stock <= 1 ? 'stock-warn' : 'stock-ok';
  return `<span class="stock-badge ${cls}">${stock}</span>`;
}

function showConfirm(title, msg, onConfirm) {
  $('modal-title').textContent = title;
  $('modal-msg').textContent   = msg;
  $('modal-overlay').classList.remove('hidden');
  const btnConfirm = $('modal-confirm');
  const btnCancel  = $('modal-cancel');
  const close = () => $('modal-overlay').classList.add('hidden');
  btnConfirm.onclick = () => { close(); onConfirm(); };
  btnCancel.onclick  = close;
}

// ================================================================
//  NAVIGATION
// ================================================================
function navigate(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const page = $(`page-${pageId}`);
  if (page) page.classList.add('active');
  const nav = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  if (nav) nav.classList.add('active');

  // Refresh data saat masuk halaman
  if (pageId === 'books')        renderBooksTable();
  if (pageId === 'borrow-queue') renderQueue();
  if (pageId === 'history')      renderHistory(_historyFilter);
}

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => {
    navigate(el.dataset.page);
    // tutup sidebar di mobile
    document.getElementById('sidebar').classList.remove('open');
  });
});

$('hamburger').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
});

// ================================================================
//  PAGE: 4. TAMPILKAN SEMUA BUKU
// ================================================================
function renderBooksTable() {
  const key  = $('sort-key').value;
  const books = lib.getAllSorted(key);
  const tbody = $('books-tbody');
  $('total-books-label').textContent = `${books.length} buku`;
  $('book-count-badge').textContent  = books.length;

  if (!books.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Belum ada buku dalam sistem.</td></tr>`;
    return;
  }

  tbody.innerHTML = books.map((b, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><span class="code-badge">${b.code}</span></td>
      <td>${b.title}</td>
      <td>${b.author}</td>
      <td>${b.year}</td>
      <td>${stockBadge(b.stock)}</td>
      <td><span class="rack-badge">${b.rack}</span></td>
    </tr>`).join('');
}

$('sort-key').addEventListener('change', renderBooksTable);

// ================================================================
//  PAGE: 1. TAMBAH BUKU
// ================================================================
let _deleteTarget = null;

$('btn-find-delete').addEventListener('click', () => {
  const code = $('delete-code').value.trim();
  if (!code) { showResult('delete-result', '❌ Masukkan kode buku terlebih dahulu.', 'error'); return; }
  const book = lib.findBook(code);
  if (!book) {
    showResult('delete-result', `❌ Buku '${code.toUpperCase()}' tidak ditemukan.`, 'error');
    $('delete-book-preview').classList.add('hidden');
    $('btn-do-delete').classList.add('hidden');
    _deleteTarget = null;
    return;
  }
  _deleteTarget = book;
  hideResult('delete-result');
  $('delete-book-preview').innerHTML =
    `<strong>${book.title}</strong> — ${book.author} (${book.year})<br>
     Kode: <strong>${book.code}</strong> | Rak: <strong>${book.rack}</strong> | Stok: <strong>${book.stock}</strong>`;
  $('delete-book-preview').classList.remove('hidden');
  $('btn-do-delete').classList.remove('hidden');
});

$('delete-code').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); $('btn-find-delete').click(); }
});

$('form-delete-book').addEventListener('submit', (e) => {
  e.preventDefault();
  if (!_deleteTarget) return;
  showConfirm(
    'Hapus Buku',
    `Yakin hapus "${_deleteTarget.title}" (${_deleteTarget.code})?`,
    () => {
      lib.removeBook(_deleteTarget.code);
      showResult('delete-result', `✅ Buku <strong>${_deleteTarget.code}</strong> "${_deleteTarget.title}" berhasil dihapus dari sistem.`, 'success');
      $('delete-book-preview').classList.add('hidden');
      $('btn-do-delete').classList.add('hidden');
      $('delete-code').value = '';
      toast(`Buku ${_deleteTarget.code} berhasil dihapus.`, 'success');
      $('book-count-badge').textContent = lib.getAllSorted().length;
      _deleteTarget = null;
    }
  );
});

// ================================================================
//  PAGE: TAMBAH BUKU
// ================================================================
$('form-add-book').addEventListener('submit', (e) => {
  e.preventDefault();
  const code   = $('add-code').value.trim();
  const title  = $('add-title').value.trim();
  const author = $('add-author').value.trim();
  const year   = parseInt($('add-year').value);
  const stock  = parseInt($('add-stock').value);
  const rack   = $('add-rack').value.trim().toUpperCase();

  if (!code || !title || !author) {
    showResult('add-result', '❌ Kode, judul, dan pengarang tidak boleh kosong.', 'error'); return;
  }
  if (isNaN(year) || year < 1000 || year > 9999) {
    showResult('add-result', '❌ Tahun terbit tidak valid (1000–9999).', 'error'); return;
  }
  if (isNaN(stock) || stock < 0) {
    showResult('add-result', '❌ Stok tidak valid (minimal 0).', 'error'); return;
  }
  if (!/^[A-Z][0-9]$/.test(rack)) {
    showResult('add-result', '❌ Format rak salah! Harus 1 huruf kapital + 1 angka (Contoh: A1, B5).', 'error'); return;
  }

  const result = lib.addBook(code, title, author, year, rack, stock);
  if (result.ok) {
    showResult('add-result',
      `✅ Buku ditambahkan ke slot hash <strong>#${result.slot}</strong><br>
       📖 <strong>${title}</strong> — ${author} (${year})<br>
       Kode: <strong>${code.toUpperCase()}</strong> | Stok: ${stock} | Rak: ${rack}`,
      'success');
    $('form-add-book').reset();
    $('add-stock').value = '1';
    toast(`Buku ${code.toUpperCase()} berhasil ditambahkan!`, 'success');
    $('book-count-badge').textContent = lib.getAllSorted().length;
  } else {
    showResult('add-result', `❌ ${result.msg}`, 'error');
  }
});

// ================================================================
//  PAGE: 3. UPDATE STOK
// ================================================================
let _updateTarget = null;

$('btn-find-update').addEventListener('click', () => {
  const code = $('update-code').value.trim();
  if (!code) { showResult('update-result', '❌ Masukkan kode buku terlebih dahulu.', 'error'); return; }
  const book = lib.findBook(code);
  if (!book) {
    showResult('update-result', `❌ Buku '${code.toUpperCase()}' tidak ditemukan.`, 'error');
    $('update-book-preview').classList.add('hidden');
    $('update-controls').style.display = 'none';
    $('btn-do-update').classList.add('hidden');
    _updateTarget = null;
    return;
  }
  _updateTarget = book;
  hideResult('update-result');
  $('update-book-preview').innerHTML =
    `<strong>${book.title}</strong> — ${book.author} (${book.year})<br>
     Kode: <strong>${book.code}</strong> | Rak: <strong>${book.rack}</strong> | Stok saat ini: <strong>${book.stock}</strong>`;
  $('update-book-preview').classList.remove('hidden');
  $('update-controls').style.display = 'grid';
  $('btn-do-update').classList.remove('hidden');
});

$('form-update-stock').addEventListener('submit', (e) => {
  e.preventDefault();
  if (!_updateTarget) return;
  const op     = $('update-op').value;
  const amount = parseInt($('update-amount').value);
  if (isNaN(amount) || amount < 1) {
    showResult('update-result', '❌ Jumlah harus minimal 1.', 'error'); return;
  }
  const delta  = op === 'add' ? amount : -amount;
  const result = lib.updateStock(_updateTarget.code, delta);
  if (result.ok) {
    showResult('update-result',
      `✅ Stok <strong>${_updateTarget.code}</strong> berhasil diperbarui menjadi <strong>${result.stock} unit</strong>.`,
      'success');
    const updated = lib.findBook(_updateTarget.code);
    $('update-book-preview').innerHTML =
      `<strong>${updated.title}</strong> — ${updated.author} (${updated.year})<br>
       Kode: <strong>${updated.code}</strong> | Rak: <strong>${updated.rack}</strong> | Stok saat ini: <strong>${updated.stock}</strong>`;
    toast(`Stok ${_updateTarget.code} → ${result.stock} unit`, 'success');
  } else {
    showResult('update-result', `❌ ${result.msg}`, 'error');
  }
});

// ================================================================
//  PAGE: CARI BUKU
// ================================================================
// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tabId = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.add('active');
  });
});

// Binary Search
$('btn-search-code').addEventListener('click', () => {
  const code = $('search-code-input').value.trim();
  if (!code) { toast('Masukkan kode buku terlebih dahulu.', 'error'); return; }

  const { book, steps, total } = lib.findBookBinary(code);
  const log = $('bs-steps');
  log.classList.remove('hidden');

  let logHTML = `<span class="step-check">[Binary Search] Mencari '${code.toUpperCase()}' dari ${total} buku terurut:</span>\n`;
  steps.forEach(s => {
    if (s.found) {
      logHTML += `<span class="step-found">  ✅ Cek indeks ${s.mid} → kode: ${s.code} ← DITEMUKAN!</span>\n`;
    } else {
      logHTML += `<span class="step-miss">  Cek indeks ${s.mid} → kode: ${s.code}</span>\n`;
    }
  });
  log.innerHTML = logHTML;

  const area = $('search-code-result');
  if (book) {
    area.innerHTML = `
      <div class="book-card">
        <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
          <span class="code-badge">${book.code}</span>
          <span style="font-weight:700;font-size:15px">${book.title}</span>
        </div>
        <div style="color:var(--text-muted);font-size:13px;line-height:2">
          Pengarang: <strong>${book.author}</strong><br>
          Tahun: <strong>${book.year}</strong> &nbsp;|&nbsp;
          Rak: <span class="rack-badge">${book.rack}</span> &nbsp;|&nbsp;
          Stok: ${stockBadge(book.stock)}
        </div>
      </div>`;
  } else {
    area.innerHTML = `<div class="result-box error">❌ Buku '${code.toUpperCase()}' tidak ditemukan.</div>`;
  }
});

$('search-code-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') $('btn-search-code').click();
});

// Trie Autocomplete
$('search-title-input').addEventListener('input', () => {
  const prefix = $('search-title-input').value;
  const list   = $('autocomplete-list');
  if (!prefix.trim()) { list.classList.add('hidden'); return; }

  const titles = lib.findByTitlePrefix(prefix);
  if (!titles.length) { list.classList.add('hidden'); return; }

  list.innerHTML = titles.map(t => `<li data-title="${t}">${t}</li>`).join('');
  list.classList.remove('hidden');
});

$('autocomplete-list').addEventListener('click', (e) => {
  if (e.target.tagName === 'LI') {
    const title = e.target.dataset.title;
    $('search-title-input').value = title;
    $('autocomplete-list').classList.add('hidden');
    renderTitleSearchResults(title);
  }
});

document.addEventListener('click', (e) => {
  if (!e.target.closest('.autocomplete-wrapper')) $('autocomplete-list').classList.add('hidden');
});

$('search-title-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    $('autocomplete-list').classList.add('hidden');
    renderTitleSearchResults($('search-title-input').value);
  }
});

function renderTitleSearchResults(prefix) {
  const books = lib.findBooksByTitlePrefix(prefix);
  const area  = $('search-title-result');
  if (!books.length) {
    area.innerHTML = `<div class="result-box error">❌ Tidak ditemukan judul buku dengan awalan tersebut.</div>`;
    return;
  }
  area.innerHTML = books.map(b => `
    <div class="book-card">
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
        <span class="code-badge">${b.code}</span>
        <span style="font-weight:700;font-size:15px">${b.title}</span>
      </div>
      <div style="color:var(--text-muted);font-size:13px;line-height:2">
        Pengarang: <strong>${b.author}</strong><br>
        Tahun: <strong>${b.year}</strong> &nbsp;|&nbsp;
        Rak: <span class="rack-badge">${b.rack}</span> &nbsp;|&nbsp;
        Stok: ${stockBadge(b.stock)}
      </div>
    </div>`).join('');
}

// ================================================================
//  PAGE: ANTRIAN PINJAM
// ================================================================
function renderQueue() {
  const items = lib._queue.toArray();
  const visual = $('queue-visual');
  $('queue-size-badge').textContent = `${items.length}/${QUEUE_CAP}`;

  if (!items.length) {
    visual.innerHTML = `<div class="queue-empty-msg">📭 Antrian kosong</div>`;
    return;
  }

  visual.innerHTML = items.map((req, i) => {
    const book = lib.findBook(req.bookCode);
    const title = book ? book.title : '?';
    return `
      <div class="queue-item ${i === 0 ? 'first-item' : ''}">
        <span class="queue-pos">${i === 0 ? '→' : i + 1}</span>
        <div style="flex:1;min-width:0">
          <div class="queue-name">${req.memberName}</div>
          <div style="font-size:11px;color:var(--text-dim)">${title}</div>
        </div>
        <span class="queue-book">${req.bookCode}</span>
        <span class="queue-date">${req.date}</span>
      </div>`;
  }).join('');
}

$('form-enqueue').addEventListener('submit', (e) => {
  e.preventDefault();
  const member = $('borrow-member').value.trim();
  const code   = $('borrow-code').value.trim();
  if (!member || !code) {
    showResult('enqueue-result', '❌ Nama anggota dan kode buku tidak boleh kosong.', 'error'); return;
  }
  const result = lib.enqueueBorrow(member, code);
  if (result.ok) {
    showResult('enqueue-result',
      `✅ <strong>${member}</strong> masuk antrian pada posisi <strong>#${result.pos}</strong><br>
       Buku: <span class="code-badge">${code.toUpperCase()}</span>`,
      'success');
    $('borrow-member').value = '';
    $('borrow-code').value   = '';
    renderQueue();
    toast(`${member} masuk antrian peminjaman.`, 'success');
  } else {
    showResult('enqueue-result', `❌ ${result.msg}`, 'error');
  }
});

$('btn-process-borrow').addEventListener('click', () => {
  if (lib._queue.isEmpty()) {
    showResult('process-result', 'ℹ️ Antrian kosong. Tidak ada peminjaman untuk diproses.', 'info'); return;
  }
  const result = lib.processBorrow();
  if (result.ok) {
    showResult('process-result',
      `✅ Peminjaman diproses!<br>
       Anggota: <strong>${result.req.memberName}</strong><br>
       Buku: <span class="code-badge">${result.book.code}</span> ${result.book.title}<br>
       Stok sisa: <strong>${result.book.stock} unit</strong>`,
      'success');
    renderQueue();
    toast(`Peminjaman oleh ${result.req.memberName} berhasil diproses.`, 'success');
  } else {
    showResult('process-result', `❌ ${result.msg}`, 'error');
  }
});

// Tombol "Lihat Riwayat Peminjaman" di sub-menu antrian (setara sub-menu #4 Python)
$('btn-show-borrow-history').addEventListener('click', () => {
  _historyFilter = 'PINJAM';
  document.querySelectorAll('.pill').forEach(p => {
    p.classList.toggle('active', p.dataset.filter === 'PINJAM');
  });
  navigate('history');
});

// ================================================================
//  PAGE: 7. PENGEMBALIAN BUKU
// ================================================================
$('form-return').addEventListener('submit', (e) => {
  e.preventDefault();
  const member = $('return-member').value.trim();
  const code   = $('return-code').value.trim();
  if (!member || !code) {
    showResult('return-result', '❌ Nama dan kode buku tidak boleh kosong.', 'error'); return;
  }
  const result = lib.returnBook(member, code);
  if (result.ok) {
    showResult('return-result',
      `✅ Buku <span class="code-badge">${result.book.code}</span> <strong>${result.book.title}</strong>
       berhasil dikembalikan oleh <strong>${member}</strong>.<br>
       Stok sekarang: <strong>${result.book.stock} unit</strong>.`,
      'success');
    $('form-return').reset();
    toast(`Pengembalian buku ${result.book.code} berhasil!`, 'success');
  } else {
    showResult('return-result', `❌ ${result.msg}`, 'error');
  }
});

// ================================================================
//  PAGE: RIWAYAT
// ================================================================
let _historyFilter = 'PINJAM';

document.querySelectorAll('.pill').forEach(pill => {
  pill.addEventListener('click', () => {
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    _historyFilter = pill.dataset.filter;
    renderHistory(_historyFilter);
  });
});

function renderHistory(filter) {
  const history = lib.getHistory();
  const tbody   = $('history-tbody');
  const entries = Object.entries(history)
    .filter(([, log]) => log.action === filter)
    .sort(([a], [b]) => b.localeCompare(a)); // terbaru dulu

  if (!entries.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Belum ada riwayat ${filter === 'PINJAM' ? 'peminjaman' : 'pengembalian'}.</td></tr>`;
    return;
  }

  tbody.innerHTML = entries.map(([, log], i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${log.date}</td>
      <td>${log.name}</td>
      <td><span class="code-badge">${log.book_code}</span></td>
      <td>
        <span style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;
          background:${log.action === 'PINJAM' ? 'var(--accent-soft)' : 'var(--success-soft)'};
          color:${log.action === 'PINJAM' ? 'var(--accent)' : 'var(--success)'}">
          ${log.action}
        </span>
      </td>
    </tr>`).join('');
}

$('btn-clear-history').addEventListener('click', () => {
  showConfirm('Hapus Semua Riwayat', 'Seluruh riwayat aktivitas akan dihapus permanen. Lanjutkan?', () => {
    localStorage.removeItem(LS_HISTORY);
    renderHistory(_historyFilter);
    toast('Semua riwayat berhasil dihapus.', 'success');
  });
});

// ================================================================
//  INISIALISASI APLIKASI
// ================================================================
(function init() {
  const loaded = lib.load();
  if (!loaded) {
    INITIAL_BOOKS.forEach(b => lib.addBook(b.code, b.title, b.author, b.year, b.rack, b.stock));
    toast('Data awal berhasil dimuat (8 buku).', 'info');
  } else {
    toast('Data berhasil dimuat dari penyimpanan lokal.', 'success');
  }
  navigate('add-book');
})();
