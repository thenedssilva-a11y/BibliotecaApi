/* Access JWT stays in this tab's memory; refresh credential remains HttpOnly in the browser. */
let accessToken = null;
let currentUser = null;
let page = 1;
let totalPages = 1;
let searchTimer = null;
let editingBook = null;

const $ = (selector) => document.querySelector(selector);
const rows = $("#book-rows");
const authOverlay = $("#auth-overlay");
const authMessage = $("#auth-message");
const loginForm = $("#login-form");
const setupForm = $("#setup-form");
const bookOverlay = $("#book-overlay");
const bookForm = $("#book-form");
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const money = (value) => new Intl.NumberFormat("pt-BR", {style:"currency", currency:"BRL"}).format(value);

function csrfCookie() {
  const found = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("csrf_refresh_token="));
  return found ? decodeURIComponent(found.split("=").slice(1).join("=")) : "";
}

async function renewAccess() {
  const csrf = csrfCookie();
  if (!csrf) return false;
  const response = await fetch("/auth/refresh", {method:"POST", credentials:"same-origin", headers:{"X-CSRF-TOKEN":csrf}});
  if (!response.ok) return false;
  const result = await response.json();
  accessToken = result.access_token;
  return true;
}

async function request(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(path, {...options, headers, credentials:"same-origin"});
  if (response.status === 401 && retry && !path.startsWith("/auth/") && await renewAccess()) return request(path, options, false);
  let body = null;
  try { body = await response.json(); } catch { /* Empty body is valid for some responses. */ }
  if (!response.ok) {
    const error = new Error(body?.error?.message || "Não foi possível concluir a solicitação.");
    error.status = response.status;
    error.payload = body;
    throw error;
  }
  return body;
}

function showAuth(message = "", success = false) {
  authMessage.textContent = message;
  authMessage.classList.toggle("success", success);
  authOverlay.hidden = false;
  document.body.classList.add("locked");
}

function enterApp(user) {
  currentUser = user;
  authOverlay.hidden = true;
  document.body.classList.remove("locked");
  $("#profile-name").textContent = user?.nome || "Administrador";
  $("#profile-role").textContent = user?.role === "admin" ? "Administrador" : "Usuário";
  $("#avatar").textContent = (user?.nome || "A").trim().charAt(0).toUpperCase();
  $("#add-book-button").hidden = user?.role !== "admin";
  $("#logout-button").hidden = false;
  loadBooks();
}

function setAuthMode(mode) {
  const isSetup = mode === "setup";
  loginForm.hidden = isSetup;
  setupForm.hidden = !isSetup;
  $("#login-tab").classList.toggle("active", !isSetup);
  $("#setup-tab").classList.toggle("active", isSetup);
  $("#auth-title").textContent = isSetup ? "Configure seu acervo." : "Acesse seu acervo.";
  authMessage.textContent = "";
}

$("#login-tab").addEventListener("click", () => setAuthMode("login"));
$("#setup-tab").addEventListener("click", () => setAuthMode("setup"));

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = loginForm.querySelector("button[type=submit]");
  button.disabled = true;
  authMessage.textContent = "Entrando…";
  try {
    const data = Object.fromEntries(new FormData(loginForm));
    const result = await request("/auth/login", {method:"POST", body:JSON.stringify(data)}, false);
    accessToken = result.access_token;
    enterApp(result.usuario);
    loginForm.reset();
  } catch (error) {
    showAuth(error.message);
  } finally { button.disabled = false; }
});

setupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = setupForm.querySelector("button[type=submit]");
  button.disabled = true;
  authMessage.textContent = "Criando administrador…";
  try {
    const data = Object.fromEntries(new FormData(setupForm));
    await request("/setup/admin", {method:"POST", body:JSON.stringify(data)}, false);
    setupForm.reset();
    setAuthMode("login");
    showAuth("Administrador criado. Agora entre com seu e-mail e senha.", true);
  } catch (error) {
    showAuth(error.message);
  } finally { button.disabled = false; }
});

