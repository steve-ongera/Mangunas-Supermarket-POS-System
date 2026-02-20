import { useState, useEffect, createContext, useContext } from "react";
import { Routes, Route, Navigate, useNavigate, Link, useLocation } from "react-router-dom";
import axios from "axios";

const API = axios.create({ baseURL: "http://localhost:8000/api" });
API.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("access");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));
  const login = (u, access, refresh) => {
    localStorage.setItem("access", access);
    localStorage.setItem("refresh", refresh);
    localStorage.setItem("user", JSON.stringify(u));
    setUser(u);
  };
  const logout = () => {
    localStorage.clear();
    setUser(null);
  };
  return <AuthCtx.Provider value={{ user, login, logout }}>{children}</AuthCtx.Provider>;
}

function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setErr("");
    try {
      const { data } = await API.post("/auth/login/", form);
      login(data.user, data.access, data.refresh);
      nav("/pos");
    } catch { setErr("Invalid username or password"); }
    setLoading(false);
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-icon">🛒</div>
          <h1>Mangunas</h1>
          <p>Supermarket POS</p>
        </div>
        <form onSubmit={submit}>
          <div className="field">
            <label>Username</label>
            <input value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} required autoFocus />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required />
          </div>
          {err && <div className="err-msg">{err}</div>}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}

const NAV = [
  { to: "/pos", icon: "⊞", label: "POS" },
  { to: "/dashboard", icon: "◈", label: "Dashboard" },
  { to: "/products", icon: "◻", label: "Products" },
  { to: "/orders", icon: "≡", label: "Orders" },
  { to: "/customers", icon: "◎", label: "Customers" },
];