async function loadBooks() {
  rows.innerHTML = '<tr><td colspan="6" class="empty-row">Carregando catálogo…</td></tr>';
  const [sort, order] = $("#sort-filter").value.split(":");
  const params = new URLSearchParams({page, per_page:20, sort, order});
  const q = $("#search-input").value.trim();
  const category = $("#category-filter").value;
  if (q) params.set("q", q);
  if (category) params.set("categoria", category);
  try {
    const result = await request(`/livros?${params}`);
    totalPages = Math.max(1, result.pages);
    $("#page-label").textContent = page;
    $("#pagination-label").textContent = result.total ? `${(page - 1) * 20 + 1}–${Math.min(page * 20, result.total)} de ${result.total} livros` : "Nenhum livro encontrado";
    $("#result-count").textContent = `${result.total} ${result.total === 1 ? "livro encontrado" : "livros encontrados"}`;
    $("#prev-page").disabled = page <= 1;
    $("#next-page").disabled = page >= totalPages;
    renderBooks(result.items);
    updateStats(result.summary);
    updateCategories(result.categories);
  } catch (error) {
    rows.innerHTML = `<tr><td colspan="6" class="empty-row">${esc(error.message)}</td></tr>`;
    if (error.status === 401) showAuth("Sua sessão expirou. Entre novamente.");
  }
}

function updateStats(summary) {
  $("#stat-titles").textContent = summary.titles;
  $("#stat-units").textContent = summary.units.toLocaleString("pt-BR");
  $("#stat-low").textContent = summary.low_stock;
}

function updateCategories(categories) {
  const select = $("#category-filter");
  const old = select.value;
  select.replaceChildren(new Option("Todas as categorias", ""), ...categories.map((name) => new Option(name, name)));
  if (categories.includes(old)) select.value = old;
}

function renderBooks(books) {
  if (!books.length) {
    rows.innerHTML = '<tr><td colspan="6" class="empty-row">Nenhum resultado com estes filtros.</td></tr>';
    return;
  }
  rows.replaceChildren(...books.map((book) => {
    const row = document.createElement("tr");
    const title = document.createElement("td"); title.className = "book-title";
    title.textContent = book.titulo;
    const isbn = document.createElement("span"); isbn.className = "isbn"; isbn.textContent = book.isbn; title.append(isbn);
    const author = document.createElement("td"); author.textContent = book.autor;
    const category = document.createElement("td"); const badge = document.createElement("span"); badge.className = "category-pill"; badge.textContent = book.categoria; category.append(badge);
    const price = document.createElement("td"); price.className = "price"; price.textContent = money(book.preco);
    const stock = document.createElement("td"); const stockLabel = document.createElement("span"); stockLabel.className = `stock${book.quantidade_estoque <= 3 ? " low" : ""}`; stockLabel.textContent = `${book.quantidade_estoque} un.`; stock.append(stockLabel);
    const actions = document.createElement("td");
    if (currentUser?.role === "admin") {
      const group = document.createElement("div"); group.className = "row-actions";
      group.append(actionButton("↻", "Atualizar estoque", () => changeStock(book)), actionButton("✎", "Editar livro", () => openBookModal(book)), actionButton("×", "Excluir livro", () => deleteBook(book), "delete-button"));
      actions.append(group);
    }
    row.append(title, author, category, price, stock, actions);
    return row;
  }));
}

function actionButton(label, title, onClick, extraClass = "") {
  const button = document.createElement("button"); button.type = "button"; button.className = `icon-button ${extraClass}`; button.textContent = label; button.title = title; button.setAttribute("aria-label", title); button.addEventListener("click", onClick); return button;
}

function toast(message) {
  const node = $("#toast"); node.textContent = message; node.classList.add("show"); window.clearTimeout(toast.timer); toast.timer = window.setTimeout(() => node.classList.remove("show"), 2600);
}