function Layout({ children }) {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sb-icon">🛒</span>
          <span>Mangunas</span>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(n => (
            <Link key={n.to} to={n.to} className={`nav-item${loc.pathname.startsWith(n.to) ? " active" : ""}`}>
              <span className="nav-icon">{n.icon}</span>
              <span>{n.label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-pill">{user?.username?.[0]?.toUpperCase()}</div>
          <span className="user-name">{user?.username}</span>
          <button onClick={() => { logout(); nav("/login"); }} className="logout-btn" title="Logout">⏻</button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}

// ─── Dashboard ──────────────────────────────────────────────────────────────

function Dashboard() {
  const [data, setData] = useState(null);
  useEffect(() => { API.get("/dashboard/").then(r => setData(r.data)); }, []);

  if (!data) return <div className="page-loading">Loading…</div>;

  const stats = [
    { label: "Today's Sales", value: `KSh ${data.today_sales.toLocaleString()}`, color: "#22c55e", icon: "💰" },
    { label: "Orders Today", value: data.today_orders, color: "#3b82f6", icon: "🧾" },
    { label: "Total Products", value: data.total_products, color: "#a855f7", icon: "📦" },
    { label: "Low Stock Items", value: data.low_stock_count, color: "#ef4444", icon: "⚠️" },
  ];

  return (
    <div className="page">
      <div className="page-header"><h2>Dashboard</h2></div>
      <div className="stats-grid">
        {stats.map(s => (
          <div key={s.label} className="stat-card" style={{ "--accent": s.color }}>
            <div className="stat-icon">{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="section-title">Recent Orders</div>
      <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Order #</th><th>Customer</th><th>Cashier</th><th>Total</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {data.recent_orders.map(o => (
              <tr key={o.id}>
                <td><code>{o.order_number}</code></td>
                <td>{o.customer_name || "—"}</td>
                <td>{o.cashier_name}</td>
                <td>KSh {parseFloat(o.total_amount).toLocaleString()}</td>
                <td><span className={`badge badge-${o.status}`}>{o.status}</span></td>
                <td>{new Date(o.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Products Page ───────────────────────────────────────────────────────────

function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editProduct, setEditProduct] = useState(null);
  const [form, setForm] = useState({ name: "", barcode: "", price: "", cost_price: "", stock_quantity: "", category: "", low_stock_threshold: 10 });

  const load = () => {
    const params = {};
    if (search) params.search = search;
    if (catFilter) params.category = catFilter;
    API.get("/products/", { params }).then(r => setProducts(r.data.results || r.data));
  };

  useEffect(() => { load(); }, [search, catFilter]);
  useEffect(() => { API.get("/categories/").then(r => setCategories(r.data.results || r.data)); }, []);

  const openAdd = () => { setEditProduct(null); setForm({ name: "", barcode: "", price: "", cost_price: "", stock_quantity: "", category: "", low_stock_threshold: 10 }); setShowModal(true); };
  const openEdit = (p) => { setEditProduct(p); setForm({ name: p.name, barcode: p.barcode || "", price: p.price, cost_price: p.cost_price, stock_quantity: p.stock_quantity, category: p.category || "", low_stock_threshold: p.low_stock_threshold }); setShowModal(true); };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editProduct) await API.patch(`/products/${editProduct.id}/`, form);
      else await API.post("/products/", form);
      setShowModal(false); load();
    } catch (err) { alert("Error saving product"); }
  };

  const deactivate = async (id) => {
    if (!confirm("Deactivate this product?")) return;
    await API.patch(`/products/${id}/`, { is_active: false });
    load();
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Products</h2>
        <button className="btn-primary" onClick={openAdd}>+ Add Product</button>
      </div>
      <div className="toolbar">
        <input className="search-input" placeholder="Search products…" value={search} onChange={e => setSearch(e.target.value)} />
        <select className="select-input" value={catFilter} onChange={e => setCatFilter(e.target.value)}>
          <option value="">All Categories</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      <div className="products-grid">
        {products.map(p => (
          <div key={p.id} className={`product-card${p.is_low_stock ? " low-stock" : ""}`}>
            <div className="product-name">{p.name}</div>
            <div className="product-cat">{p.category_name}</div>
            <div className="product-price">KSh {parseFloat(p.price).toLocaleString()}</div>
            <div className={`product-stock${p.is_low_stock ? " warning" : ""}`}>Stock: {p.stock_quantity}</div>
            {p.is_low_stock && <div className="low-badge">Low Stock</div>}
            <div className="product-actions">
              <button className="btn-sm" onClick={() => openEdit(p)}>Edit</button>
              <button className="btn-sm danger" onClick={() => deactivate(p.id)}>Remove</button>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal">
            <div className="modal-header"><h3>{editProduct ? "Edit Product" : "Add Product"}</h3><button onClick={() => setShowModal(false)}>✕</button></div>
            <form onSubmit={save} className="modal-form">
              <div className="form-row">
                <div className="field"><label>Name *</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} required /></div>
                <div className="field"><label>Barcode</label><input value={form.barcode} onChange={e => setForm(p => ({ ...p, barcode: e.target.value }))} /></div>
              </div>
              <div className="form-row">
                <div className="field"><label>Selling Price (KSh) *</label><input type="number" step="0.01" value={form.price} onChange={e => setForm(p => ({ ...p, price: e.target.value }))} required /></div>
                <div className="field"><label>Cost Price (KSh)</label><input type="number" step="0.01" value={form.cost_price} onChange={e => setForm(p => ({ ...p, cost_price: e.target.value }))} /></div>
              </div>
              <div className="form-row">
                <div className="field"><label>Stock Qty *</label><input type="number" value={form.stock_quantity} onChange={e => setForm(p => ({ ...p, stock_quantity: e.target.value }))} required /></div>
                <div className="field"><label>Low Stock Threshold</label><input type="number" value={form.low_stock_threshold} onChange={e => setForm(p => ({ ...p, low_stock_threshold: e.target.value }))} /></div>
              </div>
              <div className="field">
                <label>Category</label>
                <select value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}>
                  <option value="">— None —</option>
                  {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── POS Terminal ────────────────────────────────────────────────────────────

function POSTerminal() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState("");
  const [selCat, setSelCat] = useState("");
  const [customer, setCustomer] = useState(null);
  const [custSearch, setCustSearch] = useState("");
  const [custResults, setCustResults] = useState([]);
  const [payModal, setPayModal] = useState(false);
  const [payMethod, setPayMethod] = useState("cash");
  const [cashTendered, setCashTendered] = useState("");
  const [mpesaPhone, setMpesaPhone] = useState("");
  const [mpesaStatus, setMpesaStatus] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [lastReceipt, setLastReceipt] = useState(null);

  useEffect(() => {
    const params = {};
    if (search) params.search = search;
    if (selCat) params.category = selCat;
    API.get("/products/", { params }).then(r => setProducts(r.data.results || r.data));
  }, [search, selCat]);

  useEffect(() => { API.get("/categories/").then(r => setCategories(r.data.results || r.data)); }, []);

  useEffect(() => {
    if (!custSearch) { setCustResults([]); return; }
    const t = setTimeout(() => API.get("/customers/", { params: { search: custSearch } }).then(r => setCustResults(r.data.results || r.data)), 300);
    return () => clearTimeout(t);
  }, [custSearch]);

  const addToCart = (p) => {
    setCart(prev => {
      const ex = prev.find(c => c.id === p.id);
      if (ex) return prev.map(c => c.id === p.id ? { ...c, qty: c.qty + 1 } : c);
      return [...prev, { ...p, qty: 1 }];
    });
  };

  const updateQty = (id, qty) => {
    if (qty <= 0) setCart(prev => prev.filter(c => c.id !== id));
    else setCart(prev => prev.map(c => c.id === id ? { ...c, qty } : c));
  };

  const subtotal = cart.reduce((s, c) => s + parseFloat(c.price) * c.qty, 0);
  const tax = subtotal * 0.16;
  const total = subtotal + tax;
  const change = parseFloat(cashTendered || 0) - total;

  const placeOrder = async () => {
    setProcessing(true);
    try {
      const { data: order } = await API.post("/orders/", {
        customer: customer?.id || null,
        discount_amount: "0.00",
        items: cart.map(c => ({ product: c.id, quantity: c.qty, unit_price: c.price, discount: "0.00" })),
      });

      if (payMethod === "cash") {
        const { data } = await API.post("/payments/cash/", { order_id: order.id, cash_tendered: parseFloat(cashTendered) });
        setLastReceipt({ order: data.order, change: data.change });
        setCart([]); setPayModal(false); setCustomer(null); setCashTendered("");
      } else if (payMethod === "mpesa") {
        const { data } = await API.post("/payments/mpesa/stk-push/", { order_id: order.id, phone_number: mpesaPhone, amount: order.total_amount });
        setMpesaStatus({ checkoutId: data.checkout_request_id, orderId: order.id, message: "STK push sent! Waiting for payment…" });
      }
    } catch (e) {
      alert("Error processing payment: " + (e.response?.data?.error || e.message));
    }
    setProcessing(false);
  };

  const pollMpesa = async () => {
    if (!mpesaStatus?.checkoutId) return;
    try {
      const { data } = await API.get(`/payments/mpesa/query/${mpesaStatus.checkoutId}/`);
      if (data.ResultCode === "0" || data.ResultCode === 0) {
        setMpesaStatus(p => ({ ...p, message: "✅ Payment confirmed!" }));
        setTimeout(() => { setCart([]); setPayModal(false); setCustomer(null); setMpesaPhone(""); setMpesaStatus(null); }, 2000);
      } else {
        setMpesaStatus(p => ({ ...p, message: "Still pending… check your phone." }));
      }
    } catch { setMpesaStatus(p => ({ ...p, message: "Error querying status" })); }
  };

  return (
    <div className="pos-wrap">
      {/* Receipt modal */}
      {lastReceipt && (
        <div className="modal-overlay">
          <div className="modal receipt-modal">
            <div className="receipt-header">
              <div className="receipt-brand">🛒 Mangunas Supermarket</div>
              <div className="receipt-num">Order #{lastReceipt.order.order_number}</div>
              <div className="receipt-date">{new Date(lastReceipt.order.created_at).toLocaleString()}</div>
            </div>
            <div className="receipt-items">
              {lastReceipt.order.items.map(i => (
                <div key={i.id} className="receipt-item">
                  <span>{i.product_name} x{i.quantity}</span>
                  <span>KSh {parseFloat(i.total_price).toFixed(2)}</span>
                </div>
              ))}
            </div>
            <div className="receipt-totals">
              <div className="receipt-row"><span>Subtotal</span><span>KSh {parseFloat(lastReceipt.order.subtotal).toFixed(2)}</span></div>
              <div className="receipt-row"><span>VAT (16%)</span><span>KSh {parseFloat(lastReceipt.order.tax_amount).toFixed(2)}</span></div>
              <div className="receipt-row total-row"><span>TOTAL</span><span>KSh {parseFloat(lastReceipt.order.total_amount).toFixed(2)}</span></div>
              <div className="receipt-row"><span>Change</span><span>KSh {parseFloat(lastReceipt.change).toFixed(2)}</span></div>
            </div>
            <div className="receipt-footer">Thank you for shopping at Mangunas!</div>
            <button className="btn-primary w-full" onClick={() => setLastReceipt(null)}>New Sale</button>
          </div>
        </div>
      )}

      {/* Left: Products */}
      <div className="pos-products">
        <div className="pos-search-bar">
          <input className="search-input" placeholder="Search products or scan barcode…" value={search} onChange={e => setSearch(e.target.value)} autoFocus />
        </div>
        <div className="cat-tabs">
          <button className={`cat-tab${!selCat ? " active" : ""}`} onClick={() => setSelCat("")}>All</button>
          {categories.map(c => <button key={c.id} className={`cat-tab${selCat == c.id ? " active" : ""}`} onClick={() => setSelCat(c.id)}>{c.name}</button>)}
        </div>
        <div className="pos-product-grid">
          {products.map(p => (
            <button key={p.id} className="pos-product-btn" onClick={() => addToCart(p)} disabled={p.stock_quantity <= 0}>
              <div className="ppb-name">{p.name}</div>
              <div className="ppb-price">KSh {parseFloat(p.price).toLocaleString()}</div>
              <div className={`ppb-stock${p.stock_quantity <= 0 ? " out" : p.is_low_stock ? " low" : ""}`}>
                {p.stock_quantity <= 0 ? "Out of stock" : `${p.stock_quantity} left`}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right: Cart */}
      <div className="pos-cart">
        <div className="cart-top">
          <h3>Current Sale</h3>
          <div className="customer-selector">
            <input placeholder="Search customer…" value={custSearch} onChange={e => setCustSearch(e.target.value)} />
            {custResults.length > 0 && (
              <div className="cust-dropdown">
                {custResults.map(c => (
                  <div key={c.id} className="cust-option" onClick={() => { setCustomer(c); setCustSearch(""); setCustResults([]); }}>
                    {c.name} · {c.phone}
                  </div>
                ))}
              </div>
            )}
            {customer && <div className="selected-customer">👤 {customer.name} <button onClick={() => setCustomer(null)}>✕</button></div>}
          </div>
        </div>

        <div className="cart-items">
          {cart.length === 0 && <div className="cart-empty">Tap products to add them here</div>}
          {cart.map(item => (
            <div key={item.id} className="cart-item">
              <div className="ci-name">{item.name}</div>
              <div className="ci-controls">
                <button onClick={() => updateQty(item.id, item.qty - 1)}>−</button>
                <span>{item.qty}</span>
                <button onClick={() => updateQty(item.id, item.qty + 1)}>+</button>
              </div>
              <div className="ci-total">KSh {(parseFloat(item.price) * item.qty).toFixed(2)}</div>
              <button className="ci-remove" onClick={() => updateQty(item.id, 0)}>✕</button>
            </div>
          ))}
        </div>

        <div className="cart-totals">
          <div className="ct-row"><span>Subtotal</span><span>KSh {subtotal.toFixed(2)}</span></div>
          <div className="ct-row"><span>VAT (16%)</span><span>KSh {tax.toFixed(2)}</span></div>
          <div className="ct-row ct-total"><span>TOTAL</span><span>KSh {total.toFixed(2)}</span></div>
        </div>

        <button className="btn-checkout" disabled={cart.length === 0} onClick={() => setPayModal(true)}>
          Checkout →
        </button>

        <button className="btn-clear" onClick={() => setCart([])}>Clear Cart</button>
      </div>

      {/* Payment Modal */}
      {payModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setPayModal(false)}>
          <div className="modal pay-modal">
            <div className="modal-header"><h3>Payment — KSh {total.toFixed(2)}</h3><button onClick={() => setPayModal(false)}>✕</button></div>

            <div className="pay-methods">
              {["cash", "mpesa"].map(m => (
                <button key={m} className={`pay-method-btn${payMethod === m ? " active" : ""}`} onClick={() => setPayMethod(m)}>
                  {m === "cash" ? "💵 Cash" : "📱 M-Pesa"}
                </button>
              ))}
            </div>

            {payMethod === "cash" && (
              <div className="pay-cash">
                <div className="field"><label>Cash Tendered (KSh)</label>
                  <input type="number" step="0.01" min={total} value={cashTendered} onChange={e => setCashTendered(e.target.value)} autoFocus /></div>
                {cashTendered && <div className="change-display">Change: KSh {Math.max(change, 0).toFixed(2)}</div>}
                <div className="quick-cash">
                  {[500, 1000, 2000, 5000].map(v => (
                    <button key={v} className="btn-sm" onClick={() => setCashTendered(v)}>KSh {v}</button>
                  ))}
                  <button className="btn-sm" onClick={() => setCashTendered(Math.ceil(total / 50) * 50)}>Exact</button>
                </div>
              </div>
            )}

            {payMethod === "mpesa" && (
              <div className="pay-mpesa">
                {!mpesaStatus ? (
                  <>
                    <div className="field"><label>M-Pesa Phone Number</label>
                      <input placeholder="07XXXXXXXX" value={mpesaPhone} onChange={e => setMpesaPhone(e.target.value)} /></div>
                    <p className="mpesa-hint">Customer will receive an STK push on their phone</p>
                  </>
                ) : (
                  <div className="mpesa-status">
                    <div className="mpesa-msg">{mpesaStatus.message}</div>
                    <button className="btn-sm" onClick={pollMpesa}>Check Status</button>
                  </div>
                )}
              </div>
            )}

            <div className="modal-footer">
              <button className="btn-ghost" onClick={() => setPayModal(false)}>Cancel</button>
              {!mpesaStatus && (
                <button className="btn-primary" onClick={placeOrder} disabled={processing || (payMethod === "cash" && !cashTendered) || (payMethod === "mpesa" && !mpesaPhone)}>
                  {processing ? "Processing…" : "Confirm Payment"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Orders Page ─────────────────────────────────────────────────────────────

function Orders() {
  const [orders, setOrders] = useState([]);
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const params = {};
    if (status) params.status = status;
    API.get("/orders/", { params }).then(r => setOrders(r.data.results || r.data));
  }, [status]);

  return (
    <div className="page">
      <div className="page-header"><h2>Orders</h2></div>
      <div className="toolbar">
        <select className="select-input" value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All Statuses</option>
          {["pending", "completed", "cancelled", "refunded"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Order #</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Status</th><th>Date</th><th></th></tr></thead>
          <tbody>
            {orders.map(o => (
              <tr key={o.id} className="clickable" onClick={() => setSelected(o)}>
                <td><code>{o.order_number}</code></td>
                <td>{o.customer_name || "Walk-in"}</td>
                <td>{o.items?.length || 0}</td>
                <td>KSh {parseFloat(o.total_amount).toLocaleString()}</td>
                <td>{o.payments?.[0]?.method?.toUpperCase() || "—"}</td>
                <td><span className={`badge badge-${o.status}`}>{o.status}</span></td>
                <td>{new Date(o.created_at).toLocaleDateString()}</td>
                <td><button className="btn-sm">View</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setSelected(null)}>
          <div className="modal order-detail-modal">
            <div className="modal-header"><h3>Order #{selected.order_number}</h3><button onClick={() => setSelected(null)}>✕</button></div>
            <div className="order-detail">
              <div className="od-meta">
                <span>Customer: {selected.customer_name || "Walk-in"}</span>
                <span>Cashier: {selected.cashier_name}</span>
                <span className={`badge badge-${selected.status}`}>{selected.status}</span>
              </div>
              <table className="data-table">
                <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead>
                <tbody>
                  {selected.items?.map(i => (
                    <tr key={i.id}><td>{i.product_name}</td><td>{i.quantity}</td><td>KSh {parseFloat(i.unit_price).toFixed(2)}</td><td>KSh {parseFloat(i.total_price).toFixed(2)}</td></tr>
                  ))}
                </tbody>
              </table>
              <div className="od-totals">
                <span>Subtotal: KSh {parseFloat(selected.subtotal).toFixed(2)}</span>
                <span>VAT: KSh {parseFloat(selected.tax_amount).toFixed(2)}</span>
                <strong>Total: KSh {parseFloat(selected.total_amount).toFixed(2)}</strong>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Customers Page ──────────────────────────────────────────────────────────

function Customers() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", email: "" });

  const load = () => {
    const params = {};
    if (search) params.search = search;
    API.get("/customers/", { params }).then(r => setCustomers(r.data.results || r.data));
  };

  useEffect(() => { load(); }, [search]);

  const save = async (e) => {
    e.preventDefault();
    await API.post("/customers/", form);
    setShowModal(false); load();
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Customers</h2>
        <button className="btn-primary" onClick={() => { setForm({ name: "", phone: "", email: "" }); setShowModal(true); }}>+ Add Customer</button>
      </div>
      <div className="toolbar">
        <input className="search-input" placeholder="Search by name…" value={search} onChange={e => setSearch(e.target.value)} />
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Loyalty Points</th><th>Member Since</th></tr></thead>
          <tbody>
            {customers.map(c => (
              <tr key={c.id}>
                <td><strong>{c.name}</strong></td>
                <td>{c.phone || "—"}</td>
                <td>{c.email || "—"}</td>
                <td><span className="points-badge">{c.loyalty_points} pts</span></td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal">
            <div className="modal-header"><h3>Add Customer</h3><button onClick={() => setShowModal(false)}>✕</button></div>
            <form onSubmit={save} className="modal-form">
              <div className="field"><label>Full Name *</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} required /></div>
              <div className="field"><label>Phone (for M-Pesa)</label><input value={form.phone} onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} /></div>
              <div className="field"><label>Email</label><input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} /></div>
              <div className="modal-footer">
                <button type="button" className="btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── App Root ─────────────────────────────────────────────────────────────────

function PrivateRoute({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={
          <PrivateRoute>
            <Layout>
              <Routes>
                <Route path="/pos" element={<POSTerminal />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/products" element={<Products />} />
                <Route path="/orders" element={<Orders />} />
                <Route path="/customers" element={<Customers />} />
                <Route path="/" element={<Navigate to="/pos" replace />} />
              </Routes>
            </Layout>
          </PrivateRoute>
        } />
      </Routes>
    </AuthProvider>
  );
}