function openBookModal(book = null) {
  editingBook = book;
  bookForm.reset();
  bookForm.elements.id.value = book?.id || "";
  $("#book-modal-title").textContent = book ? "Editar livro" : "Adicionar livro";
  $("#save-book-button").innerHTML = book ? 'Salvar alterações <span>→</span>' : 'Salvar livro <span>→</span>';
  for (const name of ["titulo","autor","isbn","editora","ano_publicacao","categoria","preco","quantidade_estoque","descricao"]) bookForm.elements[name].value = book?.[name] ?? "";
  bookOverlay.hidden = false;
  bookForm.elements.titulo.focus();
}

function closeBookModal() { bookOverlay.hidden = true; editingBook = null; }
$("#add-book-button").addEventListener("click", () => openBookModal());
document.querySelectorAll(".close-modal").forEach((button) => button.addEventListener("click", closeBookModal));
bookOverlay.addEventListener("click", (event) => { if (event.target === bookOverlay) closeBookModal(); });

bookForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(bookForm));
  delete data.id;
  for (const field of ["ano_publicacao", "quantidade_estoque"]) data[field] = Number(data[field]);
  data.preco = Number(data.preco);
  const button = $("#save-book-button"); button.disabled = true;
  try {
    await request(editingBook ? `/livros/${editingBook.id}` : "/livros", {method:editingBook ? "PUT" : "POST", body:JSON.stringify(data)});
    closeBookModal(); toast(editingBook ? "Livro atualizado." : "Livro adicionado ao catálogo."); await loadBooks();
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; }
});

async function changeStock(book) {
  const value = window.prompt(`Nova quantidade em estoque para “${book.titulo}”:`, String(book.quantidade_estoque));
  if (value === null) return;
  if (!/^\d+$/.test(value) || Number(value) > 1000000) { toast("Informe uma quantidade inteira entre 0 e 1.000.000."); return; }
  try { await request(`/livros/${book.id}/estoque`, {method:"PATCH", body:JSON.stringify({quantidade_estoque:Number(value)})}); toast("Estoque atualizado."); await loadBooks(); }
  catch (error) { toast(error.message); }
}

async function deleteBook(book) {
  if (!window.confirm(`Excluir “${book.titulo}” do catálogo?`)) return;
  try { await request(`/livros/${book.id}`, {method:"DELETE"}); toast("Livro excluído."); await loadBooks(); }
  catch (error) { toast(error.message); }
}

$("#search-input").addEventListener("input", () => { window.clearTimeout(searchTimer); searchTimer = window.setTimeout(() => {page = 1; loadBooks();}, 250); });
$("#category-filter").addEventListener("change", () => {page = 1; loadBooks();});
$("#sort-filter").addEventListener("change", () => {page = 1; loadBooks();});
$("#prev-page").addEventListener("click", () => {if (page > 1) {page--; loadBooks();}});
$("#next-page").addEventListener("click", () => {if (page < totalPages) {page++; loadBooks();}});
document.addEventListener("keydown", (event) => { if (event.key === "/" && !["INPUT","TEXTAREA"].includes(document.activeElement.tagName) && authOverlay.hidden && bookOverlay.hidden) { event.preventDefault(); $("#search-input").focus(); } if (event.key === "Escape") closeBookModal(); });

$("#logout-button").addEventListener("click", async () => {
  try { const csrf = csrfCookie(); await fetch("/auth/logout", {method:"POST", credentials:"same-origin", headers:csrf ? {"X-CSRF-TOKEN":csrf} : {}}); } finally {accessToken = null; currentUser = null; $("#logout-button").hidden = true; $("#add-book-button").hidden = true; showAuth("Você saiu do acervo.", true);}
});

$("#footer-date").textContent = new Intl.DateTimeFormat("pt-BR", {month:"long", year:"numeric"}).format(new Date()).toUpperCase();
renewAccess().then(async (ok) => {
  if (ok) {
    try { const user = await request("/auth/me", {}, false); enterApp(user); }
    catch { showAuth(); }
  } else showAuth();
});
